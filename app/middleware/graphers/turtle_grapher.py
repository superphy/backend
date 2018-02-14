# a collection of turtle generation functions
# not meant to be run directly
# only contains functions related to rdflib.Graph manipulation
# only nonspecific stuff: shouldn't contain any functions directly related
# to data structure(rdf triple organization) of the modules you're dev'ing

import config
from middleware.graphers.turtle_utils import generate_hash, generate_uri as gu, link_uris
from middleware.blazegraph.upload_graph import queue_upload
from middleware.graphers.turtle_utils import actual_filename
from rdflib import Namespace, Graph, Literal, plugin
from Bio import SeqIO
from os.path import basename


def generate_graph(transitive=True):
    """
    Parses all the Namespaces defined in the config file and returns a graph
    with them bound.

    Return:
        (rdflib.Graph): a graph with all the defined Namespaces bound to it.
    """

    graph = Graph()

    for key in config.namespaces.keys():
        if key is 'root':
            graph.bind('', config.namespaces['root'])
        else:
            graph.bind(key, config.namespaces[key])

    # add edge equivlaence properties
    if transitive:
        graph.add((gu(':hasPart'), gu('rdf:type'), gu('owl:TransitiveProperty')))
        graph.add((gu(':isFoundIn'), gu('rdf:type'), gu('owl:TransitiveProperty')))
    # graph.add((gu(':hasPart'), gu('rdf:type'), gu('owl:SymmetricProperty')))

    # make AntimicrobialResistanceGene & VirulenceFactor subclasses of :Marker
    graph.add((gu(':AntimicrobialResistanceGene'), gu('rdfs:subClassOf'), gu(':Marker')))
    graph.add((gu(':VirulenceFactor'), gu('rdfs:subClassOf'), gu(':Marker')))
    graph.add((gu(':PanGenomeRegion'), gu('rdfs:subClassOf'), gu(':Marker')))

    # human-readable dc:description for edge types
    graph.add((gu('ge:0001076'), gu('dc:description'), Literal('O-Type')))
    graph.add((gu('ge:0001077'), gu('dc:description'), Literal('H-Type')))
    graph.add((gu('ge:0000024'), gu('dc:description'), Literal('Upload_Date')))
    graph.add((gu(':Marker'), gu('dc:description'), Literal('Any_Marker')))
    graph.add((gu(':VirulenceFactor'), gu('dc:description'), Literal('Virulence_Factor')))
    graph.add((gu(':AntimicrobialResistanceGene'), gu('dc:description'), Literal('AMR_Gene')))
    # human-readable dc:description for object types
    graph.add((gu('so:0001462'), gu('dc:description'), Literal('Bag_of_Contigs')))
    graph.add((gu(':spfyId'), gu('dc:description'), Literal('SpfyId')))

    return graph


def generate_turtle_skeleton(query_file):
    """
    Handles the main generation of a turtle object.

    NAMING CONVENTIONS:
    uriIsolate: this is the top-most entry, a uniq. id per file is allocated by checking our DB for the greatest most entry (not in this file)
        ex. :spfy234
    uriAssembly: aka. the genome ID, this is a sha1 hash of the file contents
        ex. :4eb02f5676bc808f86c0f014bbce15775adf06ba
    uriContig: indiv contig ids; from SeqIO.record.id - this should be uniq to a contig (at least within a given file)
        ex. :4eb02f5676bc808f86c0f014bbce15775adf06ba/contigs/FLOF01006689.1
        note: the record.id is what RGI uses as a prefix for ORF_ID (ORF_ID has additional _314 or w/e #s)

    Args:
       query_file(str): path to the .fasta file (this should already incl the directory)
    Returns:
        graph: the graph with all the triples generated from the .fasta file
    """
    # Base graph generation
    graph = generate_graph()

    # uriGenome generation
    file_hash = generate_hash(query_file)
    uriGenome = gu(':' + file_hash)
    # set the object type for uriGenome
    graph.add((uriGenome, gu('rdf:type'), gu('g:Genome')))
    # this is used as the human readable display of Genome
    graph.add((uriGenome, gu('dc:description'), Literal(actual_filename(query_file))))
    # note that timestamps are not added in base graph generation, they are only added during the check for duplicate files in blazegraph

    # uri for bag of contigs
    # ex. :4eb02f5676bc808f86c0f014bbce15775adf06ba/contigs/
    uriContigs = gu(uriGenome, "/contigs")
    # set the object type for uriContigs
    graph.add((uriContigs, gu('rdf:type'), gu('so:0001462')))
    # link the bag of contigs to the genome
    graph = link_uris(graph, uriGenome, uriContigs)
    # graph.add((uriGenome, gu(':hasPart'), uriContigs))

    for record in SeqIO.parse(open(query_file), "fasta"):
        # ex. :4eb02f5676bc808f86c0f014bbce15775adf06ba/contigs/FLOF01006689.1
        uriContig = gu(uriContigs, '/' + record.id)
        # add the object type to uriContig
        graph.add((uriContig, gu('rdf:type'), gu('g:Contig')))
        # linking the spec contig and the bag of contigs
        graph = link_uris(graph, uriContigs, uriContig)
        # graph.add((uriContigs, gu(':hasPart'), uriContig))
        # uriContig attributes
        graph.add((uriContig, gu('g:DNASequence'), Literal(record.seq)))
        graph.add((uriContig, gu('g:Description'),
                   Literal(record.description)))
        graph.add((uriContig, gu('g:Identifier'),
                   Literal(record.id)))
        # human-readable ; the description here is different because
        # record.description tends to be rather long
        # instead, record.id is the accession eg: FLOF01006689.1
        graph.add((uriContig, gu('dc:description'),
                   Literal(record.description)))
    return graph


def turtle_grapher(query_file):
    graph = generate_turtle_skeleton(query_file)
    return queue_upload(graph)
