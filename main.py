"""Endless Novel V0 - Main Game Execution Script"""

import os
import copy
import json
import traceback
import random # Import random for action resolver
from dotenv import load_dotenv
import anthropic
import google.generativeai as genai

# Import configuration, utilities, and engine modules
from config import (MAX_TURNS, PROMPT_DIR, MAX_HISTORY_MESSAGES, DEBUG_IGNORE_LOCATION, DEBUG_MODE)
from utils import load_prompt_template, call_claude_api
from narrative import handle_narrative_turn, construct_claude_prompt as construct_narrative_prompt
from dialogue import handle_dialogue_turn, summarize_conversation
from visuals import call_gemini_api, construct_gemini_prompt
from character_manager import CharacterManager
from location_manager import LocationManager
# Use the Gamemaster Assessor module
from gamemaster import get_gamemaster_assessment 
# Use the Action Resolver module
from action_resolver import resolve_action 
# Use the State Manager module
from state_manager import translate_interaction_to_state_updates

# --- API Client Initialization --- #
def initialize_clients() -> tuple[anthropic.Anthropic | None, genai.GenerativeModel | None, str | None, str | None]:
    """Initializes and returns API clients and model names."""
    load_dotenv()
    claude_client = None
    gemini_client = None
    anthropic_model_name = None
    google_model_name = None
    try:
        # Claude Client
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        anthropic_model_name = os.getenv("ANTHROPIC_MODEL_NAME")
        if anthropic_api_key and anthropic_model_name:
            claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
            print("[INFO] Anthropic client initialized.")
        else:
            if not anthropic_api_key: print("[ERROR] ANTHROPIC_API_KEY not found.")
            if not anthropic_model_name: print("[ERROR] ANTHROPIC_MODEL_NAME not found.")
            print("[ERROR] Claude API calls will fail.")

        # Gemini Client
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_model_name = os.getenv("GOOGLE_MODEL_NAME")
        if google_api_key and google_model_name:
            genai.configure(api_key=google_api_key)
            gemini_client = genai.GenerativeModel(google_model_name)
            print(f"[INFO] Google AI client initialized for model: {google_model_name}")
        else:
            if not google_api_key: print("[ERROR] GOOGLE_API_KEY not found.")
            if not google_model_name: print("[ERROR] GOOGLE_MODEL_NAME not found.")
            print("[ERROR] Gemini API calls will fail.")
            
    except Exception as e:
        print(f"[ERROR] Failed during API client initialization: {e}")

    return claude_client, gemini_client, anthropic_model_name, google_model_name

# --- Initial Game State --- #
INITIAL_GAME_STATE = {
    'player': {
        'name': 'Player',
        'inventory': ['a worn adventurer pack', 'flint and steel'],
        'stats': {'strength': 12, 'charisma': 10} # Example stats
    },
    'location': 'whispering_forest_edge',
    'time_of_day': 'morning',
    'current_npcs': ['varnas_the_skeptic'], # Store IDs of NPCs present
    'companions': {
        'varnas_the_skeptic': {
            'name': 'Varnas the Skeptic',
            'archetype': 'companion',
            'description': "A weathered man with distrustful eyes, clad in worn leather.",
            'traits': ['skeptic', 'guarded', 'pragmatic'],
            'location': 'whispering_forest_edge',
            'inventory': ['worn leather armor', 'short sword', 'skeptical frown'],
            'stats': {'strength': 11, 'charisma': 8}, # Example NPC stats
            'memory': {
                'dialogue_history': []
            },
            'relationships': {
                'player': {
                    'trust': 20,
                    'temporary_statuses': {}
                }
            },
            'following_player': False # Explicit follow status
        }
    },
    'narrative_flags': {},
    'current_chapter': 1,
    'current_objective': None,
    'dialogue_active': False,
    'dialogue_partner': None,
    'last_player_action': None,
    'narrative_context_summary': "Sunlight filters through the ancient trees of the Whispering Forest. The air is cool and smells of damp earth and pine. Your companion, Varnas, shifts his weight beside you."
}

