# baseURI: https://www.github.com/superphy#
from datetime import datetime
from rdflib import Literal
from middleware.graphers.turtle_grapher import generate_graph
from middleware.graphers.turtle_utils import generate_uri as gu, link_uris
from middleware.blazegraph.reserve_id import reservation_triple
from scripts.savvy import savvy


def write_graph(graph):
    """
    Used to write a rdf graph to disk as a turtle file.
    """
    data = graph.serialize(format="turtle")
    f = 'spfy_ontology.ttl'
    with open(f, 'w') as fl:
        fl.write(data)
    return f


def ontology_link(graph, uri_towards_spfyid, uri_towards_marker):
    """
    Creats links that work in WebVOWL.
    """

    def name(uri):
        return str(uri).split('/')[-1][:3]

    hasPart = gu(':hasPart' + '_' + name(uri_towards_spfyid) + '_' + name(uri_towards_marker))
    isFoundIn = gu(':isFoundIn' + '_' + name(uri_towards_marker) + '_' + name(uri_towards_spfyid))
    # hasPart:
    graph.add((
        hasPart,
        gu('rdfs:domain'),
        uri_towards_spfyid
    ))
    graph.add((
        hasPart,
        gu('rdfs:range'),
        uri_towards_marker
    ))
    # isFoundIn
    graph.add((
        isFoundIn,
        gu('rdfs:domain'),
        uri_towards_marker
    ))
    graph.add((
        isFoundIn,
        gu('rdfs:range'),
        uri_towards_spfyid
    ))
    # Edge types. Subsequent calls will not add to graph.
    graph.add((
        hasPart,
        gu('rdf:type'),
        gu('owl:ObjectProperty')
    ))
    graph.add((
        isFoundIn,
        gu('rdf:type'),
        gu('owl:TransitiveProperty')
    ))
    graph.add((
        hasPart,
        gu('rdf:type'),
        gu('owl:TransitiveProperty')
    ))
    return graph


