import logging
import config
import redis
from rq import Queue
from modules.metadata.metadata import upload_metadata
from modules.loggingFunctions import initialize_logging

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
multiples_q = Queue('multiples', connection=redis_conn, default_timeout=config.DEFAULT_TIMEOUT)


def blob_meta_enqueue(csv_file):
    job_meta = multiples_q.enqueue(upload_metadata, csv_file, result_ttl=-1)
    log.info('JOB ID IS: ' + job_meta.get_id())
    return job_meta.get_id()
