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

from backports import tempfile

import ontology
import exceptions
from sequences import MarkerSequences

logger = logging.getLogger(__name__)



def phylotyper(query, subtype):
    '''
    Wrapper for Phylotyper

    Args:
        query (str): Genome URI
        subtype (str): Phylotyper recognized subtype (e.g. stx1)

    Returns:
        file to tab-delimited text results
    
    '''

    # Validate subtype ontology
    try:
        ontology.load(subtype)
    except exceptions.DatabaseException as err:
        logger.error('Please run VF detection before calling Phylotyper. Error message: {}'.format(err))
    except Exception as err:
        logger.error('Unexpected error from phylotyper ontology loading. Error message: {}'.format(err))
        raise err


    # Get loci to use in subtype prediction
    uri = 'subt:'+subtype
    loci_results = ontology.schema_query(uri)
    loci = [ l['locus'] for l in sorted(loci_results, key=lambda k: k['i'])]

    # Get list of permissable subtype values
    subtypes_results = ontology.subtypeset_query(uri)
    subtypes = {}
    for r in subtypes_results:
        subtypes[r['value']] = r['part']

    # Get alleles for this genome
    markerseqs = MarkerSequences(loci)
    fasta = markerseqs.fasta(query)

    if fasta:
        # Run phylotyper

        with tempfile.TemporaryDirectory(dir=temporary_dir) as temp_dir:

            query_file = os.path.join(temp_dir, 'query.fasta')
            with open(query_file, 'w') as fh:
                fh.write(fasta)

            subprocess.call(['phylotyper', 'genome', '--noplots',
                             subtype,
                             temp_dir,
                             query_file])

            # Match assignment with accepted ontology object
            
            # rename and move the tsv to the original directory, if applicable
            pt_file = os.path.join(outputdir)
            shutil.move(outputname+'.txt', amr_file)

    else:
        # No loci, nothing to do

    return amr_file

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        help="FASTA file",
        required=True
    )
    parser.add_argument(
        "-s",
        help="Phylotyper subtype scheme",
        required=True
    )
    args = parser.parse_args()
    print amr(args.i)