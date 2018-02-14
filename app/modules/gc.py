import logging
import config
import redis
from rq import Queue
from modules.comparisons.groupcomparisons import groupcomparisons
from modules.loggingFunctions import initialize_logging

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
priority_q = Queue('priority', connection=redis_conn, default_timeout=600)


def blob_gc_enqueue(query, target):
    job_gc = priority_q.enqueue(groupcomparisons, query, target, result_ttl=-1)
    log.info('JOB ID IS: ' + job_gc.get_id())
    return job_gc.get_id()
