import os
import pandas as pd
from rdflib import Graph, Literal
from werkzeug.utils import secure_filename
from modules.comparisons.logical_queries import resolve_spfyids
from middleware.graphers.turtle_utils import generate_uri as gu
from middleware.blazegraph.upload_graph import upload_graph
from modules.metadata.mappings import mapping

d = {'Human': 'http://purl.bioontology.org/ontology/NCBITAXON/9606',
     'Bovine': 'http://purl.bioontology.org/ontology/NCBITAXON/9913'}


def parse(column_header, cell_value, sid, graph):
    try:
        # Look up the header in the mapping dictionary.
        d = mapping[column_header]
        # Add the cell into the graph.
        graph.add((gu(sid), gu(d['relation']), Literal(cell_value)))
        # Add a human-readable description of the relation type, if it's defined.
        if d['human_readable']:
            graph.add((gu(d['relation']), gu('dc:description'), Literal(d['human_readable'])))
    except:
        # The column_header wasn't found in mapping.
        pass
    return graph


def read(filename):
    """
    Args:
        filename(Str): an absolute path to the file
    """
    extension = filename.split('.')[-1]
    # Check we support the filetype.
    assert extension in ('xls', 'xlsx', 'csv')

    if extension in ('xls', 'xlsx'):
        return pd.read_excel(filename)
    else:
        return pd.read_csv(filename)


def generate_metadata_graph(df, spfyid=None):
    graph = Graph()
    for f in df.filename:
        # Resolve the spfyid for that file.
        # Note: we have to run secure_filename to replicate the same saved
        # name in the db.
        # Spfyid is accepted as a parameter for testing purposes.
        if not spfyid:
            spfyid = resolve_spfyids(gu('dc:description'), secure_filename(f))
        # check if a spfyid was found
        # Note: spfyid should be a Set
        if spfyid:
            # take the first (and only) spfyid
            sid = str(spfyid.pop())
            # Retrieve the row specific to that filename.
            row = df[df.filename == f]
            # Iterate through the column headers.
            for column_header in row:
                # Grab the value at that cell.
                cell_value = row[column_header][0]
                # Check that the cell doesn't just say 'undefined'
                if cell_value not in ('undefined', 'n/a', 'NaN'):
                    # There's a unique case for the serotype.
                    if column_header == 'serotype':
                        # Split the serotype value in O- and H- type.
                        for st in cell_value.upper().split(':'):
                            if 'O' in st:
                                # We pass the O-Type instead of using the
                                # column header
                                graph = parse('O-Type', st, sid, graph)
                            elif 'H' in st:
                                graph = parse('H-Type', st, sid, graph)
                    else:
                        # Otherise, the normal.
                        graph = parse(column_header, cell_value, sid, graph)
    return graph


def upload_metadata(filename):
    df = read(filename)
    graph = generate_metadata_graph(df)
    upload_graph(graph)
    return graph.serialize(format='json-ld')
