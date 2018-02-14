import os
import shutil
import pytest
from hashlib import sha1
from scripts.savvy import mock_reserve_id, get_spfyid_file, savvy
from tests.constants import ARGS_DICT


def sha1_hash(f):
    """
    Note: hash comparisons can't be used on anything that contains a blank
    node as the assigned values may be different. Use length comparison
    instead.
    """
    return sha1(open(f, 'rb').read()).hexdigest()


def length(f):
    return len(open(f, 'rb').readlines())


def test_mock_reserve_id():
    f = get_spfyid_file()
    if os.path.isfile(f):
        # you already have a spfyid file
        # this isn't the case in a test env, but may be true if tests are run after using savvy.py
        with open(f) as fl:
            spfyid = fl.read()
            spfyid = int(spfyid)
        # in the case that savvy.py was previously used (and tests may be running in a production env)
        # therefore, we don't call mock_reserve_id() directly as it'll overwrite their file
        assert spfyid > 0
    else:
        # this is the expected test env where the spfyid file doesn't exist
        # first call returns 1 as the id
        assert mock_reserve_id() == 1
        # second call should have incremented the stored file
        assert mock_reserve_id() == 2
        # delete the spfyid_count file that was created
        os.remove(f)


def test_savvy():
    f = get_spfyid_file()
    if os.path.isfile(f):
        print 'There is already an ID file, not sure why tests are being run. If you want to retest, run sudo rm /tmp/spfyid_count.txt'
        assert False
    else:
        single_dict = dict(ARGS_DICT)
        single_dict.update({'i': os.path.abspath('tests/ecoli/GCA_001894495.1_ASM189449v1_genomic.fna')})
        r = savvy(single_dict)
        for result in r:
            if 'base' in result:
                assert sha1_hash(result) == sha1_hash('tests/refs/GCA_001894495.1_ASM189449v1_genomic.fna_base.ttl')
            elif 'ectyper' in result:
                if '.ttl' in result:
                    assert length(result) == length('tests/refs/GCA_001894495.1_ASM189449v1_genomic.fna_ectyper.ttl')
                elif '.json' in result:
                    assert length(result) == length('tests/refs/GCA_001894495.1_ASM189449v1_genomic.fna_ectyper.json')
            elif 'rgi' in result:
                if '.ttl' in result:
                    assert length(result) == length('tests/refs/GCA_001894495.1_ASM189449v1_genomic.fna_rgi.ttl')
                elif '.json' in result:
                    assert length(result) == length('tests/refs/GCA_001894495.1_ASM189449v1_genomic.fna_rgi.json')