# --- State Update Application Logic --- #
def apply_state_updates(update_requests: list, game_state: dict, character_manager: CharacterManager, location_manager: LocationManager, prompt_templates: dict, gemini_client, gemini_model_name, action_succeeded: bool) -> tuple[bool, list]:
    """Applies state updates suggested by the Gamemaster, after validation.
       Only applies certain updates if the core action succeeded.

    Args:
        update_requests: List of update request dicts from the Gamemaster.
        game_state: The current game state (will be modified).
        character_manager: The CharacterManager instance.
        location_manager: The LocationManager instance.
        prompt_templates: Dictionary of loaded prompt templates (for summarization).
        gemini_client: Gemini client for summarization.
        gemini_model_name: Gemini model name for summarization.
        action_succeeded: Boolean indicating if the core action (requiring roll/check) passed.

    Returns:
        A tuple: (stop_processing_flag, feedback_messages)
    """
    stop_processing_flag = False
    feedback_messages = []

    if not update_requests:
        return stop_processing_flag, feedback_messages

    print(f"[INFO] Applying {len(update_requests)} suggested state update(s). Action Success: {action_succeeded}")
    for request in update_requests:
        request_name = request.get('request_name')
        params = request.get('parameters', {})
        print(f"  - Applying: {request_name} with params: {params}")
        
        # Determine if this update should only happen on success
        requires_success = request_name not in ["start_dialogue", "end_dialogue", "create_character", "update_relationship"] 
        # ^ Example: Dialogue changes, creation happen regardless. State changes, item exchange might depend on success.
        # Adjust this logic based on your game rules!

        if requires_success and not action_succeeded:
            print(f"    [State Update Skipped] Action failed, skipping dependent update: {request_name}")
            # Optional: Add feedback like "(Failed attempt to {request_name})"
            continue # Skip to next request
            
        try:
            # --- Apply Validated Updates (Copy logic from previous execute_gamemaster_tools) ---
            # Reuse the validation and application logic from the previous version of `execute_gamemaster_tools`
            # adapting it to use `request_name` instead of `tool_name`.
            # Key is to ADD validation checks before applying changes.

            if request_name == "update_game_state":
                # ... (validation and application logic for location, time, inventory, flags...) ...
                updates_applied = False
                state_change_summary = []
                if "location" in params: # Location
                    new_loc = params['location']
                    if game_state.get('location') != new_loc:
                        if location_manager.is_valid_location(new_loc):
                            game_state['location'] = new_loc; updates_applied = True; feedback_messages.append(f"(Moved to {new_loc})")
                            location_manager.update_follower_locations(new_loc)
                        else: feedback_messages.append(f"(Cannot move to invalid location: {new_loc})")
                if "time_of_day" in params: # Time
                    new_time = params['time_of_day']
                    if game_state.get('time_of_day') != new_time:
                        game_state['time_of_day'] = new_time; updates_applied = True; feedback_messages.append(f"(Time is now {new_time})")
                if "player_inventory_add" in params: # Inv Add
                    items = params.get("player_inventory_add", [])
                    if items: game_state['player'].setdefault('inventory', []).extend(items); updates_applied = True; feedback_messages.append(f"(You obtained: {', '.join(items)})")
                if "player_inventory_remove" in params: # Inv Remove
                    items = params.get("player_inventory_remove", [])
                    removed = []
                    if items:
                        inv = game_state['player'].setdefault('inventory', [])
                        for item in items: 
                            if item in inv: 
                                try: inv.remove(item); removed.append(item)
                                except ValueError: pass
                        if removed: updates_applied = True; feedback_messages.append(f"(You lost: {', '.join(removed)})")
                        if len(removed) < len(items): feedback_messages.append(f"(Could not remove: {', '.join(i for i in items if i not in removed)})")
                if "narrative_flags_set" in params: # Flags Set
                    flags = params.get("narrative_flags_set", {})
                    if flags: game_state.setdefault('narrative_flags', {}).update(flags); updates_applied = True; feedback_messages.append(f"(Flag(s) updated: {flags})")
                if "narrative_flags_delete" in params: # Flags Del
                    keys = params.get("narrative_flags_delete", [])
                    deleted = []
                    if keys: 
                        flags = game_state.setdefault('narrative_flags', {})
                        for key in keys: 
                            if key in flags: del flags[key]; deleted.append(key)
                        if deleted: updates_applied = True; feedback_messages.append(f"(Flag(s) removed: {deleted})")
                if "current_objective" in params: # Objective
                    new_obj = params['current_objective']
                    if game_state.get('current_objective') != new_obj:
                         game_state['current_objective'] = new_obj; updates_applied = True; feedback_messages.append(f"(New objective: {new_obj})")
                if not updates_applied: print(f"  [INFO] update_game_state requested, but no valid changes applied.")

            elif request_name == "start_dialogue":
                char_id = params.get('target_id') # Use target_id from Gamemaster schema
                if not char_id:
                    feedback_messages.append("(Who to talk to?)")
                else:
                    is_present = location_manager.is_character_present(char_id, game_state.get('location'))
                    char_exists = character_manager.get_character_data(char_id)
                    if char_exists and is_present:
                        if not game_state['dialogue_active']:
                            game_state['dialogue_active'] = True
                            game_state['dialogue_partner'] = char_id
                            name = character_manager.get_name(char_id)
                            feedback_messages.append(f"(Conversation started with {name}.)")
                        else:
                            name = character_manager.get_name(game_state['dialogue_partner'])
                            feedback_messages.append(f"(Already talking to {name}.)")
                            stop_processing_flag = True
                    elif char_exists:
                        feedback_messages.append(f"({character_manager.get_name(char_id)} is not here.)")
                        stop_processing_flag = True
                    else:
                        feedback_messages.append(f"(Unknown character: {char_id})")
                        stop_processing_flag = True
                    
            elif request_name == "create_character":
                # ... (validation [archetype exists, location valid] and application) ...
                arch = params.get('archetype')
                loc = params.get('location') or game_state.get('location')
                hint = params.get('name_hint')
                if not arch: feedback_messages.append("[SYS ERR: Create char missing archetype]")
                elif not loc or not location_manager.is_valid_location(loc): feedback_messages.append(f"[SYS ERR: Create char invalid location: {loc}]")
                else:
                    new_id = character_manager.generate_character(arch, loc, hint)
                    if new_id: 
                        name = character_manager.get_name(new_id)
                        feedback_messages.append(f"({name} appears.)")
                    else: 
                        feedback_messages.append("[SYS ERR: Character generation failed.]")
                stop_processing_flag = True

            elif request_name == "end_dialogue":
                # ... (validation [dialogue active] and application, including summarization) ...
                if game_state['dialogue_active']:
                    partner_id = game_state.get('dialogue_partner')
                    name = character_manager.get_name(partner_id)
                    # Summarize
                    history = character_manager.get_dialogue_history(partner_id)
                    if history:
                        summary = summarize_conversation(history, character_manager, gemini_client, gemini_model_name, prompt_templates.get("summarization"))
                        game_state['narrative_context_summary'] += f"\n\n[Summary with {name}: {summary}]"
                    # Update state
                    game_state['dialogue_active'] = False; game_state['dialogue_partner'] = None
                    feedback_messages.append(f"(Conversation with {name} ends.)"); stop_processing_flag = True
                else: feedback_messages.append("(No conversation to end.)"); stop_processing_flag = True

            elif request_name == "exchange_item":
                item = params.get('item_name')
                giver = params.get('giver_id')
                receiver = params.get('receiver_id')
                if not all([item, giver, receiver]):
                    feedback_messages.append("[SYS ERR: Exchange item missing params]")
                elif giver == receiver:
                    feedback_messages.append("(Cannot exchange with self.)")
                elif game_state.get('dialogue_partner') not in [giver, receiver] and 'player' not in [giver, receiver]:
                    feedback_messages.append("(Can only exchange with dialogue partner.)")
                else:
                    giver_has = character_manager.has_item(giver, item) if giver != 'player' else item in game_state['player'].get('inventory', [])
                    if giver_has:
                        removed = character_manager.remove_item(giver, item) if giver != 'player' else game_state['player']['inventory'].remove(item) or True
                        if removed:
                            added = character_manager.add_item(receiver, item) if receiver != 'player' else game_state['player'].setdefault('inventory', []).append(item) or True
                            if added:
                                g_name = "You" if giver == 'player' else character_manager.get_name(giver)
                                r_name = "you" if receiver == 'player' else character_manager.get_name(receiver)
                                feedback_messages.append(f"({g_name} give{'s' if giver != 'player' else ''} {item} to {r_name}.)")
                            else:
                                if giver == 'player':
                                    game_state['player']['inventory'].append(item)
                                else:
                                    character_manager.add_item(giver, item)
                                feedback_messages.append(f"(Exchange failed: Could not add {item}.)")
                        else:
                            feedback_messages.append(f"(Exchange failed: Could not remove {item}.)")
                    else:
                        feedback_messages.append(f"(Exchange failed: {giver} does not have {item}.)")

            elif request_name == "update_relationship":
                # Use character_id from State Manager output schema
                target = params.get('character_id') 
                trust_delta = params.get('trust_delta', 0) # Default to 0 if missing
                # ADD checks for other relationship types (e.g., status effects) later if needed
                
                if not target:
                    feedback_messages.append("[SYS ERR: Update relationship missing target]")
                elif target == 'player':
                    feedback_messages.append("(Cannot update player trust.)")
                else:
                    old_trust = character_manager.get_trust(target)
                    if old_trust is not None:
                        # Apply trust update using the character manager
                        success = character_manager.update_trust(target, trust_delta)
                        if success:
                            # Check if trust actually changed (might hit cap)
                            new_trust = character_manager.get_trust(target)
                            if new_trust != old_trust:
                                feedback_messages.append(f"(Trust with {character_manager.get_name(target)} {'increased' if trust_delta > 0 else 'decreased'}.)")
                            else:
                                feedback_messages.append(f"(Trust with {character_manager.get_name(target)} already at limit.)")
                        else:
                            feedback_messages.append(f"(Trust update failed for {target}.)")
                    else:
                        feedback_messages.append(f"(Trust update failed: Invalid target {target}.)")

            elif request_name == "set_follow_status":
                char_id = params.get('character_id')
                following = params.get('following')
                
                # --- Corrected Validation --- 
                # Validate character exists and is present based on THEIR location, not game_state['location']
                char_exists = character_manager.get_character_data(char_id)
                char_current_loc = character_manager.get_location(char_id) if char_exists else None
                player_current_loc = game_state.get('location') # Player's location for presence check

                if not char_id or not char_exists:
                    feedback_messages.append(f"[SYS ERR: Set follow invalid character: {char_id}]")
                # Check if the character's location matches the player's current location
                elif char_current_loc != player_current_loc: 
                     feedback_messages.append(f"[SYS ERR: Set follow target not present: {char_id} is at {char_current_loc}, player is at {player_current_loc}]")
                elif following is None or not isinstance(following, bool):
                    feedback_messages.append(f"[SYS ERR: Set follow invalid value: {following}]")
                else:
                    current = character_manager.get_follow_status(char_id) # Check status for the target char_id
                    name = character_manager.get_name(char_id)
                    if current == following:
                        feedback_messages.append(f"({name} is already {'following' if following else 'waiting'}.)") # Adjusted wording
                    elif current is None:
                        feedback_messages.append(f"(Cannot get follow status for {name}.)")
                    else:
                        # Apply the status update using the correct char_id
                        success = character_manager.set_follow_status(char_id, following)
                        if success:
                            feedback_messages.append(f"({name} will {'now follow' if following else 'wait here'}.)") # Adjusted wording
                        else:
                            feedback_messages.append(f"(Failed to set follow status for {name}.)")
            else:
                print(f"[WARNING] Unknown state update request name: {request_name}")
                feedback_messages.append(f"[Internal Note: Unknown request '{request_name}'.]")

        except Exception as e:
            print(f"[ERROR] Exception applying state update '{request_name}': {e}")
            traceback.print_exc()
            feedback_messages.append(f"[SYSTEM ERROR applying update: {request_name}]")

        if stop_processing_flag:
            break
            
    return stop_processing_flag, feedback_messages

