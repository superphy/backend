# usage:    cd app/
#           python -m pytest --ignore modules/ectyper/ecoli_serotyping -v

import pytest
import os
import subprocess
import cPickle as pickle
import pandas as pd

from modules.qc.qc import qc, check_header_parsing, check_ecoli
from middleware.blazegraph.reserve_id import write_reserve_id
from modules.ectyper.call_ectyper import call_ectyper_vf, call_ectyper_serotype
from modules.amr.amr import amr
from modules.amr.amr_to_dict import amr_to_dict
from middleware.display.beautify import beautify
from middleware.graphers.datastruct_savvy import datastruct_savvy
from middleware.graphers.turtle_grapher import turtle_grapher

from tests.constants import ARGS_DICT


# utility function to generate full path (still relative to root, not absoulte) for files in directories
def listdir_fullpath(d):
    valid_extensions = ('.fasta', '.fna')
    l = []
    for f in os.listdir(d):
        filename, file_extension = os.path.splitext(f)
        if file_extension in valid_extensions:
            l.append(os.path.join(d, f))
    return l


# globals for testing
GENOMES_LIST_NOT_ECOLI = listdir_fullpath('tests/notEcoli')
GENOMES_LIST_ECOLI = listdir_fullpath('tests/ecoli')
GENOMES_LIST_HEADERS = listdir_fullpath('tests/headers')


#### Non-Blazegraph/RQ Tests

# QC-related test.
def test_ecoli_checking():
    for ecoli_genome in GENOMES_LIST_ECOLI:
        assert check_ecoli(ecoli_genome) == True
    for non_ecoli_genome in GENOMES_LIST_NOT_ECOLI:
        assert check_ecoli(non_ecoli_genome) == False


# QC-related test.
def test_header_parsing():
    # Test header parsing for general E.Coli genomes.
    for ecoli_genome in GENOMES_LIST_ECOLI:
        assert check_header_parsing(ecoli_genome) == True

    # Test header parsing for genomes we're having problems with.
    for ecoli_genome in GENOMES_LIST_HEADERS:
        assert check_header_parsing(ecoli_genome) == True


# QC-related test.
def test_qc():
    for ecoli_genome in GENOMES_LIST_ECOLI:
        assert qc(ecoli_genome) == True
    for non_ecoli_genome in GENOMES_LIST_NOT_ECOLI:
        assert qc(non_ecoli_genome) == False


def test_ectyper_vf():
    """Check the ECTyper from `superphy` which is used for virulance factor
    identification. Installed as a submodule in the `modules` directory.
    """
    for ecoli_genome in GENOMES_LIST_ECOLI:
        # basic ECTyper check
        single_dict = dict(ARGS_DICT)
        single_dict.update({'i': ecoli_genome})
        pickled_ectyper_dict = call_ectyper_vf(single_dict)
        ectyper_dict = pickle.load(open(pickled_ectyper_dict, 'rb'))
        assert type(ectyper_dict) == dict

        # beautify ECTyper check
        json_return = beautify(single_dict, pickled_ectyper_dict)
        assert type(json_return) == list


def test_ectyper_serotype():
    """Check the ECTyper from `master` which only performs serotyping.
    Installed in the conda environment.
    """
    for ecoli_genome in GENOMES_LIST_ECOLI:
        # Check that the conda env can run ectyper.
        ret_code = subprocess.call(['ectyper', '-i', ecoli_genome])
        assert ret_code == 0

        # Check the actual call from Spfy's code.
        single_dict = dict(ARGS_DICT)
        single_dict.update({'i': ecoli_genome})
        serotype_csv = call_ectyper_serotype(single_dict)
        ectyper_serotype_df = pd.read_csv(serotype_csv)
        assert isinstance(ectyper_serotype_df, pd.DataFrame)


def test_amr():
    ecoli_genome = GENOMES_LIST_ECOLI[0]
    # this generates the .tsv
    pickled_amr_tsv = amr(ecoli_genome)
    filename, file_extension = os.path.splitext(pickled_amr_tsv)
    assert file_extension == '.tsv'

    # convert the tsv to a directory
    pickled_amr_dict = amr_to_dict(pickled_amr_tsv)
    amr_dict = pickle.load(open(pickled_amr_dict, 'rb'))
    assert type(amr_dict) == dict

    # beautify amr check
    single_dict = dict(ARGS_DICT)
    single_dict.update({'i': ecoli_genome})
    json_return = beautify(single_dict, pickled_amr_dict)
    assert type(json_return) == list
