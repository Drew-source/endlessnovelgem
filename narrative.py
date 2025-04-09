"""Narrative Engine: Handles narrative turns and prompt construction."""
import json
import anthropic
from utils import call_claude_api
# Removed tool imports
from character_manager import CharacterManager # Import CharacterManager for type hinting
from location_manager import LocationManager # Import LocationManager

# --- Game State Update Logic --- #
# REMOVED apply_tool_updates function - This logic moves to main.py, triggered by Gamemaster

# --- Prompt Construction --- #
def construct_claude_prompt(
    current_state: dict,
    conversation_history: list,
    character_manager: CharacterManager,
    location_manager: LocationManager, # Add location_manager
    prompt_templates: dict
) -> dict:
    """Constructs the Claude prompt components for a narrative turn.

    Args:
        current_state: The current game state dictionary.
        conversation_history: List of previous message dicts.
        character_manager: The CharacterManager instance.
        location_manager: The LocationManager instance.
        prompt_templates: Dictionary containing loaded prompt template strings.

    Returns a dictionary containing system prompt, user turn prompt,
    and conversation history for the API call.
    """
    system_prompt = prompt_templates.get("claude_system", "Error: System prompt missing.")
    turn_template = prompt_templates.get("claude_turn_template", "Error: Turn template missing.")

    if "Error:" in system_prompt or "Error:" in turn_template:
        print("[ERROR] Cannot construct Claude prompt due to missing templates.")
        # Return structure expected by call_claude_api (system + messages)
        return {"system": "", "messages": [{"role": "user", "content": "Error in prompt construction."}]}

    # Determine present characters using LocationManager
    player_location = current_state.get('location')
    present_character_ids = location_manager.get_characters_at_location(player_location)
    present_character_names = [character_manager.get_name(cid) or cid for cid in present_character_ids]

    # Differentiate between companions and other NPCs if needed (using archetype)
    # For now, just list all present characters
    companion_names_present = ", ".join(present_character_names) or "None"
    companion_ids_present = ", ".join(present_character_ids) or "None"
    
    # Key info formatting - simplified for clarity
    key_info_str = "; ".join([f"{k}: {v}" for k, v in current_state.get('narrative_flags', {}).items()])
    if not key_info_str: key_info_str = "None"

    context = {
        'player_location': player_location or 'an unknown place',
        'characters_present': companion_names_present, # Using combined list for now
        'companions_present': companion_names_present, # Keep both for template compatibility?
        'companion_ids_present': companion_ids_present,
        'time_of_day': current_state.get('time_of_day', 'unknown'),
        'key_information': key_info_str, # Use formatted string
        'recent_events_summary': current_state.get('narrative_context_summary', 'The story has just begun.'),
        'current_objective': current_state.get('current_objective', 'None stated.'),
        'last_player_action': current_state.get('last_player_action', 'None')
    }

    try:
        user_turn_prompt_text = turn_template.format(**context)
    except KeyError as e:
        print(f"[ERROR] Missing key in Claude turn template: {e}. Template: \n{turn_template}")
        user_turn_prompt_text = f"Describe the situation based on context. (Template error: {e})"
    except Exception as e:
        print(f"[ERROR] Failed to format Claude turn template: {e}")
        user_turn_prompt_text = "Describe the situation based on context. (Formatting error)"

    # Construct the final messages list for the API
    messages_for_api = conversation_history + [{"role": "user", "content": user_turn_prompt_text}]

    return {
        "system": system_prompt,
        "messages": messages_for_api # Pass the full message list
    }

# --- Narrative Turn Handling --- #
def handle_narrative_turn(
    game_state: dict,
    conversation_history: list,
    character_manager: CharacterManager,
    location_manager: LocationManager, # Add location_manager
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    prompt_templates: dict,
) -> tuple[anthropic.types.Message | None, dict]:
    """Handles a single narrative turn: constructs prompt, calls API for TEXT ONLY.

    Args:
        game_state: The current game state.
        conversation_history: The current narrative history.
        character_manager: The CharacterManager instance.
        location_manager: The LocationManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model.
        prompt_templates: Dictionary of loaded prompt templates.

    Returns:
        A tuple containing:
        - The raw Anthropic Message object from the API call, or None on failure.
        - The prompt_details dictionary used for the API call.
    """
    print("\n>>> Processing Player Action... Asking Narrative LLM for text... <<<")
    
    # Construct prompt using the function in this module
    prompt_details = construct_claude_prompt(
        game_state, 
        conversation_history, 
        character_manager,
        location_manager, # Pass location_manager
        prompt_templates
    )

    # Call Claude API using the utility function - NO TOOLS passed
    response_obj = call_claude_api(
        claude_client=claude_client,
        model_name=claude_model_name,
        prompt_details=prompt_details,
        tools=None # Ensure no tools are passed
    )

    return response_obj, prompt_details
