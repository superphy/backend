import os
import tarfile
import zipfile
from datetime import datetime
# flask/external lib
from flask import Blueprint, render_template, request, jsonify, current_app, g, url_for, redirect
from werkzeug.utils import secure_filename
from flask_recaptcha import ReCaptcha
# spfy code
from modules.spfy import spfy
from routes.file_utils import handle_tar, handle_zip, fix_uri
from routes.job_utils import fetch_job

bp = Blueprint('main', __name__)

@bp.route('/results/<job_id>')
def job_status(job_id):
    job = fetch_job(job_id)
    if job.is_finished:
        return jsonify(job.result)
    elif job.is_failed:
        return job.exc_info, 415
    else:
        return "Still pending", 202

# this is the standard route in spfy
@bp.route('/upload', methods=['POST'])
def upload():
    recaptcha = ReCaptcha(app=current_app)
    if recaptcha.verify():
        form = request.form
        options = {}
        #defaults
        options['amr']=True
        options['vf']=True
        options['serotype']=True
        options['pi']=90

	# for compat w 4.3.3
	options['bulk'] = False

        # processing form data
        for key, value in form.items():
            #we need to convert lower-case true/false in js to upper case in python
                #remember, we also have numbers
            if not value.isdigit():
                if value.lower() == 'false':
                    value = False
                else:
                    value = True
                if key == 'options.amr':
                    options['amr']=value
                if key == 'options.vf':
                    options['vf']=value
                if key == 'options.serotype':
                    options['serotype']=value
            else:
                if key =='options.pi':
                    options['pi']=int(value)

        # get a list of files submitted
        uploaded_files = request.files.getlist("file")
        print uploaded_files

        #set up constants for identifying this sessions
        now = datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        jobs_dict = {}

        for file in uploaded_files:
            if file:
                # for saving file
                filename = os.path.join(current_app.config[
                                        'DATASTORE'], now + '-' + secure_filename(file.filename))
                file.save(filename)
                print 'IVE SAVED YO FILE AT', str(filename)

                if tarfile.is_tarfile(filename):
                    # set filename to dir for spfy call
                    filename = handle_tar(filename, now)
                elif zipfile.is_zipfile(filename):
                    filename = handle_zip(filename, now)

                # for enqueing task
                jobs_enqueued = spfy(
                    {'i': filename, 'disable_serotype': False, 'disable_amr': False, 'disable_vf': False, 'pi':options['pi'], 'options':options})
                jobs_dict.update(jobs_enqueued)
        return jsonify(jobs_dict)
    else:
        return "Captcha Failed Verification", 500

@bp.route('/', methods=['GET', 'POST'])
def index():
    return render_template("index.html")
