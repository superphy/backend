import os
import tarfile
import zipfile
import redis

import tempfile
import time

import flask
import werkzeug

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_recaptcha import ReCaptcha
from werkzeug.utils import secure_filename
from routes.file_utils import fix_uri, handle_tar, handle_zip
from modules.gc import blob_gc_enqueue
from modules.spfy import spfy
from middleware.api import subtyping_dependencies

bp_ra_posts = Blueprint('reactapp_posts', __name__)


# for Subtyping module
def handle_groupresults(jobs_dict):
    """
    if we're grouping results for the Front-End
    take all jobs in jobs_dict and store it in Redis (not RQ)
    respond with a key to fetch this jobs_dict from Redis
    relies on a new check in /results/<job_id> which is able to poll RQ
    tasks on behalf of the front-end
        Args:
            jobs_dict (dict): a dictionary where job ids are the keys and
                the values are also dictionaries with keys 'analysis' and 'file'
        Return:
            (dict): a dictionary with key as novel jobid of form 'blob' + hash
                meant to be parsable by same code as for old, non-grouped ver
    """
    print 'handle_groupresults(): started'
    # generate a novel job id
    # we prepend 'blob' so the /results path can tell its our custom object
    # and shouldnt be retrieved from RQ
    job_id = 'blob' + str(hash(str(jobs_dict)))
    # start a redis connection
    redis_url = current_app.config['REDIS_URL']
    redis_connection = redis.from_url(redis_url)
    # with redis.from_url(redis_url) as redis_connection:
    # set the job_id: jobs_dict pair in Redis
    redis_connection.set(job_id, jobs_dict)
    # create a similar structure to the old return
    d = {job_id: {}}
    d[job_id]['analysis'] = "Subtyping"
    st = set()
    for key in jobs_dict:
        st.add(jobs_dict[key]['file'])
    s = ''

    for f in st:
        s += f + ' '
    d[job_id]['file'] = s
    print 'handle_groupresults(): finished'
    return d


# for Subtyping module
def create_blob_id(f, analysis, blob_dict):
    """
    Connects to Redis and creats a blob id which is the key to a dict of
    the three params.
    Return:
        (dict) : a blob id that mimicks the dict form of a regular RQ id
        ex.
        {blob-2017-06-14-16-11-46-159226-5517466316371560478:
            {
             "analysis": "Virulence Factors and Serotype",
             "file": "/datastore/2017-06-14-21-26-43-375215-GCA_001891695.1_ASM189169v1_genomic.fna"
             }
        }
    """
    # generate a novel job id
    # we prepend 'blob' so the /results path can tell its our custom object
    # and shouldnt be retrieved via RQ
    blob_id = 'blob-' + datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f") + '-' + str(hash(str(blob_dict)))
    # start a redis connection
    redis_url = current_app.config['REDIS_URL']
    redis_connection = redis.from_url(redis_url)
    # with redis.from_url(redis_url) as redis_connection:
    # set the job_id: jobs_dict pair in Redis
    redis_connection.set(blob_id, blob_dict)
    # create a similar structure to the old return
    d = {blob_id: {}}
    d[blob_id]['analysis'] = analysis
    d[blob_id]['file'] = f
    return d


