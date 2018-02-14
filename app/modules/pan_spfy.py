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
from middleware.blazegraph.reserve_id import write_reserve_id
from modules.amr.amr import amr
from modules.amr.amr_to_dict import amr_to_dict
from middleware.display.beautify import beautify
from middleware.graphers.datastruct_savvy import datastruct_savvy, parse_gene_dict
from middleware.graphers.turtle_grapher import turtle_grapher, generate_graph
from modules.PanPredic.pan import pan
from middleware.graphers.turtle_utils import generate_uri as gu
from modules.PanPredic.queries import get_single_region
from datetime import datetime
import ast
import cPickle as pickle
from middleware.blazegraph import upload_graph

# the only ONE time for global variables
# when naming queues, make sure you actually set a worker to listen to that queue
# we use tnnhe high priority queue for things that should be immediately
# returned to the user
redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
singles_q = Queue('singles', connection=redis_conn, default_timeout=config.PAN_TIMEOUT)
multiples_q = Queue('multiples', connection=redis_conn,
                    default_timeout=config.PAN_TIMEOUT)
blazegraph_q = Queue('blazegraph', connection=redis_conn)


def graph_upload(graph, dict, genomeURI, region):
    """
    :param graph:
    :param dict:
    :param genomeURI: amr_dict
    :param region:
    :return:
    """

    graph = parse_gene_dict(graph, dict, genomeURI, region)
    upload_graph.upload_graph(graph)


def pan_bundle(panpickle, job_pan):
    """
    queue the queueing dependent on panseq to finish, now we don't have to wait for panseq before queueing other tasks
    """

    pan_results = pickle.load(open(panpickle, 'rb'))
    job_dict = {}
    graph = generate_graph()
    for region in pan_results:
        region_s = str(region)

        for genomeURI in pan_results[region]:

            # checks if genome URI already has a pangenome associated, if so we don't need to process it further

            if not get_single_region(genomeURI):
                job_pan_datastruct = multiples_q.enqueue(graph_upload, graph, pan_results[region][genomeURI], genomeURI,
                                                         'PanGenomeRegion', depends_on=job_pan)
                job_dict[job_pan_datastruct.get_id()] = {'file': genomeURI, 'analysis': 'Panseq'}
                # clears graph
                graph = generate_graph()

    return job_dict


def blob_savvy_enqueue(single_dict):
    """
    Handles enqueueing of single file to multiple queues.
    :param single_dict: single dictionary of arguments
        ex. {'i': '/datastore/2017-06-30-21-53-27-595283-GCA_000023365.1_ASM2336v1_genomic.fna', 'pi': 90, 'options': {'pi': 90, 'amr': False, 'serotype': True, 'vf': True}}}
        Where `options` is the user-selected choices for serotyping and
        the disable_* is useddef get_fasta_header_from_file(filename):                                                                                                              |        job_pan = singles_q.enqueue(pan, single_dict, pickle_file, depends_on=job_id)
 for running Ectyper; these are separate so we can
        always run ectyper in singles/backlog_singles while still returning to
        the user only what they selected.
    :return: dictionary with jobs ids and relevant headers
    """

    jobs = {}
    job_list = []
    query_list = single_dict['i']
    pan_jobs = {}

    if single_dict['options']['pan']:
        query_file = single_dict['i'][0]
        for file in query_list:
            job_qc = multiples_q.enqueue(qc, file, result_ttl=-1)
            job_id = blazegraph_q.enqueue(write_reserve_id, file, depends_on=job_qc, result_ttl=-1)
            pan_jobs[job_qc.get_id()] = {'file': file, 'analysis': 'Quality Control'}
            pan_jobs[job_id.get_id()] = {'file': file, 'analysis': 'ID Reservation'}



    else:
        query_file = single_dict['i']

    def pan_pipeline(singles, multiples):

        job_dict = {}
        now = datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
        pickle_file = os.path.join(current_app.config['DATASTORE'], now + '_panpickle.p')
        job_pan = singles_q.enqueue(pan, single_dict, pickle_file, depends_on=job_id)

        job_pan_id = job_pan.get_id()

        job_pan_bundle = singles_q.enqueue(pan_bundle, pickle_file, job_pan_id, depends_on=job_pan)

        job_dict[job_pan_bundle.get_id()] = {'file': now + '_panseq_results', 'analysis': 'Panseq'}
        job_dict[job_pan.get_id()] = {'file': now + 'pan_run', 'analysis': 'Panseq'}

        return job_dict

    if single_dict['options']['pan']:
        pan_job_dict = pan_pipeline(singles_q, multiples_q)
        jobs.update(pan_job_dict)
        jobs.update(pan_jobs)

    #### PANPREDICT PIPELINE




    # the base file data for blazegraph
    job_turtle = multiples_q.enqueue(
        turtle_grapher, query_file, depends_on=job_qc)

    # new to 4.3.3 if bulk ids used return the endpoint of datastruct generation
    # to poll for completion of all jobs
    # these two ifs handle the case where amr (or vf or serotype) might not
    # be selected but bulk is


    return jobs


def blob_savvy(args_dict):
    """
    Handles enqueuing of all files in a given directory or just a single file
    """
    d = {}

    d.update(blob_savvy_enqueue(args_dict))

    return d


def spfy(args_dict):
    """
    """
    # abs path resolution should be handled in spfy.py
    # args_dict['i'] = os.path.abspath(args_dict['i'])

    jobs_dict = blob_savvy(args_dict)

    return jobs_dict
