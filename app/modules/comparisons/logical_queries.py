# this is used to build the actual groups, based on user-selected options, for Fisher's
import config
import logging
import time
from modules.loggingFunctions import initialize_logging
from middleware.graphers.turtle_utils import generate_uri as gu
from modules.comparisons.sparql_utils import generate_prefixes
from middleware.decorators import toset, tolist, tostring, prefix, submit
from modules.comparisons.frontend_queries import is_group

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


### For querying spfyIds

@toset
@submit
@prefix
def query_spfyids(relation, attribute):
    """
    Grabs all objectids having the relation.
    """
    query = """
    SELECT ?s WHERE {{
        ?s2 <{relation}> '{attribute}' ; (:hasPart|:isFoundIn) ?s .
        ?s a <{spfyIdUri}> .
    }}
    """.format(relation=relation, attribute=attribute, spfyIdUri=gu(':spfyId'))
    return query


@toset
@submit
@prefix
def query_objectids(relation, attribute):
    """
    Grabs all objectids having the relation. This is used when attributes are directly linked to a spfyid object.
    """
    query = """
    SELECT ?s WHERE {{
        ?s <{relation}> '{attribute}' .
    }}
    """.format(relation=relation, attribute=attribute)
    return query


# Negated:

@toset
@submit
@prefix
def query_spfyids_negated(relation, attribute):
    """
    Grabs all objectids having the relation.
    """
    query = """
    SELECT ?s WHERE {{
        ?s2 <{relation}> ?o ; (:hasPart|:isFoundIn) ?s .
        ?s a <{spfyIdUri}> .
        MINUS {{?s2 <{relation}> '{attribute}'}}
    }}
    """.format(relation=relation, attribute=attribute, spfyIdUri=gu(':spfyId'))
    return query


@toset
@submit
@prefix
def query_objectids_negated(relation, attribute):
    """
    Grabs all objectids having the relation.
    """
    query = """
    SELECT ?s WHERE {{
        ?s <{relation}> ?o .
        MINUS {{?s <{relation}> '{attribute}'}}
    }}
    """.format(relation=relation, attribute=attribute)
    return query


### For determining which query to use

@tolist
@submit
@prefix
def query_objecttypes(uri):
    """
    Grabs the types of a given uri.
    """
    query = """
    SELECT ?s WHERE {{
        <{uri}> a ?s .
    }}
    """.format(uri=uri)
    return query


@tostring
@submit
@prefix
def query_single_objectid(relation, attribute):
    """
    Grabs a single object id having the relation.
    """
    query = """
    SELECT ?s WHERE {{
        ?s <{relation}> '{attribute}' .
    }}
    LIMIT 1
    """.format(relation=relation, attribute=attribute)
    return query


def directlink_spfyid(relation, attribute):
    """
    Tells you if a given relation-attribute pair has a direct link to a given spfyId.
    This is required for generating more complex SPARQL queries.
    """
    objectid = query_single_objectid(relation, attribute)
    objectypes = query_objecttypes(objectid)
    return unicode(gu(':spfyId')) in objectypes


### Actual called functions

def resolve_spfyids(relation, attribute):
    """
    Args:
        relation: ex. "http://purl.obolibrary.org/obo/GENEPIO_0001076"
        attribute: ex. "O136"
    Ret:
    """
    if directlink_spfyid(relation, attribute):
        # if we have a direct link to a spfyid, we can generate automatically.
        set_spfyids = query_objectids(relation, attribute)
    else:
        set_spfyids = query_spfyids(relation, attribute)
    return set_spfyids


def resolve_spfyids_negated(relation, attribute):
    """
    A special case of resolve_spfyids() as the underlying queries have to be different.
    """
    if directlink_spfyid(relation, attribute):
        # if we have a direct link to a spfyid, we can generate automatically.
        set_spfyids = query_objectids_negated(relation, attribute)
    else:
        set_spfyids = query_spfyids_negated(relation, attribute)
    return set_spfyids


@toset
@submit
@prefix
def query_targets(spfyid, target):
    # base select query
    query = """
    SELECT ?target WHERE {{
        <{spfyid}> (:hasPart|:isFoundIn) ?target .
    """.format(spfyid=spfyid)
    # the queries have to be structured differently if the target is a object type or is a specific instance
    if is_group(target):
        # then targetUri is a object type
        query += " ?target a <{target}> .}}".format(target=target)
    else:
        # then targetUri is an attribute
        query += " ?targetobject <{target}> ?target.}}".format(target=target)
    return query


if __name__ == "__main__":
    # print resolve_spfyids(gu('ge:0001076'), 'O157')
    # print testcase_pollviaspfy()
    print resolve_spfyids(gu('g:Identifier'), 'LGNE01000001.1')
