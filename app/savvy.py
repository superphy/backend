#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# use: python savvy.py -i samples/ANLJ01.1.fsa_nt

# S:erotype
# A:ntimicrobial Resistance
# V:irulence Factors
# -vy

import logging
# long function calls, cause datastruct_savvy is important
import datastruct_savvy

import pandas as pd

from rdflib import Graph
from turtle_utils import generate_uri as gu
from turtle_grapher import generate_output, generate_graph, generate_turtle_skeleton, generate_file_output

from os.path import basename

# bruteforce
from insert import upload_graph

# for pairwise comparison of rows in panadas
from itertools import tee, izip


def call_ectyper(graph, args_dict):
    # i don't intend to import anything from ECTyper (there are a lot of
    # imports in it - not sure if we'll use them all)
    import subprocess

    from rdflib import Literal
    from ast import literal_eval
    from os.path import splitext

    ectyper_dict = {}
    #logging.info('calling ectyper from fun call_ectyper')
    # concurrency is handled at the batch level, not here (note: this might change)
    # we only use ectyper for serotyping and vf, amr is handled by rgi directly
    if not args_dict['disable_serotype'] or not args_dict['disable_vf']:
        ectyper_dict = subprocess.check_output(['./app/ecoli_serotyping/src/Tools_Controller/tools_controller.py',
                                                '-in', args_dict['i'],
                                                '-s', str(
                                                    int(not args_dict['disable_serotype'])),
                                                '-vf', str(
                                                    int(not args_dict['disable_vf'])),
                                                '-pi', str(args_dict['pi'])
                                                ])
        #logging.info('inner call completed')

        # because we are using check_output, this catches any print messages from tools_controller
        # TODO: switch to pipes
        if 'error' in ectyper_dict.lower():
            #logging.error('ectyper failed for' + args_dict['i'])
            print 'ECTyper failed for: ', args_dict['i']
            print 'returning graph w/o serotype'
            return graph

        #logging.info('evalulating ectyper output')
        # generating the dict
        ectyper_dict = literal_eval(ectyper_dict)
        # logging.info(ectyper_dict)
        #logging.info('evaluation okay')

        # TODO: edit ectyper sure were not using this ducktape approach
        # we are calling tools_controller on only one file, so grab that dict
        key, ectyper_dict = ectyper_dict.popitem()

        if not args_dict['disable_serotype']:
            # serotype parsing
            #logging.info('parsing Serotype')
            graph = datastruct_savvy.parse_serotype(
                graph, ectyper_dict['Serotype'], args_dict['uriIsolate'])
            #logging.info('serotype parsed okay')

        if not args_dict['disable_vf']:
            # vf
            #logging.info('parsing vf')
            graph = datastruct_savvy.parse_gene_dict(
                graph, ectyper_dict['Virulence Factors'], args_dict['uriGenome'])
            #logging.info('vf parsed okay')

    if not args_dict['disable_amr']:
        # amr
        #logging.info('generating amr')
        amr_result = generate_amr(
            graph, args_dict['uriGenome'], args_dict['i'])
        graph = amr_result['graph']
        ectyper_dict['Antimicrobial Resistance'] = amr_result['amr_dict']
        #logging.info('amr generation okay')

    return {'graph': graph, 'ectyper_dict': ectyper_dict}


