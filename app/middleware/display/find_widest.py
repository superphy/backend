import logging
import pandas as pd
from itertools import tee, izip
from modules.loggingFunctions import initialize_logging

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def widest(reading_list):
    """
    Finds the gene with the widest coverage
    args:
        reading_list(list(pandas.DataFrame))
    return:
        (panadas.DataFrame)
    """
    # sanity check
    if reading_list:
        w = reading_list[0]
        for element in reading_list:
            if abs(element.hitstart - element.hitstop) > abs(w.hitstart - w.hitstop):
                w = element
        return w
    else:
        return reading_list


def overlap(row2, reading_window):
    """
    returns true is either end (ie. anypart) of row2 overlaps with the reading_window
    """
    row2_min_overlaps = reading_window['min'] <= min(row2.hitstart, row2.hitstop) <= reading_window['max']
    row2_max_overlaps = reading_window['min'] <= max(row2.hitstart, row2.hitstop) <= reading_window['max']
    return row2_min_overlaps or row2_max_overlaps


def check_alleles_multiple(hits, new_hits):
    """
    checks for multiple hits of the same gene and appends to new_hits. also strips out overlap
    """
    ## hits is only EVER empty when we've only want serotype
    # recall that serotype inof is stored in new_hits whereas hits contains everything BUT serotype
    if hits.empty:
        return new_hits

    # this checks for alleles overlap
    hits.sort_values(['analysis', 'filename', 'contigid', 'hitname', 'hitstart', 'hitstop'], inplace=True)

    # set the reading_frame to the first row
    reading_list = []
    reading_window = {'min': min(hits.iloc[0].hitstart, hits.iloc[0].hitstop),
                      'max': max(hits.iloc[0].hitstart, hits.iloc[0].hitstop)}

    for (i1, row1), (i2, row2) in pairwise(hits.iterrows()):
        if row1.analysis != row2.analysis:
            # at intersection between two hits
            at_intersection = True
        elif row1.filename != row2.filename:
            at_intersection = True
        elif row1.contigid != row2.contigid:
            at_intersection = True
        elif row1.hitname != row2.hitname:
            at_intersection = True
        elif not overlap(row2, reading_window):
            # is not overlap, then at this pt we're are a 2nd non-overlapping (& possibly doubly expressed) occurance of the gene
            at_intersection = True
        else:
            at_intersection = False

        if at_intersection:
            if not reading_list:
                # ie reading_list is empty
                # in this case since we're already at an intersection, then row1 is unique
                new_hits.append(dict(row1))
            else:
                new_hits.append(dict(widest(reading_list)))
            reading_list = []
            reading_window['min'] = min(row2.hitstart, row2.hitstop)
            reading_window['max'] = max(row2.hitstart, row2.hitstop)
        else:
            # ie we found an overlap
            # expand the reading_window
            reading_window['min'] = min(reading_window['min'], row2.hitstart, row2.hitstop)
            reading_window['max'] = max(reading_window['max'], row2.hitstart, row2.hitstop)
            reading_list.append(row2)

            # check for end of iteration
            if cmp(dict(row2), dict(hits.iloc[-1])) == 0:
                new_hits.append(dict(widest(reading_list)))

    return new_hits


def weird_name(subq, subp):
    """
    returns true if either value is a weird name and short be ignored
    """
    t = ('st', 'tia')
    return (subq in t) or (subp in t)


def substring_cut(hits):
    """
    iterrows should return deep copies, not sure if this will work properly
    """
    for i1, row1 in hits.iterrows():
        subframe = hits.loc[hits.index > i1]
        for i2, row2 in subframe.iterrows():
            if ((row1.hitname.lower() in row2.hitname.lower()) or (
                        row2.hitname.lower() in row1.hitname.lower())) and not weird_name(row1.hitname, row2.hitname):
                if len(row1.hitname) > len(row2.hitname):
                    hits.loc[i1, 'hitname'] = row2.hitname
                elif len(row1.hitname) < len(row2.hitname):
                    hits.loc[i2, 'hitname'] = row1.hitname
    return hits


def check_alleles(converted_json):
    """
    Args:
        converted_json : a list of dictionaries that have removed results not specific to the user's requests.
    """
    # we are working with the new dict format that is directly converted to json
    hits = pd.DataFrame(converted_json)
    if hits.empty:
        raise Exception('The Panadas DF from gene_dict is empty.')
    new_hits = []

    log.debug('Pandas DF in check_alleles(): ' + str(hits))

    # we're not interested in checking serotype, so we drop it
    if 'Serotype' in hits.analysis.unique():
        new_hits.append(dict(hits[hits['analysis'] == 'Serotype'].iloc[0]))
        hits = hits[hits['analysis'] != 'Serotype']

    log.debug(new_hits)

    # we've update the db for VF so an allele check is only needed for AMR
    if 'Antimicrobial Resistance' in hits.analysis.unique():
        # strip allele info from data
        # assumes if an underscore is in a gene name, that anything after the underscore refers to an allele
        hits['hitname'] = hits['hitname'].apply(lambda x: x.split('_')[0].split('-I')[0].split('-V')[0])
        hits = substring_cut(hits)

    # this checks for alleles overlap
    new_hits = check_alleles_multiple(hits, new_hits)
    return new_hits
