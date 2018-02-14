"""Check and Setup Phylotyper Ontology and Subtyping Schemes


Example:
    $ python ontolog.py -s stx1

"""

import logging
import os
from rdflib import Graph, Literal, XSD

from modules.phylotyper.exceptions import ValuesError, DatabaseError
from middleware.graphers.turtle_utils import generate_uri as gu
from middleware.decorators import submit, prefix, tojson
from middleware.blazegraph.upload_graph import upload_turtle, upload_graph

from modules.phylotyper.graph_refs import graph_refs

log = logging.getLogger(__name__)
typing_ontology_version = '<https://www.github.com/superphy/typing/1.0.0>'
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


@submit
@prefix
def version_query(v):
    """
    Queries for a given typing ontology version

    returns:
        dictionary

    """
    query = '''
        SELECT ?version
        WHERE {{
            ?version rdf:type owl:Ontology .
            ?version owl:versionIRI {ver}
        }}
        '''.format(ver=v)

    return query


@tojson
@submit
@prefix
def schema_query(subtype):
    """
    Queries for a phylotyper subtype definition

    Returns:
        dictionary

    """
    query = '''
        SELECT ?i ?locus
        WHERE {{
            VALUES ?subtype {{ {} }}
            ?subtype rdf:type subt:Phylotyper ;
                typon:hasSchema ?schema .
            ?schema typon:hasSchemaPart ?schemaPart .
            ?schemaPart typon:index ?i ;
                typon:hasLocus ?locus
        }}
        '''.format(subtype)

    return query


@tojson
@submit
@prefix
def subtypeset_query(subtype):
    """
    Queries for a phylotyper subtype values

    Returns:
        dictionary

    """
    query = '''
        SELECT ?part ?value
        WHERE {{
            VALUES ?subtype {{ {} }}
            ?subtype rdf:type subt:Phylotyper ;
                subt:hasSubtypeSet ?sset .
            ?sset subt:hasDefinedClass ?part .
            ?part subt:subtypeValue ?value
        }}
        '''.format(subtype)

    return query


@submit
@prefix
def subtype_query(subtype, rdftype='subt:Phylotyper'):
    """
    Queries for a specific URI of given type

    Returns:
        dictionary

    """
    query = '''
        SELECT ?subtype
        WHERE {{
            ?subtype rdf:type  {} .
            VALUES ?subtype {{ {} }}
        }}
        '''.format(rdftype, subtype)

    return query


def match_version(version):
    """
    Returns true if ontology with given version is already in database

    Args:
        version(str): ontology version string e.g. <https://www.github.com/superphy/typing/1.0.0>

    """

    result = version_query(version)

    if result['results']['bindings']:
        return True
    else:
        return False


def find_object(uri, rdftype):
    """
    Returns true if URI is already in database

    Args:
        uri(str): URI with prefix defined in config.py
        rdftype(str): the URI linked by a rdf:type relationship to URI

    """

    result = subtype_query(uri, rdftype)

    if result['results']['bindings']:
        return True
    else:
        return False


def generate_graph(uri, loci, values):
    """
    Returns graph object that defines phylotyper subtype schema

    """

    subtype = uri.split(':')[1]

    # Check for existance of schema Marker components
    for l in loci:
        if not find_object(l, ':Marker'):
            raise DatabaseError(uri, l)

    # Proceed with creating subtype schema
    graph = Graph()

    # Create instance of phylotyper subtype
    phylotyper = gu(uri)
    a = gu('rdf:type')
    label = gu('rdfs:label')
    graph.add((phylotyper, a, gu('subt:Phylotyper')))

    # Define Schema
    schema_uri = uri + 'Schema'
    schema = gu(schema_uri)
    graph.add((schema, a, gu('typon:Schema')))
    graph.add((schema, label, Literal('{} schema'.format(subtype), lang='en')))

    part = 1
    for l in loci:
        schemapart = gu(schema_uri + '_part_{}'.format(part))
        graph.add((schemapart, a, gu('typon:SchemaPart')))
        graph.add((schemapart, label, Literal('{} schema part {}'.format(subtype, part), lang='en')))
        graph.add((schemapart, gu('typon:index'), Literal(part, datatype=XSD.integer)))
        graph.add((schemapart, gu('typon:hasLocus'), gu(l)))
        graph.add((schema, gu('typon:hasSchemaPart'), schemapart))

        part += 1

    graph.add((phylotyper, gu('typon:hasSchema'), schema))

    # Define Subtype Values
    set_uri = uri + 'SubtypeSet'
    subtype_set = gu(set_uri)
    graph.add((subtype_set, a, gu('subt:SubtypeSet')))
    graph.add((subtype_set, label, Literal('{} subtype set'.format(subtype), lang='en')))

    for v in values:
        setpart = gu(set_uri + '_class_{}'.format(v))
        graph.add((setpart, a, gu('subt:SubtypeClass')))
        graph.add((setpart, label, Literal('{} subtype class {}'.format(subtype, v), lang='en')))
        graph.add((setpart, gu('subt:subtypeValue'), Literal(v, datatype=XSD.string)))
        graph.add((subtype_set, gu('subt:hasDefinedClass'), setpart))

    graph.add((phylotyper, gu('subt:hasSubtypeSet'), subtype_set))

    return graph


def stx1_graph():
    """
    Returns graph object that defines stx2 phylotyper subtype schema

    """

    return generate_graph('subt:stx1', [':stx1A', ':stx1B'], ['a', 'c', 'd', 'untypeable'])


def stx2_graph():
    """
    Returns graph object that defines stx2 phylotyper subtype schema

    """

    return generate_graph('subt:stx2', [':stx2A', ':stx2B'], ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'untypeable'])


def eae_graph():
    """
    Returns graph object that defines eae phylotyper subtype schema

    """

    return generate_graph('subt:eae', [':eae'],
                          ["alpha-1", "alpha-2", "beta-1", "beta-2", "epsilon-1", "epsilon-2", "eta-1", "eta-2",
                           "gamma-1", "iota-1", "iota-2", "kappa-1", "lambda-1", "mu-1", "nu-1", "omicron-1", "pi-1",
                           "rho-1", "sigma-1", "theta-2", "xi-1", "zeta-1", "untypeable"])


def load(subtype):
    """
    Loads typing ontology and schema for a given phylotyper subtype

    Args:
        subtype(str): A subtype name that matches one of the defined subtype initialization methods in this module

    Returns:
        list with marker URIs that make up schema for subtype

    """

    func_name = subtype + '_graph'
    uri = 'subt:' + subtype

    if not func_name in globals():
        raise ValuesError(subtype)
    graph_func = globals()[func_name]

    ontology_turtle_file = os.path.join(__location__, 'superphy_subtyping.ttl')

    if not match_version(typing_ontology_version):
        log.info('Uploading subtyping ontolog version: {}'.format(typing_ontology_version))
        response = upload_turtle(ontology_turtle_file)
        log.info('Upload returned response: {}'.format(response))
        # add reference graph of ecoli_vf
        log.info('Uploading VF reference genes')
        vf_graph = graph_refs()
        vf_response = upload_graph(vf_graph)
        log.info('Upload returned response: {}'.format(vf_response))

    if not find_object(uri, 'subt:Phylotyper'):
        log.info('Uploading subtype definition: {}'.format(subtype))
        graph = graph_func()
        response = upload_graph(graph)
        log.info('Upload returned response: {}'.format(response))

        # Database ready to recieve phylotyper data for this subtype


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        help="Phylotyper subtype scheme",
        required=True
    )
    args = parser.parse_args()

    load(args.s)
