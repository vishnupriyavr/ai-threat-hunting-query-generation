# Technical Approach: Multi-Agent System (MAS) Architecture

This architecture uses a specialized "Hunt Squad" where agents communicate via a shared state (e.g., using CrewAI Flows).

# Agent Roles & Responsibilities

**The Data Profiler (EDA Agent):**
_Goal_: Automates "EDA Checklist."
_Action_: Scans nineteenFeaturesDf.csv to calculate cardinality, missingness, and value distributions.
_Output_: Generates the eda_summary.json and alerts the next agent to "hub" entities like sourceIPAddress or userIdentityarn.

**The Ontology Architect (KG Agent):**
_Goal_: Construct and maintain the Knowledge Graph.
_Action_: Uses findings from the Profiler to define nodes and relationships in Neo4j. It dynamically adjusts the schema—for example, deciding if GetCallerIdentity (Hypothesis 5) should be a distinct RECON node based on its frequency in the logs.

**The Hunt Strategist (Planner Agent):**
_Goal_: Decompose hypotheses into logical steps.
_Action_: Reads a hypothesis from hypotheses.json and queries the KG to see "how" to find it. For Hypothesis 7, it identifies that it must look at requestParametersinstanceType.

**The Query Engineer (Generation Agent):**
_Goal_: Write executable SQL/Athena code.
_Action_: Uses the Three-Tier Prompting Architecture to generate queries, ensuring it never "hallucinates" fields by strictly adhering to the ontology provided by the Architect.

**The Triage & Verification Agent:**
_Goal_: Analyze results and handle errors.
_Action_: Reviews the query output. If results are "noisy," it forces the Planner to refine the hunt. If the query fails, it sends the error logs back to the Query Engineer for a "Self-Correction" cycle.

## The Agentic Lifecycle: From EDA to Investigation
**Phase A: The "Pre-Flight" Autonomous EDA**
1. Profiler Agent triggers on the nineteenFeaturesDf.csv. It notices that userIdentitytype is 100% populated with 'Root' or 'IAMUser' values.
2. It sends a message to the Ontology Architect: "I recommend making userIdentitytype a primary attribute for the User node to support Hypothesis" 
3.The Architect automatically updates the Neo4j schema logic.

**Phase B: The Hypothesis Execution (Agentic Reasoning)**
For example, in Hypothesis 9a (Suspicious User Agents)
1. _Strategist_: "To find suspicious agents, I need to check the userAgent field for 'kali', 'parrot', or 'powershell'.
2. _Architect_: "Wait, the EDA summary shows userAgent is 15% null. I will provide a 'Gold Standard' example that includes WHERE userAgent IS NOT NULL."
3. _Engineer_: Generates the SQL query using ILIKE as per the "Case Sensitivity" challenge solution.
4. _Triage Agent_: "The query returned 5,000 results. This is too much noise. Strategist, please refine the hypothesis to only look for these agents associated with errorCode = 'AccessDenied' (Hypothesis 4)."

## Implementation Strategy: Tool-Use & Grounding
To make this "Agentic," agents must have access to specific Tools (using Model Context Protocol or custom API wrappers)

| Agent            | Tool Access              | Purpose          |
|------------------|--------------------------|------------------|
| Profiler         | pandas_analyzer          | Run the Python EDA script and return eda_summary.json.       |
| Architect        | neo4j_cypher_executor    | Create nodes/edges and query the graph schema.               |
| Engineer         | athena_sql_executor (DuckDB stub) | Run queries against the local CSV via `src/mcp_data_server.py` during development; swap to Athena (boto3) for production. |
| Triage           | result_summarizer        | Use an LLM to "read" the first 10 rows and determine if they match the threat intent.|

Refer to the "Containerized Development Environment" section for instructions on how to run the application.

## Containerized Development Environment

The project is designed to be run in a containerized environment using Docker and Docker Compose.

### Dockerfile

The `Dockerfile` defines the environment for the Python application. It installs the necessary dependencies from `requirements.txt` and copies the application code into the `/app` directory in the container.

### docker-compose.yml

The `docker-compose.yml` file defines the services that make up the application. These services include:

