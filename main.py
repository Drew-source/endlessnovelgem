"""Endless Novel V0 - Main Game Execution Script"""

import os
import copy
import json
from dotenv import load_dotenv
import anthropic
import google.generativeai as genai

# Import configuration, utilities, and engine modules
from config import (MAX_TURNS, PROMPT_DIR, MAX_HISTORY_MESSAGES,
                  update_game_state_tool, start_dialogue_tool, end_dialogue_tool, create_character_tool, DEBUG_IGNORE_LOCATION,
                  exchange_item_tool, update_relationship_tool)
from utils import load_prompt_template, call_claude_api
from narrative import handle_narrative_turn, apply_tool_updates
from dialogue import handle_dialogue_turn, summarize_conversation
from visuals import call_gemini_api, construct_gemini_prompt
from character_manager import CharacterManager

# --- API Client Initialization --- #
def initialize_clients() -> tuple[anthropic.Anthropic | None, genai.GenerativeModel | None, str | None, str | None]:
    """Initializes and returns API clients and model names."""
    load_dotenv()

    # Claude Client
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model_name = os.getenv("ANTHROPIC_MODEL_NAME")
    claude_client = None
    if anthropic_api_key and anthropic_model_name:
        try:
            claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
            print("[INFO] Anthropic client initialized.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Anthropic client: {e}")
    else:
        if not anthropic_api_key: print("[ERROR] ANTHROPIC_API_KEY not found.")
        if not anthropic_model_name: print("[ERROR] ANTHROPIC_MODEL_NAME not found.")
        print("[ERROR] Claude API calls will fail.")

    # Gemini Client
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_model_name = os.getenv("GOOGLE_MODEL_NAME")
    gemini_client = None
    if google_api_key and google_model_name:
        try:
            genai.configure(api_key=google_api_key)
            gemini_client = genai.GenerativeModel(google_model_name)
            print(f"[INFO] Google AI client initialized for model: {google_model_name}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Google AI client: {e}")
    else:
        if not google_api_key: print("[ERROR] GOOGLE_API_KEY not found.")
        if not google_model_name: print("[ERROR] GOOGLE_MODEL_NAME not found.")
        print("[ERROR] Gemini API calls will fail.")

    return claude_client, gemini_client, anthropic_model_name, google_model_name

# --- Initial Game State --- #
# Defined here as it's the starting point for the main loop
INITIAL_GAME_STATE = {
    'player': {
        'name': 'Player',
        'inventory': ['a worn adventurer pack', 'flint and steel'],
    },
    'location': 'whispering_forest_edge', # Use an ID-like name
    'time_of_day': 'morning',
    'current_npcs': [],
    'companions': { # Renaming? Or keep as companions? Let's keep for now.
        'varnas_the_skeptic': {
            'name': 'Varnas the Skeptic',
            'archetype': 'companion', # Added
            'description': "A weathered man with distrustful eyes, clad in worn leather.", # Added
            'traits': ['skeptic', 'guarded', 'pragmatic'], # Added
            'location': 'whispering_forest_edge', # Explicit location
            # 'present' is removed - determined dynamically
            'inventory': ['worn leather armor', 'short sword', 'skeptical frown'],
            # Old relationship fields removed
            'memory': {
                'dialogue_history': []
            },
            'relationships': { # Added nested structure
                'player': {
                    'trust': 20, # Starting trust from config
                    'temporary_statuses': {}
                }
            }
        }
    },
    'narrative_flags': {},
    'current_chapter': 1,
    'current_objective': None,
    'dialogue_active': False,
    'dialogue_partner': None,
    # 'dialogue_target': None, # Removing this, partner is enough
    'last_player_action': None,
    'narrative_context_summary': "Sunlight filters through the ancient trees of the Whispering Forest. The air is cool and smells of damp earth and pine. Your companion, Varnas, shifts his weight beside you."
}