def generate_amr(graph, uriGenome, fasta_file):
    import subprocess
    import pandas

    from os import rename
    from rdflib import BNode, Literal

    if '/' in fasta_file:
        outputname = fasta_file.split('/')[-1]
    else:
        outputname = fasta_file

    # differs from ectyper as we dont care about the temp results, just the final .tsv
    # direct (the main) call
    print subprocess.call(['rgi',
                     '-i', fasta_file,
                     '-o', 'outputs/' + outputname])

    print fasta_file

    # the rgi_json call in rgitool.py isn't needed for us
    # this generates the .tsv we want
    subprocess.call(['rgi_jsontab',
                     '-i', 'outputs/' + outputname + '.json',
                     '-o', 'outputs/' + outputname])

    rename('outputs/' + outputname + '.txt', 'outputs/' + outputname + '.tsv')

    amr_results = pandas.read_table('outputs/' + outputname + '.tsv')
    amr_results = amr_results[
        ['ORF_ID', 'START', 'STOP', 'ORIENTATION', 'CUT_OFF', 'Best_Hit_ARO']]

    amr_results.rename(
        columns={'ORF_ID': 'contig_id', 'Best_Hit_ARO': 'GENE_NAME'}, inplace=True)

    # sometimes there are spaces at the end of the contig id, also we remove
    # the additional occurance tag that RGI adds to contig ids
    amr_results['contig_id'] = amr_results['contig_id'].apply(
        lambda n: n.strip().rsplit('_', 1)[0])

    # note: you might be tempted to prefix a set_index('contig_id') but
    # remember, the same contig might have multiple genes
    amr_results = amr_results.to_dict(orient='index')

    # we have to manually check for contigs with multiple genes
    # TODO: write something less horrendously slow and memory consuming
    amr_dict = {}
    for i in amr_results.keys():
        contig_id = amr_results[i]['contig_id']
        if contig_id not in amr_dict.keys():
            amr_dict[contig_id] = []
        amr_dict[contig_id].append(dict((keys, amr_results[i][keys]) for keys in (
            'START', 'STOP', 'GENE_NAME', 'ORIENTATION', 'CUT_OFF', 'GENE_NAME')))
    # wipe the amr_results early
    amr_results = None

    graph = datastruct_savvy.parse_gene_dict(graph, amr_dict, uriGenome)

    return {'graph': graph, 'amr_dict': amr_dict}

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def widest(reading_list):
    '''
    Finds the gene with the widest coverage
    args:
        reading_list(list(pandas.DataFrame))
    return:
        (panadas.DataFrame)
    '''
    #sanity check
    if reading_list:
        w = reading_list[0]
        for element in reading_list:
            if abs(element.hitstart - element.hitstop) > abs(w.hitstart - w.hitstop):
                w = element
        return w
    else:
        return reading_list

def overlap(row2, reading_window):
    '''
    returns true is either end (ie. anypart) of row2 overlaps with the reading_window
    '''
    row2_min_overlaps = reading_window['min'] <= min(row2.hitstart,row2.hitstop) <= reading_window['max']
    row2_max_overlaps = reading_window['min'] <= max(row2.hitstart,row2.hitstop) <= reading_window['max']
    return row2_min_overlaps or row2_max_overlaps

def check_alleles_multiple(hits, new_hits):
    '''
    checks for multiple hits of the same gene and appends to new_hits. also strips out overlap
    '''
    #this checks for alleles overlap
    hits.sort_values(['analysis','filename','contigid','hitname','hitstart','hitstop'], inplace=True)

    # set the reading_frame to the first row
    #sanity check
    if not hits.empty:
        reading_list = []
        reading_window = {'min':min(hits.iloc[0].hitstart,hits.iloc[0].hitstop),'max':max(hits.iloc[0].hitstart,hits.iloc[0].hitstop)}
    else:
        raise ValueError
        return new_hits

    for (i1, row1), (i2, row2) in pairwise(hits.iterrows()):
        if row1.analysis != row2.analysis:
            # at intersection between two hits
            at_intersection = True
        elif row1.filename != row2.filename:
            at_intersection = True
        elif row1.contigid != row2.contigid:
            at_intersection = True
        elif row1.hitname != row2.hitname:
            at_intersection = True
        elif not overlap(row2, reading_window):
            #is not overlap, then at this pt we're are a 2nd non-overlapping (& possibly doubly expressed) occurance of the gene
            at_intersection = True
        else:
            at_intersection = False

        if at_intersection:
            if not reading_list:
                #ie reading_list is empty
                # in this case since we're already at an intersection, then row1 is unique
                new_hits.append(dict(row1))
            else:
                new_hits.append(dict(widest(reading_list)))
            reading_list = []
            reading_window['min'] = min(row2.hitstart, row2.hitstop)
            reading_window['max'] = max(row2.hitstart, row2.hitstop)
        else:
            #ie we found an overlap
            #expand the reading_window
            reading_window['min']=min(reading_window['min'],row2.hitstart,row2.hitstop)
            reading_window['max']=max(reading_window['max'],row2.hitstart,row2.hitstop)
            reading_list.append(row2)

            #check for end of iteration
            if cmp(dict(row2),dict(hits.iloc[-1])) == 0:
                new_hits.append(dict(widest(reading_list)))

    return new_hits

