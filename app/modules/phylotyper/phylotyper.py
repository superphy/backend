"""Phylotyper module

Start phylotyper job. Uses default result directories

Example:
    :

        $ python example_google.py

"""

import subprocess
import os
import shutil
import logging
from tempfile import mkdtemp
import pandas as pd
import cPickle as pickle
from rdflib import Graph, BNode, Literal, XSD
import re
from collections import OrderedDict


import config
from modules.turtleGrapher.turtle_utils import generate_uri as gu, fulluri_to_basename as u2b, normalize_rdfterm as normalize 
from modules.blazeUploader.upload_graph import upload_graph
from modules.phylotyper import ontology, exceptions
from modules.phylotyper.sequences import MarkerSequences, phylotyper_query

logger = logging.getLogger(__name__)



def phylotyper(query, subtype, result_file):
    """ Wrapper for Phylotyper

    Args:
        query (str): Genome URI
        subtype (str): Phylotyper recognized subtype (e.g. stx1)
        result_file (str): File location to write phylotyper tab-delim result to

    Returns:
        file to tab-delimited text results
    
    """

    # Validate subtype ontology
    try:
        ontology.load(subtype)
    except exceptions.DatabaseError as err:
        logger.error('Please run VF detection before calling Phylotyper. Error message: {}'.format(err))
    except Exception as err:
        logger.error('Unexpected error from phylotyper ontology loading. Error message: {}'.format(err))
        raise err


    # Get loci to use in subtype prediction
    uri = 'subt:'+subtype
    loci_results = ontology.schema_query(uri)
    loci = [ gu(l['locus']) for l in sorted(loci_results, key=lambda k: k['i'])]

    # Get alleles for this genome
    markerseqs = MarkerSequences(loci)
    fasta = markerseqs.fasta(query)

    temp_dir = mkdtemp(prefix='pt', dir=config.DATASTORE)
    query_file = os.path.join(temp_dir, 'query.fasta')
    output_file = os.path.join(temp_dir, 'subtype_predictions.tsv')

    if fasta:
        # Run phylotyper
        with open(query_file, 'w') as fh:
            fh.write(fasta)

        subprocess.call(['phylotyper', 'genome', '--noplots',
                         subtype,
                         temp_dir,
                         query_file])

    else:
        # No loci
        # Report no loci status in output
        with open(output_file, 'w') as fh:
            fh.write("#Empty Header")
            fh.write("Required alleles not found")

    shutil.move(output_file, result_file)
    shutil.rmtree(temp_dir)
          
    return result_file


def to_dict(pt_file, subtype, pickle_file):
    """ Convert output into intermediate output

      Returns pickled dictionary indexed by subtype predictions

    """
      
    pt_results = pd.read_table(pt_file)
    
    pt_results = pt_results[['subtype','probability','loci']]

    pt_results = pt_results.to_dict()
    pt_results['contig'] = {}
    pt_results['start'] = {}
    pt_results['stop'] = {}

    # Parse marker URIs, starts, stops, etc from loci field
    # Discard rest
    for k, v in pt_results['loci'].iteritems():
        loci = eval(v)
        contigs = []
        starts = []
        stops = []
        locis = []
        for l in loci:
            datasections = l.split(" ")
            locsections = datasections[2].split(":")
            contigs.append(locsections[-3])
            contigpos = map(lambda i: int(i), locsections[-2].split('..'))
            contigpos.sort()
            starts.append(contigpos[0])
            stops.append(contigpos[1])
            locis.append(datasections[1])

        pt_results['loci'][k] = locis
        pt_results['contig'][k] = contigs
        pt_results['start'][k] = starts
        pt_results['stop'][k] = stops
    
    pickle.dump(pt_results, open(pickle_file, 'wb'))

    return pickle_file


def beautify(p_file):
    """ Convert phylotyper data into json format used by front end


    """

    pt_dict = pickle.load(open(p_file, 'rb'))

    #print(pt_dict)

    # Expand into table rows - one per loci
    table_rows = []
    for k in pt_dict['loci']:
        
        # Location info
        for i in range(len(pt_dict['loci'][k])):
            instance_dict = {}
            instance_dict['start'] = pt_dict['start'][k][i]
            instance_dict['stop'] = pt_dict['stop'][k][i]
            instance_dict['contig'] = pt_dict['contig'][k][i]
            
            # Genome
            # Subtype info
            instance_dict['subtype'] = pt_dict['subtype'][k]
            instance_dict['probability'] = pt_dict['probability'][k]
        
            table_rows.append(instance_dict)

    return table_rows
        



