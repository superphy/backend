import logging
import re
import pandas as pd
import cPickle as pickle
from modules.loggingFunctions import initialize_logging
from middleware.display.find_widest import check_alleles
from middleware.graphers.turtle_utils import actual_filename
from middleware.models import unpickle
from middleware.modellers import model_vf

# logging
log_file = initialize_logging()
log = logging.getLogger(__name__)


def json_return(gene_dict, args_dict):
    """
    This converts the gene dict into a json format for return to the front end
    """
    log.debug('args_dict: ' + str(args_dict))
    log.debug('gene_dict: ' + str(gene_dict))
    json_r = []

    # strip gene_dicts that user doesn't want to see
    # remember, we want to run all analysis on our end so we have that data in blazegraph
    d = dict(gene_dict)

    #log.debug('Results Gene Dict: ' + str(d))

    for analysis in gene_dict:
        if analysis == 'Serotype' and not args_dict['options']['serotype']:
            del d['Serotype']
        if analysis == 'Antimicrobial Resistance' and not args_dict['options']['amr']:
            del d['Antimicrobial Resistance']
        if analysis == 'Virulence Factors' and not args_dict['options']['vf']:
            del d['Virulence Factors']
    gene_dict = d

    log.debug('After deletion from gene_dict: ' + str(gene_dict))

    for analysis in gene_dict:
        if analysis == 'Serotype':
            instance_dict = {}
            instance_dict['filename'] = actual_filename(args_dict['i'])
            instance_dict['hitname'] = str(gene_dict[analysis].values()).replace(',', ' ').replace("'","").strip("[").strip("]")
            if not "No prediction" in instance_dict['hitname']:
                instance_dict['hitname'] = instance_dict['hitname'].replace(" ",":",1).replace(" ","")
            instance_dict['contigid'] = 'n/a'
            instance_dict['analysis'] = analysis
            instance_dict['hitorientation'] = 'n/a'
            instance_dict['hitstart'] = 'n/a'
            instance_dict['hitstop'] = 'n/a'
            instance_dict['hitcutoff'] = 'n/a'
            json_r.append(instance_dict)
        else:
            for contig_id in gene_dict[analysis]:
                # where gene_results is a list for amr/vf
                for item in gene_dict[analysis][contig_id]:
                    # for w/e reason vf, has a '0' int in the list of dicts
                    # TODO: bug fix^
                    if type(item) is dict:
                        instance_dict = {}
                        instance_dict['filename'] = actual_filename(args_dict['i'])
                        instance_dict['contigid'] = contig_id
                        instance_dict['analysis'] = analysis
                        instance_dict['hitname'] = item['GENE_NAME']
                        instance_dict['hitorientation'] = item['ORIENTATION']
                        instance_dict['hitstart'] = item['START']
                        instance_dict['hitstop'] = item['STOP']
                        # For VF.
                        if 'RAW' in item:
                            # Search the GI.
                            pattern = r'gi:\d*'
                            a = re.search(pattern, item['RAW'])
                            # Try searching for other format.
                            if not a:
                                pattern = r'gi\|\d*'
                                a = re.search(pattern, item['RAW'])
                            # Try searching for GB.
                            if not a:
                                pattern = r'gi\|\d*'
                                b = re.search(pattern, item['RAW'])
                            if a:
                                gi = a.group()
                                # Calling it 'aro' for now.
                                # TODO: rename to something generic (have to modify grouch).
                                instance_dict['aro'] = 'https://www.ncbi.nlm.nih.gov/protein/' + gi
                                # Find the longname.
                                longname = item['RAW'].split(gi)[-1][2:]
                                instance_dict['longname'] = longname
                            elif b:
                                s = b.group()
                                gb = s.split('|')[-1]
                                instance_dict[
                                    'aro'] = 'https://www.ncbi.nlm.nih.gov/nuccore/' + gb
                                # Too many cases to parse.
                                instance_dict['longname'] = item['RAW']
                            else:
                                instance_dict['aro'] = 'n/a'
                                instance_dict['longname'] = item['RAW']
                        if analysis == 'Antimicrobial Resistance':
                            instance_dict['hitcutoff'] = item['CUT_OFF']
                        else:
                            instance_dict['hitcutoff'] = args_dict['pi']
                        json_r.append(instance_dict)
    return json_r

def has_failed(json_r):
    # check if we tried to beautify a failed analysis
    failed = False
    if isinstance(json_r, list):
        if not json_r:
            failed = True
    elif isinstance(json_r,pd.DataFrame):
        if json_r.empty:
            failed = True
    return failed

def handle_failed(json_r, args_dict):
    ret = []
    instance_dict = {}
    instance_dict['filename'] = actual_filename(args_dict['i'])
    instance_dict['contigid'] = 'n/a'
    #instance_dict['analysis'] = analysis
    instance_dict['hitname'] = 'No Results Found.'
    instance_dict['hitorientation'] = 'n/a'
    instance_dict['hitstart'] = 'n/a'
    instance_dict['hitstop'] = 'n/a'
    instance_dict['hitcutoff'] = 'n/a'

    if not args_dict['options']['serotype']:
        t = dict(instance_dict)
        t.update({'analysis':'Serotype'})
        ret.append(t)
    if not args_dict['options']['vf']:
        t = dict(instance_dict)
        t.update({'analysis':'Virulence Factors'})
        ret.append(t)
    if not args_dict['options']['amr']:
        t = dict(instance_dict)
        t.update({'analysis':'Antimicrobial Resistance'})
        ret.append(t)
    return ret

# TODO: convert this to models-only.
def beautify(gene_dict, args_dict=None):
    '''
    Converts a given 'spit' datum (a dictionary with our results from rgi/ectyper) to a json form used by the frontend. This result is to be stored in Redis by the calling RQ Worker.
    :param args_dict: The arguments supplied by the user. In the case of spfy web-app, this is used to determine which analysis options were set.
    :param pickled_dictionary: location of the .p pickled dictionary object. This is supplied by the enqueue call in spfy.py
    :param gene_dict: optionally, if using this to test via cli, you can supply the actual dictionary object.
    :return: json representation of the results, as required by the front-end.
    '''
    if isinstance(gene_dict, str): # For the tests.
        gene_dict = pickle.load(open(gene_dict, 'rb'))
    # Convert the old ECTYper's dictionary structure into list and adds metadata (filename, etc.).
    json_r =  json_return(gene_dict, args_dict)
    # For VF/AMR, find widest gene matched. Strip shorter matches.
    if args_dict['options']['vf'] or args_dict['options']['amr']:
        json_r = check_alleles(json_r)
    # Check if there is an analysis module that has failed in the result.
    if has_failed(json_r):
        # If failed, return.
        return handle_failed(json_r, args_dict)
    else:
        return json_r

def display_subtyping(pickled_result, args_dict=None):
    result = unpickle(pickled_result)
    if isinstance(result, dict):
        # VF.
        list_return = beautify(gene_dict=result, args_dict=args_dict)
        assert isinstance(list_return, list)
        l = model_vf(list_return)
        return l
    elif isinstance(result, list):
        # Serotyping.
        return result
    else:
        raise Exception("beautify() could not handle pickled file: {0}.".format(pickled_result))
