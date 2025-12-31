# Explainability Features Implemented

To enhance the explainability of the threat hunting query generation system, the following features have been implemented:

1.  **Hypothesis Interpretation**:
    *   **Purpose**: Provides a concise, human-readable summary of what the given threat hypothesis is asking for.
    *   **Implementation**: The `decompose_hypothesis` function in `src/planner.py` now uses the `architect_agent` to generate this interpretation based on the raw hypothesis text. This interpretation is stored in the `Plan` object and subsequently in the `HuntState`.

2.  **Query Reasoning**:
    *   **Purpose**: Explains the rationale behind the structure and components of the generated SQL query.
    *   **Implementation**: The `query_engineer` agent (via prompt engineering in `src/planner.py`) is now explicitly instructed to return a JSON object that includes its reasoning for constructing the SQL filter. This reasoning is extracted in `src/query_generator.py` and stored in `HuntState`.

3.  **Assumptions Made**:
    *   **Purpose**: Clearly states any assumptions that the system made during the process of generating the query (e.g., specific timeframes, default values for ambiguous terms).
    *   **Implementation**: Similar to query reasoning, the `query_engineer` agent is prompted to include any assumptions in its structured JSON output. These assumptions are extracted in `src/query_generator.py` and stored in `HuntState`.

4.  **Confidence Score & Explanation**:
    *   **Purpose**: Provides a quantifiable measure of the system's confidence in the generated query's correctness and the results' relevance, along with a textual explanation of that confidence.
    *   **Implementation**: The `triage_agent`, which leverages the `result_summarizer` tool, already computes a confidence score and explanation. The `execute_threat_hunt` method in `src/query_generator.py` now explicitly captures this confidence score and its explanation from the `triage_agent`'s structured response and stores them in `HuntState`.

These explainability features are displayed in the `frontend/streamlit_app.py` interface, offering users greater insight into how queries are formed and why certain results are presented.