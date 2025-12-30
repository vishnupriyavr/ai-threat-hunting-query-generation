from crewai import Crew, Flow
from crewai.flow import start, listen, router, end
from crewai.utilities.logger import log
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from src.agents import profiler_agent, architect_agent, query_engineer, triage_agent
from src.profiler import run_profiler
from src.planner import decompose_hypothesis, Plan


class HuntState(BaseModel):
    eda_summary: Dict[str, Any] = {}
    kg_schema_ready: bool = False
    current_hypothesis_id: str = ""
    hypothesis_text: str = ""
    generated_query: str = ""
    query_results: List[Dict] = []
    plan: Plan | None = None
    retry_count: int = 0
    max_retries: int = 3


@Flow
class AgenticThreatHunt:
    
    @start
    def perform_autonomous_eda(self, state: HuntState) -> HuntState:
        log.info("Phase A: The Profiler Agent analyzes the 1.9M row dataset.")
        try:
            result = run_profiler()
        except Exception:
            result = profiler_agent.execute_task(
                "Perform a full cardinality and missingness check on nineteenFeaturesDf.csv"
            )
        state.eda_summary = result
        log.info("EDA Complete: Hub entities identified.")
        return state

    @listen(perform_autonomous_eda)
    def construct_knowledge_graph(self, state: HuntState) -> HuntState:
        log.info("Phase A: The Architect Agent builds the ontology in Neo4j.")
        architect_agent.execute_task(
            f"Update Neo4j ontology using these findings: {state.eda_summary}"
        )
        state.kg_schema_ready = True
        log.info("Knowledge Graph schema constructed and ready.")
        return state

    @listen(construct_knowledge_graph)
    def execute_threat_hunt(self, state: HuntState) -> HuntState:
        log.info("Phase B: Strategist and Engineer collaborate to run the hunt.")
        if not state.plan:
            state.plan = decompose_hypothesis(state.current_hypothesis_id, state.hypothesis_text)
        
        query_prompt = state.plan.generate()
        state.generated_query = query_engineer.execute_task(query_prompt)
        log.info(f"Generated Query: {state.generated_query}")

        state.query_results = triage_agent.execute_task(
            task="Execute the generated query and return the results.",
            context={"sql_query": state.generated_query}
        )
        log.info("Query executed. Results obtained.")
        return state

    @router(execute_threat_hunt)
    def verify_and_correct(self, state: HuntState) -> str:
        log.info("The Triage Agent evaluates the results and decides if a retry is needed.")
        if not state.query_results and state.retry_count < state.max_retries:
            state.retry_count += 1
            log.warning(f"No results for Hypothesis {state.current_hypothesis_id}. Retrying...")
            return "execute_threat_hunt"
        
        if len(state.query_results) > 1000:
            log.info("Results too noisy. Directing Strategist to refine filters.")
            state.plan.refine("further restrict the results")
            return "execute_threat_hunt"
            
        return "end_flow"

    @end
    def end_flow(self, state: HuntState) -> HuntState:
        log.info("Threat hunt complete.")
        return state