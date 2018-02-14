# this module generates the options for selection by the user on the front-end
import config
import logging
import time
# import cPickle as pickle
from functools import wraps
from SPARQLWrapper import SPARQLWrapper, JSON
from modules.loggingFunctions import initialize_logging
from middleware.graphers.turtle_utils import generate_uri as gu
from modules.comparisons.sparql_utils import generate_prefixes
from middleware.decorators import toset, tolist, submit

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

blazegraph_url = config.database['blazegraph_url']


# blazegraph_url = 'http://localhost:8080/bigdata/sparql'

@tolist
@submit
def get_instances(objectTypeUri):
    """
    Gets all instances of a given object type.
    Example use: to get all :Markers in blazegraph.
    Args:
        objecttype: a rdflib.URI
    Returns:
        a list of the result.
        :param objectTypeUri: 
    """
    # SPARQL Query
    query = """
    SELECT DISTINCT ?objectinstance WHERE {{
        ?objectinstance a <{objectTypeUri}> .
    }}
    """.format(objectTypeUri=objectTypeUri)
    return query


@tolist
@submit
def get_all_attribute_types():
    """
    Returns all types of attributes (ie. all edge types) currently in blazegraph.
    """
    # SPARQL Query
    query = """
    SELECT DISTINCT ?attributetype WHERE {{
        ?anything ?attributetype ?attribute .
    }}
    """
    return query


@tolist
@submit
def get_attribute_values(attributeTypeUri):
    """
    Given an attribute type(ex. ge:0001076, aka. O-Type).
    Returns a list of all distinct attribute values.
    """
    if is_group(attributeTypeUri):
        # SPARQL Query
        query = """
        SELECT DISTINCT ?s WHERE {{
            ?s a <{attributeTypeUri}> .
        }}
        LIMIT 100
        """.format(attributeTypeUri=attributeTypeUri)
    else:
        # SPARQL Query
        query = """
        SELECT DISTINCT ?attribute WHERE {{
            ?s <{attributeTypeUri}> ?attribute .
        }}
        LIMIT 100
        """.format(attributeTypeUri=attributeTypeUri)

    return query


@toset
@submit
def get_types():
    """
    Gets a list distinct rdf:type objects (ie. all possible object types) by querying the blazegraph db.
    Used to determine if a given query Uri is an object type or an attribute of the object.
    Returns just the URIs.
    """
    # SPARQL Query
    query = """
    SELECT DISTINCT ?objecttype WHERE {{
        ?objectinstance a ?objecttype .
    }}
    """
    return query


def is_group(uri):
    """
    Returns True if a given URI is in the list of possible object types (ie. group types), otherwise False (ie. attributeType).
    """
    # log.info('is_group:' + uri)
    # log.info('is_group: get_types()')
    types = get_types()
    # log.info(types)
    isgroup = unicode(uri) in types
    # log.info('is_group:' + str(isgroup))
    return isgroup


if __name__ == "__main__":
    '''
    For testing...
    '''
    print log_file
    # get all possible attribute types
    log.info(get_all_attribute_types())
    # user selects an attribute type => get all distinct attribute values
    log.info(get_attribute_values(gu('ge:0001076')))
    # user selects two specific values
    # at this point, we no longer have to worry about query speed because none of the below queries are immediately returned to the ui (instead, they are handled in RQ)
    start = time.time()
    log.info(start)
    log.info(query('O157', 'O101', gu(':VirulenceFactor'), gu('ge:0001076'), gu('ge:0001076')))
    stop = time.time()
    log.info(stop - start)
