import pandas
import rdflib
from modules.metadata.metadata import generate_metadata_graph, read

metadata_sheet = 'tests/example_metadata.xlsx'


def test_read_excel():
    assert type(read(metadata_sheet)) is pandas.core.frame.DataFrame


def test_metadata():
    df = read(metadata_sheet)
    graph = generate_metadata_graph(df, {':spfy1'})
    assert type(graph) is rdflib.graph.Graph
