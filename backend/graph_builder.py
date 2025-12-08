import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from schemas import ChampionGraphData

load_dotenv()
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_pw = os.getenv("NEO4J_PASSWORD")

print(neo4j_pw, neo4j_uri, neo4j_user)

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pw))

class GraphInserter:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
        
    def close(self):
        self.driver.close()
        
    def insert_data(self, champions_list):
        with self.driver.session() as session:
            for champ_data in champions_list:
                print(f'Processing {champ_data['champion_name']}...')
                
                # create Champion node
                session.run(
                    """
                    MERGE (c:Champion {name: $name})
                    SET c.primary_role = $role
                    """,
                    name=champ_data['champion_name'],
                    role=champ_data['primary_role']
                )
                
                # create other Nodes and Edges from Relationship list
                for rel in champ_data['relationships']:
                    self._create_relationship(session, champ_data['champion_name'], rel)
    
    def _create_relationship(self, session, source_name, rel_data):
        target_name = rel_data['target']
        rel_type = rel_data['relation_type']
        reasoning = rel_data['reasoning']

        # 1. Determine Target Node Label
        # If it's a "PLAYS_IN" relationship, the target is a Position.
        # Otherwise, it's a Mechanic (Weakness, Strategy, etc).
        if rel_type == "PLAYS_IN":
            target_label = "Position"
        else:
            target_label = "Mechanic"

        # 2. Run the Cypher Query
        # This creates the Target Node (if it doesn't exist) AND the Edge
        query = f"""
        MATCH (c:Champion {{name: $source}})
        MERGE (t:{target_label} {{name: $target}})
        MERGE (c)-[r:{rel_type}]->(t)
        SET r.reasoning = $reasoning
        """

        session.run(
            query,
            source=source_name,
            target=target_name,
            reasoning=reasoning
        )
        
with open('backend/processed_champions_v2.json', 'r') as f:
    data = json.load(f)

# 2. Run the Inserter
inserter = GraphInserter(neo4j_uri, (neo4j_user, neo4j_pw))
try:
    inserter.insert_data(data)
    print("✅ All data inserted!")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    inserter.close()