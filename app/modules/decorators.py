import config
import logging
from functools import wraps
from SPARQLWrapper import SPARQLWrapper, JSON
from modules.loggingFunctions import initialize_logging

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)

blazegraph_url = config.database['blazegraph_url']
#blazegraph_url = 'http://localhost:8080/bigdata/sparql'

def tofromHumanReadable(func):
    '''
    Converts between to and from URIs and human-readable names.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        def parse(r):
            @tostring
            @submit
            @prefix
            def query_description():
                query = """
                SELECT ?description WHERE {{
                    <{r}> dc:description ?description .
                }}
                """.format(r=r)
                return query

            @tostring
            @submit
            @prefix
            def query_uri():
                query = """
                SELECT ?uri WHERE {{
                    ?uri dc:description <{r}> .
                }}
                """.format(r=r)
                return query
            # check if this is a uri
            if 'http' in r:
                # query for a description
                response = query_description()
                # no description found
                if response == "":
                    return r
                else:
                    return response
            # we've received a description
            else:
                # check for a URI
                response = query_uri()
                if response == "":
                    return r
                else:
                    return response
        results = func(*args, **kwargs)
        # check if we received a list or set
        if type(results) in (list, set):
            # create a blank list for results
            l = []
            for r in results:
                l.append(parse(r))
            if type(results) is set:
                return set(l)
            else:
                return l
        else:
            return parse(results)
    return func_wrapper

def tojson(func):
    '''
    A decorator to convert JSON response of sparql query to a simple string.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        l = []
        for result in results['results']['bindings']:
            # create a blank dictionary per result
            d = {}
            keys = sorted(result.keys())
            # Note: though this is writeen as a loop, we expect only 1 key in keys
            for k in keys:
                # get the value at that key
                d[k] = result[k]['value']
            l.append(d)
        log.debug(l)
        return l
    return func_wrapper

def tostring(func):
    '''
    A decorator to convert JSON response of sparql query to a simple string.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        s = ""
        for result in results['results']['bindings']:
            keys = result.keys()
            # Note: though this is writeen as a loop, we expect only 1 key in keys
            for k in keys:
                # get the value at that key
                s += (result[k]['value'])
        log.debug(s)
        return s
    return func_wrapper

def toset(func):
    '''
    A decorator to convert JSON response of sparql query to a set.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        st = set()
        for result in results['results']['bindings']:
            keys = result.keys()
            # Note: though this is written as a loop, we expect only 1 key in keys
            for k in keys:
                # get the value at that key
                st.add(result[k]['value'])
        log.debug(st)
        return st
    return func_wrapper

def tolist(func):
    '''
    A decorator to convert JSON response of sparql query to a list.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        l = []
        for result in results['results']['bindings']:
            keys = result.keys()
            # Note: though this is writeen as a loop, we expect only 1 key in keys
            for k in keys:
                # get the value at that key
                l.append(result[k]['value'])
        log.debug(l)
        return l
    return func_wrapper

def prefix(func):
    '''
    A decorator to add prefixes to a given query generation function.
    Uses namespaces defined in the config.py file to generate all the prefixes you might need in a SPARQL query.
    Returns a string.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # generate prefixes
        prefixes = ''
        for key in config.namespaces.keys():
            if key is 'root':
                prefixes += 'PREFIX : <{name}> '.format(name=config.namespaces['root'])
            else:
                prefixes += 'PREFIX {prefix}: <{name}> '.format(prefix=key, name=config.namespaces[key])
        # generate the query
        query = func(*args, **kwargs)
        return prefixes + query
    return func_wrapper

def submit(func):
    '''
    A decorator to submit a given query generation function.
    '''
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        query = func(*args, **kwargs)
        log.debug(query)
        sparql = SPARQLWrapper(blazegraph_url)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        log.debug(results)
        return results
    return func_wrapper
