import json
import os
from dotenv import load_dotenv
from backend.schemas import ChampionNode
from google import genai
import time
from google.genai.errors import ServerError

load_dotenv()
client = genai.Client()

INPUT_FILE = 'backend/champions.json'
OUTPUT_FILE = 'backend/processed_champions_v4.json'

# load json
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    input_json = json.load(f)

logic_rules = """
        RULES:
        1. "Projectile Block" -> IF ability blocks/destroys missiles.
        2. "Grievous Wounds" -> IF ability reduces healing.
        3. "Shield Reave" -> IF ability destroys shields.
        4. "Anti-Dash" -> IF ability specifically prevents the usage of movement abilities (Grounding effects) OR knocks down enemies mid-dash (Poppy W). 
            - EXCLUDE: Generic Crowd Control (Stuns, Roots, Charms, Fears) that incidentally stop movement, or Walls
            - Example: Poppy W is Anti-Dash. Ahri E (Charm) is NOT Anti-Dash.
        5. "Unstoppable" -> IF champion has an ability that provides immunity to Crowd Control.
            - EXCLUDE -> Generic Invulnerability/Stasis
            - Example: Olaf R is Unstoppable. Bard R / Xayah R is NOT Unstoppable
        6. "Cleanse" -> IF champion has an ability that removes a Crowd Control effect
        7. "Anti-Auto Attack" -> IF champion dodges or blinds attacks.
            - EXCLUDE -> Generic Invulnerability/Stasis
            - Example: Shen W is Anti-Auto Attack. Taric R is NOT Anti-Auto Attack
        8. "High Sustain" -> IF champion's kit revolves around healing.
            - EXCLUDE Champions with only small/sparse instances of healing
        9. "High Mobility" -> IF and only if champion's kit heavily revolves around dashes and movement speed 
            - EXCLUDE Champions with single, long-cooldown dashes
            - Example: Lillia, Katarina are classic High Mobility. Aatrox is High Mobility as his abiliities require dash. Gwen is NOT High Mobility.
        10. "Shielding" -> IF champion heavily relies on shields.
            - Example: Karma is Shielding. Jarvan IV is NOT Shielding
        11. "Projectile Reliant" -> IF champion's decisive and most important abilities are skillshots / projectiles
            - Example: Ashe is Projectile Reliant as all her abilities are projectiles. Blitzcrank only has 1 projectile, but it is paramount to his kit. Thus he is Projectile Reliant.
        
        ARCHETYPE CLASSIFICATION RULES:
        - "Vanguard": Aggressive tanks with hard, offensive engage abilities (e.g., Leona, Malphite, Amumu).
        - "Warden": Defensive tanks that protect allies (e.g., Braum, Galio, Taric).
        - "Diver": Fighters who dive backlines but aren't pure tanks (e.g., Vi, Camille, Irelia).
        - "Juggernaut": High durability/damage, low mobility (e.g., Darius, Garen, Nasus).
        - "Burst": Champions designed to 100-0 a target instantly (e.g., Syndra, LeBlanc, Zed).
        - "Battlemage": Sustained close-range magic damage (e.g., Ryze, Swain, Vladimir).
        - "Artillery": Extreme range poke, low mobility (e.g., Xerath, Vel'Koz, Varus).
        - "Marksman": Continuous attack damange from range, traditional ADCs (Jinx, Ashe, Caitlyn)
        - "Enchanter": Heals/Shields/Buffs allies (e.g., Lulu, Soraka, Janna).
        - "Catcher": Relies on fishing for picks/hooks (e.g., Thresh, Blitzcrank, Morgana).
        """

processed_ids = set()
output_list = []

if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        try:
            saved_data = json.load(f)
            output_list = [ChampionNode(**item) for item in saved_data]
            processed_ids = {item.name for item in output_list}
            print(f"Loaded {len(output_list)} champions from previous run.")
        except (json.JSONDecodeError, KeyError):
            print("Output file corrupted or empty. Starting fresh.")

for champion_id, champion_raw_data in input_json["data"].items():
    
    if champion_id in processed_ids:
        print(f"Skipping {champion_id} (already done)")
        continue
        
    print(f"Processing {champion_id}...")

    # Prompt Engineering
    prompt = (
        f"You are a League of Legends expert. Extract data for '{champion_id}' into the required JSON schema.\n\n"
        f"RAW DATA: {json.dumps(champion_raw_data)}\n\n"
        f"RULES:\n{logic_rules}\n"
        "INSTRUCTIONS:\n"
        "1. Analyze the raw data for abilities and mechanics.\n"
        "2. Map mechanics strictly to the 'StrategicMechanic' list. If an ability matches a rule, create a MechanicExplanation entry.\n"
        "3. For 'primary_position', use your INTERNAL KNOWLEDGE of the current meta (e.g., Yasuo -> Mid, Top). The raw data does not have this.\n"
        "4. Choose exactly ONE 'archetype' that best fits the champion's playstyle.\n"
        "Output valid JSON matching the ChampionNode schema."
    )

    max_retries = 8
    response = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": ChampionNode,
                    "temperature": 0.3
                }
            )
            break
        except ServerError as e:
            wait = (2 ** attempt)
            print(f"Server Error. Retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"Fatal Error on {champion_id}: {e}")
            break
    
    # Save & parsing
    if response and response.text:
        try:
            data = json.loads(response.text)
            champion_node = ChampionNode(**data)
            
            output_list.append(champion_node)
            processed_ids.add(champion_id)
            
            # Incremental save
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
                json.dump([node.model_dump() for node in output_list], outfile, indent=4)
            
            print(f"Processed successfully: {champion_id}", flush=True)
                
        except Exception as e:
            print(f"Validation Failed for {champion_id}: {e}")
    
    time.sleep(0.5)

print("Processing Complete.")