# Endless Novel - Version 0: Text-Based Narrative Engine
# Main Python script for the core game loop.

# --- Imports ---
# import anthropic # Placeholder for Anthropic API client
# import google.generativeai as genai # Placeholder for Google AI API client
# import os # For potentially loading API keys from environment
import time # For potential pauses/delays
import os # Now needed for path joining
import re
import json
import anthropic # Ensure imported
from dotenv import load_dotenv # For loading .env
import google.generativeai as genai # Add Google AI import
import copy # Needed for deepcopy
from google.api_core import retry

# --- Constants & Configuration ---
LOG_FILE = "game_log.json"
MAX_TURNS = 50 # Limit game length for testing
PROMPT_DIR = "prompts" # Ensure this is defined

# Load API keys securely (e.g., from environment variables)
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure API clients (replace with actual initialization)
# claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
# genai.configure(api_key=GOOGLE_API_KEY)
# gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or specific Gemini 2.5 Pro model when available via API

# --- API Client Initialization ---
# Load .env file at the start
load_dotenv()

# Initialize clients (could be done once globally or within functions)
# Global initialization might be cleaner
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
anthropic_model_name = os.getenv("ANTHROPIC_MODEL_NAME")

claude_client = None
if anthropic_api_key:
    try:
        claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
        print("[INFO] Anthropic client initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Anthropic client: {e}")
else:
    print("[ERROR] ANTHROPIC_API_KEY not found. Claude API calls will fail.")

# Initialize Google client
google_api_key = os.getenv("GOOGLE_API_KEY")
google_model_name = os.getenv("GOOGLE_MODEL_NAME")
gemini_client = None # Default to None

if google_api_key and google_model_name:
    try:
        genai.configure(api_key=google_api_key)
        gemini_client = genai.GenerativeModel(google_model_name)
        print(f"[INFO] Google AI client initialized for model: {google_model_name}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Google AI client: {e}")
        gemini_client = None # Ensure it's None on error
else:
    # Key or model name was missing
    if not google_api_key:
        print("[ERROR] GOOGLE_API_KEY not found. Gemini API calls will fail.")
    if not google_model_name:
        print("[ERROR] GOOGLE_MODEL_NAME not found. Gemini API calls will fail.")
    # gemini_client is already None from the initial declaration

# --- Game State (Final V0 Structure) ---
# See `docs/intent_v0.md` Section 4 and `docs/dialogue_system_design_v1.md` for details
INITIAL_GAME_STATE = {
    # Player Character
    'player': {
        'name': 'Player',
        'inventory': ['a worn adventurer pack', 'flint and steel'], # Example starting items
    },

    # World State
    'location': 'the edge of an ancient, whispering forest', # More evocative start
    'time_of_day': 'morning',
    'current_npcs': [], # Non-companions present

    # Companions (Core Feature)
    'companions': {
        # Example companion added for testing structure
        'varnas_the_skeptic': {
            'name': 'Varnas the Skeptic',
            'present': True,
            'inventory': ['worn leather armor', 'short sword', 'skeptical frown'],
            'relation_to_player_score': 0.5,
            'relation_to_player_summary': "Watches you with guarded neutrality.",
            'relations_to_others': {},
            # NEW: Memory structure for dialogue history
            'memory': {
                'dialogue_history': [],
                # Future: 'key_facts_learned': {}, 'relationship_log': [], 'emotional_state': 'neutral'
            }
        },
        # Add more companions here as needed
    },

    # Narrative / Quest Progression
    'narrative_flags': {},
    'current_chapter': 1,
    'current_objective': None,

    # NEW: Dialogue State Flags
    'dialogue_active': False,
    'dialogue_partner': None, # Stores companion ID when dialogue is active

    # Interaction / LLM Context
    'dialogue_target': None, # Review: Keep, remove, or sync with dialogue_partner? See design doc.
    'last_player_action': None,
    'narrative_context_summary': "Sunlight filters through the ancient trees. The air is cool and smells of damp earth and pine. Your companion, Varnas, shifts his weight beside you."
}

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

# NEW: Tool to specifically start dialogue
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

# NEW: Tool to specifically end dialogue
end_dialogue_tool = {
    "name": "end_dialogue",
    "description": "Ends the current direct conversation with a character. Use this when the conversation concludes naturally or the player indicates they want to stop talking.",
    "input_schema": {
        "type": "object",
        "properties": {},
         # No parameters needed, it always ends the *current* dialogue.
    }
}

