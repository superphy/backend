# loads all the reference Virulence Factors
import os
import shutil
import requests
from tempfile import NamedTemporaryFile
from rdflib import Literal
from middleware.graphers.turtle_grapher import generate_graph
from middleware.graphers.turtle_utils import generate_uri as gu


def get_ref_vfs():
    # we use a tempfile.TemporaryFile to store the ref
    tf = NamedTemporaryFile()
    # try to get the VF ref file from github
    try:
        f = requests.get(
            'https://raw.githubusercontent.com/phac-nml/ecoli_vf/master/data/repaired_ecoli_vfs_shortnames.ffn')
        print 'Retrieved ref vf file from GitHub.'
        # github return Unicdoe, we want the str
        tf.write(str(f.text))
    except:
        # if fails, use the backup copy in superphy/backend's ECTyper submodule
        print 'Could not retrieve ecoli_vf from GitHub. Using backup...'
        f = 'modules/ectyper/ecoli_serotyping/Data/repaired_ecoli_vfs_shortnames.ffn'
        with open(f, 'r+b') as fl:
            shutil.copyfileobj(fl, tf)
    # we need to set read position back to beginning
    tf.seek(0)
    return tf


def identify_name(line):
    """
    Determines the name of the gene in a given header.
    """
    sub = ''
    if ')' in line:
        if 'gi:' in line:
            sub = line.split('(')[2].split(')')[0]
        else:
            sub = line[line.find("(") + 1:line.find(")")]
    return sub


def graph_refs():
    # get the reference VF file as a tempfile.TemporaryFile
    f = get_ref_vfs()

    # read this reference file write in into a list
    lines = [line.rstrip('\n') for line in f.readlines()]
    f.close()

    # create a blank graph object
    g = generate_graph()

    # iterate using i for the header's position
    for i in range(0, len(lines), 2):
        sub = identify_name(lines[i])
        # create a uri from this VF
        # ex. :mexN
        uriGene = gu(':' + sub)
        # label it a VF, this will also label it a :Marker
        g.add((uriGene, gu('rdf:type'), gu(':VirulenceFactor')))
        # add the gene seq
        g.add((uriGene, gu('g:DNASequence'), Literal(lines[i + 1])))

    return g
