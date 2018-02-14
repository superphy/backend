import logging
from modules.loggingFunctions import initialize_logging
import scipy.stats as stats
import pandas as pd

# import time

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


def fishers(queryAttributeUriA, queryAttributeUriB, targetUri, results):
    # split the results into sub vars
    ## num of uniq subjects in A
    nA = results[0]['N']
    ## num of uniq subjects in B
    nB = results[1]['N']
    ## dictionary with the results from A
    dictA = results[0]['d']
    ## dictionary with the results from B
    dictB = results[1]['d']
    log.debug(str(nA))
    log.debug(str(nB))
    log.debug(str(len(dictA)))
    log.debug(str(len(dictB)))

    # join all possible targets as req for Fisher's
    # we could instead query the db for `DISTINCT ?s WHERE ?s a targetUri`, but I'm not interested in targets that neither queryA nor queryB has.
    all_targets = set(dictA.keys())
    all_targets.update(dictB.keys())
    log.debug('Length of All Targets: ' + str(len(all_targets)))

    # create a pandas dataframe for storing aggregate results from fisher's
    df = pd.DataFrame(
        columns=['target', 'queryA', 'queryB', 'presentQueryA', 'absentQueryA', 'presentQueryB', 'absentQueryB',
                 'pvalue', 'oddsratio'])

    # iterate through targets and perform fisher's
    for index, target in enumerate(all_targets):
        log.debug('Target: ' + target)
        # tags for dataframe
        queryA = queryAttributeUriA
        queryB = queryAttributeUriB
        # check if target is found in queryA
        if target in dictA.keys():
            presentQueryA = len(dictA[target])
        else:
            presentQueryA = 0
        absentQueryA = nA - presentQueryA
        log.debug('presentQueryA: ' + str(presentQueryA))
        log.debug('absentQueryA: ' + str(absentQueryA))
        # check if target is found in queryB
        if target in dictB.keys():
            presentQueryB = len(dictB[target])
        else:
            presentQueryB = 0
        absentQueryB = nB - presentQueryB
        log.debug('presentQueryB: ' + str(presentQueryB))
        log.debug('absentQueryB: ' + str(absentQueryB))
        if absentQueryB < 0 or absentQueryA < 0:
            log.error('A:')
            log.error(dictA[target])
            log.error('B:')
            log.error(dictB[target])
        # compute fisher's exact test
        # table structure is:
        #           queryUriA   queryUriB
        #   Present
        #   Absent
        pvalue, oddsratio = stats.fisher_exact([[presentQueryA, presentQueryB], [absentQueryA, absentQueryB]])
        # add results to new row on pandas dataframe
        df.loc[index] = [target, queryA, queryB, presentQueryA, absentQueryA, presentQueryB, absentQueryB, pvalue,
                         oddsratio]

    return df


if __name__ == "__main__":
    '''
    For testing...
    '''
    # start = time.time()
    # print fishers('O157', 'O101', gu(':VirulenceFactor'), gu('ge:0001076'), gu('ge:0001076'))
    # stop = time.time()
    # print(stop-start)
