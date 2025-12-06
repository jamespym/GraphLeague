import json
import os
from dotenv import load_dotenv
from schemas import ChampionGraphData
from google import genai

load_dotenv()
client = genai.Client()

# load json
with open('backend/champions.json', 'r', encoding='utf-8') as f:
    input_json = json.load(f)
    
counter = 0
output_list = []
for champion_id, champion_raw_data in input_json["data"].items():
    logic_rules = """
        MVP RULES OF ENGAGEMENT:
        1. "Projectile Block" -> IF ability blocks/destroys missiles.
        2. "Grievous Wounds" -> IF ability reduces healing.
        3. "Shield Reave" -> IF ability destroys shields.
        4. "Anti-Dash" -> IF ability stops movement/dashes within a set area.
        5. "Unstoppable" -> IF champion ignores Crowd Control.
        6. "Anti-Auto Attack" -> IF champion dodges or blinds attacks.
        7. "High Sustain" -> IF champion's kit revolves around healing

        LOGIC (WEAKNESSES):
        - IF "High Sustain" -> Weak to "Grievous Wounds"
        - IF "Shielding" -> Weak to "Shield Reave"
        - IF "Projectile Reliant" -> Weak to "Projectile Block"
        - IF "High Mobility" -> Weak to "Anti-Dash"
        """
    
    prompt = (
        f"Based on the following raw data, extract the relationships into the required JSON schema, using only the provided vocabulary"
        f"Champion raw data: {json.dumps(champion_raw_data)}"
        f"{logic_rules}\n"
        "Output valid JSON only. Do not output Python class constructors (e.g., do not write ChampionNode(...)). Output standard JSON objects (e.g., {'name': '...'})."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt,
        config={"response_mime_type": "application/json",
                "response_json_schema": ChampionGraphData.model_json_schema(),
        }
    )
    
    try:
        data = json.loads(response.text)
        output_list.append(ChampionGraphData(**data))
        print(f"Successfully processed {champion_id}")
    except json.JSONDecodeError as e:
            print(f"Failed to process {champion_id}. Error: {e}")
    
    counter += 1
    
    if counter == 3: break
    


print(output_list)