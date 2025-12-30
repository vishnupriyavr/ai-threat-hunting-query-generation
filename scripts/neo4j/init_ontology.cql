// Initialize basic ontology and constraints for the Knowledge Graph
CREATE CONSTRAINT event_name_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE;
CREATE CONSTRAINT field_name_unique IF NOT EXISTS FOR (f:Field) REQUIRE f.name IS UNIQUE;

// Sample events and fields
MERGE (ev1:Event {name: 'ConsoleLogin'});
MERGE (ev2:Event {name: 'GetCallerIdentity'});
MERGE (ev3:Event {name: 'RunInstances'});
MERGE (ev4:Event {name: 'CreateAccessKey'});

MERGE (f1:Field {name: 'sourceIPAddress'});
MERGE (f2:Field {name: 'userAgent'});
MERGE (f3:Field {name: 'requestParameters.instanceType'});
MERGE (f4:Field {name: 'errorCode'});

// Relationships: events have fields
MERGE (ev1)-[:HAS_FIELD]->(f1);
MERGE (ev1)-[:HAS_FIELD]->(f2);
MERGE (ev2)-[:HAS_FIELD]->(f1);
MERGE (ev3)-[:HAS_FIELD]->(f3);
MERGE (ev4)-[:HAS_FIELD]->(f4);

// Sample tags / node classes
MERGE (t1:Tag {name: 'RECON'});
MERGE (ev2)-[:TAGGED_AS]->(t1);

// Add a small sample mapping example
MERGE (m:Mapping {id: 'sample1'})-[:MAPS_EVENT]->(ev3);
MERGE (m)-[:MAPS_FIELD]->(f3);

RETURN 'OK';