def substring_cut(hits):
    '''
    iterrows should return deep copies, not sure if this will work properly
    '''
    for i1, row1 in hits.iterrows():
        subframe = hits.loc[hits.index>i1]
        for i2, row2 in subframe.iterrows():
            if (row1.hitname.lower() in row2.hitname.lower()) or (row2.hitname.lower() in row1.hitname.lower()):
                if len(row1.hitname) > len(row2.hitname):
                    hits.loc[i1,'hitname']=row2.hitname
                elif len(row1.hitname) < len(row2.hitname):
                    hits.loc[i2, 'hitname']=row1.hitname
    return hits

def check_alleles(gene_dict):
    #we are working with the new dict format that is directly converted to json
    hits = pd.DataFrame(gene_dict)
    new_hits = []

    # we're not interested in checking serotype, so we drop it
    if 'Serotype' in hits.analysis.unique():
        new_hits.append(dict(hits[hits['analysis']=='Serotype'].iloc[0]))
        hits = hits[hits['analysis'] != 'Serotype']

    #strip allele info from data
    # assumes if an underscore is in a gene name, that anything after the underscore refers to an allele
    hits['hitname'] = hits['hitname'].apply(lambda x: x.split('_')[0])

    hits = substring_cut(hits)

    #this checks for alleles overlap
    new_hits = check_alleles_multiple(hits, new_hits)

    return new_hits


def json_return(args_dict, gene_dict):
    json_r = []

    # strip gene_dicts that user doesn't want to see
    # remember, we want to run all analysis on our end so we have that data in blazegraph
    d = dict(gene_dict)
    for analysis in gene_dict:
        if analysis == 'Serotype' and not args_dict['options']['serotype']:
            del d['Serotype']
        if analysis == 'Antimicrobial Resistance' and not args_dict['options']['amr']:
            del d['Antimicrobial Resistance']
        if analysis == 'Virulence Factors' and not args_dict['options']['vf']:
            del d['Virulence Factors']
    gene_dict = d



    for analysis in gene_dict:
        if analysis == 'Serotype':
            instance_dict = {}
            instance_dict['filename'] = basename(args_dict['i'])[27:]
            instance_dict['hitname'] = str(gene_dict[analysis].values()).replace(',', ' ').strip("'").strip("[").strip("]")
            instance_dict['contigid'] = 'n/a'
            instance_dict['analysis'] = analysis
            instance_dict['hitorientation'] = 'n/a'
            instance_dict['hitstart'] = 'n/a'
            instance_dict['hitstop'] = 'n/a'
            instance_dict['hitcutoff'] = 'n/a'
            json_r.append(instance_dict)
        else:
            for contig_id in gene_dict[analysis]:
                # where gene_results is a list for amr/vf
                for item in gene_dict[analysis][contig_id]:
                    # for w/e reason vf, has a '0' int in the list of dicts
                    # TODO: bug fix^
                    if type(item) is dict:
                        instance_dict = {}
                        instance_dict['filename'] = basename(args_dict['i'])[27:]
                        instance_dict['contigid'] = contig_id
                        instance_dict['analysis'] = analysis
                        instance_dict['hitname'] = item['GENE_NAME']
                        instance_dict['hitorientation'] = item['ORIENTATION']
                        instance_dict['hitstart'] = item['START']
                        instance_dict['hitstop'] = item['STOP']
                        if analysis == 'Antimicrobial Resistance':
                            instance_dict['hitcutoff'] = item['CUT_OFF']
                        else:
                            instance_dict['hitcutoff'] = args_dict['pi']
                        json_r.append(instance_dict)

    json_r = check_alleles(json_r)

    return json_r


