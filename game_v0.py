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

# --- Constants & Configuration ---
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

# Similarly initialize Google client later...
google_api_key = os.getenv("GOOGLE_API_KEY")
google_model_name = os.getenv("GOOGLE_MODEL_NAME")
gemini_client = None
if google_api_key:
    try:
        # Ensure the correct import is used if needed: from google import genai
        genai.configure(api_key=google_api_key) # Using configure method for now
        # Or initialize using client = genai.Client(api_key=google_api_key)
        gemini_client = genai.GenerativeModel(google_model_name) # Matching configure method
        print("[INFO] Google AI client initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Google AI client: {e}")
else:
    print("[ERROR] GOOGLE_API_KEY not found. Gemini API calls will fail.")

# --- Game State (Final V0 Structure) ---
# See `docs/intent_v0.md` Section 4 for details
game_state = {
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

# --- Core Functions ---

def get_player_input() -> str:
    """Gets the player's command from the console."""
    player_input = input("\n> ").strip().lower()
    # Add basic parsing or validation if needed later
    return player_input

def update_game_state(player_input: str, current_state: dict):
    """Stores the raw player input for the current turn.

    In the V0 LLM-centric design, all other state updates are handled
    by parsing structured data from the Claude API response.
    """
    # Only store the last action. Claude interprets it.
    current_state['last_player_action'] = player_input
    print(f"[DEBUG] Stored player action: {player_input}")
    # The game state dictionary is modified in-place.

def call_claude_api(prompt_details: dict) -> dict | None:
    """Calls the Claude 3.7 Sonnet API using the Messages endpoint.

    Handles basic API call, system prompt, and user message.
    Tool definition and handling will be added.

    Args:
        prompt_details: A dictionary containing pre-formatted prompt components:
                        {'system_prompt': str, 'user_prompt': str, 'history': list}

    Returns:
        A dictionary containing the API response structure or None on failure.
        Structure TBD based on tool use, but will include narrative/tool calls.
    """
    if not claude_client:
        print("[ERROR] Anthropic client not initialized. Cannot call Claude API.")
        return None
    if not anthropic_model_name:
        print("[ERROR] Anthropic model name not configured.")
        return None

    system_prompt = prompt_details.get('system_prompt', "")
    user_prompt = prompt_details.get('user_prompt', "") # This is the formatted turn prompt
    # TODO: Integrate conversation history management
    messages = [
        {"role": "user", "content": user_prompt} 
    ]

    print(f"--- Calling Claude ({anthropic_model_name}) --- ")
    # print(f"System Prompt: {system_prompt[:100]}..." if system_prompt else "None") # Optional debug
    # print(f"User Prompt: {user_prompt[:200]}...") # Optional debug

    try:
        response = claude_client.messages.create(
            model=anthropic_model_name,
            max_tokens=2048,  # Adjust as needed, maybe make configurable
            system=system_prompt,
            messages=messages,
            # TODO: Add 'tools' parameter with update_game_state tool definition
            # TODO: Add 'tool_choice' parameter if needed
        )
        
        # Return the raw response object for now - parsing happens later
        # We need the full object to check stop_reason, content types etc.
        print("[DEBUG] Claude API call successful.")
        return response # Return the actual Anthropic response object

    except anthropic.APIConnectionError as e:
        print(f"[ERROR] Anthropic API connection error: {e}")
    except anthropic.RateLimitError as e:
        print(f"[ERROR] Anthropic rate limit exceeded: {e}")
    except anthropic.APIStatusError as e:
        print(f"[ERROR] Anthropic API status error: {e.status_code} - {e.response}")
    except Exception as e:
        print(f"[ERROR] Unexpected error calling Claude API: {e}")

    return None # Indicate failure

def call_gemini_api(prompt: str) -> str:
    """Calls the Gemini API to generate descriptive placeholders.

    Placeholder: Implement actual API call using the Google AI client.
    Needs error handling.
    See `docs/intent_v0.md` Section 3.
    """
    print("--- Calling Gemini (Placeholder) ---")
    print(f"Prompt:\n{prompt}")
    # response = gemini_model.generate_content(...)
    # return response.text
    time.sleep(0.5) # Simulate API latency
    # --- Replace with actual API call and response handling ---
    placeholder_description = "IMAGE: [A detailed close-up of an angry squirrel, fur bristling, perched on a mossy oak branch. Morning light dapples the scene.]\nSOUND: [Angry squirrel chattering sounds]"
    return placeholder_description

def construct_claude_prompt(current_state: dict) -> dict:
    """Constructs the Claude prompt components.

    Returns a dictionary containing system prompt, user turn prompt,
    and potentially conversation history (TODO).
    """
    system_prompt = PROMPT_TEMPLATES.get("claude_system", "Error: System prompt missing.")
    turn_template = PROMPT_TEMPLATES.get("claude_turn", "Error: Turn template missing.")

    # Prepare context dictionary for formatting the template
    # Handle potential missing keys gracefully
    # TODO: Include companion info correctly
    context = {
        'player_location': current_state.get('location', 'an unknown place'),
        'characters_present': ', '.join(current_state.get('current_npcs', []) or ["None"]), 
        'companions_present': ', '.join([comp['name'] for comp_id, comp in current_state.get('companions', {}).items() if comp.get('present')]) or "None",
        'time_of_day': current_state.get('time_of_day', 'unknown'),
        'key_information': '; '.join([f"{k}: {v}" for k, v in current_state.get('narrative_flags', {}).items()] or ["None"]), # Format flags
        'recent_events_summary': current_state.get('narrative_context_summary', 'The story has just begun.'),
        'dialogue_target': str(current_state.get('dialogue_target', 'No active conversation.')),
        'last_player_action': current_state.get('last_player_action', 'None')
    }

    user_turn_prompt = turn_template.format(**context)
    
    # TODO: Implement history management
    history = [] 

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_turn_prompt,
        "history": history
    }