def generate_ontology(example=True):
    """
    Generates an ontology for the Spfy backend using utility methods used in
    production. Serializes the ontology as a turtle file, similar to faldo.ttl
    Recall that an ontology is really just a set of triples, but applied to
    classes/subclasses instead of specific instances.
    """
    # generates the base graph with namespaces appended to it
    # also defines edge relations for :hasPart and :isFoundIn
    # also defines subclasses for our custom types
    graph = generate_graph(transitive=False)

    # adds info about this ontology being generated
    graph.add((gu('https://www.github.com/superphy#'), gu('rdf:type'), gu('owl:Ontology')))
    graph.add(
        (gu('https://www.github.com/superphy#'), gu('dc:license'), gu('https://www.apache.org/licenses/LICENSE-2.0')))

    # spfyId class
    graph.add((gu(':spfyId'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu(':spfyId'), gu('rdfs:comment'), Literal(':spfyid')))

    # ge:0001567 'bacterium'
    graph.add((gu('ge:0001567'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('ge:0001567'), gu('rdfs:comment'), Literal('subject species')))
    graph.add((gu('ge:0001567'), gu('rdfs:domain'), gu(':spfyId')))

    # ge:0001076
    graph.add((gu('ge:0001076'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('ge:0001076'), gu('rdfs:comment'), Literal('o-antigen')))
    graph.add((gu('ge:0001076'), gu('rdfs:domain'), gu(':spfyId')))

    # ge:0001077
    graph.add((gu('ge:0001077'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('ge:0001077'), gu('rdfs:comment'), Literal('h-antigen')))
    graph.add((gu('ge:0001077'), gu('rdfs:domain'), gu(':spfyId')))

    # ge:0001684
    graph.add((gu('ge:0001684'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('ge:0001684'), gu('rdfs:comment'), Literal('k-antigen')))
    graph.add((gu('ge:0001684'), gu('rdfs:domain'), gu(':spfyId')))

    # genome file class
    graph.add((gu('g:Genome'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('g:Genome'), gu('rdfs:comment'), Literal('genome instance')))

    # Link genome file class and spfyid class.
    # If example=True, the reservation_triple() will do this instead.
    if not example:
        graph = ontology_link(graph, gu(':spfyId'), gu('g:Genome'))

    # dc:date on g:Genome
    graph.add((gu('dc:date'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('dc:date'), gu('rdfs:comment'), Literal('submission date')))
    graph.add((gu('dc:date'), gu('rdfs:domain'), gu('g:Genome')))

    # dc:description on g:Genome
    graph.add((gu('dc:description'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('dc:description'), gu('rdfs:comment'), Literal('class descriptor')))
    graph.add((gu('dc:description'), gu('rdfs:domain'), gu('g:Genome')))

    # bag of contigs class
    graph.add((gu('so:0001462'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('so:0001462'), gu('rdfs:comment'), Literal('bag of contigs')))

    # link bag of contigs
    if not example:
        graph = ontology_link(graph, gu('g:Genome'), gu('so:0001462'))

    # contig class
    graph.add((gu('g:Contig'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('g:Contig'), gu('rdfs:comment'), Literal('a contig')))

    # g:Identifier
    graph.add((gu('g:Identifier'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('g:Identifier'), gu('rdfs:comment'), Literal('accession number ie. record.id')))
    graph.add((gu('g:Identifier'), gu('rdfs:domain'), gu('g:Contig')))

    # g:DNASequence
    graph.add((gu('g:DNASequence'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('g:DNASequence'), gu('rdfs:comment'), Literal('a dna sequence')))
    graph.add((gu('g:DNASequence'), gu('rdfs:domain'), gu('g:Contig')))

    # g:Description
    graph.add((gu('g:Description'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('g:Description'), gu('rdfs:comment'), Literal('record.description')))
    graph.add((gu('g:Description'), gu('rdfs:domain'), gu('g:Contig')))

    # faldo:Reference
    # here, we differ from faldo's implementation:
    # in faldo, it is diffined as an edge type
    # instead, we define it as an addition class type a g:Contig may have
    graph.add((gu('faldo:Reference'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('faldo:Reference'), gu('rdf:comment'), Literal('a g:Contig that is referenced in some :Marker')))
    graph.add((gu('faldo:Reference'), gu('rdfs:subClassOf'), gu('g:Contig')))

    if not example:
        graph = ontology_link(graph, gu('so:0001462'), gu('g:Contig'))

    # faldo:Region
    graph.add((gu('faldo:Region'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('faldo:Region'), gu('rdf:comment'), Literal('a region containing the start and the end positions')))

    if not example:
        graph = ontology_link(graph, gu('g:Contig'), gu('faldo:Region'))

    # faldo:Position
    graph.add((gu('faldo:Position'), gu('rdf:type'), gu('owl:Class')))
    graph.add((gu('faldo:ExactPosition'), gu('rdfs:subClassOf'), gu('faldo:Position')))
    graph.add((gu('faldo:ForwardStrandPosition'), gu('rdfs:subClassOf'), gu('faldo:ExactPosition')))
    graph.add((gu('faldo:ReverseStrandPosition'), gu('rdfs:subClassOf'), gu('faldo:ExactPosition')))

    # the faldo ontology defines the position number under faldo:position
    # note the lower-case
    graph.add((gu('faldo:position'), gu('rdf:type'), gu('owl:DatatypeProperty')))
    graph.add((gu('faldo:position'), gu('rdfs:comment'), Literal('the numerical location of a position')))
    graph.add((gu('faldo:position'), gu('rdfs:domain'), gu('faldo:Position')))

    # faldo:Begin faldo:End
    # here, we also differe from faldo's implementation
    # faldo implements it as an edge type to a blank node
    # we instead implement it as a class type applied to that blank node
    graph.add((gu('faldo:Begin'), gu('rdfs:subClassOf'), gu('faldo:Position')))
    graph.add((gu('faldo:End'), gu('rdfs:subClassOf'), gu('faldo:Position')))

    # link faldo:Position to faldo:Reference
    if not example:
        graph = ontology_link(graph, gu('faldo:Region'), gu('faldo:Position'))

    # :Marker
    graph.add((gu(':Marker'), gu('rdf:type'), gu('owl:Class')))
    # the subclasses AntimicrobialResistanceGene and VirulenceFactor
    # were already defined in the generate_graph functions

    # link :Marker and faldo:Region
    if not example:
        graph = ontology_link(graph, gu('faldo:Region'), gu(':Marker'))

    return graph


def generate_example(args_dict):
    ontology_graph = generate_ontology(example=True)
    savvy_graphs = savvy(args_dict=args_dict, return_graphs=True)
    for g in savvy_graphs:
        ontology_graph = ontology_graph + g
    return ontology_graph


def main(args_dict):
    if 'i' in args_dict and args_dict['i'] is not None:
        # Then a file was supplied so we generate the ontology with an example.
        g = generate_example(args_dict)
        return write_graph(g)
    else:
        # A file wasn't supplied.
        # Generate the base ontology.
        g = generate_ontology(example=False)
        return write_graph(g)


if __name__ == '__main__':
    import argparse
    import os

    # parsing cli-input
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        help="FASTA file"
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
    parser.add_argument("--pi",
                        type=int,
                        help="Percentage of identity wanted to use against the database. From 0 to 100, default is 90%.",
                        default=90, choices=range(0, 100))
    args = parser.parse_args()
    # we make a dictionary from the cli-inputs and add are uris to it
    # mainly used for when a func needs a lot of the args
    args_dict = vars(args)

    # check/convert file to abspath
    if 'i' in args_dict and args_dict['i'] is not None:
        args_dict['i'] = os.path.abspath(args_dict['i'])

    # add nested dictionary to mimick output from spfy web-app
    spfy_options = {'vf': not args_dict['disable_vf'], 'amr': not args_dict['disable_amr'],
                    'serotype': not args_dict['disable_serotype']}
    # the 'options' field represents things the user (of the web-app) has chosen to display, we still run ALL analysis on their files so their choices are not added to module calls (& hence kept separate)
    args_dict['options'] = spfy_options

    print main(args_dict)
