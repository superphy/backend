import logging
import config
import redis
from rq import Queue
from modules.dbsearch.search_queries import  search_accession
from modules.loggingFunctions import initialize_logging

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
priority_q = Queue('priority', connection=redis_conn, default_timeout=config.DEFAULT_TIMEOUT)

def blob_search_enqueue(s):
    job_db = priority_q.enqueue(
        search_accession,
        s,
        result_ttl=-1)
    log.info('JOB ID IS: ' + job_db.get_id())
    return job_db.get_id()
