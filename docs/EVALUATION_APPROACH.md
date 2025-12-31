# Evaluation Approach: Agentic Threat Hunt

This document outlines the methodology and tooling used to evaluate the performance, accuracy, and efficiency of the Agentic Threat Hunt system. The evaluation process transforms raw execution logs into structured metrics and readable reports.

## 1. Evaluation Methodology
The evaluation focuses on four key dimensions:
* **Success Rate:** Can the agent generate syntactically correct queries that return data?
* **Schema Faithfulness:** Does the agent accurately use canonical CloudTrail fields?
* **Efficiency:** How long does the agent take to move from hypothesis to result?
* **Reasoning Quality:** Is the agent's logic sound and aligned with the hypothesis?

## 2. Core Evaluation Scripts

### A. `generate_eval_report.py`
This script is the primary reporting engine. It processes the execution logs to calculate high-level performance metrics and generates a Markdown summary.

* **Key Functions:**
    * **Schema Validation (`calculate_faithfulness`):** It compares the fields used in the generated SQL against a list of `CANONICAL_FIELDS` (standard CloudTrail schema). It calculates a percentage score based on how many fields are standard versus non-standard.
    * **Log Parsing:** Uses Regex to extract Hunt IDs, Hypotheses, SQL queries, row counts, and latency from `eval_runner.log`.
    * **Metric Aggregation:** * *Query Success Rate:* The % of hunts that returned 1 or more rows.
        * *Avg Latency:* The mean time taken per hunt.
        * *Groundedness:* The average Schema Faithfulness score across all hunts.
* **Output:** Generates `EVALUATION_REPORT_generated.md`, which contains a summary metrics table and a per-hypothesis breakdown of results.



### B. `parse_hunt_logs.py`
This script serves as a data extraction tool, converting unstructured log text into a structured format for deeper analysis or spreadsheet integration.

* **Key Functions:**
    * **Granular Extraction:** Unlike the report generator, this script specifically targets the `AGENT REASONING` field and the full `SQL` query string.
    * **State Tracking:** It maintains the context of a hunt (ID and Hypothesis) as it iterates through lines of logs, ensuring that reasoning and results are mapped to the correct ID.
* **Output:** Generates `detailed_hunt_report.csv`. This CSV includes columns for **ID, Hypothesis, Rows, Reasoning, and SQL**, making it ideal for manual auditing of the agent's thought process.

## 3. Evaluation Workflow

The evaluation follows a linear pipeline:

1.  **Execution:** The `run_all_hunts.py` script executes the agent and pipes all output to `eval_runner.log`.
2.  **Structuring:** `parse_hunt_logs.py` scans the log to create a `detailed_hunt_report.csv` for row-by-row auditing.
3.  **Analysis:** `generate_eval_report.py` processes the log to calculate statistical scores and "faithfulness" to the data schema.
4.  **Reporting:** A final `EVALUATION_REPORT_generated.md` is produced for stakeholders to review the agent's performance.



## 4. Key Metrics Defined

| Metric | Definition |
| :--- | :--- |
| **Query Success Rate** | The ratio of hunts that successfully queried the database and returned data. |
| **Schema Faithfulness** | A percentage representing how strictly the agent adhered to the known CloudTrail schema. |
| **Trajectory Efficiency** | The average number of reasoning loops or tool calls the agent made to reach a conclusion. |
| **Avg. Latency** | The average wall-clock time required to complete a single hunt. |