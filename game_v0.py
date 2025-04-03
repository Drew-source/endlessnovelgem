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
# See `docs/intent_v0.md` Section 4 for details
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
            'relations_to_others': {}
        },
        # Add more companions here as needed
    },

    # Narrative / Quest Progression
    'narrative_flags': {},
    'current_chapter': 1,
    'current_objective': None,

    # Interaction / LLM Context
    'dialogue_target': None, # Name (ID) of NPC or Companion in dialogue
    'last_player_action': None,
    'narrative_context_summary': "Sunlight filters through the ancient trees. The air is cool and smells of damp earth and pine. Your companion, Varnas, shifts his weight beside you."
}

# --- Tool Definition for Claude --- 
# This defines the structure Claude should use to request state changes.
update_game_state_tool = {
    "name": "update_game_state",
    "description": "Updates the explicit game state based on narrative events. Use this ONLY when the story requires a change to tracked variables like location, inventory, character presence/relationships, or narrative flags.",
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
            "dialogue_target": {"type": ["string", "null"], "description": "Set the current dialogue target (companion/NPC ID) or null to clear the focus."}, # Allow null
            "current_objective": {"type": ["string", "null"], "description": "Set the player's current main objective text or null to clear."} # Allow null
        },
        "additionalProperties": False # Disallow unexpected top-level update keys
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
    "gemini_placeholders": load_prompt_template("gemini_placeholder_template.txt")
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

    # Dialogue Target
    if "dialogue_target" in tool_input and game_state.get('dialogue_target') != tool_input['dialogue_target']:
        game_state['dialogue_target'] = tool_input['dialogue_target'] # Can be None
        change_str = f"Dialogue Target -> {game_state['dialogue_target']}"
        print(f"  [State Update] {change_str}")
        state_changed_summary.append(change_str)
        updates_applied = True

    # Current Objective
    if "current_objective" in tool_input and game_state.get('current_objective') != tool_input['current_objective']:
        game_state['current_objective'] = tool_input['current_objective'] # Can be None
        change_str = f"Current Objective -> {game_state['current_objective']}"
        print(f"  [State Update] {change_str}")
        state_changed_summary.append(change_str)
        updates_applied = True

    if not updates_applied:
        print("  [State Info] Tool input received, but no actual state changes applied.")

    # Optionally, update a summary field for logging/display?
    if state_changed_summary:
         game_state['last_tool_update_summary'] = " | ".join(state_changed_summary)

# --- Core API Call Functions ---

