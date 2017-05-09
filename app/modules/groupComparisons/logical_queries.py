import config
import logging
import time
from modules.loggingFunctions import initialize_logging
from modules.turtleGrapher.turtle_utils import generate_uri as gu
from modules.groupComparisons.sparql_utils import generate_prefixes
from modules.groupComparisons.decorators import toset, tolist, tostring, prefix, submit

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

@tostring
@submit
@prefix
def query_objectids(relation, attribute):
    '''
    Grabs all objectids having the relation.
    '''
    query = """
    SELECT ?s WHERE {{
        ?s <{relation}> '{attribute}' .
    }}
    """.format(relation=relation,attribute=attribute)
    return query

@tostring
@submit
@prefix
def query_single_objectid(relation, attribute):
    '''
    Grabs a single object id having the relation.
    '''
    query = """
    SELECT ?s WHERE {{
        ?s <{relation}> '{attribute}' .
    }}
    LIMIT 1
    """.format(relation=relation,attribute=attribute)
    return query

@tolist
@submit
@prefix
def query_objecttypes(uri):
    '''
    Grabs the types of a given uri.
    '''
    query = """
    SELECT ?s WHERE {{
        <{uri}> a ?s .
    }}
    """.format(uri=uri)
    return query

def directlink_spfyid(relation, attribute):
    '''
    Tells you if a given relation-attribute pair has a direct link to a given spfyId.
    This is required for generating more complex SPARQL queries.
    '''
    objectid = query_single_objectid(relation, attribute)
    print objectid
    objectypes = query_objecttypes(objectid)
    print objectypes
    return unicode(gu(':spfyId')) in objectypes

def resolve_spfyids(relation, attribute):
    '''
    Args:
        relation: ex. "http://purl.obolibrary.org/obo/GENEPIO_0001076"
        attribute: ex. "O136"
    Ret:
    '''
    print directlink_spfyid(relation, attribute)
    if directlink_spfyid(relation, attribute):
        # if we have a direct link to a spfyid, we can generate automatically.
        spfyids = query_objectids(relation, attribute)
        return spfyids

if __name__ == "__main__":
    resolve_spfyids(gu('ge:0001076'), 'O157')
