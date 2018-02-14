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
from modules.ectyper.call_ectyper import call_ectyper_vf, call_ectyper_serotype
from modules.amr.amr import amr
from modules.amr.amr_to_dict import amr_to_dict
from middleware.display.beautify import beautify
from middleware.graphers.datastruct_savvy import datastruct_savvy
from middleware.graphers.turtle_grapher import turtle_grapher
from middleware.graphers.turtle_utils import actual_filename
from modules.phylotyper import phylotyper

from modules.loggingFunctions import initialize_logging
import logging

# logging
initialize_logging()
logger = logging.getLogger(__name__)

# the only ONE time for global variables
# when naming queues, make sure you actually set a worker to listen to that queue
# we use the high priority queue for things that should be immediately
# returned to the user
redis_url = config.REDIS_URL
redis_conn = redis.from_url(redis_url)
singles_q = Queue('singles', connection=redis_conn)
multiples_q = Queue('multiples', connection=redis_conn,
                    default_timeout=config.DEFAULT_TIMEOUT)
blazegraph_q = Queue('blazegraph', connection=redis_conn)
if config.BACKLOG_ENABLED:
    # backlog queues
    backlog_singles_q = Queue('backlog_singles', connection=redis_conn)
    backlog_multiples_q = Queue(
        'backlog_multiples', connection=redis_conn, default_timeout=config.DEFAULT_TIMEOUT)


