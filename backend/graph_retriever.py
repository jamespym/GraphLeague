import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from schemas import ChampionGraphData

load_dotenv()

class GraphRetriever:
    def __init__(self):
        load_dotenv()
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_pw = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pw))
        
    def close(self):
        self.driver.close()
        
    def get_counter_picks(self, champion_name):
        with self.driver.session() as session:
            # 1. Find the Champion's Weaknesses
            # 2. Find who has the Mechanic that exploits that weakness
            # 3. Filter by Role (Optional, but good for context)
            query = """
            MATCH (target:Champion {name: $name})
            MATCH (target)-[:PLAYS_IN]->(common_role:Position)
            MATCH (target)-[r1:WEAK_TO]->(weakness:Mechanic)
            MATCH (counter:Champion)-[r2:HAS_MECHANIC]->(weakness)
            MATCH (counter)-[:PLAYS_IN]->(common_role)
            
            RETURN 
                target.name as Target, 
                weakness.name as Weakness, 
                counter.name as Counter, 
                counter.primary_role as Position,
                r1.reasoning as Why_Weak,
                r2.reasoning as How_Counter
            LIMIT 10
            """
            
            result = session.run(query, name=champion_name)
            return [record.data() for record in result] # streamed
        
    def get_synergy_picks(self, champion_name):
        """
        Finds champions that share synergistic mechanics (e.g., Yasuo + Knock Up)
        """
        with self.driver.session() as session:
            query = """
            MATCH (c1:Champion {name: $name})-[:HAS_MECHANIC]->(mech:Mechanic)
            MATCH (c2:Champion)-[:HAS_MECHANIC]->(mech)
            WHERE c1 <> c2
            RETURN c1.name, mech.name, c2.name, c2.primary_role
            LIMIT 5
            """
            result = session.run(query, name=champion_name)
            return [record.data() for record in result]
        
    def get_matchup_advice(self, champion_name, opp_champion_name):
        # not yet finalised
        """
        Gets information on champion specific matchups using 
        """
        your_champ = self.get_counter_picks(champion_name)
        opp_champ = self.get_counter_picks(opp_champion_name)
        matchup_data = {
        "your_champion": champion_name,
        "opposing_champion": opp_champion_name,
        "your_weakness_data": your_champ,
        "opponent_weakness_data": opp_champ
        }
        return matchup_data
        
test = GraphRetriever()
print(test.get_counter_picks("Akali"))