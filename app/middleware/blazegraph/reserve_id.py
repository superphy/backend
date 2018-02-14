import os
import logging
from datetime import datetime
from middleware.graphers.turtle_utils import generate_hash, generate_uri as gu, link_uris
from middleware.blazegraph.upload_graph import upload_graph
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Literal, Graph
import config
from modules.loggingFunctions import initialize_logging

log_file = initialize_logging()
log = logging.getLogger(__name__)

blazegraph_url = config.database['blazegraph_url']


def check_duplicates(uriGenome):
    """
    Checks for duplicates in Blazegraph by computing genomeURI (the sha3(sorted content of file) from a graph object).
    :param uriGenome: 
    :return: None if no duplicates found, otherwise return the int of the duplicate's spfyID
    """

    # SPARQL Query
    sparql = SPARQLWrapper(blazegraph_url)
    query = """
    SELECT ?spfyid WHERE {{
        ?spfyid a <{spfyIdType}> .
        ?spfyid <{hasPart}> <{uriGenome}> .
    }}
    """.format(spfyIdType=gu(':spfyId'), hasPart=gu(':hasPart'), uriGenome=uriGenome)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    log.debug('check_duplicates():')
    log.debug(query)
    log.debug(results)
    if not results['results']['bindings']:
        return None
    else:
        # ex. of result from Blazegraph:  {u'head': {u'vars': [u'spfyid']}, u'results': {u'bindings': [{u'spfyid': {u'type': u'uri', u'value': u'https://www.github.com/superphy#spfy2224'}}]}}
        # would return: 2224
        return int(results['results']['bindings'][0]['spfyid']['value'].split('spfy')[1])


def check_largest_spfyid():
    """
    Checks the current largest spfyID is the database (via sort of insert timestamps).
    :return: (int)
    """
    sparql = SPARQLWrapper(blazegraph_url)
    query = """
    SELECT ?spfyid WHERE {{
        ?spfyid a <{spfyIdType}> .
        ?spfyid <{hasPart}> ?genomeid .
        ?genomeid a <{genomeIdType}> .
        ?genomeid <{dateIdType}> ?date .
    }}
    ORDER BY DESC(?date) LIMIT 1
    """.format(spfyIdType=gu(':spfyId'), hasPart=gu(':hasPart'), genomeIdType=gu('g:Genome'),
               dateIdType=gu('ge:0000024'))
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    # run the query against the db
    results = sparql.query().convert()
    # print 'query'
    # print results
    # # try to convert the results
    # reuslts = results.convert()
    # print 'results'
    # print results
    log.debug('check_largest_spfyid():')
    log.debug(query)
    log.debug(results)
    # check that there was some result
    if results['results']['bindings']:
        # if there was a result, return the int of the spfyid
        return int(results['results']['bindings'][0]['spfyid']['value'].split('spfy')[1])
    else:
        # no result was found (fresh DB)
        return 0


def reservation_triple(graph, uriGenome, spfyid):
    uriIsolate = gu(':spfy' + str(spfyid))
    # set object type of spfyid
    graph.add((uriIsolate, gu('rdf:type'), gu(':spfyId')))
    # add plain id # as an attribute
    graph.add((uriIsolate, gu('dc:identifier'), Literal(spfyid)))
    # human-readable
    graph.add((uriIsolate, gu('dc:description'), Literal('Spfy' + str(spfyid))))

    # associatting isolate URI with assembly URI
    graph = link_uris(graph, uriIsolate, uriGenome)
    # graph.add((uriIsolate, gu(':hasPart'), uriGenome))
    # set the object type for uriGenome
    graph.add((uriGenome, gu('rdf:type'), gu('g:Genome')))

    # timestamp
    now = datetime.now()
    now_readable = now.strftime("%Y-%m-%d")
    now_accurate = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
    # dc:date is used for presentation elements
    graph.add((uriGenome, gu('dc:date'), Literal(now_readable)))
    # upload date is used for comparisons
    graph.add((uriGenome, gu('ge:0000024'), Literal(now_accurate)))
    return graph


def reserve_id(query_file):
    """
    given some fasta file:
    (1) Check for duplicates in blazegraph
    (2) If no duplicate is found, check for largest current spfyID
    (3) Create a triple (with associated timestamp) that links the fasta file hash to the spfyID
    (4) Upload that file to Blazegraph to reserve that spfyID
    (5) Return the spfyID to use in proceeding pipeline
    -> If a duplicate is found, just return that spfyID
    """

    # uriGenome generation
    file_hash = generate_hash(query_file)
    log.debug(file_hash)
    uriGenome = gu(':' + file_hash)
    log.debug(uriGenome)

    duplicate = check_duplicates(uriGenome)
    log.debug('check_duplicates() returned: ' + str(duplicate))
    if not duplicate:
        # no duplicates were found, check the current largest spfyID
        largest = check_largest_spfyid()
        # create a rdflib.graph object with the spfyID we want the new file to use
        graph = Graph()
        graph = reservation_triple(graph, uriGenome, largest + 1)
        # uploading the reservation graph secures the file->spfyID link
        upload_graph(graph)
        # returns the (int) of the spfyID we want the new file to use
        return largest + 1
    else:
        # a duplicate was found, return the (int) of it's spfyID
        return duplicate


def write_reserve_id(query_file):
    """
    A write function for pipeline in spfy.py to write out file.
    :param query_file:
    :return:
    """
    spfyid = reserve_id(query_file)
    log.info('SpfyID #:' + str(spfyid))
    id_file = os.path.abspath(query_file) + '_id.txt'
    with open(id_file, 'w+') as f:
        f.write(str(spfyid))
    return id_file


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", required=True)
    args = parser.parse_args()
    print log_file
    print reserve_id(args.i)
