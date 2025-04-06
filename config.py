"""Configuration settings and tool definitions for Endless Novel V0."""

# --- Constants ---
LOG_FILE = "game_log.json"
MAX_TURNS = 50 # Limit game length for testing
PROMPT_DIR = "prompts" # Ensure this is defined
MAX_HISTORY_MESSAGES = 20 # Max messages to keep in narrative history

# --- Debugging Flags ---
DEBUG_IGNORE_LOCATION = True # If True, bypasses location checks for presence and prevents location updates.

# --- Tool Definition for Claude ---
# This defines the structure Claude should use to request state changes.
update_game_state_tool = {
    "name": "update_game_state",
    "description": "Updates the explicit game state based on narrative events (e.g., player location, player inventory, companion state, flags, objectives). Use ONLY for these specific state changes. DO NOT use this to introduce new characters (use create_character), or to start/end dialogue.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "The new unique ID or descriptive name for the player's location."},
            "time_of_day": {"type": "string", "description": "The new time of day (e.g., 'afternoon', 'evening')."},
            "player_inventory_add": {"type": "array", "items": {"type": "string"}, "description": "List of item names to add to player inventory."},
            "player_inventory_remove": {"type": "array", "items": {"type": "string"}, "description": "List of item names to remove from player inventory."},
            "narrative_flags_set": {"type": "object", "description": "Dictionary of narrative flags to set or update (key: value). Example: {'quest_started': true, 'door_unlocked': false}"},
            "narrative_flags_delete": {"type": "array", "items": {"type": "string"}, "description": "List of narrative flag keys to delete."},
            "companion_updates": {
                "type": "object",
                "description": "Updates for specific COMPANIONS/CHARACTERS managed by CharacterManager, keyed by character ID (e.g., 'varnas_the_skeptic'). Use this for changes like inventory or relationships FOR EXISTING characters.",
                "additionalProperties": { # Allows updates for any character ID
                    "type": "object",
                    "properties": {
                         "inventory_add": {"type": "array", "items": {"type": "string"}},
                         "inventory_remove": {"type": "array", "items": {"type": "string"}},
                         "relation_to_player_score": {"type": "number", "description": "DEPRECATED - Use update_relationship tool for trust changes during dialogue."}, # Mark as deprecated? or remove?
                         "relation_to_player_summary": {"type": "string", "description": "DEPRECATED - Relationship summaries evolve naturally through dialogue and trust changes."}, 
                         "relations_to_others_set": {"type": "object", "description": "(Future Use) Dict of other character IDs to relationship scores."}
                    },
                    "additionalProperties": False # Prevent unexpected fields per companion
                }
            },
            "current_objective": {"type": ["string", "null"], "description": "Set the player's current main objective text or null to clear."}
        },
        "additionalProperties": False # Disallow unexpected top-level update keys
    }
}

# Tool to specifically start dialogue
start_dialogue_tool = {
    "name": "start_dialogue",
    "description": "Initiates a direct conversation with a specific character who is present. Use this when the narrative indicates the player wants to talk to someone.",
    "input_schema": {
        "type": "object",
        "properties": {
            "character_id": {
                "type": "string",
                "description": "The unique ID of the companion character to start talking to (e.g., 'varnas_the_skeptic'). Must be one of the currently present companions."
            }
        },
        "required": ["character_id"]
    }
}

# Tool to specifically end dialogue
end_dialogue_tool = {
    "name": "end_dialogue",
    "description": "Ends the current direct conversation with a character. Use this when the conversation concludes naturally or the player indicates they want to stop talking.",
    "input_schema": {
        "type": "object",
        "properties": {},
         # No parameters needed, it always ends the *current* dialogue.
    }
}

# --- Character Creation Tool --- #
create_character_tool = {
    "name": "create_character",
    "description": "Generates and adds a new character to the game world based on a requested archetype and location. Use this when the narrative calls for a new NPC to appear.",
    "input_schema": {
        "type": "object",
        "properties": {
            "archetype": {
                "type": "string",
                "description": "The type of character to create.",
                "enum": ["townsperson", "companion", "foe", "love_interest"] # Allowed archetypes
            },
            "location": {
                "type": "string",
                "description": "The location ID/name where the character should be created. If omitted, might default to player location based on context."
            },
            "name_hint": {
                "type": "string",
                "description": "An optional hint for the character's name (e.g., a specific name suggested by narrative)."
            }
            # Consider adding 'context_summary' later if generation needs more narrative input
        },
        "required": ["archetype"]
        # Location is technically required by the manager, but let the LLM 
        # potentially infer it or make it optional here and handle default in Python?
        # Making it not required here for flexibility, will handle default in Python if needed.
    }
}
