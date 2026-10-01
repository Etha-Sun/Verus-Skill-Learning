from skillopt_verusage.skill_validation import aggregate, schedule


def test_schedule_preserves_every_condition_repeat_pair():
    items=[{"id":str(i)} for i in range(20)]
    pilot,main=schedule(items,["initial","original_only","augmented"],["0","1","2"],2)
    keys=[(r,c,x["id"]) for r,c,x in pilot+main]
    assert len(keys)==len(set(keys))==120
    assert len(pilot)==9
    assert all(r==0 for r,c,x in pilot)


def test_joint_cost_does_not_reward_failure_or_timeout():
    rows=[]
    for cond,hard,within,tokens in [("original_only",1,True,100),("augmented",0,True,1),("reviewed",1,False,2)]:
        rows.append({"condition":cond,"repetition":0,"id":"x","hard":hard,"within_budget":within,"usage":{"completion_tokens":tokens}})
    result=aggregate(rows,["original_only","augmented","reviewed"])
    assert result["conditions"]["augmented"]["usage"]["completion_tokens"]==1
    assert result["paired_against_original_only"]["augmented"]["jointly_solved_n"]==0
    assert result["paired_against_original_only"]["reviewed"]["jointly_solved_n"]==0
    assert result["paired_against_original_only"]["reviewed"]["original_only_solves"]==1


def test_invalid_success_is_not_an_efficiency_win():
    rows = [{"condition": c, "repetition": 0, "id": "x", "hard": 1,
             "within_budget": True, "fidelity": f, "usage": {"completion_tokens": n}}
            for c, f, n in [("original_only", "V2_TRACE", 100), ("augmented", "V0_INVALID", 2)]]
    summary = aggregate(rows, ["original_only", "augmented"])
    assert summary['conditions']['augmented']['within_budget_solved'] == 0
    assert summary['conditions']['augmented']['invalid'] == 1
    assert summary['paired_against_original_only']['augmented']['jointly_solved_n'] == 0
