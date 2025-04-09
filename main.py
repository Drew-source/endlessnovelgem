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
from config import (MAX_TURNS, PROMPT_DIR, MAX_HISTORY_MESSAGES, DEBUG_IGNORE_LOCATION)
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
                # ... (validation [char exists, present, not already in dialogue] and application) ...
                char_id = params.get('character_id')
                if not char_id: feedback_messages.append("(Who to talk to?)")
                else:
                    is_present = location_manager.is_character_present(char_id, game_state.get('location'))
                    char_exists = character_manager.get_character_data(char_id)
                    if char_exists and is_present:
                        if not game_state['dialogue_active']:
                            game_state['dialogue_active'] = True; game_state['dialogue_partner'] = char_id
                            name = character_manager.get_name(char_id); feedback_messages.append(f"(Conversation started with {name}.)"); stop_processing_flag = True
                        else: name = character_manager.get_name(game_state['dialogue_partner']); feedback_messages.append(f"(Already talking to {name}.)"); stop_processing_flag = True
                    elif char_exists: feedback_messages.append(f"({character_manager.get_name(char_id)} is not here.)"); stop_processing_flag = True
                    else: feedback_messages.append(f"(Unknown character: {char_id})" ); stop_processing_flag = True
                    
            elif request_name == "create_character":
                # ... (validation [archetype exists, location valid] and application) ...
                arch = params.get('archetype')
                loc = params.get('location') or game_state.get('location')
                hint = params.get('name_hint')
                if not arch: feedback_messages.append("[SYS ERR: Create char missing archetype]")
                elif not loc or not location_manager.is_valid_location(loc): feedback_messages.append(f"[SYS ERR: Create char invalid location: {loc}]")
                else:
                    new_id = character_manager.generate_character(arch, loc, hint)
                    if new_id: name = character_manager.get_name(new_id); feedback_messages.append(f"({name} appears.)"); location_manager.update_current_npcs()
                    else: feedback_messages.append("[SYS ERR: Character generation failed.]")
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
                # ... (validation [item exists, giver has it, receiver valid] and application) ...
                item = params.get('item_name'); giver = params.get('giver_id'); receiver = params.get('receiver_id')
                if not all([item, giver, receiver]): feedback_messages.append("[SYS ERR: Exchange item missing params]")
                elif giver == receiver: feedback_messages.append("(Cannot exchange with self.)")
                elif game_state.get('dialogue_partner') not in [giver, receiver] and 'player' not in [giver, receiver]: feedback_messages.append("(Can only exchange with dialogue partner.)")
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
                            else: # Rollback
                                if giver == 'player': game_state['player']['inventory'].append(item)
                                else: character_manager.add_item(giver, item)
                                feedback_messages.append(f"(Exchange failed: Could not add {item}.)")
                        else: feedback_messages.append(f"(Exchange failed: Could not remove {item}.)")
                    else: feedback_messages.append(f"(Exchange failed: {giver} does not have {item}.)")

            elif request_name == "update_relationship":
                # ... (validation [trait valid, change valid, partner correct] and application) ...
                trait = params.get('trait'); change = params.get('change'); char_id = params.get('character_id')
                partner_id = game_state.get('dialogue_partner')
                if not game_state['dialogue_active'] or char_id != partner_id: feedback_messages.append("[SYS ERR: Update relationship invalid context]")
                elif trait not in ['trust', 'anger']: feedback_messages.append(f"[SYS ERR: Invalid trait: {trait}]")
                elif change is None: feedback_messages.append("[SYS ERR: Update relationship missing change]")
                else:
                    success = False; feedback = ""
                    if trait == 'trust' and isinstance(change, int):
                         success = character_manager.update_trust(partner_id, change); feedback = f"Trust changed by {change}."
                    elif trait == 'anger' and isinstance(change, dict) and 'action' in change:
                         action = change.get('action'); duration = int(change.get('duration', 1))
                         if action == 'set': success = character_manager.set_status(partner_id, 'anger', duration); feedback = f"Anger set for {duration} turns."
                         elif action == 'remove': success = character_manager.remove_status(partner_id, 'anger'); feedback = "Anger removed."
                         else: feedback = f"Invalid anger action: {action}"
                    if success: feedback_messages.append(f"({character_manager.get_name(partner_id)}: {feedback})")
                    elif not feedback: feedback_messages.append(f"(Update {trait} failed: invalid params.)")
                    else: feedback_messages.append(f"(Update {trait} failed.)")

            elif request_name == "set_follow_status":
                # ... (validation [partner correct, value boolean, status different] and application) ...
                char_id = params.get('character_id'); following = params.get('following')
                partner_id = game_state.get('dialogue_partner')
                if not game_state['dialogue_active'] or char_id != partner_id: feedback_messages.append("[SYS ERR: Set follow invalid context]")
                elif following is None or not isinstance(following, bool): feedback_messages.append("[SYS ERR: Set follow invalid value]")
                else:
                    current = character_manager.get_follow_status(partner_id)
                    name = character_manager.get_name(partner_id)
                    if current == following: feedback_messages.append(f"({name} is already {'following' if following else 'not following'}.)")
                    elif current is None: feedback_messages.append(f"(Cannot get follow status for {name}.)")
                    else:
                        success = character_manager.set_follow_status(partner_id, following)
                        if success: feedback_messages.append(f"({name} is {'now following' if following else 'no longer following'}.)")
                        else: feedback_messages.append(f"(Failed to set follow status for {name}.)")
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
    """Runs the main game loop using the GM Assessor + Action Resolver architecture."""
    claude_client, gemini_client, claude_model_name, gemini_model_name = initialize_clients()

    # Load prompt templates
    prompt_templates = {}
    required_prompts = ["claude_system", "claude_turn_template",
                        "gemini_placeholder_template", "dialogue_system",
                        "summarization", "gamemaster_system"] # Use gamemaster prompt
    for name in required_prompts:
        template_content = load_prompt_template(f"{name}.txt")
        prompt_templates[name] = template_content
        if "Error:" in template_content:
             print(f"[FATAL] Failed to load critical prompt template: {name}.txt. Exiting.")
             return

    game_state = copy.deepcopy(INITIAL_GAME_STATE)
    turn_count = 0
    conversation_history = [] # Narrative history

    # Instantiate Managers
    character_manager = CharacterManager(game_state['companions'])
    location_manager = LocationManager(game_state, character_manager)

    print("Welcome to Endless Novel (v0.4 - GM Assessor Architecture)")

    # Initial Scene
    try:
        initial_text = game_state['narrative_context_summary']
        initial_gemini_prompt = construct_gemini_prompt(initial_text, game_state, prompt_templates.get("gemini_placeholder_template"))
        initial_placeholders = call_gemini_api(gemini_client, gemini_model_name, initial_gemini_prompt)
    except Exception as e:
        print(f"[WARN] Failed initial Gemini call: {e}")
        initial_placeholders = "[ Initial placeholders unavailable ]"
    display_output(initial_text, initial_placeholders)

    # --- Game Loop --- #
    while True:
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
        suggested_state_updates = []
        action_succeeded = True # Default to success unless a roll fails

        # --- Gamemaster Assessment Call ---
        gm_assessment = None
        try:
            gm_assessment = get_gamemaster_assessment(
                player_input_raw, game_state, character_manager,
                claude_client, claude_model_name, 
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
        suggested_state_updates = gm_assessment.get("suggested_state_updates", [])

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
                    claude_model_name=claude_model_name,
                    dialogue_template=prompt_templates.get("dialogue_system"),
                    outcome_message=outcome_message # Pass resolved outcome
                )
                # Logic for manual prompt construction removed from here.

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
                    claude_client, claude_model_name, prompt_templates
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
            suggested_state_updates = [] # Ensure state updates are skipped

        # --- Apply State Updates (Suggested by GM, validated here) ---
        if suggested_state_updates:
            try:
                stop_processing_flag, tool_feedback = apply_state_updates(
                     suggested_state_updates, game_state, character_manager, location_manager,
                     prompt_templates, gemini_client, gemini_model_name, 
                     action_succeeded # Pass success flag
                )
                feedback_messages.extend(tool_feedback)
            except Exception as update_exec_e:
                print(f"[ERROR] Exception applying state updates: {update_exec_e}")
                traceback.print_exc()
                feedback_messages.append(f"[SYS ERR: State update application failed: {update_exec_e}]")
                stop_processing_flag = True 
        else:
            print("[INFO] Gamemaster suggested no state updates needed.")
            # stop_processing_flag should be False unless set by GM impossibility/error
            if not any("[SYS ERR" in msg for msg in feedback_messages) and odds_str != "Impossible":
                 stop_processing_flag = False

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

        # --- Generate Placeholders ---
        if not stop_processing_flag and not game_state['dialogue_active']:
            try:
                gemini_prompt = construct_gemini_prompt(content_llm_response_text, game_state, prompt_templates.get("gemini_placeholder_template"))
                placeholder_output = call_gemini_api(gemini_client, gemini_model_name, gemini_prompt)
            except Exception as e: placeholder_output = "[ Placeholder generation failed ]"
        elif game_state['dialogue_active']: placeholder_output = "[Visuals suppressed]"
        else: placeholder_output = "[Placeholders suppressed]"

        # --- Display Output ---
        display_output(content_llm_response_text, placeholder_output, feedback_messages)

        # --- Check Turn Limit ---
        if turn_count >= MAX_TURNS: print(f"\nReached turn limit ({MAX_TURNS})."); break

    print("\nThank you for playing Endless Novel v0.4!")

# --- Entry Point ---
if __name__ == "__main__":
    main()
