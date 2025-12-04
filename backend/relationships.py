import json

with open('backend/champions.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)
    
champions = raw_data['data']
formatted_prompts = []

for name, details in champions.items():
    # Extract Tags (e.g., Fighter, Mage)
    tags = ", ".join(details.get('tags', []))
    
    # 2. Extract Passive (NEW STEP)
    # The passive is a single object, not a list
    passive_data = details.get('passive', {})
    passive_name = passive_data.get('name', 'Unknown Passive')
    passive_desc = passive_data.get('description', '')
    
    # Format the passive string
    passive_text = f"- (Passive) {passive_name}: {passive_desc}\n"
    
    # Extract Spells (Q, W, E, R)
    spells_text = ""
    for spell in details.get('spells', []):
        spell_name = spell['name']
        # Combine tooltip and description for maximum context
        desc = spell['description']
        # Clean up HTML tags if necessary, or let the LLM handle it
        spells_text += f"- {spell_name}: {desc}\n"
    
    # 3. Create the "Champion Context" string
    champion_context = f"""
    Champion Name: {name}
    Roles/Tags: {tags}
    Abilities:
    {passive_text}{spells_text}
    """

    # 4. Construct the Prompt for the LLM
    # We ask the LLM to return JSON-like relationships specifically for a Graph
    prompt = f"""
    You are an expert League of Legends analyst. 
    Analyze the following champion data and identify relationships to other concepts or champions.
    
    DATA:
    {champion_context}
    
    TASK:
    Identify 3 types of relationships based on the abilities and tags:
    1. "HAS_CC" (If they have Stun, Slow, Knockup, etc.)
    2. "BELONGS_TO_CLASS" (Based on tags)
    3. "SYNERGIZES_WITH" (Infer playstyle concepts, e.g., "Aggressive Engage", "Poke Composition")

    OUTPUT FORMAT:
    Return a JSON list of triples: [Source, Relationship, Target]
    Example: [["Aatrox", "HAS_CC", "Knock Up"], ["Aatrox", "BELONGS_TO_CLASS", "Fighter"]]
    """
    
    formatted_prompts.append(prompt)

# Example: Print the prompt for the first champion to verify
print(formatted_prompts[43])