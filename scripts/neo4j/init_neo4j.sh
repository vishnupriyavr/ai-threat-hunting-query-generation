#!/usr/bin/env bash
# Helper script: wait for neo4j and run init CQL
set -euo pipefail
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-neo4j}
CQL_FILE=/init/init_ontology.cql

echo "Waiting for Neo4j to be ready..."
until cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" 'RETURN 1' >/dev/null 2>&1; do
  sleep 1
done

echo "Running init CQL: $CQL_FILE"
cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < "$CQL_FILE"

echo "Neo4j initialization complete"