def blob_savvy_enqueue(single_dict):
    """
    Handles enqueueing of single file to multiple queues.
    :param single_dict: single dictionary of arguments
        ex. {'i': '/datastore/2017-06-30-21-53-27-595283-GCA_000023365.1_ASM2336v1_genomic.fna', 'pi': 90, 'options': {'pi': 90, 'amr': False, 'serotype': True, 'vf': True}}}
        Where `options` is the user-selected choices for serotyping and
        the disable_* is used for running Ectyper; these are separate so we can
        always run ectyper in singles/backlog_singles while still returning to
        the user only what they selected.
    :return: dictionary with jobs ids and relevant headers
    """
    jobs = {}
    query_file = single_dict['i']

    job_qc = multiples_q.enqueue(qc, query_file, result_ttl=-1)
    job_id = blazegraph_q.enqueue(
        write_reserve_id, query_file, depends_on=job_qc, result_ttl=-1)

    # ECTYPER PIPELINE
    def ectyper_pipeline(singles, multiples):
        """The ectyper call is special in that it requires the entire arguments
        to decide whether to carry the serotype option flag, virulance
        factors option flag, and percent identity field. We use the old ECTyper
        for VF and the new ECTyper for Serotyping.
        """
        if single_dict['options']['vf']:
            # Create a copy of the arguments dictionary and disable Serotype.
            # This copy is passed to the old ECTyper.
            single_dict_vf = dict(single_dict)
            single_dict_vf['options']['serotype'] = False
            # Enqueue the old ECTyper
            job_ectyper_vf = singles.enqueue(
                call_ectyper_vf,
                single_dict_vf,
                depends_on=job_id)
        if single_dict['options']['serotype']:
            # Enqueue the new ECTyper
            job_ectyper_serotype = multiples.enqueue(
                call_ectyper_serotype,
                single_dict,
                depends_on=job_id)

        # datastruct_savvy() stores result to Blazegraph.
        if single_dict['options']['bulk']:
            # If bulk uploading is set, we return the datastruct as the end task
            # to poll for job completion, therefore must set ttl of -1.
            if single_dict['options']['vf']:
                job_ectyper_datastruct = multiples.enqueue(
                    datastruct_savvy,
                    query_file,
                    query_file + '_id.txt',
                    query_file + '_ectyper_vf.p',
                    depends_on=job_ectyper,
                    result_ttl=-1)
            if single_dict['options']['serotype']:
                job_ectyper_datastruct = multiples.enqueue(
                    datastruct_savvy,
                    query_file,
                    query_file + '_id.txt',
                    query_file + '_ectyper_serotype.p',
                    depends_on=job_ectyper,
                    result_ttl=-1)
        else:
            job_ectyper_datastruct = multiples.enqueue(
                datastruct_savvy, query_file, query_file + '_id.txt', query_file + '_ectyper.p', depends_on=job_ectyper)
        d = {'job_ectyper': job_ectyper,
             'job_ectyper_datastruct': job_ectyper_datastruct}
        # only bother parsing into json if user has requested either vf or
        # serotype
        if (single_dict['options']['vf'] or single_dict['options']['serotype']) and not single_dict['options']['bulk']:
            job_ectyper_beautify = multiples.enqueue(
                beautify, single_dict, query_file + '_ectyper.p', depends_on=job_ectyper, result_ttl=-1)
            d.update({'job_ectyper_beautify': job_ectyper_beautify})
        return d

    # if user selected any ectyper-dependent options on the front-end
    if single_dict['options']['vf'] or single_dict['options']['serotype']:
        ectyper_jobs = ectyper_pipeline(singles_q, multiples_q)
        job_ectyper = ectyper_jobs['job_ectyper']
        job_ectyper_datastruct = ectyper_jobs['job_ectyper_datastruct']
        if not single_dict['options']['bulk']:
            job_ectyper_beautify = ectyper_jobs['job_ectyper_beautify']
    # or if the backlog queue is enabled
    elif config.BACKLOG_ENABLED:
        # we need to create a dict with these options enabled:

        # just enqueue the jobs, we don't care about returning them
        ectyper_jobs = ectyper_pipeline(backlog_singles_q, backlog_multiples_q)
        job_ectyper_datastruct = ectyper_jobs['job_ectyper_datastruct']

    # END ECTYPER PIPELINE

    # AMR PIPELINE
    def amr_pipeline(multiples):
        job_amr = multiples.enqueue(amr, query_file, depends_on=job_id)
        job_amr_dict = multiples.enqueue(
            amr_to_dict, query_file + '_rgi.tsv', depends_on=job_amr)
        # this uploads result to blazegraph
        if single_dict['options']['bulk']:
            job_amr_datastruct = multiples.enqueue(
                datastruct_savvy, query_file, query_file + '_id.txt', query_file + '_rgi.tsv_rgi.p',
                depends_on=job_amr_dict, result_ttl=-1)
        else:
            job_amr_datastruct = multiples.enqueue(
                datastruct_savvy, query_file, query_file + '_id.txt', query_file + '_rgi.tsv_rgi.p',
                depends_on=job_amr_dict)
        d = {'job_amr': job_amr, 'job_amr_dict': job_amr_dict,
             'job_amr_datastruct': job_amr_datastruct}
        # we still check for the user-selected amr option again because
        # if it was not selected but BACKLOG_ENABLED=True, we dont have to
        # enqueue it to backlog_multiples_q since beautify doesnt upload
        # blazegraph
        if single_dict['options']['amr'] and not single_dict['options']['bulk']:
            job_amr_beautify = multiples.enqueue(
                beautify, single_dict, query_file + '_rgi.tsv_rgi.p', depends_on=job_amr_dict, result_ttl=-1)
            d.update({'job_amr_beautify': job_amr_beautify})
        return d

    if single_dict['options']['amr']:
        amr_jobs = amr_pipeline(multiples_q)
        job_amr = amr_jobs['job_amr']
        job_amr_dict = amr_jobs['job_amr_dict']
        job_amr_datastruct = amr_jobs['job_amr_datastruct']
        if not single_dict['options']['bulk']:
            job_amr_beautify = amr_jobs['job_amr_beautify']
    elif config.BACKLOG_ENABLED:
        amr_pipeline(backlog_multiples_q)

    # END AMR PIPELINE

    # Phylotyper Pipeline
    def phylotyper_pipeline(multiples, subtype):

        jobname = '_pt' + subtype
        tsvfile = query_file + jobname + '.tsv'
        picklefile = query_file + jobname + '.p'

        job_pt = multiples.enqueue(
            phylotyper.phylotyper, None, subtype, tsvfile, id_file=query_file + '_id.txt',
            depends_on=job_ectyper_datastruct)
        job_pt_dict = multiples.enqueue(
            phylotyper.to_dict, tsvfile, subtype, picklefile,
            depends_on=job_pt)
        job_pt_datastruct = multiples.enqueue(
            phylotyper.savvy, picklefile, subtype,
            depends_on=job_pt_dict)

        d = {'job' + jobname: job_pt, 'job' + jobname + '_dict': job_pt_dict,
             'job' + jobname + '_datastruct': job_pt_datastruct}
        # we still check for the user-selected amr option again because
        # if it was not selected but BACKLOG_ENABLED=True, we dont have to
        # enqueue it to backlog_multiples_q since beautify doesnt upload
        # blazegraph
        if single_dict['options'][subtype]:
            job_pt_beautify = multiples.enqueue(
                phylotyper.beautify, picklefile, actual_filename(query_file),
                depends_on=job_pt_dict, result_ttl=-1)
            d.update({'job' + jobname + '_beautify': job_pt_beautify})

        return d

    if single_dict['options']['stx1']:
        pt_jobs = phylotyper_pipeline(multiples_q, 'stx1')
        job_stx1_beautify = pt_jobs['job_ptstx1_beautify']
    elif config.BACKLOG_ENABLED:
        phylotyper_pipeline(backlog_multiples_q, 'stx1')

    if single_dict['options']['stx2']:
        pt_jobs = phylotyper_pipeline(multiples_q, 'stx2')
        job_stx2_beautify = pt_jobs['job_ptstx2_beautify']
    elif config.BACKLOG_ENABLED:
        phylotyper_pipeline(backlog_multiples_q, 'stx2')

    if single_dict['options']['eae']:
        pt_jobs = phylotyper_pipeline(multiples_q, 'eae')
        job_eae_beautify = pt_jobs['job_pteae_beautify']
    elif config.BACKLOG_ENABLED:
        phylotyper_pipeline(backlog_multiples_q, 'eae')
    # END Phylotyper pipeline

    # the base file data for blazegraph
    job_turtle = multiples_q.enqueue(
        turtle_grapher, query_file, depends_on=job_qc)

    jobs[job_qc.get_id()] = {'file': single_dict['i'],
                             'analysis': 'Quality Control'}
    jobs[job_id.get_id()] = {'file': single_dict['i'],
                             'analysis': 'ID Reservation'}

    # new to 4.3.3 if bulk ids used return the endpoint of datastruct generation
    # to poll for completion of all jobs
    # these two ifs handle the case where amr (or vf or serotype) might not
    # be selected but bulk is
    if single_dict['options']['vf'] or single_dict['options']['serotype']:
        ret_job_ectyper = job_ectyper_datastruct
    if single_dict['options']['amr']:
        ret_job_amr = job_amr_datastruct
    # if bulk uploading isnt used, return the beautify result as the final task
    if not single_dict['options']['bulk']:
        if single_dict['options']['vf'] or single_dict['options']['serotype']:
            ret_job_ectyper = job_ectyper_beautify
        if single_dict['options']['amr']:
            ret_job_amr = job_amr_beautify
    # add the jobs to the return
    if single_dict['options']['vf'] or single_dict['options']['serotype']:
        jobs[ret_job_ectyper.get_id()] = {'file': single_dict[
            'i'], 'analysis': 'Virulence Factors and Serotype'}
    if single_dict['options']['amr']:
        jobs[ret_job_amr.get_id()] = {'file': single_dict[
            'i'], 'analysis': 'Antimicrobial Resistance'}
    if single_dict['options']['stx1']:
        jobs[job_stx1_beautify.get_id()] = {'file': single_dict[
            'i'], 'analysis': 'Phylotyper'}
    if single_dict['options']['stx2']:
        jobs[job_stx2_beautify.get_id()] = {'file': single_dict[
            'i'], 'analysis': 'Phylotyper'}
    if single_dict['options']['eae']:
        jobs[job_eae_beautify.get_id()] = {'file': single_dict[
            'i'], 'analysis': 'Phylotyper'}

    return jobs


def blob_savvy(args_dict):
    """
    Handles enqueuing of all files in a given directory or just a single file
    """
    d = {}
    if os.path.isdir(args_dict['i']):
        for f in os.listdir(args_dict['i']):
            single_dict = dict(args_dict.items() +
                               {'i': os.path.join(args_dict['i'], f)}.items())
            d.update(blob_savvy_enqueue(single_dict))
    else:
        d.update(blob_savvy_enqueue(args_dict))

    return d


def spfy(args_dict):
    """
    """
    # abs path resolution should be handled in spfy.py
    # args_dict['i'] = os.path.abspath(args_dict['i'])

    # print 'Starting blob_savvy call'
    # logger.info('args_dict: ' + str(args_dict))
    jobs_dict = blob_savvy(args_dict)

    return jobs_dict