def construct_gemini_prompt(claude_output: str, current_state: dict) -> str:
    """Constructs the Gemini prompt using a template.

    Loads template from PROMPT_DIR and formats it.
    """
    template = PROMPT_TEMPLATES.get("gemini_placeholders", "Error: Gemini template missing.")

    context = {
        'narrative_text': claude_output,
        'player_location': current_state.get('player_location', 'an unknown place')
        # Add other relevant state info if needed by the template
    }

    return template.format(**context)

def display_output(narrative: str, placeholders: str):
    """Displays the combined narrative and placeholders to the player."""
    print("\n" + "-"*40 + "\n")
    print(narrative)
    if placeholders:
        print("\n--- Placeholders ---")
        print(placeholders)
    print("\n" + "-"*40)

def parse_and_apply_state_updates(response_text: str, current_state: dict) -> tuple[str, str | None]:
    """Parses Claude's response for a <state_update> block and applies changes.

    Args:
        response_text: The full text response from the Claude API.
        current_state: The game state dictionary to modify.

    Returns:
        A tuple containing:
        - narrative_text: The response text excluding the state update block.
        - new_summary_suggestion: The suggested summary string, or None.
    """
    narrative_text = response_text
    new_summary_suggestion = None
    update_data = None

    # Regex to find the state update block
    match = re.search(r"<state_update>(.*?)</state_update>", response_text, re.DOTALL | re.IGNORECASE)

    if match:
        json_content = match.group(1).strip()
        # Remove the block from the narrative text
        narrative_text = response_text.replace(match.group(0), "").strip()

        try:
            update_data = json.loads(json_content)
            print(f"[DEBUG] Found state update data: {update_data}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to decode JSON from state update block: {e}")
            print(f"Invalid JSON content:\n{json_content}")
            # Continue without applying updates if JSON is invalid
            update_data = None

    if update_data and isinstance(update_data, dict):
        # --- Apply the updates --- 
        updates_to_apply = update_data.get("updates", {})
        if isinstance(updates_to_apply, dict):
            print(f"[DEBUG] Applying state updates: {updates_to_apply}")
            # Replace placeholder call with actual implementation
            _apply_updates_internal(updates_to_apply, current_state)
            # pass # Remove pass
        else:
            print(f"[ERROR] Invalid format for 'updates' key in state update JSON.")

        # --- Get optional summary suggestion --- 
        new_summary_suggestion = update_data.get("new_summary_suggestion")
        if new_summary_suggestion:
            print(f"[DEBUG] Found new summary suggestion: {new_summary_suggestion}")

    return narrative_text, new_summary_suggestion

