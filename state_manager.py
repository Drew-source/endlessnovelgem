"""State Manager Engine: Analyzes interactions and translates them into state update requests."""
import json
import anthropic
from utils import load_prompt_template, call_claude_api
from character_manager import CharacterManager # For type hints
from location_manager import LocationManager # IMPORT LocationManager

# --- State Manager Input Construction --- #
def construct_state_manager_context(game_state: dict, character_manager: CharacterManager, location_manager: LocationManager) -> dict:
    """Constructs the game state context dictionary for the State Manager prompt."""
    context = {}
    context['game_mode'] = 'dialogue' if game_state.get('dialogue_active') else 'narrative'
    current_location_id = game_state.get('location', 'unknown')
    context['current_location'] = current_location_id
    context['time_of_day'] = game_state.get('time_of_day', 'unknown')
    context['player_inventory'] = game_state.get('player', {}).get('inventory', [])
    context['present_characters'] = game_state.get('current_npcs', []) # Assuming current_npcs holds IDs present
    
    # Add adjacent location data
    context['adjacent_locations'] = location_manager.get_connections(current_location_id)
    
    partner_id = game_state.get('dialogue_partner')
    context['dialogue_partner_id'] = partner_id
    context['dialogue_partner_state'] = None
    
    if context['game_mode'] == 'dialogue' and partner_id:
        partner_data = character_manager.get_character_data(partner_id)
        if partner_data:
            context['dialogue_partner_state'] = {
                'name': partner_data.get('name', partner_id),
                'inventory': character_manager.get_inventory(partner_id) or [],
                'trust': character_manager.get_trust(partner_id) or 0,
                'statuses': character_manager.get_active_statuses(partner_id) or {},
                'following': character_manager.get_follow_status(partner_id) or False
            }
        else:
            print(f"[WARN] StateManager: Could not retrieve state for dialogue partner {partner_id}")

    return context

# --- State Manager Turn Handling --- #
def translate_interaction_to_state_updates(
    user_input: str,
    llm_response_text: str,
    game_state: dict,
    character_manager: CharacterManager,
    location_manager: LocationManager,
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    state_manager_template: str
) -> list:
    """Calls the State Manager LLM to translate interaction into state update requests.

    Args:
        user_input: The player's input for the turn.
        llm_response_text: The narrative/dialogue LLM's text response.
        game_state: The current game state.
        character_manager: The CharacterManager instance.
        location_manager: The LocationManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model to use for State Manager.
        state_manager_template: The loaded State Manager system prompt template.

    Returns:
        A list of state update request dictionaries [{'request_name': ..., 'parameters': ...}], or empty list.
    """
    if not claude_client or not claude_model_name:
        print("[ERROR] StateManager: Claude client or model name missing.")
        return []
    if "Error:" in state_manager_template:
         print("[ERROR] StateManager: System prompt template failed to load.")
         return []

    print("\n>>> Asking State Manager LLM to translate interaction... <<<")

    # 1. Construct the Game State Context for the prompt
    game_state_context = construct_state_manager_context(game_state, character_manager, location_manager)

    # 2. Construct the input JSON string for the State Manager prompt
    input_data_for_prompt = {
        "game_mode": game_state_context['game_mode'],
        "game_state_context": game_state_context,
        "user_input": user_input,
        "llm_response": llm_response_text
    }
    try:
        input_json_str = json.dumps(input_data_for_prompt, indent=2)
    except Exception as e:
        print(f"[ERROR] StateManager: Failed to serialize input data to JSON: {e}")
        return []

    # 3. Prepare the messages for the State Manager LLM call
    state_manager_messages = [
        {"role": "user", "content": input_json_str}
    ]

    state_manager_prompt_details = {
        "system": state_manager_template,
        "messages": state_manager_messages
    }

    # 4. Call the Claude API (No tools passed to State Manager)
    sm_response_obj = call_claude_api(
        claude_client=claude_client,
        model_name=claude_model_name,
        prompt_details=state_manager_prompt_details,
        tools=None # State Manager only outputs JSON text
    )

    # 5. Parse the State Manager's response
    update_requests = []
    if sm_response_obj and sm_response_obj.content:
        sm_text = ""
        for block in sm_response_obj.content:
            if block.type == 'text':
                sm_text += block.text
        
        sm_text = sm_text.strip()
        # Print raw response BEFORE parsing attempt
        print(f"[DEBUG] StateManager Raw Response:\n{sm_text}") 
        
        # Improved JSON extraction: Find first '[' and last ']'
        json_start = sm_text.find('[')
        json_end = sm_text.rfind(']') + 1 # +1 to include the closing bracket

        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_str = sm_text[json_start:json_end]
            print(f"[DEBUG] Extracted JSON string: {json_str}") # Debug the extracted part
            try:
                parsed_requests = json.loads(json_str)
                if isinstance(parsed_requests, list):
                    valid_requests = []
                    for req in parsed_requests:
                        if isinstance(req, dict) and 'request_name' in req and 'parameters' in req:
                            valid_requests.append(req)
                        else:
                             print(f"[WARN] StateManager: Invalid request structure ignored: {req}")
                    update_requests = valid_requests
                    # This print might be misleading if parsing failed earlier, move it up?
                    # print(f"[INFO] StateManager translated {len(update_requests)} state update requests.") 
                else:
                    print("[ERROR] StateManager: Response JSON was not a list.")
            except json.JSONDecodeError as e:
                print(f"[ERROR] StateManager: Failed to decode response JSON: {e}")
                # Show the string that failed decoding
                print(f"  Raw JSON string attempted: {repr(json_str)}") 
            except Exception as e:
                 print(f"[ERROR] StateManager: Unexpected error parsing response: {e}")
        else:
            print("[WARN] StateManager: No valid JSON array boundaries found in response.")

    elif sm_response_obj:
         print(f"[WARN] StateManager: Response object received, but no content blocks found. Stop Reason: {sm_response_obj.stop_reason}")
    else:
        print("[ERROR] StateManager: No response object received from API call.")

    # Report final count after parsing attempts
    if update_requests:
        print(f"[INFO] StateManager successfully parsed {len(update_requests)} state update requests.")
    # else: No need to print if empty

    return update_requests 