from middleware import models
from modules.spfy import spfy
from scripts.savvy import savvy
from tests import constants

class MockRQJob():
    """
    A mock Job class returned by RQ. Also emulates response the Job gets from
    querying Redis DB.
    """
    def __init__(self, is_finished=True, is_failed=False, exc_info='', result=None):
        self.is_finished = is_finished
        self.is_failed = is_failed
        self.exc_info = exc_info
        self.result = result

def test_subtyping_model_direct(l=constants.BEAUTIFY_VF_SEROTYPE):
    """
    Use our dataset to directly create a subtyping results model and validate it.
    """
    subtyping_list = [
        models.SubtypingRow(
            analysis=d['analysis'],
            contigid=d['contigid'],
            filename=d['filename'],
            hitcutoff=str(d['hitcutoff']),
            hitname=d['hitname'],
            hitorientation=d['hitorientation'],
            hitstart=str(d['hitstart']),
            hitstop=str(d['hitstop'])
        )
    for d in l]
    subtyping_result = models.SubtypingResult(
        rows = subtyping_list
    )
    subtyping_result.validate()
    # Return for incorporation into later tests.
    return subtyping_result

def test_phylotyper_model_direct(l=constants.BEAUTIFY_STX1):
    """
    Use our dataset to directly create a phylotyper results model and validate it.
    """
    phylotyper_list = [
        models.PhylotyperRow(
            contig=d['contig'],
            genome=d['genome'],
            probability=str(d['probability']),
            start=str(d['start']),
            stop=str(d['stop']),
            subtype=d['subtype'],
            subtype_gene=d['subtype_gene']
        )
    for d in l]
    phylotyper_result = models.PhylotyperResult(
        rows = phylotyper_list
    )
    phylotyper_result.validate()
    # Return for incorporation into later tests.
    return phylotyper_result

def test_pipeline_model_subtyping():
    """
    Test the Pipeline model itself for subtyping via ECTyper and RGI.
    """
    p = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    mock_serotype = MockRQJob(
        result = test_subtyping_model_direct(constants.BEAUTIFY_SEROTYPE)
    )
    mock_vf = MockRQJob(
        result = test_subtyping_model_direct(constants.BEAUTIFY_VF)
    )
    # Mimicks a Serotype result that will be converted to json.
    p.jobs.update({
        'job_ectyper_beautify_serotype': models.Job(
            rq_job=mock_serotype,
            name='job_ectyper_beautify_vf',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    # Mimicks a VF result that will be converted to json.
    p.jobs.update({
        'job_ectyper_beautify_vf': models.Job(
            rq_job=mock_vf,
            name='job_ectyper_beautify_vf',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    assert isinstance(p, models.Pipeline)
    assert isinstance(p.jobs, dict)
    for k in p.jobs:
        assert isinstance(p.jobs[k], models.Job)

    # Test Pipeline.cache_jobs()
    p.cache_jobs()
    # Test Pipeline.merge_jobs()
    p.merge_jobs()
    # Test Pipeline.complete(), should be True.
    assert p.complete()

    # Test Pipeline.to_json().
    json = p.to_json()
    assert isinstance(json, list)

    # Add an AMR job and re-test.
    mock_amr  = MockRQJob(
        result = test_subtyping_model_direct(constants.BEAUTIFY_AMR)
    )
    p.jobs.update({
        'job_ectyper_beautify_amr': models.Job(
            rq_job=mock_amr,
            name='job_ectyper_beautify_amr',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    p.merge_jobs()
    # Test Pipeline.complete(), should be True.
    assert p.complete()
    # Test Pipeline.to_json().
    json = p.to_json()
    assert isinstance(json, list)

def test_pipeline_model_phyotyping():
    """
    Test the Pipeline model itself for subtyping via Phylotyper.
    """
    p = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    mock_stx1 = MockRQJob(
        result = test_phylotyper_model_direct(constants.BEAUTIFY_STX1)
    )
    mock_stx2 = MockRQJob(
        result = test_phylotyper_model_direct(constants.BEAUTIFY_STX2)
    )
    p.jobs.update({
        'job_phylotyper_beautify_stx1': models.Job(
            rq_job=mock_stx1,
            name='job_phylotyper_beautify_stx1',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    p.jobs.update({
        'job_phylotyper_beautify_stx2': models.Job(
            rq_job=mock_stx2,
            name='job_phylotyper_beautify_stx2',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    assert isinstance(p, models.Pipeline)
    assert isinstance(p.jobs, dict)
    for k in p.jobs:
        assert isinstance(p.jobs[k], models.Job)

    # Test Pipeline.cache_jobs()
    p.cache_jobs()
    # Test Pipeline.merge_jobs()
    p.merge_jobs()
    # Test Pipeline.complete(), should be True.
    assert p.complete()

    # Test Pipeline.to_json().
    json = p.to_json()
    assert isinstance(json, list)

    # Add an AMR job and re-test.
    mock_eae  = MockRQJob(
        result = test_phylotyper_model_direct(constants.BEAUTIFY_EAE)
    )
    p.jobs.update({
        'job_phylotyper_beautify_eae': models.Job(
            rq_job=mock_eae,
            name='job_phylotyper_beautify_stx2',
            transitory=False,
            backlog=False,
            display=True
        )
    })
    p.merge_jobs()
    # Test Pipeline.complete(), should be True.
    assert p.complete()
    # Test Pipeline.to_json().
    json = p.to_json()
    assert isinstance(json, list)

def test_pipeline_model_signature():
    """
    Function signatures should be identical if called on the same function.
    """
    p1 = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    p2 = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    r1 = p1.signature()
    r2 = p2.signature()
    # These are identical pipelines, should be equal.
    assert r1 == r2

    p1 = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    p2 = models.Pipeline(
        func = savvy,
        options = constants.ARGS_DICT
    )
    r1 = p1.signature()
    r2 = p2.signature()
    # These pipelines have different functions, should be different.
    assert r1 != r2

    p1 = models.Pipeline(
        func = spfy,
        options = constants.ARGS_DICT
    )
    p2 = models.Pipeline(
        func = spfy,
        options = {'cats':1}
    )
    r1 = p1.signature()
    r2 = p2.signature()
    # These pipelines have different options, should be different.
    assert r1 != r2
