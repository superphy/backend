import os
import pytest
import cPickle as pickle
import pandas as pd
from middleware.display.beautify import beautify, json_return, has_failed
from tests.constants import ARGS_DICT, BEAUTIFY_VF_SEROTYPE

vf_serotype_gene_dict = os.path.join('tests/refs', 'GCA_000005845.2_ASM584v2_genomic.fna_ectyper-vf_serotype.p')

amr_gene_dict = os.path.join('tests/refs',
                             '2017-05-21-00-29-20-874628-GCA_000005845.2_ASM584v2_genomic.fna_rgi.tsv_rgi.p')


def test_beautify_vf_serotype():
    ## test vf & serotype json return
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': vf_serotype_gene_dict})
    assert len(beautify(single_dict, vf_serotype_gene_dict)) == len(BEAUTIFY_VF_SEROTYPE)


def test_beautify_serotype_only():
    ## test serotype only json return
    # note: this is actually the same gene results file as above
    # we only differentiate what is returned to the user, because we want all analysis ran & added to the db
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': vf_serotype_gene_dict})
    # this mimicks user selection of serotype only
    single_dict.update({'options': {'vf': False, 'amr': False, 'serotype': True}})
    # beautify is what is actually called by the RQ worker & returned to the user
    r = beautify(single_dict, vf_serotype_gene_dict)
    assert len(r) == 1


def test_beautify_json_r_serotype_only():
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': vf_serotype_gene_dict})
    # this mimicks user selection of serotype only
    single_dict.update({'options': {'vf': False, 'amr': False, 'serotype': True}})
    ## test json_r separately of failed handling
    # json_return() is a part of the beautify work
    gene_dict = pickle.load(open(vf_serotype_gene_dict, 'rb'))
    assert type(gene_dict) == dict
    assert len(gene_dict.keys()) == 2
    r = json_return(single_dict, gene_dict)
    assert len(r) == 1

    failed = has_failed(r)
    assert failed == False


def test_beautify_amr_only():
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': amr_gene_dict})
    # this mimicks user selection of serotype only
    single_dict.update({'options': {'vf': False, 'amr': True, 'serotype': False}})
    r = beautify(single_dict, amr_gene_dict)
    assert len(r) > 1


def test_beautify_json_r_amr_only():
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': amr_gene_dict})
    # this mimicks user selection of serotype only
    single_dict.update({'options': {'vf': False, 'amr': True, 'serotype': False}})
    gene_dict = pickle.load(open(amr_gene_dict, 'rb'))
    assert type(gene_dict) == dict
    assert len(gene_dict.keys()) == 1
    assert 'Antimicrobial Resistance' in gene_dict.keys()
    r = json_return(single_dict, gene_dict)
    assert len(r) > 1

    ## test some pandas stuff on the json_r
    df = pd.DataFrame(r)
    assert 'Serotype' not in df.analysis.unique()
    assert 'Virulence Factors' not in df.analysis.unique()
    assert 'Antimicrobial Resistance' in df.analysis.unique()