# Implementation of the state update logic
def _apply_updates_internal(updates: dict, state: dict):
    """Applies updates to the state dictionary based on parsed instructions.

    Handles dot notation keys and specific operation suffixes.
    Modifies the 'state' dictionary in-place.
    Includes basic error checking.
    """
    for full_key, value in updates.items():
        try:
            operation = None
            key_path = full_key
            
            # Check for operation suffixes
            valid_ops = {'.add', '.remove', '.set', '.delete'}
            for op in valid_ops:
                if key_path.endswith(op):
                    operation = op
                    key_path = key_path[:-len(op)]
                    break

            # Navigate the state dictionary using dot notation
            parts = key_path.split('.')
            target_parent = state
            # Traverse path until the second-to-last element
            for i, part in enumerate(parts[:-1]):
                if isinstance(target_parent, dict):
                    if part not in target_parent:
                        # Optionally create missing dicts, or raise error
                        # For now, let's assume structure mostly exists based on definition
                        print(f"[ERROR] Invalid path: Key '{part}' not found in state path '{'.'.join(parts[:i+1])}'. Skipping update '{full_key}'.")
                        target_parent = None # Signal error
                        break
                    target_parent = target_parent[part]
                else:
                    print(f"[ERROR] Invalid path: Cannot traverse into non-dict element at '{'.'.join(parts[:i])}'. Skipping update '{full_key}'.")
                    target_parent = None # Signal error
                    break
            
            if target_parent is None: # Check if traversal failed
                continue

            target_key = parts[-1]

            # Perform the operation
            if operation == '.add':
                if target_key not in target_parent or not isinstance(target_parent[target_key], list):
                    print(f"[ERROR] Cannot perform '.add' on non-list or missing key '{key_path}'. Skipping update '{full_key}'.")
                    continue
                target_list = target_parent[target_key]
                if isinstance(value, list):
                    target_list.extend(value)
                else:
                    target_list.append(value) # Add single item
                print(f"[DEBUG] Applied '{full_key}': Added {value} to list.")

            elif operation == '.remove':
                if target_key not in target_parent or not isinstance(target_parent[target_key], list):
                    print(f"[ERROR] Cannot perform '.remove' on non-list or missing key '{key_path}'. Skipping update '{full_key}'.")
                    continue
                target_list = target_parent[target_key]
                items_to_remove = value if isinstance(value, list) else [value]
                for item in items_to_remove:
                    try:
                        target_list.remove(item)
                        print(f"[DEBUG] Applied '{full_key}': Removed {item} from list.")
                    except ValueError:
                        print(f"[WARNING] Item '{item}' not found in list '{key_path}' for removal. Skipping item.")
            
            elif operation == '.set': # Set/update keys within a target dictionary
                if target_key not in target_parent or not isinstance(target_parent[target_key], dict):
                    print(f"[ERROR] Cannot perform '.set' on non-dict or missing key '{key_path}'. Skipping update '{full_key}'.")
                    continue
                if not isinstance(value, dict):
                    print(f"[ERROR] Value for '.set' operation must be a dictionary. Skipping update '{full_key}'.")
                    continue
                target_parent[target_key].update(value)
                print(f"[DEBUG] Applied '{full_key}': Updated dict with {value}.")

            elif operation == '.delete': # Delete keys from a target dictionary
                if target_key not in target_parent or not isinstance(target_parent[target_key], dict):
                    print(f"[ERROR] Cannot perform '.delete' on non-dict or missing key '{key_path}'. Skipping update '{full_key}'.")
                    continue
                keys_to_delete = value if isinstance(value, list) else [value]
                target_dict = target_parent[target_key]
                for key_del in keys_to_delete:
                    if key_del in target_dict:
                        del target_dict[key_del]
                        print(f"[DEBUG] Applied '{full_key}': Deleted key '{key_del}' from dict.")
                    else:
                         print(f"[WARNING] Key '{key_del}' not found in dict '{key_path}' for deletion. Skipping key.")
           
            else: # Direct assignment/replacement
                if not isinstance(target_parent, dict):
                     print(f"[ERROR] Cannot assign value to non-dictionary parent for key '{target_key}'. Skipping update '{full_key}'.")
                     continue
                target_parent[target_key] = value
                print(f"[DEBUG] Applied '{full_key}': Set value to {value}.")

        except Exception as e:
            # Catch unexpected errors during processing
            print(f"[ERROR] Unexpected error applying update '{full_key}': {e}")
            # Optionally, log the traceback

# Placeholder for the recursive update logic - needs implementation!
# def apply_updates_recursive(updates: dict, state: dict):
#     """(Placeholder) Recursively applies updates based on dot notation keys."""
#     print("[TODO] Implement apply_updates_recursive logic!")
#     # This function will need to parse keys like 'player.inventory.add'
#     # navigate the 'state' dict, and perform the correct operation.
#     pass
# Remove or comment out the old placeholder function

# --- Main Game Loop ---
def main():
    """The main entry point and game loop."""
    print("Welcome to Endless Novel (v0 - Text Only)")
    print(game_state['narrative_context_summary']) # Initial scene description

    while True:
        # 1. Get Player Input
        player_action = get_player_input()

        if player_action in ["quit", "exit"]:
            print("Goodbye!")
            break

        # 2. Update Game State (Stores player_action)
        update_game_state(player_action, game_state)

        # 3. Construct & Call Claude for Narrative/Dialogue
        claude_prompt = construct_claude_prompt(game_state)
        claude_response = call_claude_api(claude_prompt) # Using placeholder response for now

        # 4. Parse Response and Apply State Updates
        narrative_text, summary_suggestion = parse_and_apply_state_updates(claude_response, game_state)

        # --- Update Narrative Context Summary ---
        # Use suggestion if provided, otherwise use the narrative text itself (or a truncation)
        if summary_suggestion:
            game_state['narrative_context_summary'] = summary_suggestion
        elif narrative_text:
            # Basic update: use the new narrative. Could be smarter (e.g., summarize long text).
            game_state['narrative_context_summary'] = narrative_text
        # else: Keep the old summary if Claude somehow returned nothing? (Edge case)

        # 5. Construct & Call Gemini for Placeholders (Based on clean narrative)
        gemini_prompt = construct_gemini_prompt(narrative_text, game_state)
        placeholder_output = call_gemini_api(gemini_prompt)

        # 6. Display Output (Clean narrative + placeholders)
        display_output(narrative_text, placeholder_output)

if __name__ == "__main__":
    main() 