# --- Prompt Loading Utility ---
def load_prompt_template(filename: str) -> str:
    """Loads a prompt template from the PROMPT_DIR."""
    filepath = os.path.join(PROMPT_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {filepath}")
        # Return a fallback string or raise an error
        return f"Error: Prompt template '{filename}' not found."
    except Exception as e:
        print(f"[ERROR] Failed to load prompt file {filepath}: {e}")
        return f"Error loading prompt: {filename}"

# Load templates at startup (or cache them)
# We cache them here to avoid repeated file reads
PROMPT_TEMPLATES = {
    "claude_system": load_prompt_template("claude_system.txt"),
    "claude_turn": load_prompt_template("claude_turn_template.txt"),
    "gemini_placeholders": load_prompt_template("gemini_placeholder_template.txt"),
    # NEW: Dialogue system prompts
    "dialogue_system": load_prompt_template("dialogue_system.txt"),
    "summarization": load_prompt_template("summarization_template.txt"),
}

# --- Game State Update Logic ---

# REVISED: Function to apply updates based on tool input schema
def apply_tool_updates(tool_input: dict, game_state: dict):
    """Applies updates to the game_state based on the input from the update_game_state tool.

    Directly modifies the game_state dictionary.
    """
    print("\n[DEBUG] Applying tool updates:", json.dumps(tool_input, indent=2)) # Debugging line
    updates_applied = False
    state_changed_summary = [] # List to hold summary strings

    # Location
    if "location" in tool_input:
        old_loc = game_state.get('location', 'None')
        new_loc = tool_input['location']
        if old_loc != new_loc:
            game_state['location'] = new_loc
            change_str = f"Location: {old_loc} -> {new_loc}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True

    # Time of Day
    if "time_of_day" in tool_input:
        old_time = game_state.get('time_of_day', 'None')
        new_time = tool_input['time_of_day']
        if old_time != new_time:
            game_state['time_of_day'] = new_time
            change_str = f"Time: {old_time} -> {new_time}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True

    # Player Inventory Add
    if "player_inventory_add" in tool_input:
        items_to_add = tool_input.get("player_inventory_add", [])
        if isinstance(items_to_add, list):
            added = []
            for item in items_to_add:
                if item not in game_state['player']['inventory']:
                    game_state['player']['inventory'].append(item)
                    added.append(item)
            if added:
                change_str = f"Player Inventory Add: {added}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Player Inventory Remove
    if "player_inventory_remove" in tool_input:
        items_to_remove = tool_input.get("player_inventory_remove", [])
        removed = []
        if isinstance(items_to_remove, list):
            # Iterate safely while modifying
            current_inv = list(game_state['player']['inventory'])
            for item in items_to_remove:
                if item in current_inv:
                    try:
                        game_state['player']['inventory'].remove(item)
                        removed.append(item)
                    except ValueError: pass # Should not happen if check passed
            if removed:
                change_str = f"Player Inventory Remove: {removed}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Narrative Flags Set/Update
    if "narrative_flags_set" in tool_input:
        flags_to_set = tool_input.get("narrative_flags_set", {})
        if isinstance(flags_to_set, dict) and flags_to_set:
            updated_flags = {k:v for k,v in flags_to_set.items() if game_state['narrative_flags'].get(k) != v}
            if updated_flags:
                 game_state['narrative_flags'].update(updated_flags)
                 change_str = f"Narrative Flags Set/Update: {updated_flags}"
                 print(f"  [State Update] {change_str}")
                 state_changed_summary.append(change_str)
                 updates_applied = True

    # Narrative Flags Delete
    if "narrative_flags_delete" in tool_input:
        flags_to_delete = tool_input.get("narrative_flags_delete", [])
        deleted = []
        if isinstance(flags_to_delete, list):
            for flag_key in flags_to_delete:
                if flag_key in game_state['narrative_flags']:
                    del game_state['narrative_flags'][flag_key]
                    deleted.append(flag_key)
            if deleted:
                change_str = f"Narrative Flags Delete: {deleted}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Current NPCs Add
    if "current_npcs_add" in tool_input:
        npcs_to_add = tool_input.get("current_npcs_add", [])
        added = []
        if isinstance(npcs_to_add, list):
            for npc in npcs_to_add:
                if npc not in game_state['current_npcs']:
                    game_state['current_npcs'].append(npc)
                    added.append(npc)
            if added:
                change_str = f"NPCs Add: {added}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Current NPCs Remove
    if "current_npcs_remove" in tool_input:
        npcs_to_remove = tool_input.get("current_npcs_remove", [])
        removed = []
        if isinstance(npcs_to_remove, list):
             current_npcs_list = list(game_state['current_npcs'])
             for npc in npcs_to_remove:
                 if npc in current_npcs_list:
                    try:
                         game_state['current_npcs'].remove(npc)
                         removed.append(npc)
                    except ValueError: pass # Already gone
             if removed:
                change_str = f"NPCs Remove: {removed}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Companion Updates
    if "companion_updates" in tool_input:
        companion_changes = tool_input.get("companion_updates", {})
        if isinstance(companion_changes, dict):
            comp_updates_applied = False
            for comp_id, updates in companion_changes.items():
                comp_change_summary = []
                if comp_id in game_state['companions'] and isinstance(updates, dict):
                    companion_state = game_state['companions'][comp_id]
                    # Check each possible update within the companion object
                    if "present" in updates and companion_state.get('present') != updates['present']:
                        companion_state['present'] = updates['present']
                        comp_change_summary.append(f"present={updates['present']}")
                        comp_updates_applied = True
                    if "inventory_add" in updates:
                         added_items = []
                         if 'inventory' not in companion_state: companion_state['inventory'] = []
                         for item in updates.get("inventory_add", []):
                             if item not in companion_state['inventory']:
                                 companion_state['inventory'].append(item)
                                 added_items.append(item)
                         if added_items: comp_change_summary.append(f"inv_add={added_items}")
                         if added_items: comp_updates_applied = True # Only flag if change occurred
                    if "inventory_remove" in updates:
                         removed_items = []
                         if 'inventory' in companion_state:
                             current_comp_inv = list(companion_state['inventory'])
                             for item in updates.get("inventory_remove", []):
                                 if item in current_comp_inv:
                                     try:
                                        companion_state['inventory'].remove(item)
                                        removed_items.append(item)
                                     except ValueError: pass
                             if removed_items: comp_change_summary.append(f"inv_remove={removed_items}")
                             if removed_items: comp_updates_applied = True
                    if "relation_to_player_score" in updates and companion_state['relation_to_player'].get('score') != updates['relation_to_player_score']:
                        companion_state['relation_to_player']['score'] = updates['relation_to_player_score']
                        comp_change_summary.append(f"rel_score={updates['relation_to_player_score']}")
                        comp_updates_applied = True
                    if "relation_to_player_summary" in updates and companion_state['relation_to_player'].get('summary') != updates['relation_to_player_summary']:
                        companion_state['relation_to_player']['summary'] = updates['relation_to_player_summary']
                        comp_change_summary.append("rel_summary_updated")
                        comp_updates_applied = True
                    if "relations_to_others_set" in updates:
                        others_set = updates.get("relations_to_others_set", {})
                        if isinstance(others_set, dict) and others_set:
                           if 'relations_to_others' not in companion_state: companion_state['relations_to_others'] = {}
                           updated_rels = {k:v for k,v in others_set.items() if companion_state['relations_to_others'].get(k) != v}
                           if updated_rels:
                               companion_state['relations_to_others'].update(updated_rels)
                               comp_change_summary.append(f"rels_others_set={updated_rels}")
                               comp_updates_applied = True
                # Log summary for this companion if changes were made
                if comp_change_summary:
                     change_str = f"Companion Update ({comp_id}): {'; '.join(comp_change_summary)}"
                     print(f"  [State Update] {change_str}")
                     state_changed_summary.append(change_str)
            if comp_updates_applied: updates_applied = True # Overall flag

    # Current Objective Update
    if "current_objective" in tool_input:
        old_obj = game_state.get('current_objective', None)
        new_obj = tool_input['current_objective'] # Can be None
        if old_obj != new_obj:
            game_state['current_objective'] = new_obj
            change_str = f"Objective: {old_obj} -> {new_obj}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True
            
    if not updates_applied:
        print("  [State Update] Tool call received, but no actual changes applied.")

    return updates_applied, state_changed_summary # Return status and summary

# --- Core API Call Functions ---

def call_claude_api(prompt_details: dict, tools=None) -> anthropic.types.Message | None:
    """Calls the Claude 3.7 Sonnet API using the Messages endpoint.

    Handles system prompt, user message, and includes the `update_game_state` tool.
    Now returns the raw Message object for the caller to handle.
    Accepts either a pre-constructed 'messages' list in prompt_details OR
    constructs messages from 'history' and 'user_prompt'.

    Args:
        prompt_details: A dictionary containing either:
                        - 'system': str, 'messages': list (for dialogue)
                        - 'system_prompt': str, 'user_prompt': str, 'history': list (for narrative)
        tools: Optional list of tools to provide to the API.

    Returns:
        The Anthropic Message object containing the response, or None on failure.
        Caller must check response.stop_reason and process content/tool calls.
    """
    if not claude_client:
        print("[ERROR] Anthropic client not initialized. Cannot call Claude API.")
        return None
    if not anthropic_model_name:
        print("[ERROR] Anthropic model name not configured.")
        return None

    # Determine message construction method based on keys in prompt_details
    if 'messages' in prompt_details and 'system' in prompt_details:
        # Dialogue call: Use pre-constructed messages list
        system_prompt = prompt_details.get('system', "")
        messages = prompt_details.get('messages', [])
        history_len_debug = len(messages) # For debug print
        print(f"--- Calling Claude ({anthropic_model_name}) for Dialogue (History: {history_len_debug} msgs) --- ")
    elif 'history' in prompt_details and 'user_prompt' in prompt_details:
        # Narrative call: Construct messages from history and user_prompt
        system_prompt = prompt_details.get('system_prompt', "")
        user_prompt = prompt_details.get('user_prompt', "")
        history = prompt_details.get('history', [])

        # TODO: Add history truncation logic here if it gets too long
        MAX_HISTORY_TURNS = 10 # Example limit (5 user, 5 assistant)
        truncated_history = history[-(MAX_HISTORY_TURNS*2):] if len(history) > (MAX_HISTORY_TURNS*2) else history
        history_len_debug = len(truncated_history) # For debug print
        
        messages = truncated_history + [
            {"role": "user", "content": user_prompt}
        ]
        print(f"--- Calling Claude ({anthropic_model_name}) for Narrative (Tools: {bool(tools)}, History: {history_len_debug} msgs) --- ")
    else:
        print("[ERROR] Invalid prompt_details structure for call_claude_api.")
        return None

    try:
        # Conditionally construct API call arguments
        api_args = {
            "model": anthropic_model_name,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": messages, # Use the constructed or provided messages list
        }
        if tools:
            api_args["tools"] = tools # Only add tools parameter if tools were provided

        response = claude_client.messages.create(**api_args)

        print("[DEBUG] Claude API call initiated (might result in tool use).")
        return response

    except anthropic.APIConnectionError as e:
        print(f"[ERROR] Anthropic API connection error: {e}")
    except anthropic.RateLimitError as e:
        print(f"[ERROR] Anthropic rate limit exceeded: {e}")
    except anthropic.APIStatusError as e:
        print(f"[ERROR] Anthropic API status error: {e.status_code} - {e.response}")
        # Also print response body if available and useful
        try: 
            print(f"[ERROR] Response Body: {e.response.text}")
        except Exception: pass
    except Exception as e:
        print(f"[ERROR] Unexpected error calling Claude API: {e}")

    return None

def call_gemini_api(prompt: str) -> str:
    """Calls the Gemini API to generate descriptive placeholders.

    Uses the initialized gemini_client.
    Includes basic error handling.
    """
    if not gemini_client:
        print("[ERROR] Gemini client not initialized. Cannot call Gemini API.")
        # Return a default placeholder or error string
        return "[ Gemini API call skipped - client not initialized ]"

    print(f"--- Calling Gemini ({google_model_name}) --- ")
    print(f"[DEBUG] Gemini prompt length: {len(prompt)} chars.")

    try:
        # Safety settings can be configured here if needed
        # generation_config = genai.types.GenerationConfig(temperature=0.7)
        response = gemini_client.generate_content(prompt)
        # Check for response safety/finish reason if needed (response.prompt_feedback)
        if response.text:
            print("[DEBUG] Gemini API call successful.")
            return response.text
        else:
            # Handle cases where generation might be blocked or empty
            print(f"[WARNING] Gemini response finished but contains no text. Finish reason: {response.candidates[0].finish_reason}")
            # Check safety ratings: response.candidates[0].safety_ratings
            return "[ Gemini generated no text - possibly blocked? ]"

    except Exception as e:
        # Catching general exceptions for now - specific API errors can be added
        # e.g., google.api_core.exceptions.GoogleAPIError
        print(f"[ERROR] Unexpected error calling Gemini API: {e}")
        return f"[ ERROR calling Gemini: {e} ]"

# NEW: Function to handle Claude's response, including tool use
def handle_claude_response(initial_response: anthropic.types.Message | None,
                           prompt_details: dict, # Contains system_prompt, user_prompt, history/messages
                           game_state: dict
                           ) -> tuple[str, anthropic.types.Message | None, list | None, anthropic.types.Message | None, bool]:
    """Handles the response from Claude, including potential tool use.

    If a state update tool is used, it applies the updates and makes a second call
    to get the final narrative. If dialogue tools are used, it updates state
    and returns immediately with appropriate text.

    Args:
        initial_response: The Message object from the first call_claude_api.
        prompt_details: Dict containing the original prompt components used.
        game_state: The current game state dictionary (will be modified by tool use).

    Returns:
        A tuple containing:
        - processed_text: The final narrative/dialogue string for display.
        - initial_response_obj: The original response object received from the API (contains tool_use if applicable).
        - tool_results_content_sent: The list sent back in the user-role message for tool results (only for update_game_state).
        - final_response_obj: The Message object from the second call (if made), else None.
        - stop_processing_flag: Boolean indicating if a dialogue tool stopped processing.
    """
    # Initialize return values
    processed_text = ""
    initial_response_obj = initial_response # Always return the first response
    tool_results_content_sent = None
    final_response_obj_after_tool = None # Specific name for clarity
    stop_processing_flag = False

    if not initial_response:
        processed_text = "[ERROR] Received no response object from Claude API call."
        return processed_text, initial_response_obj, tool_results_content_sent, final_response_obj_after_tool, stop_processing_flag

    # --- Extract any text generated *before* potential tool use --- #
    if initial_response.content:
        for block in initial_response.content:
            if block.type == "text":
                processed_text += block.text + "\n"
    processed_text = processed_text.strip()
    # ------------------------------------------------------------- #

    # Check for tool use stop reason
    if initial_response.stop_reason == "tool_use":
        print("\n[INFO] Claude requested tool use.")
        tool_calls_found = False
        tool_results_content_list = [] # Renamed for clarity

        # Iterate through content blocks to find tool requests
        for block in initial_response.content:
            if block.type != "tool_use": continue

            tool_calls_found = True
            tool_name = block.name
            tool_input = block.input
            tool_use_id = block.id
            print(f"[INFO] Handling tool use ID: {tool_use_id}, Name: {tool_name}")

            # --- Process Specific Tools --- #
            if tool_name == "update_game_state":
                # ... (logic for applying update_game_state as before) ...
                # --- Start of update_game_state logic ---
                update_error = None
                try:
                    updates_applied, state_change_summary = apply_tool_updates(tool_input, game_state)
                    if updates_applied:
                        tool_result_text = f"Game state updated successfully: {state_change_summary}"
                    else:
                        tool_result_text = "State update requested, but no changes were applicable."
                    # tool_used_and_processed = True # Not strictly needed anymore
                    # make_second_call = True
                except Exception as e:
                    print(f"[ERROR] Failed to apply tool updates for {tool_use_id}: {e}")
                    update_error = e
                    tool_result_text = f"Error applying game state update: {e}"

                # Prepare result for the second call (if making one)
                tool_results_content_list.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_result_text,
                    # Optional: "is_error": bool(update_error)
                })
                # --- End of update_game_state logic ---

            elif tool_name == "start_dialogue":
                # ... (logic for applying start_dialogue as before) ...
                # --- Start of start_dialogue logic ---
                character_id = tool_input.get('character_id')
                if character_id and character_id in game_state.get('companions', {}):
                    if game_state['companions'][character_id].get('present', False):
                        if not game_state['dialogue_active']:
                            game_state['dialogue_active'] = True
                            game_state['dialogue_partner'] = character_id
                            partner_name = game_state['companions'][character_id].get('name', character_id)
                            print(f"[INFO] Tool initiated dialogue with {partner_name} ({character_id}).")
                            processed_text += f"\n(You begin a conversation with {partner_name}.)"
                            stop_processing_flag = True
                        else:
                            print(f"[WARN] Tool requested start_dialogue, but dialogue is already active with {game_state['dialogue_partner']}.")
                            processed_text += f"\n(You are already talking to {game_state['companions'].get(game_state['dialogue_partner'],{}).get('name','someone')}.)"
                            stop_processing_flag = True
                    else:
                        print(f"[WARN] Tool requested start_dialogue with {character_id}, but they are not present.")
                        processed_text += f"\n({game_state['companions'][character_id].get('name', character_id)} is not here to talk to.)"
                        stop_processing_flag = True
                else:
                    print(f"[WARN] Tool requested start_dialogue with invalid/unknown character ID: {character_id}")
                    processed_text += f"\n(You look around, but don't see anyone named '{character_id}' to talk to.)"
                    stop_processing_flag = True
                # --- End of start_dialogue logic ---

            elif tool_name == "end_dialogue":
                # ... (logic for applying end_dialogue as before) ...
                 # --- Start of end_dialogue logic ---
                if game_state['dialogue_active']:
                    partner_id = game_state.get('dialogue_partner')
                    partner_name = game_state.get('companions', {}).get(partner_id, {}).get('name', 'Someone')
                    print(f"[INFO] Tool ended dialogue with {partner_name}.")

                    if partner_id and partner_id in game_state.get('companions', {}):
                        # ... (summarization logic) ...
                        partner_memory = game_state['companions'][partner_id].get('memory', {})
                        dialogue_history_to_summarize = partner_memory.get('dialogue_history', [])
                        if dialogue_history_to_summarize:
                            summary = summarize_conversation(dialogue_history_to_summarize)
                            current_summary = game_state.get('narrative_context_summary', '')
                            game_state['narrative_context_summary'] = current_summary + f"\n\n[Summary of conversation with {partner_name}: {summary}]"
                            print(f"[DEBUG] Appended summary to narrative context.")

                    game_state['dialogue_active'] = False
                    game_state['dialogue_partner'] = None
                    processed_text += f"\n(The conversation with {partner_name} ends.)"
                    stop_processing_flag = True
                else:
                    print("[WARN] Tool requested end_dialogue, but dialogue was not active.")
                    processed_text += "\n(There was no conversation to end.)"
                    stop_processing_flag = True
                 # --- End of end_dialogue logic ---

            else: # Unknown tool requested
                print(f"[WARNING] Claude requested unknown tool: {tool_name}")
                processed_text += f"\n[Internal Note: Claude requested unknown tool '{tool_name}'.]"
                stop_processing_flag = True

            # If a dialogue tool told us to stop, break from processing further tool calls
            if stop_processing_flag:
                break
        # --- End Tool Processing Loop --- #

        # If a stop was requested (dialogue tool used), return immediately
        if stop_processing_flag:
            # Return current text, original response, no tool result, no final response, True flag
            return processed_text.strip(), initial_response_obj, None, None, True

        # If we processed 'update_game_state' (check if tool_results_content_list is populated)
        if tool_results_content_list: # This implies update_game_state was the tool processed
            tool_results_content_sent = tool_results_content_list # Assign for return value
            print("[INFO] Sending tool results back to Claude for final narrative...")
            # --- Construct messages for the second call --- 
            # Determine message construction method based on keys in prompt_details
            if 'messages' in prompt_details and 'system' in prompt_details:
                 # Dialogue call structure (shouldn't happen here, but for safety)
                 system_prompt = prompt_details.get('system', '')
                 original_messages_sent = prompt_details.get('messages', [])
            elif 'history' in prompt_details and 'user_prompt' in prompt_details:
                 # Narrative call structure
                 system_prompt = prompt_details.get('system_prompt', '')
                 user_prompt = prompt_details.get('user_prompt', '')
                 history = prompt_details.get('history', [])
                 original_messages_sent = history + [{"role": "user", "content": user_prompt}]
            else:
                 print("[ERROR] Invalid prompt_details for second call construction.")
                 original_messages_sent = []
                 system_prompt = ""
            
            # Construct assistant message from the *initial* response
            assistant_turn_content = []
            if initial_response.content:
                 assistant_turn_content = [block.model_dump(exclude_unset=True) for block in initial_response.content]
            assistant_turn_message = {"role": initial_response.role, "content": assistant_turn_content}

            messages_for_second_call = original_messages_sent + \
                                       [assistant_turn_message] + \
                                       [{ "role": "user", "content": tool_results_content_sent }]
            
            # Make the second API call WITHOUT tools parameter
            second_response = None
            if claude_client and anthropic_model_name:
                try:
                    # Re-use call_claude_api for consistency?
                    # Need to adapt prompt_details for the second call
                    second_call_prompt_details = {
                        "system": system_prompt, # Use system/messages structure
                        "messages": messages_for_second_call
                    }
                    second_response = call_claude_api(second_call_prompt_details, tools=None)
                    final_response_obj_after_tool = second_response # Assign to correct return var
                    print("[DEBUG] Second Claude call successful.")
                except Exception as e:
                     print(f"[ERROR] Error in second Claude call after tool use: {e}")
                     processed_text += f"\n[ERROR] Failed to get final narrative after tool use: {e}"
            else:
                processed_text += "\n[ERROR] Claude client not available for second call after tool use."
        
        elif tool_calls_found: # Tool use stop reason, but no recognized tool *successfully processed* for a second call
             print(f"[WARNING] Tool use stop reason, but no tool requiring a second call ({update_game_state_tool['name']}) was processed.")
             # This path might be hit if only start/end dialogue were called but stop_processing wasn't set somehow? Or unknown tool.
             processed_text += f"\n[Internal Note: Claude attempted an action that wasn't fully processed.]"

    # --- Extract final narrative text (if second call was made) --- 
    # This text comes *only* from the second response object
    if final_response_obj_after_tool and final_response_obj_after_tool.content:
        final_narrative_pieces = []
        for block in final_response_obj_after_tool.content:
            if block.type == 'text':
                final_narrative_pieces.append(block.text)
        # Overwrite processed_text with only the result from the second call
        processed_text = "\n".join(final_narrative_pieces).strip()
        
    # --- Final checks if no text was generated --- 
    # Check if processed_text is still empty after all steps
    if not processed_text.strip():
        if initial_response.stop_reason != "tool_use": # If it wasn't tool use, it should have generated text
            print(f"[WARNING] No narrative text found in non-tool-use Claude response. Stop Reason: {initial_response.stop_reason}. Content: {initial_response.content}")
            processed_text = f"[Internal Note: Claude responded but provided no narrative text. Stop Reason: {initial_response.stop_reason}]"
        elif not final_response_obj_after_tool: # Tool use occurred, but second call failed or wasn't made, and no pre-tool text existed
             processed_text = "[Internal Note: Action processed, but no final narrative generated.]" # Default message

    # Return all components
    return processed_text.strip(), initial_response_obj, tool_results_content_sent, final_response_obj_after_tool, stop_processing_flag

