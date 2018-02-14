import logging
from modules.loggingFunctions import initialize_logging
from modules.comparisons.logical_queries import resolve_spfyids, resolve_spfyids_negated

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


def handle_logical(group):
    """
    Accepts a (list) group (of relations) as input, hanldes negation/logical operators, and returns a set of spfyids that match the relation-attribute & account for the operators.
    """
    # sanity check
    if type(group) is not list:
        raise Exception("Invalid Argument. Requires a list of relation-attribute pairs for a group.")
    # create a blank universe which is our end result
    universe = set()
    for index, d in enumerate(group):
        # d is of form: {"negated":false,"relation":"http://purl.obolibrary.org/obo/GENEPIO_0001076","attribute":"O136","logical":null}

        # create a temporary set before we merge with universe

        # get the initial set
        if d['negated']:
            # get everything not d
            log.info('Handling negation for pair: ' + d['relation'] + d['attribute'])
            log.info(index)
            current_set = resolve_spfyids_negated(d['relation'], d['attribute'])
        else:
            # get spfyids in regular fashion
            current_set = resolve_spfyids(d['relation'], d['attribute'])
        log.info('Length of current set: ' + str(len(current_set)))
        log.info('Length of current universe: ' + str(len(universe)))

        # handle any logical operators, if applicable
        if index > 0 and 'logical' in group[index - 1].keys():
            # note: a logical operator should be REQUIRED if relation-attribute pairs > 1
            operator = group[index - 1]['logical']
            if operator == 'AND':
                universe = universe.intersection(current_set)
            elif operator == 'OR':
                universe = universe.union(current_set)
            log.info('Length of universe after logical: ' + str(len(universe)))
        else:
            # is index <= 0 (then index=0) and it is the current universe
            universe = current_set
            log.info('Length of initial universe: ' + str(len(universe)))
    return universe


if __name__ == "__main__":
    d1 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O157",
          "logical": "OR"}
    u_d1 = handle_logical([d1])
    log.info('*Length of u_d1: ' + str(len(u_d1)))
    d2 = {"negated": False, "relation": "http://purl.obolibrary.org/obo/GENEPIO_0001076", "attribute": "O136"}
    u_d2 = handle_logical([d2])
    log.info('*Length of u_d2: ' + str(len(u_d2)))
    u_d1_or_d2 = handle_logical([d1, d2])
    log.info('*Length of u_d1_or_d2: ' + str(len(u_d1_or_d2)))
