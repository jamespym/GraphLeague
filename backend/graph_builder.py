import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from schemas import ChampionNode

load_dotenv()
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_pw = os.getenv("NEO4J_PASSWORD")

#print(neo4j_pw, neo4j_uri, neo4j_user)

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pw))

LOGIC_RULES = {
    # IF target has [Key], THEN they are WEAK_TO [Value]
    "High Sustain": "Grievous Wounds",
    "Shielding": "Shield Reave",
    "High Mobility": "Anti-Dash",
    "Projectile Reliant": "Projectile Block", # Intermediate logic tag
    
    # Archetype Logic (Derived Rules)
    "Marksman": "Projectile Block",
    "Artillery": "Projectile Block"
}

ARCHETYPE_RULES = {
    "Burst":      [
        {"target": "Marksman", "reason": "Deletes squishy target instantly"},
        {"target": "Artillery", "reason": "Deletes squishy target instantly"},
        {"target": "Enchanter", "reason": "Deletes squishy target instantly"}
    ],
    "Marksman":   [
        {"target": "Juggernaut", "reason": "Kites and shreds health stackers"},
        {"target": "Warden", "reason": "Consistent DPS breaks tank defenses"},
        {"target": "Vanguard", "reason": "Consistent DPS breaks tank defenses"}
    ],
    "Artillery":  [
        {"target": "Juggernaut", "reason": "Out-ranges and pokes down"},
        {"target": "Battlemage", "reason": "Out-ranges short range mages"},
        {"target": "Catcher", "reason": "Poke damage whittles down engage threats"}
    ],
    "Diver":      [
        {"target": "Artillery", "reason": "Gap closes onto immobile backline"},
        {"target": "Marksman", "reason": "Gap closes onto immobile backline"}
    ],
    "Juggernaut": [
        {"target": "Diver", "reason": "Stat-checks and out-brawls"},
        {"target": "Vanguard", "reason": "Out-damages tanks in melee"},
        {"target": "Warden", "reason": "Out-damages tanks in melee"}
    ],
    "Warden":     [
        {"target": "Burst", "reason": "Tankiness neutralizes burst"},
        {"target": "Diver", "reason": "Peel stops divers from reaching carry"}
    ],
    "Vanguard":   [
        {"target": "Enchanter", "reason": "Hard engage locks down squishies"},
        {"target": "Artillery", "reason": "Hard engage catches immobile poke"},
        {"target": "Marksman", "reason": "Hard engage catches immobile poke"}
    ],
    "Catcher":    [
        {"target": "Enchanter", "reason": "CC setup sets up kill on squishy"},
        {"target": "Marksman", "reason": "CC setup sets up kill on squishy"}
    ],
    "Enchanter":  [
        {"target": "Artillery", "reason": "Sustain negates poke damage"}
    ],
    "Battlemage": [
        {"target": "Warden", "reason": "Sustained magic damage and CC can combat tanks"},
        {"target": "Vanguard", "reason": "Sustained magic damage and CC can combat tanks"}
    ]
}

class GraphInserter:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
        
    def close(self):
        self.driver.close()
    
    def create_constraints(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Champion) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Mechanic) REQUIRE m.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Archetype) REQUIRE a.name IS UNIQUE")
            print("Constraints created.")

    # --- NEW FUNCTION: Run this ONCE to build the logic graph ---
    def init_archetype_layer(self):
        """Builds the Rock-Paper-Scissors Logic layer."""
        print("Building Archetype Logic Layer...")
        with self.driver.session() as session:
            for source_class, targets in ARCHETYPE_RULES.items():
                # 1. Ensure the Source Archetype exists
                session.run("MERGE (:Archetype {name: $name})", name=source_class)
                
                for target in targets:
                    # 2. Ensure Target, then Create the COUNTERS edge
                    session.run(
                        """
                        MATCH (source:Archetype {name: $source})
                        MERGE (target:Archetype {name: $target})
                        MERGE (source)-[:COUNTERS {reason: $reason}]->(target)
                        """,
                        source=source_class,
                        target=target['target'],
                        reason=target['reason']
                    )

    def load_champion(self, champion_data):
        with self.driver.session() as session:
            # 1. Create Champion Node (Standard)
            session.run(
                """
                MERGE (c:Champion {name: $name})
                SET c.archetype = $archetype
                """, 
                name=champion_data['name'], archetype=champion_data['archetype'])

            # --- NEW STEP: Link Champion to the Archetype Graph ---
            # This connects "Zed" to the "Burst" node we created in init_archetype_layer
            session.run(
                """
                MATCH (c:Champion {name: $name})
                MERGE (a:Archetype {name: $archetype})
                MERGE (c)-[:IS_A]->(a)
                """,
                name=champion_data['name'], archetype=champion_data['archetype']
            )

            # 2. Create Role Edges (No change)
            for role in champion_data['primary_position']:
                session.run(
                    """
                    MATCH (c:Champion {name: $name})
                    MERGE (r:Role {name: $role})
                    MERGE (c)-[:PLAYS_IN]->(r)
                    """,
                    name=champion_data['name'], role=role)

            # 3. Create Mechanic Edges (No change)
            for mech in champion_data['mechanics']:
                mech_name = mech['name'] 
                session.run(
                    """
                    MATCH (c:Champion {name: $name})
                    MERGE (m:Mechanic {name: $mech_name})
                    
                    // Capture the relationship in variable 'r'
                    MERGE (c)-[r:HAS_MECHANIC]->(m)
                    
                    // Set the description on the RELATIONSHIP 'r', not the node 'm'
                    SET r.description = $details 
                    """, 
                    name=champion_data['name'], mech_name=mech_name, details=mech['details'])

            # 4. Create Weakness Edges (Your existing Logic)
            for mech in champion_data['mechanics']:
                mech_name = mech['name']
                
                # 1. Grab the detailed explanation from the JSON
                mech_details = mech.get('details', '') 

                if mech_name in LOGIC_RULES:
                    counter_mech = LOGIC_RULES[mech_name]
                    
                    # 2. Construct a "Rich Reason" string
                    # Format: "Vulnerable to [Counter] due to [Trait]: [Specific Ability Details]"
                    rich_reason = f"Vulnerable to {counter_mech} due to {mech_name}: {mech_details}"

                    session.run(
                        """
                        MATCH (c:Champion {name: $name})
                        MERGE (m:Mechanic {name: $counter_mech})
                        MERGE (c)-[:WEAK_TO {reason: $reason}]->(m)
                        """, 
                        name=champion_data['name'], 
                        counter_mech=counter_mech, 
                        reason=rich_reason
                    )
        
with open('backend/processed_champions_v4.json', 'r') as f:
    data = json.load(f)

if __name__ == "__main__":
    loader = GraphInserter(neo4j_uri, (neo4j_user, neo4j_pw))
    
    try:
        loader.create_constraints()
        # --- NEW: Build the rules first ---
        loader.init_archetype_layer()
        
        # Load Data
        INPUT_FILE = 'backend/processed_champions_v4.json'
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            champions = json.load(f)
            
        print(f"Importing {len(champions)} champions...", flush=True)
        
        for champ in champions:
            loader.load_champion(champ)
            print(f"Imported {champ['name']}")
            
        print("Import Complete!")
        
    finally:
        loader.close()