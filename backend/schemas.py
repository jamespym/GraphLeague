from pydantic import BaseModel, Field
from typing import Literal, List, Union

StrategicMechanic = Literal[
    "Projectile Block",   # Yasuo W
    "High Sustain",       # Aatrox
    "Grievous Wounds",    # Katarina R
    "Shield Reave",       # Renekton W
    "Shielding",          # Karma (Triggers Weakness to Reave)
    "True Sight",         # TF R
    "Invisibility",       # Akali
    "Knock-up",
    "High Mobility",      # Irelia
    "Anti-Dash",          # Poppy W
    "Unstoppable",        # Olaf R
    "Cleanse",            # GP W, Milio R
    "Anti-Auto Attack",   # Shen W
]

ValidPosition = Literal["Top", "Jungle", "Mid", "Bot", "Support"]

#ValidArchetype = Literal["Tank", "Fighter", "Mage", "Assassin", "Marksman", "Support"]

# 2. Granular Subclass
ValidArchetype = Literal[
    "Vanguard",   # Offensive Tank (Leona, Malphite)
    "Warden",     # Defensive Tank (Braum, Tahm Kench)
    "Diver",      # Mobile Fighter (Camille, Renekton)
    "Juggernaut", # Immobile Fighter (Darius, Mordekaiser)
    "Burst",      # Burst Mage/Assassin (Syndra, Zed)
    "Battlemage", # Short range DPS Mage (Ryze, Vladimir)
    "Artillery",  # Long range Poke (Xerath, Jayce)
    "Marksman",   # ADC (Ashe, Jinx)
    "Enchanter",  # Buffing Support (Lulu, Janna)
    "Catcher"     # Hook/Pick Support (Thresh, Morgana)
]

class MechanicExplanation(BaseModel):
    name: StrategicMechanic
    details: str = Field(..., description="Brief explanation of WHICH ability/passive causes this and HOW. E.g., 'W (Wind Wall) destroys all incoming projectiles.'")
    
class ChampionNode(BaseModel):
     name: str
     archetype: ValidArchetype
     primary_position: List[ValidPosition]
     mechanics: List[MechanicExplanation] = Field(..., description="Strategic mechanics of the champion with context.")

'''
class Relationship(BaseModel):
    source: str
    target: Union[StrategicMechanic, ValidPosition] # The Target
    relation_type: Literal["PLAYS_IN", "IS_A", "HAS_MECHANIC", "WEAK_TO"]
    reasoning: str = Field(..., description="E.g. 'Wind Wall blocks projectiles'")

class ChampionGraphData(BaseModel):
    champion_name: str
    
    primary_role: ValidPosition
    relationships: List[Relationship]
'''