*   **`app`**: The main application service that runs the `crewai` flow.
*   **`eval`**: A service for running evaluation scripts.
*   **`data-mcp`**: A service that runs the `src/mcp_data_server.py` script, which provides tools for data analysis.
*   **`neo4j`**: A service that runs a Neo4j database.
*   **`neo4j-mcp`**: A service that runs the `src/neo4j_mcp_server.py` script, which provides a mock Neo4j MCP server for development and testing.
*   **`neo4j-init`**: A service that initializes the Neo4j database with the ontology defined in `scripts/neo4j/init_ontology.cql`.

### Running the Application

To run the application, follow these steps:

1.  Create a `.env` file in the root of the project with the following variables:
    ```
    OPENAI_API_KEY=<your_openai_api_key>
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=password
    ```
2.  Run the following command to start the services in the background:
    ```
    docker-compose up --build -d
    ```
3.  Once the services are running, you can execute the threat hunting flow with the following command:
    ```
    docker-compose exec app python main.py
    ```

## Solving Technical Challenges Agentically
**Nested JSON Hallucination:** Instead of humans teaching the agent, the Ontology Architect agent scans the first 5 rows of requestParameters during the EDA phase. It identifies the nested keys and stores them as "Verified Paths" in the Knowledge Graph for the Query Engineer to use. 
**Large Result Sets:** The Triage Agent is programmed with a "Cost Guardrail." If a query is projected to scan too much data, it automatically forces the Planner to add a eventTime window constraint. 
**Autonomous Discovery:** Once the 11 hypotheses from hypotheses.json are cleared, the system enters "Discovery Mode." The Strategist queries the Knowledge Graph for "orphaned" IP addresses that have no associated userIdentityuserName—automatically creating a new "Hypothesis 12: Anonymous Activity Detection. 


## Why EDA is Essential Before Graph Construction

- **Validating the Schema for the Agent:** EDA is needed to check how columns are populated and formatted. 
For example, `nineteenFeaturesDf.csv` has specific columns like `userIdentitytype` and `requestParametersinstanceType` — EDA helps to see the unique values inside these fields (e.g., `t2.micro` vs `p3.16xlarge`) to make query logic robust.

- **Identifying "Hub" Entities:** EDA reveals columns with high cardinality (e.g., `sourceIPAddress`, `userIdentityarn`) which could be primary node types instead of just attributes.

- **Data Quality and Missing Values:** If `errorCode` or `errorMessage` are sparsely populated,the KG will know that an `Error` node/relationship would be sparse and should be modeled carefully or treated as an attribute.

- **Relationship Discovery:** EDA can surface correlations (e.g., a particular `userAgent` is always associated with a specific `awsRegion`) that should become explicit relationships in the KG.

## How EDA Specifically Supports the Hypotheses

| Hypothesis Category | EDA Action | Impact on Knowledge Graph |
|---|---|---|
| User Recon (Hyp 5) | Check frequency of `GetCallerIdentity` in `eventName` | Decides if `API_Call` should be a distinct node type with a `RECON` label |
| Suspicious Agents (Hyp 9a/b) | Analyze distribution of `userAgent` strings for attacker patterns | Helps define a `Suspicious` property or node class in the ontology |
| Auth Failures (Hyp 1) | Examine distinct values in `errorMessage` and `errorCode` | Ensures proper linking of `User` nodes to `Failed_Login` event nodes using the correct keys |

After EDA, there will be a data map that makes the Text-to-Cypher or Text-to-SQL mapping much more reliable for the agent.

## EDA Checklist for `nineteenFeaturesDf.csv`

1. **Cardinality Check:** Unique counts for `userIdentity`, `sourceIPAddress`, `eventName`, etc.
2. **Missingness:** Fraction of missing values per column, identify columns with >50% missingness.
3. **Temporal Analysis:** Verify `eventTime` continuity and gaps that could affect time-windowing logic.
4. **Feature Overlap:** Check if `userIdentityarn` always maps to a single `userIdentityuserName` (defines hierarchy in the KG).
5. **Value Formats:** Inspect `requestParametersinstanceType` formatting to support Hypothesis #7 (EC2 instance creation detection).
6. **Top N Values:** Inspect top N values for categorical fields to find likely node types and edges.
7. **Distributional Outliers:** For numeric fields, inspect min/max and outliers.