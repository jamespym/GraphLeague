import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from google import genai
import time
from google.genai.errors import ServerError
import user_intent

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
        
    def get_counter_picks(self, enemy_name, position=None, limit=3):
        query = """
                MATCH (enemy:Champion {name: $enemyName})
                MATCH (me:Champion)
                
                // Lane Filter
                WHERE ($myLane IS NULL OR $myLane = "" OR EXISTS { (me)-[:PLAYS_IN]->(:Role {name: $myLane}) })
                
                // --- OFFENSE (Why I beat them) ---
                OPTIONAL MATCH (enemy)-[:IS_A]->(:Archetype)<-[r1:COUNTERS]-(:Archetype)<-[:IS_A]-(me)
                OPTIONAL MATCH (enemy)-[w1:WEAK_TO]->(:Mechanic)<-[r2:HAS_MECHANIC]-(me)
                
                // --- DEFENSE (Why they beat me) ---
                // Note the direction reversal: (me)-[:IS_A]...
                OPTIONAL MATCH (me)-[:IS_A]->(:Archetype)<-[r3:COUNTERS]-(:Archetype)<-[:IS_A]-(enemy)
                OPTIONAL MATCH (me)-[w2:WEAK_TO]->(:Mechanic)<-[r4:HAS_MECHANIC]-(enemy)
                
                WITH me, 
                    // Offense Counts
                    count(DISTINCT r1) AS offArch,
                    count(DISTINCT r2) AS offMech,
                    collect(DISTINCT r1.reason) + collect(DISTINCT w1.reason) AS pros,
                    
                    // Defense Counts
                    count(DISTINCT r3) AS defArch,
                    count(DISTINCT r4) AS defMech,
                    collect(DISTINCT r3.reason) + collect(DISTINCT w2.reason) AS cons

                // --- NET SCORE CALCULATION ---
                // Offense is Positive, Defense is Negative
                WITH me, pros, cons,
                    ((offArch * 1) + (offMech * 2)) AS offensiveScore,
                    ((defArch * 1) + (defMech * 2)) AS defensiveScore
                    
                WITH me, pros, cons, offensiveScore, defensiveScore,
                    (offensiveScore - defensiveScore) AS netScore
                
                // Filter: You must strictly be an ADVANTAGE (Score > 0)
                // If Blitz is +2 (Shield Reave) and -2 (Blocked Hook), he is 0 and gets filtered.
                WHERE netScore > 0

                RETURN 
                    me.name AS Champion, 
                    netScore AS Score, 
                    offensiveScore AS Offense,
                    defensiveScore AS Defense,
                    // We only show the PROS in the reasoning, but you could show cons too
                    [x IN pros WHERE x IS NOT NULL] AS Reasoning,
                    [x IN cons WHERE x IS NOT NULL] AS Risks
                ORDER BY netScore DESC, offensiveScore DESC
                LIMIT $limit
                """
        
        with self.driver.session() as session:
            params = {"enemyName": enemy_name, "myLane": position, "limit": limit}
            result = session.run(query, parameters=params)
            return [record.data() for record in result]
    
    def find_mechanic_holders(self, mechanic_name, position=None):
        # Finds all champions who HAVE a specific mechanic."""
        query = """
                // FIX 1: Add 'r' inside the brackets to capture the relationship variable
                MATCH (c:Champion)-[r:HAS_MECHANIC]->(m:Mechanic {name: $mechName})
                
                // Lane Filter
                WHERE ($myLane IS NULL OR $myLane = "" OR EXISTS { (c)-[:PLAYS_IN]->(:Role {name: $myLane}) })
                
                // FIX 2: Return 'r.description' (The Edge), NOT 'm.description' (The Node)
                RETURN c.name AS Champion, r.description AS Tool
                ORDER BY c.name ASC
                LIMIT 5
                """
        with self.driver.session() as session:
            params = {"mechName": mechanic_name, "myLane": position}
            result = session.run(query, parameters=params)
            return [record.data() for record in result]

    def get_archetype_counters(self, target_archetype, position=None):
        # Finds champions whose ARCHETYPE counters the TARGET ARCHETYPE, filtered by lane
        query = """
                MATCH (target:Archetype {name: $archName})<-[r:COUNTERS]-(counterClass:Archetype)
                MATCH (c:Champion)-[:IS_A]->(counterClass)
                
                // Lane Filter
                WHERE ($myLane IS NULL OR $myLane = "" OR EXISTS { (c)-[:PLAYS_IN]->(:Role {name: $myLane}) })
                
                RETURN c.name AS Champion, counterClass.name AS Class, r.reason AS Reason
                ORDER BY c.name ASC
                LIMIT 5
                """
        with self.driver.session() as session:
            # Pass the position parameter
            params = {"archName": target_archetype, "myLane": position}
            result = session.run(query, parameters=params)
            return [record.data() for record in result]
        
