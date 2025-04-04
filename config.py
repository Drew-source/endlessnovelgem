"""Configuration settings and tool definitions for Endless Novel V0."""

# --- Constants ---
LOG_FILE = "game_log.json"
MAX_TURNS = 50 # Limit game length for testing
PROMPT_DIR = "prompts" # Ensure this is defined
MAX_HISTORY_MESSAGES = 20 # Max messages to keep in narrative history

# --- Tool Definition for Claude ---
# This defines the structure Claude should use to request state changes.
update_game_state_tool = {
    "name": "update_game_state",
    "description": "Updates the explicit game state based on narrative events (location, inventory, character relationships, flags, objectives). Use ONLY for these narrative-driven changes. DO NOT use this to start or end dialogue; use the dedicated dialogue tools for that.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "The new unique ID or descriptive name for the player's location."},
            "time_of_day": {"type": "string", "description": "The new time of day (e.g., 'afternoon', 'evening')."},
            "player_inventory_add": {"type": "array", "items": {"type": "string"}, "description": "List of item names to add to player inventory."},
            "player_inventory_remove": {"type": "array", "items": {"type": "string"}, "description": "List of item names to remove from player inventory."},
            "narrative_flags_set": {"type": "object", "description": "Dictionary of narrative flags to set or update (key: value). Example: {'quest_started': true, 'door_unlocked': false}"},
            "narrative_flags_delete": {"type": "array", "items": {"type": "string"}, "description": "List of narrative flag keys to delete."},
            "current_npcs_add": {"type": "array", "items": {"type": "string"}, "description": "List of non-companion NPC IDs/names now present in the location."},
            "current_npcs_remove": {"type": "array", "items": {"type": "string"}, "description": "List of non-companion NPC IDs/names no longer present in the location."},
            "companion_updates": {
                "type": "object",
                "description": "Updates for specific companions, keyed by companion ID (e.g., 'varnas_the_skeptic').",
                "additionalProperties": { # Allows updates for any companion ID
                    "type": "object",
                    "properties": {
                         "present": {"type": "boolean", "description": "Set companion presence status in the current location."},
                         "inventory_add": {"type": "array", "items": {"type": "string"}},
                         "inventory_remove": {"type": "array", "items": {"type": "string"}},
                         "relation_to_player_score": {"type": "number", "minimum": 0.0, "maximum": 1.0, "description": "Update relationship score (0=hate, 1=love)."},
                         "relation_to_player_summary": {"type": "string", "description": "Update brief summary of relationship."}, # Allow direct update? Or generate?
                         "relations_to_others_set": {"type": "object", "description": "Dict of other companion/NPC IDs to relationship scores (0-1)."}
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
