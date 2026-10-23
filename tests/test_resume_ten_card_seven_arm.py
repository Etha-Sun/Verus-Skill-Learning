import pytest
import resume_ten_card_seven_arm as r


def row(job,outcome):
    return {'task_id':job['id'],'condition':job['condition'],'repeat':job['repeat'],'outcome':outcome}


def test_keep_success_and_timeout_retry_only_infrastructure_or_unstarted():
    jobs=r.e.schedule([{'id':str(i)} for i in range(8)])
    rows=[row(j,'timeout' if i%2 else 'budgeted_dual_pass') for i,j in enumerate(jobs[:30])]
    rows += [row(j,'infrastructure_aborted') for j in jobs[30:32]]
    remaining,kept,retry=r.select_remaining(jobs,rows)
    assert remaining==jobs[30:] and len(remaining)==82 and len(kept)==30 and len(retry)==2
    assert not set(kept)&{r.e.prior.driver.episode_key(j) for j in remaining}


def test_duplicate_or_unknown_results_rejected():
    jobs=r.e.schedule([{'id':'task'}]);x=row(jobs[0],'timeout')
    with pytest.raises(ValueError,match='duplicate'):r.select_remaining(jobs,[x,x])
    with pytest.raises(ValueError,match='Unknown'):r.select_remaining(jobs,[{**x,'task_id':'unknown'}])


def test_all_regular_failures_are_kept_even_when_unsolved():
    jobs=r.e.schedule([{'id':'task'}])
    remaining,kept,retry=r.select_remaining(jobs,[row(jobs[0],'proof_failure')])
    assert remaining==jobs[1:] and len(kept)==1 and not retry