# --- Prompt Construction ---

def construct_claude_prompt(current_state: dict, conversation_history: list) -> dict:
    """Constructs the Claude prompt components, including history.

    Args:
        current_state: The current game state dictionary.
        conversation_history: List of previous message dicts [{'role': ..., 'content': ...}].

    Returns a dictionary containing system prompt, user turn prompt,
    and conversation history.
    """
    system_prompt = PROMPT_TEMPLATES.get("claude_system", "Error: System prompt missing.")
    turn_template = PROMPT_TEMPLATES.get("claude_turn_template", "Error: Turn template missing.")

    # Prepare context dictionary for formatting the turn template
    present_companions = {comp_id: comp for comp_id, comp in current_state.get('companions', {}).items() if comp.get('present')}
    companion_names_present = ', '.join([comp['name'] for comp_id, comp in present_companions.items()]) or "None"
    companion_ids_present = ', '.join(present_companions.keys()) or "None"
    
    context = {
        'player_location': current_state.get('location', 'an unknown place'),
        'characters_present': ', '.join(current_state.get('current_npcs', []) or ["None"]),
        'companions_present': companion_names_present,
        'companion_ids_present': companion_ids_present, # Added for tool use
        'time_of_day': current_state.get('time_of_day', 'unknown'),
        'key_information': '; '.join([f"{k}: {v}" for k, v in current_state.get('narrative_flags', {}).items()] or ["None"]), 
        'recent_events_summary': current_state.get('narrative_context_summary', 'The story has just begun.'),
        'current_objective': current_state.get('current_objective', 'None stated.'), # Added
        'last_player_action': current_state.get('last_player_action', 'None')
    }

    user_turn_prompt = turn_template.format(**context)
    
    # Include the passed-in history
    history_to_include = conversation_history

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_turn_prompt,
        "history": history_to_include # Pass history back
    }

