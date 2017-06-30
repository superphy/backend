#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

import os

import redis
import config

from flask import current_app

# Redis Queue
from redis import Redis
from rq import Queue

# other libraries for rdflib
from rdflib import Graph

from modules.qc.qc import qc
from modules.blazeUploader.reserve_id import write_reserve_id
from modules.ectyper.call_ectyper import call_ectyper
from modules.amr.amr import amr
from modules.amr.amr_to_dict import amr_to_dict
from modules.beautify.beautify import beautify
from modules.turtleGrapher.datastruct_savvy import datastruct_savvy
from modules.turtleGrapher.turtle_grapher import turtle_grapher


# the only ONE time for global variables
# when naming queues, make sure you actually set a worker to listen to that queue
# we use the high priority queue for things that should be immediately
# returned to the user
redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
singles_q = Queue('singles', connection=redis_conn)
multiples_q = Queue('multiples', connection=redis_conn,default_timeout=config.DEFAULT_TIMEOUT)
blazegraph_q = Queue('blazegraph', connection=redis_conn)
if config.BACKLOG_ENABLED:
    # backlog queues
    backlog_singles_q = Queue('backlog_singles', connection=redis_conn)
    backlog_multiples_q = Queue('backlog_multiples', connection=redis_conn,default_timeout=config.DEFAULT_TIMEOUT)

def blob_savvy_enqueue(single_dict):
    '''
    Handles enqueueing of single file to multiple queues.
    :param f: a fasta file
    :param single_dict: single dictionary of arguments
    :return: dictionary with jobs ids and relevant headers
    '''
    jobs = {}
    query_file = single_dict['i']

    job_qc = multiples_q.enqueue(qc, query_file, result_ttl=-1)
    job_id = blazegraph_q.enqueue(write_reserve_id, query_file, depends_on=job_qc, result_ttl=-1)

    #### ECTYPER PIPELINE
    def ectyper_pipeline(singles, multiples):
        # the ectyper call is special in that it requires the entire arguments  to decide whether to carry the serotype option flag, virulance factors option flag, and percent identity field
        job_ectyper = singles.enqueue(call_ectyper, single_dict, depends_on=job_id)
        # after this call, the result is stored in Blazegraph
        job_ectyper_datastruct = multiples.enqueue(datastruct_savvy, query_file, query_file + '_id.txt', query_file + '_ectyper.p', depends_on=job_ectyper)
        # only bother parsing into json if user has requested either vf or serotype
        job_ectyper_beautify = multiples.enqueue(beautify, single_dict,query_file + '_ectyper.p', depends_on=job_ectyper, result_ttl=-1)
        return {'job_ectyper': job_ectyper, 'job_ectyper_datastruct' : job_ectyper_datastruct, 'job_ectyper_beautify': job_ectyper_beautify}

    # if user selected any ectyper-dependent options on the front-end
    if single_dict['options']['vf'] or single_dict['options']['serotype']:
        ectyper_jobs = ectyper_pipeline(singles_q, multiples_q)
        job_ectyper = ectyper_jobs['job_ectyper']
        job_ectyper_datastruct = ectyper_jobs['job_ectyper_datastruct']
        job_ectyper_beautify = ectyper_jobs['job_ectyper_beautify']
    # or if the backlog queue is enabled
    elif config.BACKLOG_ENABLED:
        # just enqueue the jobs, we don't care about returning them
        ectyper_pipeline(backlog_singles_q, backlog_multiples_q)
    #### END ECTYPER PIPELINE

    #### AMR PIPELINE
    def amr_pipeline(multiples):
        job_amr = multiples_q.enqueue(amr, query_file, depends_on=job_id)
        job_amr_dict = multiples_q.enqueue(amr_to_dict, query_file + '_rgi.tsv', depends_on=job_amr)
        # this uploads result to blazegraph
        job_amr_datastruct = multiples_q.enqueue(datastruct_savvy, query_file, query_file + '_id.txt', query_file + '_rgi.tsv_rgi.p', depends_on=job_amr_dict)
        job_amr_beautify = multiples_q.enqueue(beautify, single_dict, query_file + '_rgi.tsv_rgi.p', depends_on=job_amr_dict, result_ttl=-1)
        return {'job_amr': job_amr, 'job_amr_dict':job_amr_dict, 'job_amr_datastruct':job_amr_datastruct, 'job_amr_beautify':job_amr_beautify}

    if single_dict['options']['amr']:
        amr_jobs = amr_pipeline(multiples_q)
        job_amr = amr_jobs['job_amr']
        job_amr_dict = amr_jobs['job_amr_dict']
        job_amr_datastruct = amr_jobs['job_amr_datastruct']
        job_amr_beautify = amr_jobs['job_amr_beautify']
    elif config.BACKLOG_ENABLED:
        amr_pipeline(backlog_multiples_q)
    #### END AMR PIPELINE

    # the base file data for blazegraph
    job_turtle = multiples_q.enqueue(turtle_grapher, query_file, depends_on=job_qc)

    jobs[job_qc.get_id()] = {'file': single_dict['i'], 'analysis':'Quality Control'}
    jobs[job_id.get_id()] = {'file': single_dict['i'], 'analysis':'ID Reservation'}
    if single_dict['options']['vf'] or single_dict['options']['serotype']:
        jobs[job_ectyper_beautify.get_id()] = {'file': single_dict['i'], 'analysis': 'Virulence Factors and Serotype'}
    if single_dict['options']['amr']:
        jobs[job_amr_beautify.get_id()] = {'file': single_dict['i'], 'analysis': 'Antimicrobial Resistance'}

    return jobs

def blob_savvy(args_dict):
    '''
    Handles enqueuing of all files in a given directory or just a single file
    '''
    d = {}
    if os.path.isdir(args_dict['i']):
        for f in os.listdir(args_dict['i']):
            single_dict = dict(args_dict.items() + {'i': os.path.join(args_dict['i'], f)}.items())
            d.update(blob_savvy_enqueue(single_dict))
    else:
        d.update(blob_savvy_enqueue(args_dict))

    return d

def spfy(args_dict):
    '''
    '''
    # abs path resolution should be handled in spfy.py
    #args_dict['i'] = os.path.abspath(args_dict['i'])

    print 'Starting blob_savvy call'
    jobs_dict = blob_savvy(args_dict)

    return jobs_dict