# --- Central Response Handling --- #
def handle_claude_response(
    initial_response: anthropic.types.Message | None,
    prompt_details: dict,
    game_state: dict,
    character_manager: CharacterManager,
    # Pass necessary clients/templates for tool processing
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    gemini_client: genai.GenerativeModel | None,
    gemini_model_name: str | None,
    prompt_templates: dict
) -> tuple[str, anthropic.types.Message | None, list | None, anthropic.types.Message | None, bool]:
    """Handles the response from Claude, including tool use.

    Orchestrates calls to apply_tool_updates or summarize_conversation as needed.
    Handles the second API call logic for update_game_state.

    Args:
        initial_response: The Message object from the first Claude call.
        prompt_details: Dict containing the original prompt components.
        game_state: The current game state dictionary (will be modified).
        character_manager: The CharacterManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model.
        gemini_client: Initialized Google AI client.
        gemini_model_name: Name of the Gemini model.
        prompt_templates: Dictionary of loaded prompt templates.

    Returns:
        The 5-tuple: (processed_text, initial_response_obj,
                     tool_results_content_sent, final_response_obj_after_tool,
                     stop_processing_flag)
    """
    processed_text = ""
    initial_response_obj = initial_response
    tool_results_content_sent = None
    final_response_obj_after_tool = None
    stop_processing_flag = False

    if not initial_response:
        processed_text = "[ERROR] Received no response object from Claude API call."
        return processed_text, initial_response_obj, tool_results_content_sent, final_response_obj_after_tool, stop_processing_flag

    # Extract initial text content
    if initial_response.content:
        for block in initial_response.content:
            if block.type == "text":
                processed_text += block.text + "\n"
    processed_text = processed_text.strip()

    # Handle Tool Use
    if initial_response.stop_reason == "tool_use":
        print("\n[INFO] Claude requested tool use.")
        tool_calls_found = False
        tool_results_content_list = [] # Results for the *second* API call (if needed)
        update_game_state_called = False # Flag to check if the state update tool was called

        for block in initial_response.content:
            if block.type != "tool_use": continue

            tool_calls_found = True
            tool_name = block.name
            tool_input = block.input
            tool_use_id = block.id
            print(f"[INFO] Handling tool use ID: {tool_use_id}, Name: {tool_name}")

            if tool_name == update_game_state_tool["name"]:
                update_game_state_called = True
                update_error = None
                try:
                    # Call the function from the narrative module
                    updates_applied, state_change_summary = apply_tool_updates(tool_input, game_state)
                    if updates_applied:
                        tool_result_text = f"Game state updated successfully: {state_change_summary}"
                    else:
                        tool_result_text = "State update requested, but no changes were applicable."
                except Exception as e:
                    print(f"[ERROR] Failed to apply tool updates for {tool_use_id}: {e}")
                    update_error = e
                    tool_result_text = f"Error applying game state update: {e}"

                # Prepare result for the second call
                tool_results_content_list.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_result_text,
                    "is_error": bool(update_error) # Explicitly mark errors if desired
                })

            elif tool_name == start_dialogue_tool["name"]:
                character_id = tool_input.get('character_id')
                is_present = False # Default
                if DEBUG_IGNORE_LOCATION:
                    print("  [DEBUG] Ignoring location check for start_dialogue due to DEBUG_IGNORE_LOCATION flag.")
                    # Assume present if character exists
                    is_present = bool(character_manager.get_character_data(character_id))
                else:
                    # Check presence using manager and current location
                    char_location = character_manager.get_location(character_id)
                    is_present = char_location == game_state.get('location')

                if character_id and character_manager.get_character_data(character_id):
                    if is_present:
                        if not game_state['dialogue_active']:
                            game_state['dialogue_active'] = True
                            game_state['dialogue_partner'] = character_id
                            partner_name = character_manager.get_name(character_id)
                            print(f"[INFO] Tool initiated dialogue with {partner_name} ({character_id}).")
                            processed_text += f"\n(You begin a conversation with {partner_name}.)"
                            stop_processing_flag = True
                        else:
                            current_partner_id = game_state.get('dialogue_partner')
                            partner_name = character_manager.get_name(current_partner_id) or 'someone'
                            print(f"[WARN] Tool requested start_dialogue, but dialogue already active with {partner_name}.")
                            processed_text += f"\n(You are already talking to {partner_name}.)"
                            stop_processing_flag = True # Still stop, invalid action
                    else:
                        partner_name = character_manager.get_name(character_id) or character_id
                        print(f"[WARN] Tool requested start_dialogue with {partner_name}, but they are not present at {game_state.get('location')}.")
                        processed_text += f"\n({partner_name} is not here to talk to.)"
                        stop_processing_flag = True # Still stop
                else:
                    print(f"[WARN] Tool requested start_dialogue with invalid/unknown character ID: {character_id}")
                    processed_text += f"\n(You look around, but don't see anyone named '{character_id}' to talk to.)"
                    stop_processing_flag = True # Still stop

            elif tool_name == end_dialogue_tool["name"]:
                if game_state['dialogue_active']:
                    partner_id = game_state.get('dialogue_partner')
                    partner_name = character_manager.get_name(partner_id) or 'Someone'
                    print(f"[INFO] Tool ended dialogue with {partner_name}.")

                    # Summarization logic
                    if partner_id:
                        partner_data = character_manager.get_character_data(partner_id)
                        if partner_data:
                            dialogue_history = partner_data.get('memory', {}).get('dialogue_history', [])
                            if dialogue_history:
                                summary = summarize_conversation(
                                    dialogue_history=dialogue_history,
                                    gemini_client=gemini_client,
                                    gemini_model_name=gemini_model_name,
                                    summarization_template=prompt_templates.get("summarization", "Error: Summarization template missing.")
                                )
                                current_summary = game_state.get('narrative_context_summary', '')
                                game_state['narrative_context_summary'] = current_summary + f"\n\n[Summary of conversation with {partner_name}: {summary}]"
                                print(f"[DEBUG] Appended summary to narrative context.")
                            else:
                                print(f"[DEBUG] No dialogue history found for {partner_name} to summarize.")
                        else:
                             print(f"[WARN] Could not retrieve data for partner {partner_id} during summarization.")

                    game_state['dialogue_active'] = False
                    game_state['dialogue_partner'] = None
                    processed_text += f"\n(The conversation with {partner_name} ends.)"
                    stop_processing_flag = True
                else:
                    print("[WARN] Tool requested end_dialogue, but dialogue was not active.")
                    processed_text += "\n(There was no conversation to end.)"
                    stop_processing_flag = True # Still stop

            elif tool_name == create_character_tool["name"]: # Added
                print(f"[INFO] Handling create_character tool: {tool_input}")
                archetype = tool_input.get('archetype')
                location = tool_input.get('location') or game_state.get('location') # Default to current location
                name_hint = tool_input.get('name_hint')

                if not archetype:
                     print(f"[ERROR] Tool create_character called without required 'archetype'.")
                     processed_text += "\n[SYSTEM ERROR: Character creation failed - missing archetype.]"
                elif not location:
                    print(f"[ERROR] Tool create_character called but could not determine location (not provided and player location unavailable). Input: {tool_input}")
                    processed_text += "\n[SYSTEM ERROR: Character creation failed - unknown location.]"
                else:
                    new_char_id = character_manager.generate_character(
                        archetype=archetype,
                        location=location,
                        name_hint=name_hint
                    )
                    if new_char_id:
                        new_char_name = character_manager.get_name(new_char_id)
                        print(f"[INFO] Successfully generated character: {new_char_name} ({new_char_id}) at {location}")
                        processed_text += f"\n(A new character arrives: {new_char_name})" # Simple feedback
                        # TODO: Provide this info back to Claude via tool_result?
                        # For now, just give player feedback and stop processing.
                    else:
                        print(f"[ERROR] Character generation failed for archetype '{archetype}'.")
                        processed_text += "\n[SYSTEM ERROR: Character creation failed.]"
                
                stop_processing_flag = True # Stop further processing this turn

            elif tool_name == exchange_item_tool["name"]: # Added
                print(f"[INFO] Handling exchange_item tool: {tool_input}")
                item = tool_input.get('item_name')
                giver = tool_input.get('giver_id')
                receiver = tool_input.get('receiver_id')
                quantity = tool_input.get('quantity', 1) # Use default from schema if needed

                # Basic validation
                if not all([item, giver, receiver]):
                     print(f"[ERROR] exchange_item tool called with missing parameters: {tool_input}")
                     processed_text += "\n[SYSTEM ERROR: Item exchange failed - missing info.]"
                else:
                    # --- Implement actual transfer logic --- 
                    print(f"[INFO] Processing transfer: {quantity} x '{item}' from {giver} to {receiver}")
                    transfer_possible = False
                    item_removed = False
                    item_added = False
                    
                    # Check if giver has the item
                    giver_has_item = False
                    if giver == 'player':
                        giver_has_item = item in game_state['player'].setdefault('inventory', [])
                    else:
                        giver_has_item = character_manager.has_item(giver, item)

                    if giver_has_item:
                        # Attempt removal from giver
                        if giver == 'player':
                            try:
                                game_state['player']['inventory'].remove(item)
                                print(f"  [State Update] Removed '{item}' from player inventory.")
                                item_removed = True
                            except ValueError:
                                print(f"[WARN] Item '{item}' not found in player inventory despite check.")
                                item_removed = False
                        else:
                            item_removed = character_manager.remove_item(giver, item)

                        # If removal succeeded, attempt adding to receiver
                        if item_removed:
                            if receiver == 'player':
                                game_state['player']['inventory'].append(item)
                                print(f"  [State Update] Added '{item}' to player inventory.")
                                item_added = True
                            else:
                                item_added = character_manager.add_item(receiver, item)
                            
                            # Check if add succeeded (it should if remove did)
                            if item_added:
                                transfer_possible = True
                            else:
                                # Rollback: Add item back to giver if receiver add failed (should be rare)
                                print(f"[ERROR] Failed to add item '{item}' to receiver '{receiver}' after removing from '{giver}'. Rolling back.")
                                if giver == 'player':
                                    game_state['player']['inventory'].append(item)
                                else:
                                     character_manager.add_item(giver, item) # Attempt rollback add
                                transfer_possible = False
                        else:
                            print(f"[DEBUG] Failed to remove item '{item}' from giver '{giver}'. Transfer aborted.")
                            transfer_possible = False
                    else:
                        print(f"[DEBUG] Giver '{giver}' does not have item '{item}'. Transfer aborted.")
                        transfer_possible = False

                    # Provide feedback based on outcome
                    if transfer_possible:
                        processed_text += f"\n(Item exchange successful: {item})"
                    else:
                        processed_text += f"\n(Item exchange failed for '{item}'. Check inventories or logic.)"
                    
                stop_processing_flag = True # Stop further processing this turn
            
            elif tool_name == update_relationship_tool["name"]: # Added
                print(f"[INFO] Handling update_relationship tool: {tool_input}")
                trait = tool_input.get('trait')
                change = tool_input.get('change')
                partner_id = game_state.get('dialogue_partner') # Target is always the current partner

                if not partner_id:
                     print(f"[ERROR] update_relationship tool called outside of active dialogue?")
                     processed_text += "\n[SYSTEM ERROR: Cannot update relationship - not in dialogue.]"
                elif not trait or change is None:
                    print(f"[ERROR] update_relationship tool called with missing parameters: {tool_input}")
                    processed_text += "\n[SYSTEM ERROR: Relationship update failed - missing info.]"
                else:
                     # --- TODO: Implement actual update logic using CharacterManager --- 
                    print(f"[TODO] Attempting relationship update for {partner_id}: {trait}={change}")
                    success = False # Placeholder
                    if trait == 'trust' and isinstance(change, int):
                         success = character_manager.update_trust(partner_id, change)
                    elif trait == 'anger' and isinstance(change, dict) and 'action' in change:
                         if change['action'] == 'set' and 'duration' in change:
                              success = character_manager.set_status(partner_id, 'anger', change['duration'])
                         elif change['action'] == 'remove':
                              success = character_manager.remove_status(partner_id, 'anger')
                    # Add other traits/statuses later

                    if success:
                         processed_text += f"\n(Relationship updated: {trait})" # Keep feedback minimal/internal?
                    else:
                         processed_text += f"\n(Relationship update failed for {trait}.)"

                stop_processing_flag = True # Stop further processing this turn

            else: # Unknown tool
                print(f"[WARNING] Claude requested unknown tool: {tool_name}")
                processed_text += f"\n[Internal Note: Claude requested unknown tool '{tool_name}'.]"
                # Decide if unknown tools should stop processing
                stop_processing_flag = True

            # If a dialogue tool signaled to stop, break from processing further tools in this response
            if stop_processing_flag:
                break

        # --- Second API Call Logic (Only for update_game_state) --- #
        if not stop_processing_flag and update_game_state_called and tool_results_content_list:
            tool_results_content_sent = tool_results_content_list # Save for return
            print("[INFO] Sending tool results back to Claude for final narrative...")

            # Construct messages for the second call (rebuild based on original prompt_details)
            if 'messages' in prompt_details and 'system' in prompt_details:
                 system_prompt = prompt_details.get('system', '')
                 original_messages_sent = prompt_details.get('messages', [])
            elif 'history' in prompt_details and 'user_prompt' in prompt_details:
                 system_prompt = prompt_details.get('system_prompt', '')
                 user_prompt = prompt_details.get('user_prompt', '')
                 history = prompt_details.get('history', [])
                 original_messages_sent = history + [{"role": "user", "content": user_prompt}]
            else:
                 print("[ERROR] Invalid prompt_details for second call construction in handle_claude_response.")
                 original_messages_sent = []
                 system_prompt = ""

            # Reconstruct assistant message from the *initial* response
            assistant_turn_content = []
            if initial_response.content:
                 assistant_turn_content = [block.model_dump(exclude_unset=True) for block in initial_response.content]
            assistant_turn_message = {"role": initial_response.role, "content": assistant_turn_content}

            messages_for_second_call = original_messages_sent + \
                                       [assistant_turn_message] + \
                                       [{ "role": "user", "content": tool_results_content_sent }]

            # Make the second API call (NO tools)
            second_call_prompt_details = {
                "system": system_prompt,
                "messages": messages_for_second_call
            }
            # Use the utility function
            second_response = call_claude_api(
                claude_client=claude_client,
                model_name=claude_model_name,
                prompt_details=second_call_prompt_details,
                tools=None
            )
            final_response_obj_after_tool = second_response

            if second_response:
                print("[DEBUG] Second Claude call successful.")
                # Extract text ONLY from the second response
                final_narrative_pieces = []
                if second_response.content:
                    for block in second_response.content:
                        if block.type == 'text':
                            final_narrative_pieces.append(block.text)
                processed_text = "\n".join(final_narrative_pieces).strip()
            else:
                 print(f"[ERROR] Error in second Claude call after tool use.")
                 processed_text += f"\n[ERROR] Failed to get final narrative after tool use."

        elif tool_calls_found and not stop_processing_flag:
             # This case means a tool *other than* update_game_state was called,
             # and it didn't set the stop_processing_flag. This shouldn't happen
             # with start/end dialogue as currently designed.
             print(f"[WARNING] Tool use stop reason, but no tool requiring a second call was processed, and stop_processing_flag is False.")
             processed_text += f"\n[Internal Note: Claude attempted an action that wasn't fully processed.]"

    # --- Final Text Check --- #
    if not processed_text.strip():
        if initial_response and initial_response.stop_reason != "tool_use":
            print(f"[WARNING] No narrative text found in non-tool-use Claude response. Stop Reason: {initial_response.stop_reason}. Content: {initial_response.content}")
            processed_text = f"[Internal Note: Claude responded but provided no narrative text. Stop Reason: {initial_response.stop_reason}]"
        elif not final_response_obj_after_tool and initial_response and initial_response.stop_reason == "tool_use" and not stop_processing_flag:
             # Tool use happened (update_game_state), second call failed/didn't happen, and no initial text
             processed_text = "[Internal Note: Action processed, but no final narrative generated.]"
        # If stop_processing_flag is True, processed_text might contain feedback like "(Conversation ends.)", which is okay.

    return processed_text.strip(), initial_response_obj, tool_results_content_sent, final_response_obj_after_tool, stop_processing_flag