def construct_gemini_prompt(claude_output: str, current_state: dict) -> str:
    """Constructs the Gemini prompt using a template.

    Loads template from PROMPT_DIR and formats it.
    """
    template = PROMPT_TEMPLATES.get("gemini_placeholders", "Error: Gemini template missing.")

    context = {
        'narrative_text': claude_output,
        'player_location': current_state.get('location', 'an unknown place') # Correct key
        # Add other relevant state info if needed by the template
    }

    return template.format(**context)

# --- Output & Utility ---

def display_output(narrative_text: str, placeholder_text: str | None):
    """Displays the combined narrative and placeholders to the player."""
    print("\n" + "-"*40 + "\n")
    print(narrative_text.strip()) # Ensure no leading/trailing whitespace
    if placeholder_text:
        print("\n--- Visuals & Sounds ---")
        print(placeholder_text.strip())
        # print(f"You are in {current_state.get('location', 'an unknown place')}.") # Removed, redundant
    print("\n" + "-"*40)

def get_player_input() -> str:
    """Gets the player's command from the console."""
    player_input = input("\n> ").strip().lower()
    # Add basic parsing or validation if needed later
    return player_input

# --- Dialogue Handling ---
def format_dialogue_history_for_prompt(history: list) -> str:
    """Formats the dialogue history list into a string suitable for the prompt."""
    # Simple initial implementation: join speaker and utterance
    # TODO: Refine formatting (e.g., add newlines, handle long histories)
    formatted_lines = []
    for entry in history:
        speaker = entry.get("speaker", "Unknown").replace("_", " ").title() # Basic formatting
        utterance = entry.get("utterance", "...")
        formatted_lines.append(f"{speaker}: {utterance}")
    return "\n".join(formatted_lines)