def call_claude_api(prompt_details: dict) -> anthropic.types.Message | None:
    """Calls the Claude 3.7 Sonnet API using the Messages endpoint.

    Handles system prompt, user message, and includes the `update_game_state` tool.
    Now returns the raw Message object for the caller to handle.

    Args:
        prompt_details: A dictionary containing pre-formatted prompt components:
                        {'system_prompt': str, 'user_prompt': str, 'history': list}

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

    system_prompt = prompt_details.get('system_prompt', "")
    user_prompt = prompt_details.get('user_prompt', "")
    history = prompt_details.get('history', []) # Get history from details

    # Construct messages: History first, then the current user prompt
    # TODO: Add history truncation logic here if it gets too long
    MAX_HISTORY_TURNS = 10 # Example limit (5 user, 5 assistant)
    truncated_history = history[-(MAX_HISTORY_TURNS*2):] if len(history) > (MAX_HISTORY_TURNS*2) else history
    
    messages = truncated_history + [
        {"role": "user", "content": user_prompt}
    ]

    print(f"--- Calling Claude ({anthropic_model_name}) with Tool & History ({len(truncated_history)} msgs) --- ")

    try:
        response = claude_client.messages.create(
            model=anthropic_model_name,
            max_tokens=2048,
            system=system_prompt,
            messages=messages, # Use the list including history
            tools=[update_game_state_tool],
        )

        print("[DEBUG] Claude API call initiated (might result in tool use).")
        return response

    except anthropic.APIConnectionError as e:
        print(f"[ERROR] Anthropic API connection error: {e}")
    except anthropic.RateLimitError as e:
        print(f"[ERROR] Anthropic rate limit exceeded: {e}")
    except anthropic.APIStatusError as e:
        print(f"[ERROR] Anthropic API status error: {e.status_code} - {e.response}")
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
                           prompt_details: dict, # Contains system_prompt, user_prompt, history
                           game_state: dict) -> tuple[str, anthropic.types.Message | None]: # Returns text AND final Message obj
    """Handles the response from Claude, including potential tool use.

    If a tool is used, it applies the updates and makes a second call
    to get the final narrative based on the tool result.

    Args:
        initial_response: The Message object from the first call_claude_api.
        prompt_details: Dict containing the original prompt components used.
        game_state: The current game state dictionary (will be modified by tool use).

    Returns:
        A tuple containing:
        - The final narrative string, or an error message string.
        - The final Anthropic Message object (from the first or second call), or None.
    """
    if not initial_response:
        return "[ERROR] Received no response object from Claude API call.", None

    narrative_text = ""
    final_response_obj = initial_response # Start assuming the first response is final
    tool_used_and_processed = False

    # Check for tool use stop reason
    if initial_response.stop_reason == "tool_use":
        print("\n[INFO] Claude requested tool use.")
        tool_calls_found = False
        tool_results_content = [] # Content block(s) for the next user message

        # Iterate through content blocks to find tool requests
        for block in initial_response.content:
            if block.type == "tool_use" and block.name == "update_game_state":
                tool_calls_found = True
                tool_input = block.input
                tool_use_id = block.id
                print(f"[INFO] Handling tool use ID: {tool_use_id}")

                # --- Apply the updates to game_state --- 
                update_error = None
                try:
                    apply_tool_updates(tool_input, game_state) # Modifies game_state in-place
                    tool_result_text = "Game state updated successfully based on narrative events."
                    tool_used_and_processed = True # Mark success
                except Exception as e:
                    print(f"[ERROR] Failed to apply tool updates for {tool_use_id}: {e}")
                    update_error = e
                    tool_result_text = f"Error applying game state update: {e}"
                    # Decide if we should still proceed or halt?
                    # For now, report error back to Claude but continue.

                # Prepare the result content block for the next call
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_result_text,
                    # Optional: "is_error": bool(update_error)
                })
            elif block.type == "text":
                 # Capture any text Claude generated *before* the tool use block
                 # This might be context like "Okay, I will update the state..."
                 narrative_text += block.text + "\n"

        # If we found and processed tool calls, make the second API call
        if tool_used_and_processed:
            print("[INFO] Sending tool results back to Claude for final narrative...")
            # --- Construct messages for the second call --- 
            system_prompt = prompt_details.get('system_prompt', '')
            user_prompt = prompt_details.get('user_prompt', '')
            history = prompt_details.get('history', [])

            # Reconstruct the message list that *led* to the tool request
            original_messages_sent = history + [{"role": "user", "content": user_prompt}]

            # --- CORRECTED: Construct assistant message carefully --- 
            # Only include role and content from the first response
            assistant_turn_content = []
            if initial_response.content:
                 # Convert content blocks back to dictionaries for the API call
                 assistant_turn_content = [block.model_dump(exclude_unset=True) for block in initial_response.content]
                 
            assistant_turn_message = {
                "role": initial_response.role, # Should be 'assistant'
                "content": assistant_turn_content
            }
            # ------------------------------------------------------

            # Add the assistant's turn (containing the tool request) and the user's tool result turn
            messages_for_second_call = original_messages_sent + \
                                       [assistant_turn_message] + \
                                       [{
                                           "role": "user",
                                           "content": tool_results_content
                                       }]

            # Make the second API call WITHOUT tools parameter
            second_response = None
            if claude_client and anthropic_model_name:
                try:
                    second_response = claude_client.messages.create(
                        model=anthropic_model_name,
                        max_tokens=2048,
                        system=system_prompt,
                        messages=messages_for_second_call
                        # NO 'tools' parameter here!
                    )
                    final_response_obj = second_response # Use this as the final response now
                    print("[DEBUG] Second Claude call successful.")
                except Exception as e:
                     print(f"[ERROR] Error in second Claude call after tool use: {e}")
                     # Append error to any narrative collected so far
                     narrative_text += f"\n[ERROR] Failed to get final narrative after tool use: {e}"
                     # We don't return here, let the text extraction handle the partial narrative
            else:
                narrative_text += "\n[ERROR] Claude client not available for second call after tool use."
                final_response_obj = None # No valid final response
        elif tool_calls_found: # Found tool use block, but failed to process/apply?
             print("[WARNING] Found tool use block(s) but failed to process them successfully. No second call made.")
             narrative_text += "\n[Internal Error: Failed to process requested state update.]"
        else: # stop_reason was tool_use, but didn't find OUR tool?
             print(f"[WARNING] Tool use stop reason, but no '{update_game_state_tool['name']}' tool call found in content: {initial_response.content}")
             narrative_text += f"\n[Internal Note: Claude requested an unknown tool or failed to structure the request.]"

    # --- Extract final narrative text --- 
    # This runs on 'final_response_obj', which is either the first response
    # (if no tool use) or the second response (after successful tool use).
    if final_response_obj and final_response_obj.content:
        # Collect text from all text blocks in the final response
        final_narrative_pieces = []
        for block in final_response_obj.content:
            if block.type == 'text':
                final_narrative_pieces.append(block.text)
        
        # Combine any narrative collected *before* tool use (if any) with final narrative
        full_narrative = narrative_text + "\n".join(final_narrative_pieces)
        narrative_text = full_narrative.strip()

        if not narrative_text:
             # Handle cases where the final response is empty or non-text
             print(f"[WARNING] No narrative text found in final Claude response. Stop Reason: {final_response_obj.stop_reason}. Content: {final_response_obj.content}")
             narrative_text = f"[Internal Note: Claude responded but provided no narrative text. Stop Reason: {final_response_obj.stop_reason}]"
    elif not narrative_text: # If no text was ever collected (e.g., initial API call failed badly)
        narrative_text = "[ERROR] Failed to get valid final narrative content from Claude."
        final_response_obj = None # Ensure obj is None if text extraction failed

    # If tool was used, add a note about the state change summary for debugging/display
    if tool_used_and_processed and game_state.get('last_tool_update_summary'):
        narrative_text += f"\n\n[DEBUG STATE CHANGE: {game_state.pop('last_tool_update_summary', '')}]"

    return narrative_text, final_response_obj # Return text AND the final object

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
    turn_template = PROMPT_TEMPLATES.get("claude_turn_template", "Error: Turn template missing.") # Corrected filename

    # Prepare context dictionary for formatting the turn template
    # Handle potential missing keys gracefully
    # TODO: Include companion info correctly
    context = {
        'player_location': current_state.get('location', 'an unknown place'),
        'characters_present': ', '.join(current_state.get('current_npcs', []) or ["None"]), 
        'companions_present': ', '.join([comp['name'] for comp_id, comp in current_state.get('companions', {}).items() if comp.get('present')]) or "None",
        'time_of_day': current_state.get('time_of_day', 'unknown'),
        'key_information': '; '.join([f"{k}: {v}" for k, v in current_state.get('narrative_flags', {}).items()] or ["None"]), 
        'recent_events_summary': current_state.get('narrative_context_summary', 'The story has just begun.'), # Might remove this if history is good?
        'dialogue_target': str(current_state.get('dialogue_target', 'No active conversation.')),
        'last_player_action': current_state.get('last_player_action', 'None')
    }

    user_turn_prompt = turn_template.format(**context)
    
    # Include the passed-in history
    # Limit history length? (Maybe better done in call_claude_api)
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

# --- Main Game Loop ---
def main():
    game_state = INITIAL_GAME_STATE # Now this name will be defined
    turn_count = 0
    conversation_history = [] # Initialize history list

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

        # --- Append User Message to History --- 
        user_message = {"role": "user", "content": player_input_raw}
        conversation_history.append(user_message)
        # --- Truncate History (Optional but Recommended) ---
        # Keep roughly the last N turns (2*N messages)
        MAX_HISTORY_MESSAGES = 20 # Example: Keep last 10 turns
        if len(conversation_history) > MAX_HISTORY_MESSAGES:
            print(f"[DEBUG] Truncating history from {len(conversation_history)} to {MAX_HISTORY_MESSAGES} messages.")
            conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
        # ----------------------------------------

        # 2. Update State with Player Action (for context in THIS turn's prompt)
        game_state['last_player_action'] = player_input_raw

        # 3. Construct Claude Prompt (now passing history)
        prompt_details = construct_claude_prompt(game_state, conversation_history)

        # 4. Call Claude API & Handle Response (Tool Use)
        print("\n>>> Processing Player Action... Asking Claude for narrative... <<<")
        claude_response_obj = call_claude_api(prompt_details)
        narrative_text, final_response_obj = handle_claude_response(
            initial_response=claude_response_obj,
            prompt_details=prompt_details,
            game_state=game_state
        )
        
        # --- Append Assistant Message to History --- 
        if final_response_obj:
            # Reconstruct the message dict {role, content} for history storage
            assistant_content_for_history = []
            if final_response_obj.content:
                assistant_content_for_history = [block.model_dump(exclude_unset=True) for block in final_response_obj.content]
            
            assistant_message = {
                "role": final_response_obj.role,
                "content": assistant_content_for_history
            }
            conversation_history.append(assistant_message)
        else:
            # Handle case where response failed; maybe add placeholder?
            print("[WARN] No valid final response object from Claude to add to history.")
            # Optionally add a placeholder error message to history?
        # ----------------------------------------

        # --- Error Handling for Narrative --- 
        if narrative_text.startswith("[ERROR]") or narrative_text.startswith("[Internal"):
            print(f"\n[SYSTEM MESSAGE]\n{narrative_text}")
            display_output("(The world seems to pause, recovering from an unseen ripple...)", None)
            game_state['last_player_action'] = "None" # Clear action even on error
            continue # Skip Gemini call and proceed to next turn

        # 5. Construct & Call Gemini for Placeholders
        print("\n>>> Asking Gemini for scene details... <<<")
        gemini_prompt = construct_gemini_prompt(narrative_text, game_state)
        placeholder_output = call_gemini_api(gemini_prompt)

        # 6. Display Combined Output
        display_output(narrative_text, placeholder_output)

        # Clear last action for the next turn (still useful for prompt context)
        # game_state['last_player_action'] = "None"

        # Simple loop condition for now
        if turn_count >= MAX_TURNS:
            print(f"\nReached turn limit ({MAX_TURNS}).")
            break

    print("\nThank you for playing Endless Novel V0!")

# ... (rest of file) ...

if __name__ == "__main__":
    main() 