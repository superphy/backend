import logging
from modules.loggingFunctions import initialize_logging
from modules.comparisons.handle_logical import handle_logical
from modules.comparisons.logical_queries import query_targets
from modules.comparisons.fishers import fishers
from middleware.decorators import tofromHumanReadable

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


def convert(value):
    """
    Used to convert the human-readable string back into a proper URI.
    """

    @tofromHumanReadable
    def todict(q):
        return q

    d = todict(value)
    return d.keys()


def collapse(dict_targets):
    """
    Collapses all targets into a dictionary mapping each target to a set of the spfyIds its found in.
    Arg:
        dict_targets: (dict) of structure {spfyid: set(targets)}
    """
    # define the base dictionary
    d = {}
    for spfyid, set_targets in dict_targets.iteritems():
        for target in set_targets:
            if target not in d.keys():
                # then that gene has not spfyId assoc. with it yet
                d[target] = {spfyid}
            else:
                d[target].add(spfyid)
    return d


def groupcomparisons(groups, target):
    # # convert the target from its human-readable string as displayed
    # # to the user, back to the actual user
    # if type(target) not in (str, unicode):
    #     raise Exception('groupcomparisons() was called with target: ' + str(target) + ' of type ' + str(type(target)) + ' which is not str')
    # # we want everything to be uris, so only convert when necessary
    # if 'http:' not in target:
    #     print 'groupcomparisons(): target before is ' + str(target) + ' of type ' + str(type(target))
    #     target = unicode(convert(target))
    #     print 'groupcomparisons(): target after is ' + str(target) + ' of type ' + str(type(target))
    # else:
    #     print 'groupcomparisons(): not converting target which is ' + str(target) + ' of type ' + str(type(target))
    # # iterate through the groups and convert them back to uris as well
    # d = []
    # # groups is a list of two lists
    # for group in groups:
    #     # group is a list of dicts
    #     l = []
    #     for relation in group:
    #         # relation is a dict
    #         g = dict(relation)
    #         r = relation['relation']
    #         # again, have to check
    #         if 'http:' not in r:
    #             g.update({'relation':convert(r)})
    #         l.append(g)
    #     d.append(l)
    # groups = d

    log.debug(groups)
    # define a list of sets to hold all spfyids per group
    sets_spfyids = []
    # define a list of nested dictionaries mapping spfyid to all of its targets
    # this ends up being [{spfyid: set(targets)}, spfyid: set(targets)}] with spfyids being multiple
    dicts_targets = []
    # define a list (for groups) of dictionary of targets to sets of spfyids
    # end structure is: [{gene:set(spfyids)}, {gene:set(spfyids)}] with genes being multiple
    collapsed_targets = []
    # define terms required for fishers
    queryAttributeUris = []
    # define a results list to pass to fishers.py
    results = []

    # enum through the groups and parse negations/logical operators to build a set of spfyids
    for index, group in enumerate(groups):
        log.debug(index)
        sets_spfyids.append(handle_logical(group))
        # define a blank dictionary for that spfyid
        dicts_targets.append({})
        for spfyid in sets_spfyids[index]:
            dicts_targets[index][spfyid] = query_targets(spfyid, target)

        # collapse/invert the results so we use targets as keys instead of spfyids
        collapsed_targets.append(collapse(dicts_targets[index]))

        # put together the results for that group
        N = len(sets_spfyids[index])
        results.append({})
        results[index]['N'] = N
        results[index]['d'] = collapsed_targets[index]

        # put together the term/labels for fishers
        queryAttributeUris.append("")
        for i, query in enumerate(group):
            # where query is of form:
            # # d is of form: {"negated":false,"relation":"http://purl.obolibrary.org/obo/GENEPIO_0001076","attribute":"O136","logical":null}
            # negation
            if query['negated']:
                queryAttributeUris[index] += 'NOT '
            # attribute
            queryAttributeUris[index] += query['attribute'] + ' '
            # logical operator
            if len(group) > 1 and i < len(group) - 1 and 'logical' in query.keys():
                queryAttributeUris[index] += query['logical'] + ' '
        queryAttributeUris[index] = queryAttributeUris[index].strip()

    log.debug(queryAttributeUris[0])
    log.debug(queryAttributeUris[1])
    df = fishers(queryAttributeUris[0], queryAttributeUris[1], target, results)
    # apply the human-readable conversion
    df['target'] = df['target'].apply(convert)
    return df.to_json(orient='split')


if __name__ == "__main__":
    import time

    # test for OR
    da1 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O157",
           "logical": "OR"}
    da2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O136"}
    da = [da1, da2]

    db1 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O84",
           "logical": "OR"}
    db2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O54"}
    db = [db1, db2]

    target = "https://www.github.com/superphy#Marker"

    start = time.time()
    log.info([da, db])
    log.info(groupcomparisons([da, db], target))
    stop = time.time()
    log.info(stop - start)

    ## test NOT
    da1 = {"negated": True, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O157",
           "logical": "OR"}
    da2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O136"}
    da = [da1, da2]

    db1 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O84",
           "logical": "OR"}
    db2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O54"}
    db = [db1, db2]

    target = "https://www.github.com/superphy#Marker"

    start = time.time()
    log.info([da, db])
    log.info(groupcomparisons([da, db], target))
    stop = time.time()
    log.info(stop - start)

    ## test AND with NO with  non direct link
    da1 = {"negated": True, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O157",
           "logical": "AND"}
    da2 = {"negated": False, "relation": "http://www.biointerchange.org/gfvo#Identifier", "attribute": "LGNE01000001.1"}
    da = [da1, da2]

    db1 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O84",
           "logical": "OR"}
    db2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O54"}
    db = [db1, db2]

    target = "https://www.github.com/superphy#Marker"

    start = time.time()
    log.info([da, db])
    log.info(groupcomparisons([da, db], target))
    stop = time.time()
    log.info(stop - start)
