from crewai.mcp import MCPServerTcp # CHANGE from MCPServerStdio for dockerized TCP MCP servers
from crewai import Agent

# 1. Neo4j MCP Server
neo4j_mcp = MCPServerTcp(
    host="neo4j-mcp-server", # Service name from docker-compose.yml
    port=5002 # Custom port for neo4j_mcp_server
)

# 2. Local Data Server
data_mcp = MCPServerTcp(
    host="data-mcp-server", # Service name from docker-compose.yml
    port=5001 # Custom port for mcp_data_server
)

# 1. The Data Profiler (EDA Agent)
# Focuses on the 'pandas_analyzer' tool provided by data_mcp
profiler_agent = Agent(
    role="Data Profiler",
    goal="Automate the EDA checklist for nineteenFeaturesDf.csv",
    backstory="You are a data analyst specialized in high-volume CloudTrail logs. "
              "Your job is to identify hub entities and data quality issues.",
    mcps=[data_mcp], 
    verbose=True
)

# 2. The Ontology Architect (KG Agent)
# Focuses on 'neo4j_cypher_executor' to build and maintain the graph
architect_agent = Agent(
    role="Ontology Architect",
    goal="Construct and dynamically maintain the Knowledge Graph in Neo4j",
    backstory="You bridge the gap between raw data and relational logic. "
              "You use EDA findings to decide on node types like 'User' or 'API_Call'.",
    mcps=[neo4j_mcp],
    verbose=True
)


def architect_apply_cql(cypher: str) -> dict:
    """Convenience helper that applies a CQL statement to Neo4j via the local MCP stub.

    This uses the repo-local `neo4j-mcp` script so it works in tests without a real Neo4j instance.
    """
    from src.neo4j_client import execute_cypher_via_mcp

    return execute_cypher_via_mcp(cypher)

# 3. The Query Engineer (Generation Agent)
# Does not necessarily need direct MCP access, but uses the ARCHITECT'S ontology
# to generate code for the Triage agent.
query_engineer = Agent(
    role="Query Engineer",
    goal="Translate security hypotheses into executable SQL/Athena code",
    backstory="You are an expert in AWS CloudTrail schemas. You never hallucinate "
              "field names because you strictly follow the Knowledge Graph ontology.",
    allow_delegation=False,
    verbose=True
)

# 4. The Triage & Verification Agent
# Uses the 'athena_sql_executor' tool from the data_mcp to run hunts
triage_agent = Agent(
    role="Triage & Verification Agent",
    goal="Execute queries and analyze results for security relevance",
    backstory="You are a senior security responder. You run queries against the data lake, "
              "evaluate if results match threat intent, and trigger self-correction loops.",
    mcps=[data_mcp],
    verbose=True
)