import os
import tarfile
import zipfile
import redis
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_recaptcha import ReCaptcha
from werkzeug.utils import secure_filename
from routes.file_utils import fix_uri, handle_tar, handle_zip
from modules.gc import blob_gc_enqueue
from modules.pan_spfy import spfy
from routes.ra_posts import handle_groupresults, handle_singleton
from middleware.api import subtyping_dependencies

bp_ra_pan = Blueprint('reactapp_pan', __name__)


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


@bp_ra_pan.route('/api/v0/panseq', methods=['POST'])
def pan_upload():
    print('james_`debug : found the correct route')
    recaptcha = ReCaptcha(app=current_app)
    if recaptcha.verify():
        form = request.form
        options = {'pi': 90, 'pan': True, 'amr': False, 'vf': False, 'serotype': False, 'bulk': False}
        # defaults


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
                if key == 'options.bulk':
                    options['bulk'] = value
            else:
                if key == 'options.pi':
                    options['pi'] = int(value)

        # get a list of files submitted
        uploaded_files = request.files.getlist("file")

        # set up constants for identifying this sessions
        now = datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        jobs_dict = {}
        print('james_debug : entering for loop')
        print('james_debug : uploaded files : ' + str(uploaded_files))
        file_list = []
        for file in uploaded_files:
            print('james_debug : file: ' + str(file))
            if file:
                # for saving file
                filename = os.path.join(current_app.config[
                                            'DATASTORE'], now + '-' + secure_filename(file.filename))
                file.save(filename)
                # print 'Uploaded File Saved at', str(filename)

                if tarfile.is_tarfile(filename):
                    # set filename to dir for spfy call
                    filename = handle_tar(filename, now)
                elif zipfile.is_zipfile(filename):
                    filename = handle_zip(filename, now)

                print('james_debug : filename: ' + str(filename))
                if not options['pan']:
                    # for enqueing task
                    jobs_enqueued = spfy(
                        {'i': filename, 'pi': options['pi'], 'options': options})
                    jobs_dict.update(jobs_enqueued)
                else:
                    file_list.append(filename)

        # new in 4.2.0
        if options['pan']:
            jobs_enqueued = spfy({'i': file_list, 'pi': options['pi'], 'options': options})
            jobs_dict.update(jobs_enqueued)

        print 'upload(): all files enqueued, returning...'
        # if groupresults:
        #    return jsonify(handle_groupresults(jobs_dict))
        # else:
        print('james_debug: upload return: ' + str(jobs_dict))
        return jsonify(jobs_dict)
    else:
        return "Captcha Failed Verification", 500