def handle_dialogue_turn(game_state: dict, player_utterance: str) -> tuple[anthropic.types.Message | None, dict]:
    """Prepares and initiates the LLM call for a single dialogue turn.

    Adds player utterance to history, constructs prompt details, calls API
    with the end_dialogue tool enabled, and returns the raw response object
    and the prompt details used.
    Response processing (text extraction, tool handling, state changes, history update)
    is now done by handle_claude_response in the main loop.

    Args:
        game_state: The current game state dictionary.
        player_utterance: The raw input string from the player.

    Returns:
        A tuple containing:
        - The raw Anthropic Message object from the API call, or None on failure.
        - The prompt_details dictionary used for the API call.
    """
    partner_id = game_state.get('dialogue_partner')
    prompt_details_dialogue = {} # Initialize for return in case of early exit
    response_obj = None # Initialize response object

    if not partner_id or partner_id not in game_state['companions']:
        print("[ERROR] Dialogue active but no valid partner found in handle_dialogue_turn.")
        game_state['dialogue_active'] = False # End dialogue on error
        return None, prompt_details_dialogue

    print(f"[DEBUG] Preparing dialogue turn with partner: {partner_id}")
    companion_state = game_state['companions'][partner_id]
    memory = companion_state.setdefault('memory', {'dialogue_history': []})
    dialogue_history = memory.setdefault('dialogue_history', [])

    # 1. Add player utterance to history
    dialogue_history.append({"speaker": "player", "utterance": player_utterance})

    # 2. Prepare prompt details for LLM
    try:
        # --- Revised Prompt Construction --- #
        system_context = f"You are {companion_state.get('name', partner_id)}. Your relationship with the player is: {companion_state.get('relation_to_player_summary', 'Unknown')}. Location: {game_state.get('location', 'Unknown')}, Time: {game_state.get('time_of_day', 'Unknown')}. Respond naturally in character. ONLY provide dialogue, no narration or OOC text. You MUST use the end_dialogue tool IMMEDIATELY after any natural farewell utterance (e.g., 'Goodbye', 'Farewell', 'I must go now'). Do NOT use the tool otherwise." # Added stronger instruction for tool use

        messages_for_llm = []
        # Convert dialogue history to Claude message format
        for entry in dialogue_history:
            role = "user" if entry["speaker"] == "player" else "assistant"
            # Ensure content is always a list of blocks, even for simple text
            content_block = [{"type": "text", "text": entry["utterance"]}]
            messages_for_llm.append({
                "role": role,
                "content": content_block
            })

        # --- Prepare call --- #
        prompt_details_dialogue = {
            "system": system_context,
            "messages": messages_for_llm
        }

        print(f"\\n>>> Asking {companion_state.get('name', partner_id)} for response... (End dialogue tool available) <<<")
        # IMPORTANT: Pass ONLY the end_dialogue tool
        dialogue_tools = [end_dialogue_tool]
        response_obj = call_claude_api(prompt_details_dialogue, tools=dialogue_tools)

        # REMOVED: Response processing and history update logic - moved to handle_claude_response call in main loop

    except Exception as e:
        print(f"[ERROR] Exception during dialogue turn LLM call preparation or invocation: {e}")
        # Return None and empty details on error
        return None, {}

    # 5. Return the RAW response object and prompt details
    return response_obj, prompt_details_dialogue

