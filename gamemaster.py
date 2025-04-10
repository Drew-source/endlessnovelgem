"""Gamemaster Engine: Assesses action difficulty, provides outcome flavor text, and suggests state updates."""
import json
import anthropic
from utils import load_prompt_template, call_claude_api
from character_manager import CharacterManager # For type hints
from location_manager import LocationManager # IMPORT LocationManager

# --- Gamemaster Input Construction --- #
def construct_gamemaster_context(game_state: dict, character_manager: CharacterManager, location_manager: LocationManager) -> dict:
    """Constructs the game state context dictionary for the Gamemaster Assessor prompt."""
    context = {}
    context['game_mode'] = 'dialogue' if game_state.get('dialogue_active') else 'narrative'
    current_location_id = game_state.get('location', 'unknown')
    context['current_location'] = current_location_id
    context['time_of_day'] = game_state.get('time_of_day', 'unknown')
    context['player_inventory'] = game_state.get('player', {}).get('inventory', [])
    context['player_stats'] = {
        'strength': game_state.get('player', {}).get('stats', {}).get('strength', 10),
        'charisma': game_state.get('player', {}).get('stats', {}).get('charisma', 10),
    }
    context['present_characters'] = game_state.get('current_npcs', []) 
    
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
                'stats': partner_data.get('stats', {}) 
            }
        else:
            print(f"[WARN] GamemasterContext: Could not retrieve state for dialogue partner {partner_id}")

    return context

# --- Gamemaster Assessment Handling --- #
def get_gamemaster_assessment(
    user_input: str,
    game_state: dict,
    character_manager: CharacterManager,
    location_manager: LocationManager,
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    gamemaster_template: str
) -> dict | None:
    """Calls the Gamemaster LLM to assess the action and get outcome details.

    Args:
        user_input: The player's input for the turn.
        game_state: The current game state.
        character_manager: The CharacterManager instance.
        location_manager: The LocationManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model to use for Gamemaster.
        gamemaster_template: The loaded Gamemaster system prompt template.

    Returns:
        A dictionary representing the parsed JSON assessment object from the Gamemaster LLM,
        or None if the call or parsing fails.
        Expected structure: {"odds": str, "success_message": str, "failure_message": str, "suggested_state_updates": list}
    """
    if not claude_client or not claude_model_name:
        print("[ERROR] Gamemaster: Claude client or model name missing.")
        return None
    if "Error:" in gamemaster_template:
         print("[ERROR] Gamemaster: System prompt template failed to load.")
         return None

    print("\n>>> Asking Gamemaster LLM to assess action... <<<")

    # 1. Construct Context
    game_state_context = construct_gamemaster_context(game_state, character_manager, location_manager)

    # 2. Construct Input JSON
    input_data_for_prompt = {
        "game_mode": game_state_context['game_mode'],
        "game_state_context": game_state_context,
        "user_input": user_input,
    }
    try:
        input_json_str = json.dumps(input_data_for_prompt, indent=2)
    except Exception as e:
        print(f"[ERROR] Gamemaster: Failed to serialize input data: {e}")
        return None

    # 3. Prepare API Call
    gamemaster_messages = [ {"role": "user", "content": input_json_str} ]
    gamemaster_prompt_details = { "system": gamemaster_template, "messages": gamemaster_messages }

    # 4. Call Claude API
    gm_response_obj = call_claude_api(claude_client, claude_model_name, gamemaster_prompt_details)

    # 5. Parse JSON Response
    assessment_data = None
    if gm_response_obj and gm_response_obj.content:
        gm_text = "".join(block.text for block in gm_response_obj.content if block.type == 'text').strip()
        print(f"[DEBUG] Gamemaster Raw Response:\n```json\n{gm_text}\n```") 
        
        json_start = gm_text.find('{')
        json_end = gm_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = gm_text[json_start:json_end]
            try:
                parsed_data = json.loads(json_str)
                # Validate structure
                if (isinstance(parsed_data, dict) and 
                    'odds' in parsed_data and 
                    'success_message' in parsed_data and 
                    'failure_message' in parsed_data):
                    
                    assessment_data = parsed_data
                    print(f"[INFO] Gamemaster assessed odds: {parsed_data['odds']}")
                else:
                    print("[WARN] Gamemaster: Parsed JSON object missing required keys or incorrect structure.")
            except json.JSONDecodeError as e:
                print(f"[ERROR] Gamemaster: Failed to decode response JSON: {e}. JSON string: {json_str}")
            except Exception as e:
                 print(f"[ERROR] Gamemaster: Unexpected error parsing response: {e}")
        else:
            print("[WARN] Gamemaster: No valid JSON object found in response.")
    elif gm_response_obj:
         print(f"[WARN] Gamemaster: Response object received, but no content. Stop Reason: {gm_response_obj.stop_reason}")
    else:
        print("[ERROR] Gamemaster: No response object received from API call.")

    if assessment_data is None:
        print("[ERROR] Gamemaster: Failed to get valid assessment data.")
        
    return assessment_data 