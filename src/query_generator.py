import logging
import sys
import time
import json
import re
from typing import List, Dict, Any

from crewai.flow.flow import Flow, listen, start, router
from crewai import Task
from pydantic import BaseModel

from src.agents import query_engineer, triage_agent
from src.planner import decompose_hypothesis, Plan

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

def _build_query_from_plan(plan: Plan, event_filter: str) -> str:
    all_filters = []
    if event_filter and "true" not in event_filter.lower():
        clean = event_filter.replace("WHERE", "").replace(";", "").strip()
        all_filters.append(f"({clean})")

    if plan and plan.steps:
        for f in plan.steps[0].structured_filters:
            col, op = f'"{f["column"]}"', f["operator"]
            if op in ("IS NULL", "IS NOT NULL"):
                all_filters.append(f"{col} {op}")
            elif op == "=":
                all_filters.append(f"{col} = '{f['value']}'")
            elif op == "IN":
                vals = ", ".join([f"'{v}'" for v in f["value"]])
                all_filters.append(f"{col} IN ({vals})")

    where = " AND ".join(all_filters)
    return f"SELECT * FROM logs WHERE {where} LIMIT 1000" if where else "SELECT * FROM logs LIMIT 1000"

class HuntState(BaseModel):
    current_hypothesis_id: str = ""
    hypothesis_text: str = ""
    generated_query: str = ""
    query_results: List[Dict] = []
    plan: Any = None 
    retry_count: int = 0
    max_retries: int = 2
    query_reasoning: str = ""
    latency: float = 0.0

class AgenticThreatHunt(Flow[HuntState]):

    @start()
    def initialize_hunt(self):
        logger.info(f"🚀 STARTING: {self.state.current_hypothesis_id}")
        return self.state

    @listen(initialize_hunt)
    def execute_threat_hunt(self):
        start_time = time.time() # Start timer
        logger.info(f"🔍 Executing Attempt {self.state.retry_count + 1}")
        
        # 1. Plan
        self.state.plan = decompose_hypothesis(self.state.current_hypothesis_id, self.state.hypothesis_text)
        
        # 2. Query Engineering Task
        eng_task = Task(
            description=self.state.plan.generate(),
            agent=query_engineer,
            expected_output="JSON object with filter, reasoning, and assumptions keys."
        )
        
        try:
            res = str(query_engineer.execute_task(task=eng_task))
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match:
                data = json.loads(match.group())
                filter_str = data.get('filter', '')
                self.state.query_reasoning = data.get('reasoning', '')
            else:
                filter_str = res
        except Exception as e:
            logger.error(f"Engineer error: {e}")
            filter_str = ""

        # 3. Build & Triage
        self.state.generated_query = _build_query_from_plan(self.state.plan, filter_str)
        
        tri_task = Task(
            description=f"Analyze results for: {self.state.generated_query}",
            agent=triage_agent,
            expected_output="A JSON list of result rows."
        )

        try:
            tri_res = str(triage_agent.execute_task(task=tri_task))
            list_match = re.search(r'\[.*\]', tri_res, re.DOTALL)
            self.state.query_results = json.loads(list_match.group()) if list_match else []
        except Exception:
            self.state.query_results = []

        self.state.latency = time.time() - start_time # Calculate duration
        logger.info(f"⏱️ Latency for ID {self.state.current_hypothesis_id}: {self.state.latency:.2f}s")
        return self.state

    @router(execute_threat_hunt)
    def check_results(self):
        if not self.state.query_results and self.state.retry_count < self.state.max_retries:
            self.state.retry_count += 1
            return "retry"
        return "finish"

    @listen("retry")
    def on_retry(self):
        return self.execute_threat_hunt()

    @listen("finish")
    def finalize(self):
        logger.info(f"✅ Finished. Rows: {len(self.state.query_results)}")
        return self.state