def savvy(p_file, subtype):
    """ Load phylotyper results into DB


    """

    # Phylotyper scheme
    phylotyper_uri = gu('subt:'+subtype)
    
    # Get list of permissable subtype values
    subtypes_results = ontology.subtypeset_query(normalize(phylotyper_uri))
    subtypes = {}
    for r in subtypes_results:
        subtypes[ r['value'] ] = r['part']

    # Load data
    pt_dict = pickle.load(open(p_file, 'rb'))

    print(pt_dict)

    # Graph to attach new values too
    graph = Graph()
    is_a = gu('rdf:type')

    # Iterate through loci sets
    for k in pt_dict['subtype']:

        # Check assigned type is recognized subtype in scheme
        if pt_dict['subtype'][k] in subtypes:
            # New subtype assignment
            subtype_instance = BNode()
            graph.add((subtype_instance, is_a, gu('subt:PTST')))
            graph.add((subtype_instance, gu('subt:isOfPhylotyper'), phylotyper_uri))
            graph.add((subtype_instance, gu('subt:hasIdentifiedClass'), gu(subtypes[pt_dict['subtype'][k]])))
            graph.add((subtype_instance, gu('subt:score'), Literal(pt_dict['probability'][k], datatype=XSD.decimal)))

            # Link subtype to alleles
            for a in pt_dict['loci'][k]:
                allele_instance = BNode()
                graph.add((allele_instance, is_a, gu('subt:PTAllele')))
                a = re.sub(r'^spfy\|(.+)\|$',r':\g<1>',a)
                graph.add((allele_instance, gu('faldo:location'), gu(a)))
                graph.add((subtype_instance, gu('typon:hasIdentifiedAllele'), allele_instance))

            # Add link to add linkages for group comparisons

        else:
            raise exceptions.ValuesError(pt_dict['subtype'][k])

    print(graph.serialize(format='turtle'))
    upload_graph(graph)



def ignorant(genome_uri, subtype, pickle_file):
    """ Retrieve phylotyper results from DB



    """

    phylotyper_rdf = normalize(gu('subt:'+subtype))
    genome_rdf = normalize(genome_uri)

    results = phylotyper_query(phylotyper_rdf, genome_rdf)
    subtype_assignments = {}
    set_i = 0

    pt_dict = {
        'probability': {},
        'subtype': {},
        'loci': {},
        'contig': {},
        'start': {},
        'stop': {}
    }
    for row in results:
        
        if row['pt'] in subtype_assignments:
            k = subtype_assignments[row['pt']]
        else:
            k = set_i
            set_i = set_i + 1
            subtype_assignments[row['pt']] = k
            for f in pt_dict:
                pt_dict[f][k] = {}


        pt_dict['probability'][k] = float(row['score'])
        pt_dict['subtype'][k] = row['typeLabel']
        if not pt_dict['contig'][k]:
            pt_dict['contig'][k] = []
            pt_dict['loci'][k] = []
            pt_dict['start'][k] = []
            pt_dict['stop'][k] = []
        pt_dict['contig'][k].append(row['contigid'])
        pt_dict['loci'][k].append(row['region'])
        pt_dict['start'][k].append(row['beginPos'])
        pt_dict['stop'][k].append(row['endPos'])

    print(pt_dict)

    pickle.dump(pt_dict, open(pickle_file, 'wb'))

    return pickle_file



if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-g",
        help="Genome URI",
        required=True
    )
    parser.add_argument(
        "-s",
        help="Phylotyper subtype scheme",
        required=True
    )
    args = parser.parse_args()

    input_g = args.g
    if input_g.startswith('<'):
        input_g = input_g[1:-1]
    g = u2b(gu(input_g))
    pt_file = os.path.join(config.DATASTORE, g+'_pt.tsv')
    pickle_file = os.path.join(config.DATASTORE, g+'_pt.p')
    
    #phylotyper(args.g, args.s, pt_file)
    #to_dict(pt_file, args.s, pickle_file)
    #beautify(pickle_file)
    #savvy(pickle_file, args.s)
    ignorant(input_g, args.s, pickle_file+'2')