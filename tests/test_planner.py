from src.planner import decompose_hypothesis, Plan, PlanStep


def test_decompose_hypothesis_creates_plan_and_steps():
    p = decompose_hypothesis("h1", "suspicious user agent")
    assert isinstance(p, Plan)
    assert p.hypothesis_id == "h1"
    assert len(p.steps) >= 1
    assert isinstance(p.steps[0], PlanStep)


def test_refine_adds_filter_to_last_step():
    p = decompose_hypothesis("h2", "failed logins")
    before = p.steps[-1].query_prompt
    p.refine("errorCode = 'AccessDenied'")
    after = p.steps[-1].query_prompt
    assert "AccessDenied" in after
    assert before != after
