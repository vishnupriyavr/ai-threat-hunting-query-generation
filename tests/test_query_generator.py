import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("OPENAI_API_KEY", "test")

from src.query_generator import AgenticThreatHunt, HuntState

def test_perform_autonomous_eda():
    flow = AgenticThreatHunt()
    initial_state = HuntState()
    with patch("src.query_generator.run_profiler") as mock_profiler:
        mock_profiler.return_value = {"key": "value"}
        final_state = flow.perform_autonomous_eda(initial_state)
        assert final_state.eda_summary == {"key": "value"}

def test_construct_knowledge_graph():
    flow = AgenticThreatHunt()
    initial_state = HuntState(eda_summary={"key": "value"})
    with patch("src.query_generator.architect_agent") as mock_architect:
        mock_architect.execute_task.return_value = "KG constructed"
        final_state = flow.construct_knowledge_graph(initial_state)
        assert final_state.kg_schema_ready is True

def test_execute_threat_hunt():
    flow = AgenticThreatHunt()
    initial_state = HuntState(current_hypothesis_id="H001", hypothesis_text="Test hypothesis")
    with patch("src.query_generator.query_engineer") as mock_query_engineer, \
         patch("src.query_generator.triage_agent") as mock_triage_agent:
        mock_query_engineer.execute_task.return_value = "SELECT * FROM somewhere;"
        mock_triage_agent.execute_task.return_value = [{"result": "data"}]
        
        final_state = flow.execute_threat_hunt(initial_state)
        
        assert final_state.generated_query == "SELECT * FROM somewhere;"
        assert final_state.query_results == [{"result": "data"}]
        mock_query_engineer.execute_task.assert_called_once()
        mock_triage_agent.execute_task.assert_called_once_with(
            task="Execute the generated query and return the results.",
            context={"sql_query": "SELECT * FROM somewhere;"}
        )

def test_verify_and_correct_no_results_retry():
    flow = AgenticThreatHunt()
    state = HuntState(query_results=[], retry_count=0, max_retries=3, current_hypothesis_id="H001")
    
    next_step = flow.verify_and_correct(state)
    
    assert next_step == "execute_threat_hunt"
    assert state.retry_count == 1

def test_verify_and_correct_max_retries_reached():
    flow = AgenticThreatHunt()
    state = HuntState(query_results=[], retry_count=3, max_retries=3, current_hypothesis_id="H001")
    
    next_step = flow.verify_and_correct(state)
    
    assert next_step == "end_flow"

def test_verify_and_correct_noisy_results_refine():
    flow = AgenticThreatHunt()
    state = HuntState(query_results=[{}] * 1001, plan=MagicMock())
    
    next_step = flow.verify_and_correct(state)
    
    assert next_step == "execute_threat_hunt"
    state.plan.refine.assert_called_once_with("further restrict the results")

def test_verify_and_correct_good_results_end():
    flow = AgenticThreatHunt()
    state = HuntState(query_results=[{"result": "data"}])
    
    next_step = flow.verify_and_correct(state)
    
    assert next_step == "end_flow"

def test_end_flow():
    flow = AgenticThreatHunt()
    state = HuntState()
    
    final_state = flow.end_flow(state)
    
    assert final_state is state