# --- Output & Input --- #
def display_output(narrative_text: str, placeholder_text: str | None, feedback_msgs: list | None = None):
    """Displays the combined narrative, feedback, and placeholders to the player."""
    print("\n" + "-"*40 + "\n")
    if isinstance(narrative_text, str):
        print(narrative_text.strip())
    else:
        print("(No narrative text generated.)")
    if feedback_msgs:
        print("\n" + "\n".join(filter(None, feedback_msgs)))
    if placeholder_text:
        print("\n--- Visuals & Sounds ---")
        print(placeholder_text.strip())
    print("\n" + "-"*40)

def get_player_input() -> str:
    """Gets the player's command from the console."""
    return input("\n> ").strip()

# --- Main Game Loop --- #
def main():
    """Main game loop."""
    print("\n--- Initializing Endless Novel ---")
    # Initialize API Clients
    claude_client, gemini_client, anthropic_model_name, google_model_name = initialize_clients()

    # Load Prompt Templates
    prompt_templates = {}
    # Pass only the filename to load_prompt_template, it handles the directory
    for prompt_name in [
        "gamemaster_system", "state_manager_system", "dialogue_system",
        "claude_system", "location_generator", "summarization",
        "claude_turn_template", 
        "gemini_placeholder_template" # Added missing visuals template
    ]:
        # Let load_prompt_template handle joining with PROMPT_DIR
        template_content = load_prompt_template(f"{prompt_name}.txt")
        prompt_templates[prompt_name] = template_content
        if "Error:" in template_content:
            print(f"[FATAL] Failed to load critical prompt template: {prompt_name}.txt. Exiting.")
            return # Exit if a critical prompt fails

    # Initialize Managers
    game_state = copy.deepcopy(INITIAL_GAME_STATE)
    # Initialize CharacterManager correctly - it only takes the initial state dict
    character_manager = CharacterManager(game_state['companions']) 

    # Ensure the correct key is used here now that loading should work
    location_generator_template = prompt_templates.get("location_generator")
    if not location_generator_template or "Error:" in location_generator_template:
         print("[FATAL] Location generator template failed to load correctly. Exiting.")
         return
         
    # Correctly instantiate LocationManager with all required arguments in the correct order
    location_manager = LocationManager(
        game_state_ref=game_state, 
        character_manager_ref=character_manager, # Pass the character manager
        claude_client=claude_client,             # Pass the Claude client for generation
        claude_model_name=anthropic_model_name,  # Pass the Claude model name
        generator_template=location_generator_template # Pass the template
    )
    
    # Now link LM back to CM (This attribute needs to exist or be handled in CM)
    # Assuming CharacterManager needs this reference set after initialization.
    # If CM doesn't actually use location_manager internally, this line might be removable.
    # For now, keep it as it was part of the structure, but the primary fix is the __init__ call.
    character_manager.location_manager = location_manager 
    
    # --- Initial Location Generation (Before First Turn) ---
    initial_location_id = game_state.get('location')
    if initial_location_id and not DEBUG_IGNORE_LOCATION:
        try:
            print(f"[INIT] Generating initial adjacent locations for starting location: {initial_location_id}")
            location_manager.ensure_location_generated(initial_location_id)
            print(f"[INIT] Initial adjacent locations generated.")
        except AttributeError as ae:
            print(f"[FATAL ERROR] Incorrect method name called on LocationManager during init: {ae}")
            return # Stop execution if this critical setup fails
        except Exception as e:
            print(f"[ERROR] Failed to generate initial adjacent locations for {initial_location_id}: {e}")
            # Decide if this is fatal or just a warning?
            # For now, just print error and continue.

    # --- Game Loop --- #
    turn_count = 0
    conversation_history = [] # Narrative history

    print("Welcome to Endless Novel (v0.4 - GM Assessor Architecture)")

    # Initial Scene
    try:
        initial_text = game_state['narrative_context_summary']
        initial_gemini_prompt = construct_gemini_prompt(initial_text, game_state, prompt_templates.get("gemini_placeholder_template"))
        initial_placeholders = call_gemini_api(gemini_client, google_model_name, initial_gemini_prompt)
    except Exception as e:
        print(f"[WARN] Failed initial Gemini call: {e}")
        initial_placeholders = "[ Initial placeholders unavailable ]"
    display_output(initial_text, initial_placeholders)

    # --- Game Loop --- #
    while True:
        # Ensure adjacent locations are generated for the current location
        # REMOVED ensure_location_generated call from here
             
        turn_count += 1
        print(f"\n--- Turn {turn_count} --- ({'Dialogue' if game_state['dialogue_active'] else 'Narrative'})")

        player_input_raw = get_player_input()
        if player_input_raw.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break

        game_state['last_player_action'] = player_input_raw

        # Initialize turn vars
        outcome_message = ""
        content_llm_response_text = ""
        placeholder_output = None
        stop_processing_flag = False 
        feedback_messages = []
        state_manager_updates = [] # Initialize list for updates from State Manager
        action_succeeded = True # Default to success unless a roll fails

        # --- Gamemaster Assessment Call ---
        gm_assessment = None
        try:
            # Pass location_manager to the assessment function
            gm_assessment = get_gamemaster_assessment(
                player_input_raw, 
                game_state, 
                character_manager, 
                location_manager, # Added location_manager
                claude_client, 
                anthropic_model_name, 
                prompt_templates.get("gamemaster_system")
            )
        except Exception as gm_call_e:
            print(f"[ERROR] Exception during Gamemaster call: {gm_call_e}")
            traceback.print_exc()
            feedback_messages.append(f"[SYS ERR: GM call failed: {gm_call_e}]")
            # Allow loop to continue? Display error and skip turn?
            display_output("(The threads of fate tangle unexpectedly...)", None, feedback_messages)
            continue

        if gm_assessment is None:
            feedback_messages.append("[SYS ERR: Failed to get assessment from Gamemaster.]")
            display_output("(The world seems uncertain how to react...)", None, feedback_messages)
            continue # Skip rest of turn processing

        # --- Action Resolution (Python) ---
        odds_str = gm_assessment.get("odds", "Medium") # Default odds if missing
        success_msg = gm_assessment.get("success_message", "(Action succeeds.)")
        failure_msg = gm_assessment.get("failure_message", "(Action fails.)")

        if odds_str == "Impossible":
            action_succeeded = False
            outcome_message = failure_msg # Use failure message for impossibility
            feedback_messages.append(f"(Action Impossible: {failure_msg})") # Add specific feedback
            # Skip content generation? Or let it describe the impossibility? Let's let it describe.
        elif odds_str == "Accept":
            action_succeeded = True
            outcome_message = success_msg
        else: # Easy, Medium, Difficult - Perform roll
            try:
                action_succeeded = resolve_action(odds_str, game_state, character_manager)
                outcome_message = success_msg if action_succeeded else failure_msg
            except Exception as resolve_e:
                print(f"[ERROR] Exception during action resolution: {resolve_e}")
                traceback.print_exc()
                feedback_messages.append(f"[SYS ERR: Action resolution failed: {resolve_e}]")
                action_succeeded = False # Treat as failure if resolver breaks
                outcome_message = failure_msg # Default to failure message

        # --- Content Generator LLM Call (Narrative or Dialogue) ---
        try:
            if game_state['dialogue_active']:
                # *** CORRECTED DIALOGUE CALL ***
                # Call the updated handle_dialogue_turn from dialogue.py,
                # passing the resolved outcome message.
                content_llm_response_obj, _ = handle_dialogue_turn(
                    game_state=game_state,
                    player_utterance=player_input_raw,
                    character_manager=character_manager,
                    claude_client=claude_client,
                    claude_model_name=anthropic_model_name,
                    dialogue_template=prompt_templates.get("dialogue_system"),
                    outcome_message=outcome_message # Pass resolved outcome
                )
            else: # Narrative Mode
                # Append User Message (raw input) and GM Outcome Message
                conversation_history.append({"role": "user", "content": player_input_raw})
                # Inject outcome message for narrative context
                conversation_history.append({"role": "user", "content": f"[Action Outcome: {outcome_message}]"})

                if len(conversation_history) > MAX_HISTORY_MESSAGES:
                    conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
                    print(f"[DEBUG] Narrative history truncated.")

                # Call narrative handler (expects history including outcome message)
                content_llm_response_obj, _ = handle_narrative_turn(
                    game_state, conversation_history, character_manager, location_manager,
                    claude_client, anthropic_model_name, prompt_templates
                )
            
            # Extract content LLM text response (common to both branches)
            if content_llm_response_obj and content_llm_response_obj.content:
                for block in content_llm_response_obj.content:
                    if block.type == 'text':
                        content_llm_response_text = block.text.strip()
                        break
            if not content_llm_response_text:
                fallback = "(Description unclear.)" if not game_state['dialogue_active'] else "(Character says nothing.)"
                content_llm_response_text = fallback
                print("[WARN] No text content found in Content Generator LLM response.")

        except Exception as content_call_e:
            print(f"[ERROR] Exception during Content Generator LLM call: {content_call_e}")
            traceback.print_exc()
            content_llm_response_text = "(The narrative falters...)"
            feedback_messages.append(f"[SYS ERR: Content LLM call failed: {content_call_e}]")
            # Skip state manager and updates if content gen fails
            stop_processing_flag = True 

        # --- State Manager LLM Call ---
        state_manager_updates = [] # Initialize/reset updates for the turn
        if not stop_processing_flag:
            try:
                # Call the state manager function - it should return the list of updates
                state_manager_updates = translate_interaction_to_state_updates(
                    user_input=player_input_raw, # Use the original player input
                    llm_response_text=content_llm_response_text, # Use the text from narrative/dialogue LLM
                    game_state=game_state,
                    character_manager=character_manager,
                    location_manager=location_manager,
                    claude_client=claude_client,
                    claude_model_name=anthropic_model_name,
                    state_manager_template=prompt_templates.get("state_manager_system")
                )
                # REMOVED erroneous handle_claude_response call here

            except Exception as state_call_e:
                print(f"[ERROR] Exception during State Manager call: {state_call_e}")
                traceback.print_exc()
                feedback_messages.append(f"[SYS ERR: State Manager call failed: {state_call_e}]")

        # --- Apply State Updates (From State Manager) ---
        if state_manager_updates: # Check if State Manager provided updates
            print(f"[INFO] State Manager proposed {len(state_manager_updates)} updates.") # Added print
            try:
                stop_processing_flag_from_apply, tool_feedback = apply_state_updates(
                     state_manager_updates, # Pass the list received from State Manager
                     game_state, character_manager, location_manager,
                     prompt_templates, gemini_client, google_model_name,
                     action_succeeded # Pass success flag
                )
                feedback_messages.extend(tool_feedback)
                # Allow apply_state_updates to set the stop flag (e.g., for dialogue start/end)
                if stop_processing_flag_from_apply: 
                    stop_processing_flag = True 
            except Exception as update_exec_e:
                print(f"[ERROR] Exception applying state updates: {update_exec_e}")
                traceback.print_exc()
                feedback_messages.append(f"[SYS ERR: State update application failed: {update_exec_e}]")
                stop_processing_flag = True 
        else:
            # Updated print statement
            if not stop_processing_flag: # Don't print if an earlier error occurred
                 print("[INFO] State Manager suggested no state updates needed.")
            # stop_processing_flag handling remains similar, depends on previous steps or update application

        # --- Generate Placeholders (Moved BEFORE history update) ---
        if not stop_processing_flag and not game_state['dialogue_active']:
            try:
                gemini_prompt = construct_gemini_prompt(content_llm_response_text, game_state, prompt_templates.get("gemini_placeholder_template"))
                placeholder_output = call_gemini_api(gemini_client, google_model_name, gemini_prompt)
            except Exception as e: placeholder_output = f"[ Placeholder generation failed: {e} ]" # Include error
        elif game_state['dialogue_active']: placeholder_output = "[Visuals suppressed during dialogue]"
        else: placeholder_output = "[Placeholders suppressed due to error]"

        # --- Update History ---
        # Player input for dialogue is added within handle_dialogue_turn's prompt prep
        # Assistant response for dialogue needs adding here if dialogue continues
        if game_state['dialogue_active'] and not stop_processing_flag:
            partner_id = game_state.get('dialogue_partner')
            if partner_id and content_llm_response_text:
                # Add assistant response to the *persistent* history
                character_manager.add_dialogue_entry(partner_id, {"speaker": partner_id, "utterance": content_llm_response_text})
                print(f"[DEBUG MAIN] Appended assistant utterance for {partner_id} to persistent dialogue history.")
                
        elif not game_state['dialogue_active']: # Update narrative history
             # GM Outcome message was already added before narrative call
            if content_llm_response_text: # Add assistant content response
                assistant_message = {"role": "assistant", "content": content_llm_response_text}
                if not conversation_history or conversation_history[-1] != assistant_message:
                    conversation_history.append(assistant_message)
                    print("[DEBUG MAIN] Appended assistant message to narrative history.")

        # --- Generate Adjacent Locations (if needed, AFTER state updates) ---
        # Only generate for Narrative mode AFTER the turn's logic is complete
        if not game_state['dialogue_active']:
             generation_ok = True # Assume ok unless generation fails
             try:
                 current_loc = game_state.get('location')
                 if current_loc:
                     # Check the return status - Uses the CORRECT method name
                     generation_ok = location_manager.ensure_location_generated(current_loc)
                     if not generation_ok:
                         print("[WARN Loop End] Location generation failed or produced invalid data.")
                         # Add feedback for the *next* turn
                         feedback_messages.append("[System: The surrounding areas seem indistinct or difficult to discern.]")
                 else:
                     print("[WARN Loop End] Cannot ensure location generation, current location is None.")
             except Exception as e:
                 print(f"[ERROR Loop End] Exception during ensure_location_generated call: {e}")
                 traceback.print_exc()
                 feedback_messages.append("[System: An error occurred while exploring the surroundings.]") # Feedback for next turn

        # --- Display Output to Player --- 
        # Call the dedicated display function to handle narrative, feedback, and visuals
        display_output(content_llm_response_text, placeholder_output, feedback_messages)
            
        # Debug mode: print current state (Keep this separate)
        if DEBUG_MODE: # Use the constant defined in config
            print("\nDEBUG - Current State:")
            print(f"Game State: {game_state}")
            print(f"Character Manager State: {character_manager.get_state()}")
            print(f"Location Manager State: {location_manager.get_state()}")
            
        # Clear feedback messages for next turn (Keep this separate)
        # feedback_messages = [] # This seems to be missing, should probably be here

        # --- Check Turn Limit ---
        if turn_count >= MAX_TURNS: print(f"\nReached turn limit ({MAX_TURNS})."); break

    print("\nThank you for playing Endless Novel v0.4!")

# --- Entry Point ---
if __name__ == "__main__":
    main()