# for Subtyping module
def handle_singleton(jobs_dict):
    """
    Takes the jobs_dict dict and creates "blob" jobs which have the QC/ID
    Reservation job ids attached to it. This allows the front-end to poll this
    "blob" + hash job and the back-end (here) will handle checking if dependencies
    failed.
    Groups by filename and by analysis: so for a Serotype/VF and a AMR job,
    will return two "blob" ids which have the corresponding QC/ID tasks added
    to both. Also will then group by file names: so, multiple files with multiple
    jobs return a multiplicative number of "blob" ids. For example, 3 files,
    each with a Serotype/VF and a AMR job (2 jobs ea) will return 6 "blob" ids.
    """
    # create a dictionary of file names to append a list of relavant job hashes
    by_file = {}
    # a key should be a job id
    for key in jobs_dict:
        # we're inverting the structure of jobs_dict here
        # have we encountered this file before?
        f = jobs_dict[key]['file']
        if f not in by_file:
            # create a empty list using the filename as the key
            by_file[f] = {}
        # it's important we maintain the structure of jobs_dict
        # so that when it comes to polling 'blob' ids everything
        # works as expected
        by_file[f].update({key: jobs_dict[key]})
    # after this for loop, we should now have a list of dictionaries
    # where the filename is the key to a group
    # something like
    # {"/datastore/2017-06-14-21-26-43-375215-GCA_001683595.1_NGF2_genomic.fna":
    #     { "16515ba5-040d-4315-9c88-a3bf5bfbe84e": {
    #         "analysis": "Quality Control",
    #         "file": "/datastore/2017-06-14-21-26-43-375215-GCA_001683595.1_NGF2_genomic.fna"
    #       }, "9b043d55-cb16-46bd-b086-d2a11c053b54": {
    #         "analysis": "Antimicrobial Resistance",
    #         "file": "/datastore/2017-06-14-21-26-43-375215-GCA_001683595.1_NGF2_genomic.fna"
    #       }, "aa10aedc-c7c2-4fd9-8756-a907ea45382a": {
    #         "analysis": "ID Reservation",
    #         "file": "/datastore/2017-06-14-21-26-43-375215-GCA_001683595.1_NGF2_genomic.fna"
    #       },
    #       "c96619b8-b089-4a3a-8dd2-b09b5d5e38e9": {
    #         "analysis": "Virulence Factors and Serotype",
    #         "file": "/datastore/2017-06-14-21-26-43-375215-GCA_001683595.1_NGF2_genomic.fna"
    #       }
    #     }
    # }
    # create a blob_ids dict to return
    blob_ids = {}
    # step through the by_file dict
    for f in by_file:
        # step through the job Ids and figure out which is QC and which is ID
        qc = ''
        idr = ''
        for jobId in by_file[f]:
            analysis = by_file[f][jobId]['analysis']
            if analysis == "Quality Control":
                qc = jobId
            elif analysis == "ID Reservation":
                idr = jobId
        # go again and find there not QC or ID reservation and create blob ids
        for jobId in by_file[f]:
            analysis = by_file[f][jobId]['analysis']
            # look for some analysis name that isn't a dependencies
            if analysis not in subtyping_dependencies:
                # create the blob dict to be stored in redis
                blob_dict = {jobId: by_file[f][jobId]}
                blob_dict.update({qc: by_file[f][qc]})
                blob_dict.update({idr: by_file[f][idr]})
                blob_ids.update(create_blob_id(f, analysis, blob_dict))
    return blob_ids


# for Subtyping module
# the /api/v0 prefix is set to allow CORS for any postfix
@bp_ra_posts.route('/api/v0/upload', methods=['POST'])
def upload():
    recaptcha = ReCaptcha(app=current_app)
    if recaptcha.verify():
        # old file saving
        form = request.form
        options = {'amr': True, 'vf': True, 'serotype': True, 'pi': 90, 'pan': True}
        # defaults
        # new to 4.2.0
        # we consider False as default as the front-end should override this
        # to use the new feature
        groupresults = False
        # new to 4.3.3
        # allows bulk uploading where results are not returned to user
        # only the blobid to check statuses is returned (ie. don't run beautify)
        options['bulk'] = False

        # processing form data
        for key, value in form.items():
            # we need to convert lower-case true/false in js to upper case in python
            # remember, we also have numbers
            if not value.isdigit():
                if value.lower() == 'false':
                    value = False
                else:
                    value = True
                if key == 'options.amr':
                    options['amr'] = value
                if key == 'options.vf':
                    options['vf'] = value
                if key == 'options.serotype':
                    options['serotype'] = value
                if key == 'options.groupresults':
                    groupresults = value
                if key == 'options.groupresults':
                    groupresults = value
                if key == 'options.stx1':
                    options['stx1'] = value
                if key == 'options.stx2':
                    options['stx2'] = value
                if key == 'options.eae':
                    options['eae'] = value
                if key == 'options.bulk':
                    options['bulk'] = value
            else:
                if key == 'options.pi':
                    options['pi'] = int(value)
                if key == 'options.prob':
                    options['prob'] = float(value)

        # get a list of files submitted
        uploaded_files = request.files.getlist("file")
        print uploaded_files

        print 'upload(): about to enqueue files'
        # set up constants for identifying this sessions
        now = datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        jobs_dict = {}

        for file in uploaded_files:
            if file:
                # for saving file
                filename = os.path.join(current_app.config[
                                            'DATASTORE'], now + '-' + secure_filename(file.filename))
                file.save(filename)
                print 'Uploaded File Saved at', str(filename)

                if tarfile.is_tarfile(filename):
                    # set filename to dir for spfy call
                    filename = handle_tar(filename, now)
                elif zipfile.is_zipfile(filename):
                    filename = handle_zip(filename, now)

                # for enqueing task
                jobs_enqueued = spfy(
                    {'i': filename, 'pi': options['pi'], 'options': options})
                jobs_dict.update(jobs_enqueued)
        # new in 4.2.0
        print 'upload(): all files enqueued, returning...'
        if groupresults:
            return jsonify(handle_groupresults(jobs_dict))
        else:
            return jsonify(handle_singleton(jobs_dict))
    else:
        return "Captcha Failed Verification", 500


# this is for the Group Comparisons (Fishers) module
@bp_ra_posts.route('/api/v0/newgroupcomparison', methods=['POST'])
def handle_group_comparison_submission():
    query = request.json['groups']
    target = request.json['target']
    jobid = blob_gc_enqueue(query, target)
    return jobid
