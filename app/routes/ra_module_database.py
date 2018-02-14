from flask import Blueprint
from modules.db import blob_db_enqueue

bp_ra_db = Blueprint('reactapp_module_database', __name__)


@bp_ra_db.route('/api/v0/newdatabasestatus', methods=['POST'])
def handle_group_comparison_submission():
    jobid = blob_db_enqueue()
    return jobid