def summarize_conversation(dialogue_history: list) -> str:
    """Summarizes a given dialogue history using an LLM.

    Args:
        dialogue_history: List of dialogue entries [{'speaker': ..., 'utterance': ...}].

    Returns:
        A concise summary string, or an empty string if summarization fails.
    """
    if not dialogue_history:
        return "" # Nothing to summarize

    print("\n>>> Summarizing conversation... <<<")
    try:
        summary_prompt_template = PROMPT_TEMPLATES.get("summarization")
        if not summary_prompt_template:
            print("[ERROR] Summarization prompt template not found.")
            return "(Conversation summary unavailable due to template error.)"
        
        # Format history for the prompt
        history_string = format_dialogue_history_for_prompt(dialogue_history) # Reuse helper
        
        prompt_text = summary_prompt_template.replace("{{dialogue_history}}", history_string)

        # TODO: Decide which LLM for summarization (Using Gemini here)
        if not gemini_client:
            print("[WARN] Gemini client not available for summarization.")
            return "(Conversation summary unavailable.)"

        # Use basic text generation with Gemini
        response = gemini_client.generate_content(
            prompt_text,
            # Add generation config if needed (e.g., temperature, max_output_tokens)
            # generation_config=genai.types.GenerationConfig(...) 
        )

        summary = response.text.strip()
        print(f"[DEBUG] Conversation summary generated: {summary}")
        return summary

    except Exception as e:
        print(f"[ERROR] Failed to summarize conversation: {e}")
        # traceback.print_exc() # Uncomment for detailed debugging
        return "(Conversation summary failed.)"