# --- Output & Input --- #
def display_output(narrative_text: str, placeholder_text: str | None):
    """Displays the combined narrative and placeholders to the player."""
    print("\n" + "-"*40 + "\n")
    print(narrative_text.strip())
    if placeholder_text:
        print("\n--- Visuals & Sounds ---")
        print(placeholder_text.strip())
    print("\n" + "-"*40)

def get_player_input() -> str:
    """Gets the player's command from the console."""
    return input("\n> ").strip().lower()

# --- Main Game Loop --- #
def main():
    """Runs the main game loop."""
    claude_client, gemini_client, claude_model_name, gemini_model_name = initialize_clients()

    # Load prompt templates once at the start
    prompt_templates = {
        name: load_prompt_template(f"{name}.txt")
        for name in ["claude_system", "claude_turn_template",
                     "gemini_placeholder_template", "dialogue_system",
                     "summarization"]
    }

    game_state = copy.deepcopy(INITIAL_GAME_STATE)
    turn_count = 0
    conversation_history = []

    # --- Instantiate Character Manager --- #
    if 'companions' not in game_state: game_state['companions'] = {} # Ensure key exists
    character_manager = CharacterManager(game_state['companions'])

    print("Welcome to Endless Novel (v0 - Text Only)")

    # Initial Scene Description
    try:
        initial_gemini_prompt = construct_gemini_prompt(
            narrative_text="The adventure begins.",
            game_state=game_state,
            placeholder_template=prompt_templates.get("gemini_placeholder_template", "")
        )
        initial_placeholders = call_gemini_api(gemini_client, gemini_model_name, initial_gemini_prompt)
    except Exception as e:
        print(f"[WARN] Failed initial Gemini call: {e}")
        initial_placeholders = "[ Initial placeholders unavailable ]"
    display_output(game_state['narrative_context_summary'], initial_placeholders)

    # --- Game Loop --- #
    while True:
        turn_count += 1
        print(f"\n--- Turn {turn_count} --- ({'Dialogue Active' if game_state['dialogue_active'] else 'Narrative Mode'})")

        # 1. Get Player Input
        player_input_raw = get_player_input()
        if player_input_raw.lower() in ['quit', 'exit']:
            print("Goodbye!")
            break

        # Initialize turn variables
        processed_text = ""
        placeholder_output = None
        stop_processing_flag = False # Default to False

        # ----------------------------------------
        # --- DIALOGUE VS NARRATIVE ROUTING --- #
        # ----------------------------------------
        if game_state['dialogue_active']:
            # --- Handle Dialogue Turn --- #
            print("[DEBUG] Dialogue turn.")
            # 1. Call dialogue handler (constructs prompt, calls API)
            dialogue_response_obj, dialogue_prompt_details = handle_dialogue_turn(
                game_state=game_state,
                player_utterance=player_input_raw,
                character_manager=character_manager,
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                dialogue_template=prompt_templates.get("dialogue_system", "") # Pass template
            )

            # 2. Process the response (handles tools like end_dialogue)
            processed_text, initial_resp_obj_dlg, _, _, stop_processing_flag = handle_claude_response(
                initial_response=dialogue_response_obj,
                prompt_details=dialogue_prompt_details,
                game_state=game_state,
                character_manager=character_manager,
                claude_client=claude_client, # Pass clients/templates again for potential inner calls
                claude_model_name=claude_model_name,
                gemini_client=gemini_client,
                gemini_model_name=gemini_model_name,
                prompt_templates=prompt_templates
            )

            # 3. Update Character Dialogue History (if dialogue didn't end)
            if not stop_processing_flag:
                partner_id = game_state.get('dialogue_partner')
                assistant_utterance = ""
                # Extract utterance from the *initial* response object (before any tool use)
                if initial_resp_obj_dlg and initial_resp_obj_dlg.content:
                     for block in initial_resp_obj_dlg.content:
                         if block.type == 'text':
                             assistant_utterance = block.text.strip()
                             break
                
                if partner_id and partner_id in game_state.get('companions', {}) and assistant_utterance:
                    print(f"[DEBUG MAIN] Updating dialogue history for {partner_id} with assistant utterance.")
                    memory = game_state['companions'][partner_id].setdefault('memory', {'dialogue_history': []})
                    dialogue_history = memory.setdefault('dialogue_history', [])
                    # Avoid double-adding if somehow already added
                    if not dialogue_history or dialogue_history[-1].get("speaker") != partner_id:
                         dialogue_history.append({"speaker": partner_id, "utterance": assistant_utterance})
                elif partner_id:
                     print(f"[DEBUG MAIN] No assistant utterance found in dialogue response for {partner_id} to add to history.")

            placeholder_output = "[Visuals/Sounds suppressed during dialogue]"

        else:
            # --- Handle Narrative Turn --- #
            print("[DEBUG] Narrative turn.")
            # 1. Append User Message & Truncate History
            user_message = {"role": "user", "content": player_input_raw}
            conversation_history.append(user_message)
            if len(conversation_history) > MAX_HISTORY_MESSAGES:
                print(f"[DEBUG] Truncating history from {len(conversation_history)} to {MAX_HISTORY_MESSAGES} messages.")
                conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]

            # 2. Update State (Last Action)
            game_state['last_player_action'] = player_input_raw

            # 3. Call narrative handler (constructs prompt, calls API)
            initial_claude_response_obj, narrative_prompt_details = handle_narrative_turn(
                game_state=game_state,
                conversation_history=conversation_history,
                character_manager=character_manager,
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                prompt_templates=prompt_templates
            )

            # 4. Process the response (handles tools like start_dialogue, update_state)
            processed_text, initial_resp_obj_narr, tool_results_sent, final_resp_obj_narr, stop_processing_flag = handle_claude_response(
                initial_response=initial_claude_response_obj,
                prompt_details=narrative_prompt_details,
                game_state=game_state,
                character_manager=character_manager,
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                gemini_client=gemini_client,
                gemini_model_name=gemini_model_name,
                prompt_templates=prompt_templates
            )

            # 5. Update Narrative History (Crucial for Tool Use Compliance)
            if initial_resp_obj_narr:
                # Append Assistant's message (might contain tool_use)
                assistant_tool_use_message = {
                    "role": initial_resp_obj_narr.role,
                    "content": [block.model_dump(exclude_unset=True) for block in initial_resp_obj_narr.content if block]
                }
                conversation_history.append(assistant_tool_use_message)
                print(f"[DEBUG MAIN] Appended assistant message (stop_reason={initial_resp_obj_narr.stop_reason}) to history.")

                # If tool was used, append User's tool_result message(s)
                if initial_resp_obj_narr.stop_reason == "tool_use":
                    tool_results_for_history = []
                    for block in initial_resp_obj_narr.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_use_id = block.id
                            # Generate simple result confirmation for history
                            if tool_name == start_dialogue_tool["name"]: result_content = "Dialogue started successfully."
                            elif tool_name == end_dialogue_tool["name"]: result_content = "Dialogue ended successfully."
                            elif tool_name == update_game_state_tool["name"]:
                                result_content = "State update processed."
                                # Find the more detailed result if available
                                if tool_results_sent:
                                     for sent_result in tool_results_sent:
                                         if sent_result.get('tool_use_id') == tool_use_id:
                                             result_content = sent_result.get('content', result_content)
                                             break
                            else: result_content = f"Tool '{tool_name}' processed."
                            
                            tool_results_for_history.append({"type": "tool_result", "tool_use_id": tool_use_id, "content": result_content})
                    
                    if tool_results_for_history:
                        user_tool_result_message = {"role": "user", "content": tool_results_for_history}
                        conversation_history.append(user_tool_result_message)
                        print(f"[DEBUG MAIN] Appended user tool_result message(s) to history.")
                    else:
                         print(f"[WARN MAIN] Tool use detected, but no tool_results generated for history.")

                # Append Assistant's final response AFTER tool use (if applicable)
                if final_resp_obj_narr:
                    assistant_final_message = {
                        "role": final_resp_obj_narr.role,
                        "content": [block.model_dump(exclude_unset=True) for block in final_resp_obj_narr.content if block]
                    }
                    conversation_history.append(assistant_final_message)
                    print(f"[DEBUG MAIN] Appended final assistant message after tool use to history.")
            else:
                print("[WARN MAIN] No valid initial response object from Claude to add to history.")

            # 6. Generate Placeholders (if not stopped by dialogue transition)
            if not stop_processing_flag:
                print("\n>>> Asking Gemini for scene details... <<<")
                try:
                    gemini_prompt = construct_gemini_prompt(
                        narrative_text=processed_text,
                        game_state=game_state,
                        placeholder_template=prompt_templates.get("gemini_placeholder_template", "")
                    )
                    placeholder_output = call_gemini_api(gemini_client, gemini_model_name, gemini_prompt)
                except TypeError as e:
                    print(f"[ERROR] TypeError during Gemini prompt construction or call: {e}")
                    print("[WARN] Skipping placeholder generation for this turn.")
                    placeholder_output = "[ Placeholder generation error ]"
                except Exception as e:
                    print(f"[ERROR] Unexpected error during Gemini call: {e}")
                    placeholder_output = "[ Placeholder generation failed ]"
            else:
                 print("[DEBUG MAIN] stop_processing flag is True, skipping Gemini call.")
                 placeholder_output = "[Placeholders suppressed due to dialogue transition]"
        # --- END ROUTING --- #

        # 7. Display Output
        # Handle potential errors displayed in processed_text
        if processed_text.startswith("[ERROR]") or processed_text.startswith("[Internal"):
             print(f"\n[SYSTEM MESSAGE]\n{processed_text}")
             # Optionally display a generic error message to the player
             display_output("(An unexpected ripple disturbs the world...) ", None)
             # Potentially skip turn or attempt recovery?
             continue # Simple skip for now

        display_output(processed_text, placeholder_output)

        # 8. Check Turn Limit
        if turn_count >= MAX_TURNS:
            print(f"\nReached turn limit ({MAX_TURNS}).")
            break

    print("\nThank you for playing Endless Novel V0!")

# --- Entry Point --- #
if __name__ == "__main__":
    main()
