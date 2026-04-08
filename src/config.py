# Add/remove as many as you want — these are popular liquid ones based on volume
from typing import List

LIQUID_POKEMON = [
    "charizard", "pikachu", "gyarados", "umbreon", "eevee", 
    "blastoise", "venusaur", "dragonite", "lucario", "gengar", 
    "arceus", "sylveon", "koraidon", "slowpoke", "slowking", "slowbro",
    "bulbasaur", "mewtwo", "greninja", "rayquaza", "snorlax", "gardevoir",
    "squirtle", "charmander", "charmeleon", "flamigo", "lapras", "vaporeon",
    "arcanine", "ninetales", "ditto"
]

# Minimum discount to consider (tunable)
MIN_DISCOUNT_PCT = 10.0
STRONG_DEAL_THRESHOLD = 25.0
GOOD_DEAL_THRESHOLD = 15.0  
SOL_PRICE = 82.01