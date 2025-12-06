from pydantic import BaseModel, Field
from typing import Literal, List, Union

# 1. Controlled Vocabulary (The Validation Layer)

StrategicMechanic = Literal[
    "Projectile Block",   # Yasuo W, Samira W
    "High Sustain",       # Aatrox, Soraka
    "Grievous Wounds",    # Anti-Heal
    "Shield Reave",       # Renekton W
    "True Sight",         # TF R
    "Invisibility",       # Akali
    "High Mobility",      # Yasuo, Irelia
    "Anti-Dash",          # Poppy W (Grounding)
    "Unstoppable",        # Olaf R
    "Percent HP Dmg",     # Vayne
    "Knock Up",           # Yasuo Synergy
    "Anti-Auto Attack"    # Teemo, Jax
]

ValidPosition = Literal["Top", "Jungle", "Mid", "Bot", "Support"]

class Relationship(BaseModel):
    source: str
    target: Union[StrategicMechanic, ValidPosition] # The Target
    relation_type: Literal["PLAYS_IN", "HAS_MECHANIC", "WEAK_TO", "APPLIES_EFFECT"]
    reasoning: str = Field(..., description="E.g. 'Wind Wall blocks projectiles'")

class ChampionGraphData(BaseModel):
    champion_name: str
    primary_role: ValidPosition
    relationships: List[Relationship]