def savvy(args_dict):
    '''
    Args:
        args_dict(dict): i prefer working with args in a dictionary, rather than a namespace is all

    Returns:
        (rdflib.Graph): a graph object with the VF/AMR/Serotype added to it via ECTyper/RGI
    '''
    from os import remove  # for batch cleanup
    # starting #logging
    '''
    logging.basicConfig(
        filename='outputs/' + __name__ +
        args_dict['i'].split('/')[-1] + '.log',
        level=logging.INFO
    )
    '''

    print("Importing FASTA from: " + args_dict['i'])
    #logging.info('importing from' + args_dict['i'])

    # setting up graph
    graph = generate_graph()

    ectyper_result={}

    #logging.info('generating barebones ttl from file')
    graph = generate_turtle_skeleton(
        graph, args_dict['i'], args_dict['uriIsolate'], args_dict['uriGenome'])
    #logging.info('barebones ttl generated')

    if not (args_dict['disable_serotype'] and args_dict['disable_vf'] and args_dict['disable_amr']):
        #logging.info('calling ectyper')
        ectyper_result = call_ectyper(graph, args_dict)
        graph = ectyper_result['graph']
        #logging.info('ectyper call completed')

    # individual fasta logs are wiped on completion (or you'd have several
    # thousand of these)
    #remove('outputs/' + __name__ + args_dict['i'].split('/')[-1] + '.log')
    print upload_graph(graph)

    if not (args_dict['disable_serotype'] and args_dict['disable_vf'] and args_dict['disable_amr']):
        return json_return(args_dict, ectyper_result['ectyper_dict'])

if __name__ == "__main__":
    import argparse
    import os  # for batch cleanup

    from ConfigParser import SafeConfigParser
    from turtle_utils import generate_hash

    # parsing cli-input
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        help="FASTA file",
        required=True
    )
    parser.add_argument(
        "--disable-serotype",
        help="Disables use of the Serotyper. Serotyper is triggered by default.",
        action="store_true"
    )
    parser.add_argument(
        "--disable-vf",
        help="Disables use of ECTyper to get associated Virulence Factors. VFs are computed by default.",
        action="store_true"
    )
    parser.add_argument(
        "--disable-amr",
        help="Disables use of RGI to get Antimicrobial Resistance Factors.  AMR genes are computed by default.",
        action="store_true"
    )
    # note: by in large, we expect uri to be given as just the unique string
    # value  (be it the hash or the integer) without any prefixes, the actual
    # rdflib.URIRef object will be generated in this script
    # this is mainly for batch computation
    parser.add_argument(
        "--uriGenome",
        help="Allows the specification of the Genome URI separately. Expect just the hash (not an actual uri).",
    )
    # This is both for batch computation and for future extensions where there
    # are multiple sequencings per isolate (Campy)
    parser.add_argument(
        "--uriIsolate",
        help="Allows the specification of the Isolate URI separately. Expect just the integer (not the full :spfyID)",
        type=int
    )
    args = parser.parse_args()
    # we make a dictionary from the cli-inputs and add are uris to it
    # mainly used for when a func needs a lot of the args
    args_dict = vars(args)

    # starting#logging
    '''
    logging.basicConfig(
        filename='outputs/' + __name__ +
        args_dict['i'].split('/')[-1] + '.log',
        level=logging.INFO
    )
    '''

    # check if a genome uri isn't set yet
    if args_dict['uriIsolate'] is None:
        # this is temporary, TODO: include a spqarql query to the db
        uriIsolate = gu(':spfy' + str(hash(args_dict['i'].split('/')[-1])))
    else:
        uriIsolate = gu(':spfy' + args_dict['uriIsolate'])

    # if the fasta_file hash was not precomputed (batch scripts should
    # precompute it), we compute that now
    if args_dict['uriGenome'] is None:
        uriGenome = gu(':' + generate_hash(args_dict['i']))
    else:
        uriGenome = gu(':' + args_dict['uriGenome'])

    args_dict['uriIsolate'] = uriIsolate
    args_dict['uriGenome'] = uriGenome

    print savvy(args_dict)
