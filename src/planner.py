"""Planner for decomposing hypotheses into multi-step plans.

This is a lightweight Planner implementation: it turns a hypothesis string
into an ordered list of sub-queries (steps). It supports a simple `refine`
operation that adds extra filters when results are noisy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
import itertools
import textwrap

from crewai import Task 
from src.agents import architect_agent


@dataclass
class PlanStep:
    name: str
    description: str
    query_prompt: str
    structured_filters: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    hypothesis_id: str
    hypothesis_text: str
    hypothesis_interpretation: str = "" 
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)

    def refine(self, extra_filter: str) -> None:
        # Append refinement as an additional filter on the last step's query
        if not self.steps:
            return
        last = self.steps[-1]
        last.query_prompt += f"\nAdditionally, filter where {extra_filter}."
        last.metadata.setdefault("refinements", []).append(extra_filter)

    def generate(self) -> str:
        # Use a generator to build the full query plan
        prompts = [s.query_prompt for s in self.steps]
        return "\n\n".join(prompts)


def decompose_hypothesis(hypothesis_id: str, hypothesis_text: str) -> Plan:
    """Create a basic Plan from hypothesis text."""
    
    # 1. Create a Task for the interpretation
    interpretation_desc = f"Interpret the following threat hunting hypothesis in one concise sentence: '{hypothesis_text}'"
    
    interpretation_task = Task(
        description=interpretation_desc,
        agent=architect_agent,
        expected_output="A single concise sentence interpreting the threat hypothesis."
    )

    # 2. Execute using the Task object
    hypothesis_interpretation = architect_agent.execute_task(task=interpretation_task)

    p = Plan(
        hypothesis_id=hypothesis_id, 
        hypothesis_text=hypothesis_text,
        hypothesis_interpretation=str(hypothesis_interpretation) # Ensure it's stringified
    )

    # Hypothesis-specific configs
    hypothesis_configs = {
        "9a": {
            "primary_col": "userAgent",
            "base_prompt": textwrap.dedent(f"""
                Write a SQL WHERE clause condition related to the hypothesis: '{hypothesis_text}'.
                - The condition should find rows where the "userAgent" column contains keywords from the hypothesis (case-insensitive `ILIKE`), OR where the "userAgent" column IS NULL.
                - Do NOT include the 'WHERE' keyword in your response.
                - Example: ("userAgent" ILIKE '%keyword%') OR ("userAgent" IS NULL)
            """)
        },
        "9b": {
            "primary_col": "userAgent",
            "base_prompt": textwrap.dedent(f"""
                Write a SQL WHERE clause condition related to the hypothesis: '{hypothesis_text}'.
                - The condition should find rows where the "userAgent" column contains keywords from the hypothesis (case-insensitive `ILIKE`), OR where the "userAgent" column IS NULL.
                - Do NOT include the 'WHERE' keyword in your response.
                - Example: ("userAgent" ILIKE '%keyword%') OR ("userAgent" IS NULL)
            """)
        }
    }
    
    config = hypothesis_configs.get(hypothesis_id, {})
    primary_col = config.get("primary_col", "eventName")

    if "base_prompt" in config:
        base_prompt_instruction = config["base_prompt"]
    else:
        base_prompt_instruction = textwrap.dedent(f"""
            Write a SQL WHERE clause condition to find events related to the hypothesis: '{hypothesis_text}'.
            - The table is named `logs`.
            - Only filter on the "{primary_col}" column using a case-insensitive `ILIKE` match for keywords in the hypothesis.
            - Do NOT include the 'WHERE' keyword in your response.
            - Do NOT add any filters for `errorCode`.
        """)

    final_query_engineer_prompt = textwrap.dedent(f"""
        Based on the following instructions, generate a JSON object with the keys 'filter', 'reasoning', and 'assumptions'.
        The 'filter' key should contain only the SQL WHERE clause condition, as instructed.
        The 'reasoning' key should explain how you structured the query.
        The 'assumptions' key should list any assumptions you made.
        Ensure the JSON is perfectly valid and can be parsed directly.

        Instructions for 'filter' key:
        {base_prompt_instruction}
    """)

    filters = []
    successful_action_hypotheses = {"2", "3", "5", "6", "7", "10"}
    
    if hypothesis_id in successful_action_hypotheses:
        filters.append({"column": "errorCode", "operator": "IS NULL"})
    
    if hypothesis_id == "1": 
        filters.append({"column": "errorCode", "operator": "IS NOT NULL"})
    elif hypothesis_id == "4": 
        filters.append({"column": "errorCode", "operator": "IN", "value": ["AccessDenied", "UnauthorizedOperation"]})
    elif hypothesis_id == "8": 
        filters.append({"column": "errorCode", "operator": "=", "value": "NoSuchBucket"})

    sel = PlanStep(
        name="candidate_selection",
        description="Select candidate entities matching hypothesis keywords",
        query_prompt=final_query_engineer_prompt,
        structured_filters=filters
    )
    p.add_step(sel)
    return p


__all__ = ["Plan", "PlanStep", "decompose_hypothesis"]