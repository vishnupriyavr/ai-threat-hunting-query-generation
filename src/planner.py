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
    # Basic candidate selection: look for likely target column
    sel = PlanStep(
        name="candidate_selection",
        description="Select candidate entities matching hypothesis keywords",
        query_prompt=textwrap.dedent(f"""
            Write a SQL query to find events related to the hypothesis: '{hypothesis_text}'.
            - The table is named `logs`.
            - Select all columns.
            - Filter `eventName` using a case-insensitive match for keywords in the hypothesis.
            - Limit the results to 1000.
        """),
    )
    p.add_step(sel)
    return p


__all__ = ["Plan", "PlanStep", "decompose_hypothesis"]
