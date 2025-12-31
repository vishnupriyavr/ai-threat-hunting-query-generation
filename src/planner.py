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
    """Create a basic Plan from hypothesis text.

    This version creates a textual prompt that can be passed to a generation
    agent rather than a hardcoded query template.
    """
    p = Plan(hypothesis_id=hypothesis_id, hypothesis_text=hypothesis_text)

    prompt = textwrap.dedent(f"""
        Write a SQL WHERE clause condition to find events related to the hypothesis: '{hypothesis_text}'.
        - The table is named `logs`.
        - Only filter on the `eventName` column using a case-insensitive `ILIKE` match for keywords in the hypothesis.
        - Do NOT include the 'WHERE' keyword in your response.
        - Do NOT add any filters for `errorCode`.
        - Example response: "eventName" ILIKE '%some_keyword%' OR "eventName" ILIKE '%another_keyword%'
    """)

    filters = []
    # By default, many threat hunts look for SUCCESSFUL malicious actions.
    successful_action_hypotheses = {"2", "3", "5", "6", "7", "10"}
    
    if hypothesis_id in successful_action_hypotheses:
        filters.append({"column": "errorCode", "operator": "IS NULL"})
    
    # Hypothesis-specific overrides
    if hypothesis_id == "1": # Sign-in Failures
        filters.append({"column": "errorCode", "operator": "IS NOT NULL"})
    elif hypothesis_id == "4": # Unauthorized API Calls
        filters.append({"column": "errorCode", "operator": "IN", "value": ["AccessDenied", "UnauthorizedOperation"]})
    elif hypothesis_id == "8": # S3 Bucket Brute Force
        filters.append({"column": "errorCode", "operator": "=", "value": "NoSuchBucket"})

    sel = PlanStep(
        name="candidate_selection",
        description="Select candidate entities matching hypothesis keywords",
        query_prompt=prompt,
        structured_filters=filters
    )
    p.add_step(sel)
    return p


__all__ = ["Plan", "PlanStep", "decompose_hypothesis"]
