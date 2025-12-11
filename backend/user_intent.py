from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from schemas import StrategicMechanic, ValidArchetype, ValidPosition

class CounterPick(BaseModel):
    intent_type: Literal['counter_pick']
    enemy_champion: str = Field(..., description="The name of the enemy champion the user is trying to counter")
    my_position: ValidPosition | None = Field(
        None, 
        description=(
            "The user's intended role. Only if declared, you MUST normalize input to one of: "
            "'Top', 'Jungle', 'Mid', 'Bot', 'Support'. "
            "Map 'ADC' or 'Marksman' -> 'Bot'. "
            "Map 'sp' -> 'Support'."
            "Map 'jg'/'jng' as 'Jungle'"
        )
    )
    
class MechanicSearch(BaseModel):
    intent_type: Literal["mechanic_search"]
    my_position: ValidPosition | None = Field(
        None, 
        description=(
            "The user's intended role. Only if declared, you MUST normalize input to one of: "
            "'Top', 'Jungle', 'Mid', 'Bot', 'Support'. "
            "Map 'ADC' or 'Marksman' -> 'Bot'. "
            "Map 'sp' -> 'Support'."
            "Map 'jg'/'jng' as 'Jungle'"
        )
    )
    mechanic_concept: StrategicMechanic = Field(
        ..., 
        description=(
            "The specific game mechanic involved. "
            "You MUST normalize user inputs to one of the strict allowed values. "
            "Examples: Map 'anti-heal' -> 'Grievous Wounds', 'windwall' -> 'Projectile Block'."
        )
    )
    
class ArchetypeCounters(BaseModel):
    intent_type: Literal["archetype_counter"]
    enemy_archetype: ValidArchetype = Field(..., description="The archetype that the user wishes to counter")
    my_position: ValidPosition | None = Field(
        None, 
        description=(
            "The user's intended role. Only if declared, you MUST normalize input to one of: "
            "'Top', 'Jungle', 'Mid', 'Bot', 'Support'. "
            "Map 'ADC' or 'Marksman' -> 'Bot'. "
            "Map 'sp' -> 'Support'."
            "Map 'jg'/'jng' as 'Jungle'"
        )
    )
    
class UnknownIntent(BaseModel):
    intent_type: Literal["unknown"]
    reason: str = Field(..., description="Why the query could not be handled (e.g. 'Asking about lore/skins/stats/items'.")
    
    
class Router(BaseModel):
    choice: Union[CounterPick, MechanicSearch, ArchetypeCounters, UnknownIntent]