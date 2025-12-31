from crewai import Crew, Flow
from crewai.flow import start, listen, router, end
from crewai.utilities.logger import log
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from src.agents import profiler_agent, architect_agent, query_engineer, triage_agent
from src.profiler import run_profiler
from src.planner import decompose_hypothesis, Plan


def _build_query_from_plan(plan: Plan, event_name_filter: str) -> str:
    """Builds a full SQL query from a plan and an eventName filter string."""
    all_filters = []
    if event_name_filter and "true" not in event_name_filter.lower():
        all_filters.append(f"({event_name_filter})")

    # Get the structured filters from the first step
    if plan.steps:
        structured_filters = plan.steps[0].structured_filters
        for f in structured_filters:
            col = f["column"]
            op = f["operator"]
            
            # Use double quotes for column names to handle case sensitivity
            col_quoted = f'"{col}"'

            if op in ("IS NULL", "IS NOT NULL"):
                all_filters.append(f'{col_quoted} {op}')
            elif op == "=":
                val = f["value"]
                all_filters.append(f"{col_quoted} = '{val}'")
            elif op == "IN":
                vals = ", ".join([f"'{v}'" for v in f["value"]])
                all_filters.append(f'{col_quoted} IN ({vals})')

    where_clause = " AND ".join(all_filters)
    if not where_clause:
        # Avoid a dangling WHERE if no filters exist
        return "SELECT * FROM logs LIMIT 1000"

    return f"SELECT * FROM logs WHERE {where_clause} LIMIT 1000"


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
        if not state.plan or state.retry_count > 0: # Always regen plan on retry
            state.plan = decompose_hypothesis(state.current_hypothesis_id, state.hypothesis_text)
        
        # The prompt now asks for a WHERE clause fragment for eventName
        event_name_prompt = state.plan.generate()
        event_name_filter = query_engineer.execute_task(event_name_prompt)

        # Deterministically build the final query
        state.generated_query = _build_query_from_plan(state.plan, event_name_filter)
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
            log.info("High volume of results detected. Performing cardinality check...")
            try:
                import pandas as pd
                results_df = pd.DataFrame(state.query_results)
                
                # Check for sourceIPAddress cardinality as a heuristic for distributed events
                if "sourceIPAddress" in results_df.columns:
                    unique_ips = results_df["sourceIPAddress"].nunique()
                    ip_to_row_ratio = unique_ips / len(results_df)
                    
                    # If >10% of results have a unique IP, it's likely a widespread event, not noise
                    if ip_to_row_ratio > 0.1:
                        log.info(f"Cardinality analysis shows a high IP-to-row ratio ({ip_to_row_ratio:.2f}). Treating as a widespread event, not noise.")
                        return "end_flow"

            except ImportError:
                log.warning("Pandas is not installed. Falling back to simple row count for noise detection.")
            
            log.info("Results deemed too noisy. Directing Strategist to refine filters.")
            state.plan.refine("further restrict the results")
            return "execute_threat_hunt"
            
        return "end_flow"

    @end
    def end_flow(self, state: HuntState) -> HuntState:
        log.info("Threat hunt complete.")
        return state