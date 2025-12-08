import json
import os
from dotenv import load_dotenv
from schemas import ChampionGraphData
from google import genai
import time
from google.genai.errors import ServerError

load_dotenv()
client = genai.Client()

# load json
with open('backend/champions.json', 'r', encoding='utf-8') as f:
    input_json = json.load(f)
    
output_list = []

logic_rules = """
        MVP RULES OF ENGAGEMENT:
        1. "Projectile Block" -> IF ability blocks/destroys missiles.
        2. "Grievous Wounds" -> IF ability reduces healing.
        3. "Shield Reave" -> IF ability destroys shields.
        4. "Anti-Dash" -> IF ability stops movement/dashes within a set area.
        5. "Unstoppable" -> IF champion ignores Crowd Control.
        6. "Anti-Auto Attack" -> IF champion dodges or blinds attacks.
        7. "High Sustain" -> IF champion's kit revolves around healing (small/sparse instances of healing do not count)
        8. "High Mobility" -> IF and only if champion's kit heavily revolves around dashes and movement speed (a single, long-cooldown dash is not sufficient to qualify)
        9. "Shielding" -> IF champion heavily relies on shields

        LOGIC (WEAKNESSES):
        - IF "High Sustain" -> Weak to "Grievous Wounds"
        - IF "Shielding" -> Weak to "Shield Reave"
        - IF "Projectile Reliant" -> Weak to "Projectile Block"
        - IF "High Mobility" -> Weak to "Anti-Dash"
        """

output_file_path = 'backend/processed_champions_v2.json'

# Load existing progress if file exists (so you don't restart from Aatrox)
if os.path.exists(output_file_path):
    with open(output_file_path, 'r', encoding='utf-8') as f:
        try:
            saved_data = json.load(f)
            # Create a set of names we have already finished
            processed_ids = {item['champion_name'] for item in saved_data} 
            output_list = [ChampionGraphData(**item) for item in saved_data]
            print(f"Loaded {len(output_list)} champions from previous run.")
        except json.JSONDecodeError:
            processed_ids = set()
else:
    processed_ids = set()

for champion_id, champion_raw_data in input_json["data"].items():
    
    # SKIP logic: If we already have this champion, skip it
    if champion_id in processed_ids: 
        print(f"Skipping {champion_id} (already done)")
        continue
    
    prompt = (
        f"Based on the following raw data, extract the relationships into the required JSON schema, using only the provided vocabulary"
        f"Champion raw data: {json.dumps(champion_raw_data)}"
        f"{logic_rules}\n"
        "Output valid JSON only. Do not output Python class constructors (e.g., do not write ChampionNode(...)). Output standard JSON objects (e.g., {'name': '...'})."
    )

    # --- RETRY LOGIC START ---
    max_retries = 10
    response = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={"response_mime_type": "application/json",
                        "response_json_schema": ChampionGraphData.model_json_schema(),
                        "temperature": 1.0
                }
            )
            break # Success, exit retry loop
        except ServerError as e:
            if e.code == 503:
                wait = (2 ** attempt) * 2 # Wait 2s, 4s, 8s...
                print(f"API Overloaded on {champion_id}. Sleeping {wait}s...")
                time.sleep(wait)
            else:
                print(f"Critical error on {champion_id}: {e}")
                break
    # --- RETRY LOGIC END ---
    
    if response:
        try:
            data = json.loads(response.text)
            champion_obj = ChampionGraphData(**data)
            output_list.append(champion_obj)
            processed_ids.add(champion_id)
            print(f"Successfully processed {champion_id}")
            
            # --- SAVE IMMEDIATELY ---
            # This is slightly inefficient (rewriting file every time) but 
            # 100% safe for your rush. If it crashes, you lose nothing.
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                json.dump([item.model_dump() for item in output_list], outfile, indent=4)
                
        except json.JSONDecodeError as e:
            print(f"Failed to process {champion_id}. JSON Error.")
    
    time.sleep(1)
            
            