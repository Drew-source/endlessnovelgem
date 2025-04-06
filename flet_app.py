# flet_app.py
import flet as ft
import os
import copy
import json
from threading import Thread
from queue import Queue, Empty # Import Empty here

# Import configuration, utilities, and engine modules
# Assuming these modules don't have side effects on import
# and functions are self-contained enough to be called.
# Some internal print statements might still go to console.
from config import (MAX_TURNS, PROMPT_DIR, MAX_HISTORY_MESSAGES,
                  update_game_state_tool, start_dialogue_tool, end_dialogue_tool)
from utils import load_prompt_template, call_claude_api # Assuming call_claude_api exists and works
from narrative import handle_narrative_turn, apply_tool_updates
from dialogue import handle_dialogue_turn, summarize_conversation
from visuals import call_gemini_api, construct_gemini_prompt
from main import initialize_clients # Reuse initialization logic
# We need the initial state definition
from main import INITIAL_GAME_STATE
# We need the response handler
from main import handle_claude_response

# --- Flet App Main Function ---

def main(page: ft.Page):
    page.title = "Endless Novel V0 - Flet Edition"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.theme_mode = ft.ThemeMode.DARK # Or LIGHT

    # --- Initialization ---
    print("[FLET_APP] Initializing clients...")
    claude_client, gemini_client, claude_model_name, google_model_name = initialize_clients()
    if not claude_client or not gemini_client:
        # Display error in Flet UI instead of just printing
        page.add(ft.Text("[ERROR] Failed to initialize API clients. Check .env file and API keys.", color=ft.colors.RED))
        page.update()
        # Optionally return here or disable input
        # For now, let's allow it to continue but API calls will fail
        # return

    print("[FLET_APP] Loading prompts...")
    # Simplified prompt loading - assumes all templates are needed
    prompt_templates = {}
    try:
        for filename in os.listdir(PROMPT_DIR):
            if filename.endswith(".txt"):
                template_name = filename[:-4] # Remove .txt extension
                prompt_templates[template_name] = load_prompt_template(template_name)
                print(f"[FLET_APP] Loaded prompt: {template_name}")
    except FileNotFoundError:
         page.add(ft.Text(f"[ERROR] Prompt directory '{PROMPT_DIR}' not found.", color=ft.colors.RED))
         page.update()
         # return # Stop if prompts can't load
    except Exception as e:
        page.add(ft.Text(f"[ERROR] Failed to load prompts: {e}", color=ft.colors.RED))
        page.update()
        # return

    print("[FLET_APP] Setting up initial game state...")
    game_state = copy.deepcopy(INITIAL_GAME_STATE)
    conversation_history = [] # Narrative history
    # Dialogue history is stored within game_state['companions'][id]['memory']['dialogue_history']
    turn_count = 0

    # Queue for communication between game thread and UI thread
    result_queue = Queue()

    # --- UI Controls ---
    narrative_column = ft.Column(
        controls=[ft.Markdown(game_state.get('narrative_context_summary', "Welcome!"))], # Start with initial context
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        auto_scroll=True,
    )
    visuals_text = ft.Text("[Visuals and sounds will appear here]", italic=True, color=ft.Colors.SECONDARY)
    player_input = ft.TextField(
        label="What do you do?",
        hint_text="Type your action here...",
        expand=True,
        shift_enter=True, # Allows multiline input
        on_submit=lambda e: submit_turn(e), # Allow Enter to submit
    )
    submit_button = ft.ElevatedButton("Submit", on_click=lambda e: submit_turn(e))
    progress_ring = ft.ProgressRing(visible=False, width=16, height=16, stroke_width=2)
    status_bar = ft.Text("Ready.", italic=True, size=12)

    # --- Game Logic Thread Function ---
    def run_game_turn(input_text):
        nonlocal turn_count, game_state, conversation_history # Modify outer scope variables

        # --- Start Turn ---
        result_queue.put(("status", "Processing turn..."))
        turn_count += 1
        processed_text = ""
        placeholder_output = ""
        initial_resp_obj_dlg = None
        final_resp_obj_dlg = None
        initial_resp_obj_narr = None
        final_resp_obj_narr = None
        stop_processing_flag = False


        # Determine Turn Type (Dialogue or Narrative) - Copied from main.py logic
        if game_state.get('dialogue_active', False):
            # --- Handle Dialogue Turn ---
            result_queue.put(("status", "Handling dialogue..."))
            # 1. Call dialogue handler
            initial_claude_response_obj, dialogue_prompt_details = handle_dialogue_turn(
                 player_input=input_text,
                 game_state=game_state,
                 claude_client=claude_client,
                 claude_model_name=claude_model_name,
                 prompt_templates=prompt_templates,
                 max_history_messages=MAX_HISTORY_MESSAGES # Pass max history
            )
            initial_resp_obj_dlg = initial_claude_response_obj # Keep for history update

            # 2. Process response (handles end_dialogue tool, generates text)
            processed_text, _, tool_results_sent, final_resp_obj_dlg, stop_processing_flag = handle_claude_response(
                initial_response=initial_claude_response_obj,
                prompt_details=dialogue_prompt_details,
                game_state=game_state, # Modified by handle_claude_response
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                gemini_client=gemini_client, # Needed if a tool needs Gemini? Unlikely for dialogue.
                gemini_model_name=google_model_name,
                prompt_templates=prompt_templates
            )

            # 3. Update Character Dialogue History (if dialogue didn't end)
            # Logic copied from main.py - updates history within game_state
            if not stop_processing_flag:
                partner_id = game_state.get('dialogue_partner')
                assistant_utterance = ""
                if initial_resp_obj_dlg and initial_resp_obj_dlg.content:
                     for block in initial_resp_obj_dlg.content:
                         if block.type == 'text':
                             assistant_utterance = block.text.strip()
                             break
                if partner_id and partner_id in game_state.get('companions', {}) and assistant_utterance:
                    memory = game_state['companions'][partner_id].setdefault('memory', {'dialogue_history': []})
                    dialogue_history = memory.setdefault('dialogue_history', [])
                    if not dialogue_history or dialogue_history[-1].get("speaker") != partner_id:
                         dialogue_history.append({"speaker": partner_id, "utterance": assistant_utterance})

            placeholder_output = "[Visuals/Sounds suppressed during dialogue]" # As per original logic

        else:
            # --- Handle Narrative Turn --- #
            result_queue.put(("status", "Handling narrative..."))
            # 1. Append User Message & Truncate History
            user_message = {"role": "user", "content": input_text}
            conversation_history.append(user_message)
            if len(conversation_history) > MAX_HISTORY_MESSAGES:
                conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]

            # 2. Update State (Last Action)
            game_state['last_player_action'] = input_text

            # 3. Call narrative handler
            initial_claude_response_obj, narrative_prompt_details = handle_narrative_turn(
                game_state=game_state,
                conversation_history=conversation_history, # Pass current history
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                prompt_templates=prompt_templates
            )
            initial_resp_obj_narr = initial_claude_response_obj # Keep for history update

            # 4. Process the response (handles tools like start_dialogue, update_state)
            processed_text, _, tool_results_sent, final_resp_obj_narr, stop_processing_flag = handle_claude_response(
                initial_response=initial_claude_response_obj,
                prompt_details=narrative_prompt_details,
                game_state=game_state, # Modified by handle_claude_response
                claude_client=claude_client,
                claude_model_name=claude_model_name,
                gemini_client=gemini_client,
                gemini_model_name=google_model_name,
                prompt_templates=prompt_templates
            )

            # 5. Update Narrative History (Copied from main.py)
            # Appends assistant message, potential tool results, and final response to conversation_history
            if initial_resp_obj_narr:
                assistant_tool_use_message = {"role": initial_resp_obj_narr.role, "content": [block.model_dump(exclude_unset=True) for block in initial_resp_obj_narr.content if block]}
                conversation_history.append(assistant_tool_use_message)
                if initial_resp_obj_narr.stop_reason == "tool_use":
                    tool_results_for_history = []
                    for block in initial_resp_obj_narr.content:
                        if block.type == "tool_use":
                            tool_name = block.name; tool_use_id = block.id
                            if tool_name == start_dialogue_tool["name"]: result_content = "Dialogue started successfully."
                            elif tool_name == end_dialogue_tool["name"]: result_content = "Dialogue ended successfully."
                            elif tool_name == update_game_state_tool["name"]:
                                result_content = "State update processed."
                                if tool_results_sent:
                                     for sent_result in tool_results_sent:
                                         if sent_result.get('tool_use_id') == tool_use_id:
                                             result_content = sent_result.get('content', result_content); break
                            else: result_content = f"Tool '{tool_name}' processed."
                            tool_results_for_history.append({"type": "tool_result", "tool_use_id": tool_use_id, "content": result_content})
                    if tool_results_for_history:
                        user_tool_result_message = {"role": "user", "content": tool_results_for_history}
                        conversation_history.append(user_tool_result_message)
                if final_resp_obj_narr:
                    assistant_final_message = {"role": final_resp_obj_narr.role, "content": [block.model_dump(exclude_unset=True) for block in final_resp_obj_narr.content if block]}
                    conversation_history.append(assistant_final_message)

            # 6. Generate Placeholders (if not stopped by dialogue transition)
            if not stop_processing_flag:
                result_queue.put(("status", "Generating visuals..."))
                gemini_prompt = construct_gemini_prompt(
                    narrative_text=processed_text, # Use the text generated by Claude
                    game_state=game_state,
                    placeholder_template=prompt_templates.get("gemini_placeholder_template", "")
                 )
                placeholder_output = call_gemini_api(gemini_client, google_model_name, gemini_prompt)
            else:
                 placeholder_output = "[Placeholders suppressed due to dialogue transition]"


        # --- End Turn ---
        result_queue.put(("result", (processed_text, placeholder_output, turn_count)))


    # --- UI Update Function (runs in main thread) ---
    def update_ui():
        while True:
            try:
                message_type, data = result_queue.get(timeout=0.1) # Check queue briefly
                if message_type == "status":
                    status_bar.value = data
                    page.update()
                elif message_type == "result":
                    processed_text, placeholder_output, current_turn = data

                    # Append result to narrative display
                    narrative_column.controls.append(ft.Markdown(f"\n\n**Turn {current_turn}:**\n\n{processed_text}"))

                    # Update visuals text
                    visuals_text.value = placeholder_output if placeholder_output else "[No visual/sound details generated]"

                    # Check turn limit
                    if current_turn >= MAX_TURNS:
                         status_bar.value = f"Reached turn limit ({MAX_TURNS}). Game Over."
                         player_input.disabled = True
                         submit_button.disabled = True
                    else:
                        status_bar.value = f"Turn {current_turn}/{MAX_TURNS}. Ready for input."
                        player_input.disabled = False
                        submit_button.disabled = False
                        progress_ring.visible = False
                        player_input.focus() # Focus input field for next turn

                    page.update() # Update the whole page
                    # Make sure the narrative view scrolls down
                    page.scroll_to(key=narrative_column.key, duration=300)

            except Empty: # Specifically catch queue.Empty
                pass # Ignore timeout, this is expected behavior
            except Exception as e:
                # Log other potential errors
                print(f"[ERROR] UI Update loop error: {repr(e)}")

            # Check if thread is still running maybe? Or rely on disabling controls.


    # --- Event Handler for Submit Button/Enter Key ---
    def submit_turn(e):
        input_text = player_input.value.strip()
        if not input_text or player_input.disabled:
            return # Ignore empty input or when disabled

        # Clear input field
        player_input.value = ""
        # Disable input during processing
        player_input.disabled = True
        submit_button.disabled = True
        progress_ring.visible = True

        # Add player input to narrative display immediately for responsiveness
        narrative_column.controls.append(ft.Markdown(f"> {input_text}"))
        page.update() # Show the input text right away
        page.scroll_to(key=narrative_column.key, duration=300)

        # Start game logic in a separate thread
        thread = Thread(target=run_game_turn, args=(input_text,), daemon=True)
        thread.start()

    # --- Layout ---
    page.add(
        ft.Container(
            content=narrative_column,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=ft.border_radius.all(5),
            padding=10,
            expand=True, # Make narrative area fill available space
        ),
        ft.Container(
             content=visuals_text,
             padding=ft.padding.only(top=5, bottom=5)
        ),
        ft.Row(
            controls=[
                player_input,
                submit_button,
                progress_ring,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
         ft.Container(content=status_bar, padding=ft.padding.only(top=5))
    )

    # Start the UI update loop in a separate thread
    ui_updater_thread = Thread(target=update_ui, daemon=True)
    ui_updater_thread.start()

    page.update() # Initial page render
    player_input.focus() # Focus input field on start


# --- Run the Flet App ---
if __name__ == "__main__":
    # Make sure PROMPT_DIR is correct relative to where you run this
    # If PROMPT_DIR is relative in config.py, it needs to be relative
    # to the project root where you run `flet run`.
    # Consider making PROMPT_DIR an absolute path or resolving it here:
    # PROMPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), PROMPT_DIR))

    ft.app(target=main) # Use view=ft.AppView.WEB_BROWSER for web view