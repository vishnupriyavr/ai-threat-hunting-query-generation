"""Simple confidence scoring utilities for query results.

Provides a deterministic heuristic scorer and an optional LLM-backed
explanation hook (which should be stubbed/mocked in tests and CI).
"""
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional


def compute_confidence(rows: List[Dict[str, Any]], intent_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compute a confidence score (0.0-1.0) and short explanation.

    Heuristics:
    - If no rows: score 0.0
    - If intent_keywords provided: score = fraction of rows containing any keyword
    - Otherwise: score = min(1.0, len(rows) / 100.0)
    """
    if not rows:
        return {"score": 0.0, "explanation": "No results returned"}

    if intent_keywords:
        matched = 0
        for r in rows:
            text = " ".join([str(v).lower() for v in r.values()])
            for kw in intent_keywords:
                if kw.lower() in text:
                    matched += 1
                    break
        frac = matched / max(1, len(rows))
        return {"score": float(frac), "explanation": f"{matched} of {len(rows)} rows match intent keywords"}

    # fallback heuristic based on result volume
    score = min(1.0, len(rows) / 100.0)
    return {"score": float(score), "explanation": f"Heuristic score based on {len(rows)} result rows"}


def llm_explain(rows: List[Dict[str, Any]], intent_keywords: Optional[List[str]] = None) -> str:
    """Optional LLM-based explanation for confidence.

    This function is intentionally minimal and will be mocked/stubbed in tests.
    If an LLM api key is present, you could call it here; for now, return a short
    human-readable hint.
    """
    if os.environ.get("OPENAI_API_KEY"):
        # Real implementation would call the LLM; keep minimal for tests
        return "LLM explanation (stubbed in tests)"
    return "LLM not available; no further explanation provided"


__all__ = ["compute_confidence", "llm_explain"]
