import os
from flask import Blueprint, request, current_app, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from modules.meta import blob_meta_enqueue

bp_ra_meta = Blueprint('reactapp_module_metadata', __name__)


@bp_ra_meta.route('/api/v0/uploadmetadata', methods=['POST'])
def uploadmetadata():
    # get a list of files submitted
    uploaded_files = request.files.getlist("file")
    print 'upload(): about to enqueue files'
    # set up constants for identifying this sessions
    now = datetime.now()
    now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
    # we expect only 1 file
    for file in uploaded_files:
        if file:
            # for saving file
            filename = os.path.join(current_app.config[
                                        'DATASTORE'], now + '-' + secure_filename(file.filename))
            file.save(filename)
            # for enqueing task
            jobid = blob_meta_enqueue(filename)
            return jobid
    return 'Couldnt enqueue job', 500


@bp_ra_meta.route('/api/v0/get_metadata_example.xlsx', methods=['GET'])
def get_example():
    filename = 'example_metadata.xlsx'
    return send_file('static/' + filename, attachment_filename=filename)
