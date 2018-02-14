from hashlib import sha1
from rdflib import URIRef
from middleware.graphers.turtle_utils import generate_uri as gu
from middleware.graphers.turtle_utils import actual_filename


def test_generate_uri():
    # test generate usage:
    e = URIRef(u'http://www.biointerchange.org/gfvo#Contig')
    r = gu('g:Contig')
    assert r == e

    # test spfyid generation (ie. root namespace)
    e = URIRef(u'https://www.github.com/superphy#spfy1')
    r = gu(':spfy1')
    assert r == e

    # test cases where you call gu() with and existing URIRef and want to
    # append something
    # ex. gu(uriGenome, "/contigs") in datastruct_savvy.py
    # e was previously generated
    e = URIRef(u'https://www.github.com/superphy#1947b0815e6c1b11565e1ef5db9c884e3eead520/contigs')
    # mock_filehash mocks the hash of a genome file
    mock_filehash = sha1('thisvaluedoesntmatterfornow').hexdigest()
    # generate the mock uriGenome
    # this returns a rdflib.URIRef object
    mock_uriGenome = gu(':' + mock_filehash)
    # this is the test case, r is a mock uriContigs
    r = gu(mock_uriGenome, '/contigs')
    assert r == e

    # test with a url in the form of a string
    e = URIRef('https://www.github.com/superphy#')
    r = gu('https://www.github.com/superphy#')
    assert r == e


def test_actual_filename():
    # test filenames with timestamps
    s = '/datastore/2017-08-10-14-57-59-722994-GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    e = 'GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    r = actual_filename(s)
    assert r == e

    # test filenames without timestamps
    s = '/datastore/GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    e = 'GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    r = actual_filename(s)
    assert r == e

    # test filenames without timestamps or paths
    s = 'GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    e = 'GCA_900096815.1_Ecoli_AG100_Sample2_M9_Assembly_genomic.fna'
    r = actual_filename(s)
    assert r == e
