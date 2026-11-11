import pytest
from backend.app.schemas.research import AgentExecutionStep, FactCheckItem
from backend.app.schemas.chat import Citation
from backend.app.agents.fact_checker import FactCheckerAgent

def test_fact_checker_empty_claims():
    fc = FactCheckerAgent()
    res = fc.verify_claims([], [])
    assert res["grounding_score"] == 0.0
    assert len(res["fact_checks"]) == 0
    assert res["step"].agent_name == "Fact Checker Agent"

def test_agent_execution_step_model():
    step = AgentExecutionStep(
        agent_name="Planner Agent",
        title="Created subtasks",
        status="completed",
        details="Decomposed question into 2 subtasks",
        execution_time_seconds=0.45
    )
    assert step.agent_name == "Planner Agent"
    assert step.execution_time_seconds == 0.45

def test_fact_check_item_model():
    item = FactCheckItem(
        claim="Attendance must be at least 75%",
        is_supported=True,
        confidence=0.98,
        source_citation="college_rules.pdf, Page 1",
        note="Verified from text"
    )
    assert item.is_supported is True
    assert item.confidence == 0.98

