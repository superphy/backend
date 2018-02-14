import redis
from ast import literal_eval
from flask import Blueprint, request, jsonify, current_app
from routes.job_utils import fetch_job

bp_ra_statuses = Blueprint('reactapp_statuses', __name__)


# new to 4.2.0
def merge_job_results(jobs_dict, redis_connection):
    """
    Appends all results together and returns it.
    We don't do this while retriving job statuses as in most checks, the jobs
    wont all be finished
    Note: written for lists atm. (ie. only for Subtyping)
    """
    r = []
    for key in jobs_dict:
        job = fetch_job(key, redis_connection)
        if job.is_finished:
            res = job.result
            # we check for type of result as we're not returning
            # Quality Control or ID Reservation results
            # print type(res)
            if type(res) is list:
                r += job.result
        else:
            return 'ERROR: merge_job_results() was called when all jobs werent complete', 415
    return r


# new to 4.2.0
def job_status_reactapp_grouped(job_id, redis_connection):
    """
    Retrieves a dictionary of job_id from Redis (not RQ) and checks
    status of all jobs
    Returns the complete result only if all jobs are finished
    """
    # Retrieves jobs_dict
    jobs_dict = redis_connection.get(job_id)
    # redis-py returns a string by default
    # we cast this using ast.literal_eval()
    # the alt. is to set a response callback via redis_connection.set_response_callback()
    jobs_dict = literal_eval(jobs_dict)
    # print jobs_dict
    # if any job in a grouped job fails, immediately return
    # otherwise, check that all jobs are finished (pending = False)
    # before merging the job results
    pending = False
    for key in jobs_dict:
        key = str(key)
        # print key
        job = fetch_job(key, redis_connection)
        if job.is_failed:
            print "job_status_reactapp_grouped(): job failed " + job_id
            return jsonify(job.exc_info)
        elif not job.is_finished:
            pending = True
    if pending:
        return jsonify("pending")
    else:
        # if you've gotten to this point, then all jobs are finished
        return jsonify(merge_job_results(jobs_dict, redis_connection))


@bp_ra_statuses.route('/api/v0/results/<job_id>')
def job_status_reactapp(job_id):
    """
    This provides an endpoint for the reactapp to poll results. We leave job_status() intact to maintain backwards compatibility with the AngularJS app.
    """
    # start a redis connection
    redis_url = current_app.config['REDIS_URL']
    redis_connection = redis.from_url(redis_url)
    # new to 4.2.0
    # check if the job_id is of the new format and should be handled diff
    if job_id.startswith('blob'):
        return job_status_reactapp_grouped(job_id, redis_connection)
    else:
        # old code
        job = fetch_job(job_id, redis_connection)
        if job.is_finished:
            r = job.result
            # subtyping results come in the form of a list and must
            # be conv to json otherwise, you get a 500 error (isa)
            if type(r) is list:
                return jsonify(r)
            # fishers results come in the form of a df.to_json object
            # and should be returned directly
            else:
                return job.result
        elif job.is_failed:
            print 'job_status_reactapp(): job failed ' + job_id
            return jsonify(job.exc_info)
        else:
            return jsonify("pending")