# --- Main Game Loop ---
def main():
    game_state = copy.deepcopy(INITIAL_GAME_STATE) # Use deepcopy to avoid modifying the original constant
    turn_count = 0
    conversation_history = [] # Initialize history list for narrative context

    print("Welcome to Endless Novel (v0 - Text Only)")
    # Initial Scene Description - Use Gemini?
    try:
        initial_gemini_prompt = construct_gemini_prompt("The adventure begins.", game_state)
        initial_placeholders = call_gemini_api(initial_gemini_prompt)
    except Exception as e:
        print(f"[WARN] Failed initial Gemini call: {e}")
        initial_placeholders = "[ Initial placeholders unavailable ]"
    display_output(game_state['narrative_context_summary'], initial_placeholders)

    while True:
        turn_count += 1
        print(f"\n--- Turn {turn_count} ---")

        # 1. Get Player Input
        player_input_raw = get_player_input()
        if player_input_raw.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break

        # ----------------------------------------
        # --- DIALOGUE VS NARRATIVE ROUTING --- #
        # ----------------------------------------
        if game_state['dialogue_active']:
            # --- Handle Dialogue Turn --- #
            print("[DEBUG] Dialogue active.")

            # 1. Call handler to prepare prompt, add player utterance to history, and call API
            dialogue_response_obj, dialogue_prompt_details = handle_dialogue_turn(game_state, player_input_raw)

            # 2. Process the raw response using handle_claude_response
            # Unpack all 5 return values now
            processed_text, initial_resp_obj_dlg, _, final_resp_obj_dlg, stop_processing_dlg = handle_claude_response(
                initial_response=dialogue_response_obj,
                prompt_details=dialogue_prompt_details,
                game_state=game_state
            )

            # 3. Update Character Dialogue History (if dialogue didn't just end - check stop_processing_dlg)
            if not stop_processing_dlg: # Only update history if end_dialogue wasn't called
                partner_id = game_state.get('dialogue_partner')
                # Use initial_resp_obj_dlg as it contains the assistant's utterance when no tool was used
                assistant_utterance = ""
                if initial_resp_obj_dlg and initial_resp_obj_dlg.content:
                     for block in initial_resp_obj_dlg.content:
                         if block.type == 'text':
                             assistant_utterance = block.text.strip()
                             break # Take first text block
                
                if partner_id and partner_id in game_state.get('companions', {}) and assistant_utterance:
                    print(f"[DEBUG MAIN] Updating dialogue history for {partner_id} with assistant utterance.")
                    memory = game_state['companions'][partner_id].setdefault('memory', {'dialogue_history': []})
                    dialogue_history = memory.setdefault('dialogue_history', [])
                    if not dialogue_history or dialogue_history[-1].get("speaker") != partner_id:
                         dialogue_history.append({"speaker": partner_id, "utterance": assistant_utterance})
                    else:
                         print(f"[DEBUG MAIN] Skipping dialogue history update for {partner_id} - might be duplicate.")
                elif partner_id and not assistant_utterance:
                     print(f"[DEBUG MAIN] No assistant utterance found in dialogue response for {partner_id}.")
            else:
                 print(f"[DEBUG MAIN] Dialogue stopped processing (likely ended), skipping character history update.")

            # 4. Set text for display
            narrative_text = processed_text
            placeholder_output = "[Visuals/Sounds suppressed during dialogue]"

        else:
            # --- Handle Narrative Turn --- #
            print("[DEBUG] Narrative turn. Proceeding with Claude/Gemini...")
            
            # --- Append User Message to History --- 
            # Do this *before* calling Claude for the current turn
            user_message = {"role": "user", "content": player_input_raw}
            conversation_history.append(user_message)
            # --- Truncate History (Optional but Recommended) ---
            MAX_HISTORY_MESSAGES = 20
            if len(conversation_history) > MAX_HISTORY_MESSAGES:
                print(f"[DEBUG] Truncating history from {len(conversation_history)} to {MAX_HISTORY_MESSAGES} messages.")
                conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
            # ----------------------------------------

            # 2. Update State with Player Action (for context)
            game_state['last_player_action'] = player_input_raw

            # 3. Construct Claude Prompt (using the potentially truncated history)
            prompt_details = construct_claude_prompt(game_state, conversation_history)

            # 4. Call Claude API & Handle Response (Tool Use)
            print("\n>>> Processing Player Action... Asking Claude for narrative... <<<")
            available_tools = [update_game_state_tool, start_dialogue_tool, end_dialogue_tool]
            # Call API - gets the initial response (might contain tool_use)
            initial_claude_response_obj = call_claude_api(prompt_details, tools=available_tools)
            
            # Process the response - unpack all 5 return values
            processed_text, initial_resp_obj_narr, tool_results_sent, final_resp_obj_narr, stop_processing_narr = handle_claude_response(
                initial_response=initial_claude_response_obj,
                prompt_details=prompt_details,
                game_state=game_state
            )
            
            # --- CORRECTED History Update Logic for Narrative --- 
            if initial_resp_obj_narr and initial_resp_obj_narr.stop_reason == "tool_use":
                print("[DEBUG MAIN] Tool used in narrative turn. Updating history sequence.")
                # 1. Append Assistant's message containing the tool_use request(s)
                assistant_tool_use_message = {
                    "role": initial_resp_obj_narr.role,
                    "content": [block.model_dump(exclude_unset=True) for block in initial_resp_obj_narr.content if block] 
                }
                conversation_history.append(assistant_tool_use_message)
                print(f"[DEBUG MAIN] Appended assistant tool_use message to history.")

                # 2. Append User's tool_result message(s) - MANDATORY for API compliance
                tool_results_for_history = []
                for block in initial_resp_obj_narr.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_use_id = block.id
                        # Determine result content based on tool (can be simple confirmations)
                        if tool_name == "start_dialogue":
                            result_content = "Dialogue started successfully."
                        elif tool_name == "end_dialogue":
                            result_content = "Dialogue ended successfully."
                        elif tool_name == "update_game_state":
                             # Find the corresponding result text we prepared earlier
                             # Note: tool_results_sent is the list prepared *for the API*, not a simple string
                             result_block_content = "State update processed."
                             if tool_results_sent: # Check if the list was populated
                                 for sent_result in tool_results_sent:
                                     if sent_result.get('tool_use_id') == tool_use_id:
                                         result_block_content = sent_result.get('content', result_block_content)
                                         break # Found the matching result
                             result_content = result_block_content
                        else:
                            result_content = f"Tool '{tool_name}' processed."
                        
                        tool_results_for_history.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result_content # API expects string content here
                        })
                
                if tool_results_for_history:
                    user_tool_result_message = {
                        "role": "user",
                        "content": tool_results_for_history # Send the list of result blocks
                    }
                    conversation_history.append(user_tool_result_message)
                    print(f"[DEBUG MAIN] Appended user tool_result message(s) to history: {json.dumps(tool_results_for_history)}")
                
                # 3. Append Assistant's final response AFTER tool use (if applicable - only for update_game_state)
                if final_resp_obj_narr:
                    assistant_final_message = {
                        "role": final_resp_obj_narr.role,
                        "content": [block.model_dump(exclude_unset=True) for block in final_resp_obj_narr.content if block]
                    }
                    conversation_history.append(assistant_final_message)
                    print(f"[DEBUG MAIN] Appended final assistant message after tool use to history.")
            
            elif initial_resp_obj_narr: # No tool use, just a normal assistant response
                print("[DEBUG MAIN] No tool use in narrative turn. Appending standard assistant message.")
                assistant_message = {
                    "role": initial_resp_obj_narr.role,
                    "content": [block.model_dump(exclude_unset=True) for block in initial_resp_obj_narr.content if block]
                }
                conversation_history.append(assistant_message)
            else:
                # Handle case where initial call failed
                print("[WARN MAIN] No valid initial response object from Claude to add to history.")
            # ------------------------------------------------------

            # --- Error Handling & Gemini Call --- 
            # Check for errors in the *final* processed text
            if processed_text.startswith("[ERROR]") or processed_text.startswith("[Internal"):
                print(f"\n[SYSTEM MESSAGE]\n{processed_text}")
                display_output("(The world seems to pause, recovering from an unseen ripple...)", None)
                game_state['last_player_action'] = "None"
                continue 

            # 5. Construct & Call Gemini (only if dialogue didn't start/end)
            if not stop_processing_narr: # Check the flag from handle_claude_response
                 print("\n>>> Asking Gemini for scene details... <<<")
                 gemini_prompt = construct_gemini_prompt(processed_text, game_state)
                 placeholder_output = call_gemini_api(gemini_prompt)
            else:
                 print("[DEBUG MAIN] stop_processing flag is True, skipping Gemini call.")
                 placeholder_output = "[Placeholders suppressed due to dialogue transition]"
            # ----------------------------------------
        
        # --- END ROUTING --- #

        # 6. Display Combined Output (using processed_text from either branch)
        display_output(processed_text, placeholder_output)

        # Simple loop condition for now
        if turn_count >= MAX_TURNS:
            print(f"\nReached turn limit ({MAX_TURNS}).")
            break

    print("\nThank you for playing Endless Novel V0!")

# ... (rest of file) ...

if __name__ == "__main__":
    main() 