class Switchboard:
    def __init__(self):
    
        self.model = genai.Client()
        
        # 2. The Prompt is now much simpler. 
        # We don't need to explain the JSON structure or list valid literals manually.
        # The 'response_schema' handles strict enums automatically.
        self.system_prompt = """
        You are the Intent Classifier for a League of Legends strategy tool.
        Analyze the user's query and route it to the correct intent object.
        
        - Map synonyms for mechanics (e.g. "Anti-Heal" -> "Grievous Wounds").
        - Map synonyms for lanes (e.g. "ADC" -> "Bot").
        - If the query is about skins, lore, or stats, choose UnknownIntent.
        """
    
    def classify_intent(self, user_query: str):
        try:
            response = self.model.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{self.system_prompt}\n\nUser Query: {user_query}",
                config={
                "response_mime_type": "application/json",
                "response_schema": user_intent.Router, 
                "temperature": 0.3,
                }
            )
            json_data = json.loads(response.text)
            return user_intent.Router(**json_data).choice
        
        except Exception as e:
            print(f"ROUTING ERROR: {e}")
            return user_intent.UnknownIntent(
                intent_type="unknown", 
                reason="System Error during routing"
            )

    def handle_query(self, user_query, graph_retriever):
        intent = self.classify_intent(user_query)
        context_str = ""
        match intent:
            case user_intent.CounterPick():
                print(f"Intent: Counter Pick vs {intent.enemy_champion} ({intent.my_position or 'Any Lane'})")
                context_str = f"Countering {intent.enemy_champion} in {intent.my_position or 'Any Lane'}"

                graph_data = graph_retriever.get_counter_picks(
                    enemy_name=intent.enemy_champion, 
                    position=intent.my_position, 
                    limit=5
                )
            # Case 2: Who has Anti Heal?
            case user_intent.MechanicSearch():
                print(f"🔍 Intent: Mechanic Search for {intent.mechanic_concept} ({intent.my_position or 'Any Lane'})")
                context_str = f"Champions with {intent.mechanic_concept} in {intent.my_position or 'Any Lane'}"
                
                graph_data = graph_retriever.find_mechanic_holders(
                    mechanic_name=intent.mechanic_concept,
                    position=intent.my_position
                )

            # Case 3: "Who to counter Burst?"
            case user_intent.ArchetypeCounters():
                print(f"🔍 Intent: Archetype Strategy vs {intent.enemy_archetype} ({intent.my_position or 'Any Lane'})")
                context_str = f"Champions that counter {intent.enemy_archetype}s in {intent.my_position or 'Any Lane'}"
                
                graph_data = graph_retriever.get_archetype_counters(
                    target_archetype=intent.enemy_archetype,
                    position=intent.my_position # Passed to new updated function
                )

            # Case 4: Nonsense / Off-topic
            case user_intent.UnknownIntent():
                print(f"⚠️ Unknown Intent: {intent.reason}")
                return f"I can't answer that right now. {intent.reason}"
            
            # Fallback for safety
            case _:
                print("⚠️ Error: Unrecognized intent type")
                return "I understood the words, but I don't have a handler for that specific action yet."

        return graph_data, context_str
       
# test = GraphRetriever()
# #print(test.get_archetype_counters("Diver", position='Mid'))
# print(test.find_mechanic_holders("High Sustain", position='Mid'))     
            

# --- SIMPLE TEST BLOCK ---
if __name__ == "__main__":
    # 1. Initialize
    print("Initializing services...")

    sb = Switchboard()
    graph = GraphRetriever()
    print("Services ready.\n")


    # 2. Define Test Cases covering all 3 major intents
    test_queries = [
        "Who counters Yasuo mid?",                      # CounterPick
        "Which supports have anti-heal?",               # MechanicSearch + Position
        "Best picks into Divers top lane?",              # ArchetypeCounters + Position
        "Who counters lots of dashes in middle?",                      # MechanicSearch (Synonym Mapping)
        "Tell me about Arcane lore"                     # UnknownIntent
    ]
    
    # 3. Run Loop
    try:
        for q in test_queries:
            print("-" * 60)
            print(f"User Query: '{q}'")
            
            # Execute logic
            data, context = sb.handle_query(q, graph)
            
            # Print Output
            print(f"\nContext: {context}")
            if data:
                print(f"Graph Data Found: {len(data)} records")
                # Print first result to verify structure
                print(f"Sample: {data[0]}") 
            else:
                print("Graph Data: [] (Empty or Error)")
                
    except Exception as e:
        print(f"\nCRITICAL ERROR during test: {e}")
        
    finally:
        print("\nClosing database connection...")
        graph.close()