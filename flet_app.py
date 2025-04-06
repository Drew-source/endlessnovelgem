# flet_app.py
import flet as ft
import os
import copy
import json
import traceback
from threading import Thread
from queue import Queue, Empty

# Import configuration, utilities, and engine modules
from config import (MAX_TURNS, PROMPT_DIR, MAX_HISTORY_MESSAGES,
                  update_game_state_tool, start_dialogue_tool, end_dialogue_tool)
from utils import load_prompt_template, call_claude_api
from narrative import handle_narrative_turn, apply_tool_updates
from dialogue import handle_dialogue_turn, summarize_conversation
from visuals import call_gemini_api, construct_gemini_prompt
from main import initialize_clients, INITIAL_GAME_STATE, handle_claude_response

# --- Flet App Main Function ---

def main(page: ft.Page):
    page.title = "Endless Novel V0 - Flet Edition"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.theme_mode = ft.ThemeMode.DARK

    # --- Initialization ---
    print("[FLET_APP] Initializing clients...")
    claude_client, gemini_client, claude_model_name, google_model_name = initialize_clients()
    if not claude_client or not gemini_client:
        page.add(ft.Text("[ERROR] Failed to initialize API clients. Check .env file and API keys.", color=ft.colors.RED))
        page.update()

    print("[FLET_APP] Loading prompts...")
    # Load prompt templates correctly as expected by the original code
    prompt_templates = {
        name: load_prompt_template(f"{name}.txt")
        for name in ["claude_system", "claude_turn_template",
                     "gemini_placeholder_template", "dialogue_system",
                     "summarization"]
    }
    for name, template in prompt_templates.items():
        print(f"[FLET_APP] Loaded prompt: {name} ({len(template)} chars)")

    print("[FLET_APP] Setting up initial game state...")
    game_state = copy.deepcopy(INITIAL_GAME_STATE)
    conversation_history = []
    turn_count = 0

    # Queue for communication between game thread and UI thread
    result_queue = Queue()

    # --- UI Controls ---
    narrative_column = ft.Column(
        controls=[ft.Markdown(game_state.get('narrative_context_summary', "Welcome!"))],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
        auto_scroll=True,
        key="narrative_column",  # Add a key for scrolling
    )
    visuals_text = ft.Text("[Visuals and sounds will appear here]", italic=True, color=ft.Colors.GREY_400)
    player_input = ft.TextField(
        label="What do you do?",
        hint_text="Type your action here...",
        expand=True,
        shift_enter=True,
        on_submit=lambda e: submit_turn(e),
        border_color=ft.Colors.GREY_700,
        focused_border_color=ft.Colors.BLUE_500,
        cursor_color=ft.Colors.BLUE_500,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.GREY_900,
    )
    submit_button = ft.ElevatedButton(
        "Submit", 
        on_click=lambda e: submit_turn(e),
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_700,
            elevation=5,
        )
    )
    progress_ring = ft.ProgressRing(visible=False, width=16, height=16, stroke_width=2)
    status_bar = ft.Text("Ready.", italic=True, size=12)
    debug_text = ft.Text("", size=10, color=ft.Colors.RED_400, visible=False)

    # --- Game Logic Thread Function ---
    def run_game_turn(input_text):
        nonlocal turn_count, game_state, conversation_history

        try:
            # --- Start Turn ---
            result_queue.put(("status", "Processing turn..."))
            turn_count += 1
            processed_text = ""
            placeholder_output = ""
            stop_processing_flag = False

            # Determine Turn Type (Dialogue or Narrative)
            if game_state.get('dialogue_active', False):
                # --- Handle Dialogue Turn ---
                result_queue.put(("status", "Handling dialogue..."))
                # FIXED: Parameter name mismatch (player_utterance instead of player_input)
                initial_claude_response_obj, dialogue_prompt_details = handle_dialogue_turn(
                    game_state=game_state,
                    player_utterance=input_text,  # FIXED: correct parameter name
                    claude_client=claude_client,
                    claude_model_name=claude_model_name,
                    dialogue_template=prompt_templates.get("dialogue_system", "")  # FIXED: parameter name
                )

                # Process response (handles end_dialogue tool, generates text)
                processed_text, initial_resp_obj_dlg, tool_results_sent, final_resp_obj_dlg, stop_processing_flag = handle_claude_response(
                    initial_response=initial_claude_response_obj,
                    prompt_details=dialogue_prompt_details,
                    game_state=game_state,
                    claude_client=claude_client,
                    claude_model_name=claude_model_name,
                    gemini_client=gemini_client,
                    gemini_model_name=google_model_name,
                    prompt_templates=prompt_templates
                )

                # Update Character Dialogue History (if dialogue didn't end)
                if not stop_processing_flag:
                    partner_id = game_state.get('dialogue_partner')
                    assistant_utterance = ""
                    if initial_claude_response_obj and initial_claude_response_obj.content:
                        for block in initial_claude_response_obj.content:
                            if block.type == 'text':
                                assistant_utterance = block.text.strip()
                                break
                    
                    if partner_id and partner_id in game_state.get('companions', {}) and assistant_utterance:
                        memory = game_state['companions'][partner_id].setdefault('memory', {'dialogue_history': []})
                        dialogue_history = memory.setdefault('dialogue_history', [])
                        # Add player's utterance first
                        dialogue_history.append({"speaker": "player", "utterance": input_text})
                        # Then add NPC response
                        if not dialogue_history or dialogue_history[-1].get("speaker") != partner_id:
                            dialogue_history.append({"speaker": partner_id, "utterance": assistant_utterance})

                placeholder_output = "[Visuals/Sounds suppressed during dialogue]"

            else:
                # --- Handle Narrative Turn --- #
                result_queue.put(("status", "Handling narrative..."))
                # Append User Message & Truncate History
                user_message = {"role": "user", "content": input_text}
                conversation_history.append(user_message)
                if len(conversation_history) > MAX_HISTORY_MESSAGES:
                    conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]

                # Update State (Last Action)
                game_state['last_player_action'] = input_text

                # Call narrative handler
                initial_claude_response_obj, narrative_prompt_details = handle_narrative_turn(
                    game_state=game_state,
                    conversation_history=conversation_history,
                    claude_client=claude_client,
                    claude_model_name=claude_model_name,
                    prompt_templates=prompt_templates
                )

                # Process the response (handles tools like start_dialogue, update_state)
                processed_text, initial_resp_obj_narr, tool_results_sent, final_resp_obj_narr, stop_processing_flag = handle_claude_response(
                    initial_response=initial_claude_response_obj,
                    prompt_details=narrative_prompt_details,
                    game_state=game_state,
                    claude_client=claude_client,
                    claude_model_name=claude_model_name,
                    gemini_client=gemini_client,
                    gemini_model_name=google_model_name,
                    prompt_templates=prompt_templates
                )

                # Update Narrative History
                if initial_claude_response_obj:
                    # Append Assistant's message (might contain tool_use)
                    assistant_tool_use_message = {
                        "role": initial_claude_response_obj.role,
                        "content": [block.model_dump(exclude_unset=True) for block in initial_claude_response_obj.content if block]
                    }
                    conversation_history.append(assistant_tool_use_message)

                    # If tool was used, append User's tool_result message(s)
                    if initial_claude_response_obj.stop_reason == "tool_use":
                        tool_results_for_history = []
                        for block in initial_claude_response_obj.content:
                            if block.type == "tool_use":
                                tool_name = block.name
                                tool_use_id = block.id
                                # Generate simple result confirmation for history
                                if tool_name == start_dialogue_tool["name"]:
                                    result_content = "Dialogue started successfully."
                                elif tool_name == end_dialogue_tool["name"]:
                                    result_content = "Dialogue ended successfully."
                                elif tool_name == update_game_state_tool["name"]:
                                    result_content = "State update processed."
                                    # Find the more detailed result if available
                                    if tool_results_sent:
                                        for sent_result in tool_results_sent:
                                            if sent_result.get('tool_use_id') == tool_use_id:
                                                result_content = sent_result.get('content', result_content)
                                                break
                                else:
                                    result_content = f"Tool '{tool_name}' processed."
                                
                                tool_results_for_history.append({
                                    "type": "tool_result", 
                                    "tool_use_id": tool_use_id, 
                                    "content": result_content
                                })
                        
                        if tool_results_for_history:
                            user_tool_result_message = {"role": "user", "content": tool_results_for_history}
                            conversation_history.append(user_tool_result_message)

                    # Append Assistant's final response AFTER tool use (if applicable)
                    if final_resp_obj_narr:
                        assistant_final_message = {
                            "role": final_resp_obj_narr.role,
                            "content": [block.model_dump(exclude_unset=True) for block in final_resp_obj_narr.content if block]
                        }
                        conversation_history.append(assistant_final_message)

                # Generate Placeholders (if not stopped by dialogue transition)
                if not stop_processing_flag:
                    result_queue.put(("status", "Generating visuals..."))
                    gemini_prompt = construct_gemini_prompt(
                        narrative_text=processed_text,
                        game_state=game_state,
                        placeholder_template=prompt_templates.get("gemini_placeholder_template", "")
                    )
                    placeholder_output = call_gemini_api(gemini_client, google_model_name, gemini_prompt)
                else:
                    placeholder_output = "[Placeholders suppressed due to dialogue transition]"

            # --- End Turn ---
            result_queue.put(("result", (processed_text, placeholder_output, turn_count)))
        
        except Exception as e:
            # ADDED: Improved error handling with traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Game turn thread error: {e}\n{error_trace}")
            result_queue.put(("error", f"Error processing turn: {str(e)}"))
            result_queue.put(("debug", error_trace))
            # Still return some result to unblock the UI
            result_queue.put(("result", (f"An error occurred: {str(e)}", "[Error occurred]", turn_count)))

    # --- UI Update Function (runs in main thread) ---
    def update_ui():
        while True:
            try:
                message_type, data = result_queue.get(timeout=0.1)
                
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
                        player_input.focus()

                    page.update()
                    # Fix circular reference error by not scrolling to a control
                    page.scroll_to(key=narrative_column.key, duration=300)
                
                elif message_type == "error":
                    status_bar.value = "Error occurred. See details below."
                    narrative_column.controls.append(ft.Text(data, color=ft.Colors.RED_400))
                    player_input.disabled = False
                    submit_button.disabled = False
                    progress_ring.visible = False
                    page.update()
                
                elif message_type == "debug":
                    debug_text.value = data
                    debug_text.visible = True
                    page.update()

            except Empty:
                pass
            except Exception as e:
                print(f"[ERROR] UI Update loop error: {repr(e)}")
                # Try to report the error to the UI
                try:
                    status_bar.value = f"UI update error: {str(e)}"
                    page.update()
                except:
                    pass

    # --- Event Handler for Submit Button/Enter Key ---
    def submit_turn(e):
        input_text = player_input.value.strip()
        if not input_text or player_input.disabled:
            return

        # Clear input field
        player_input.value = ""
        # Disable input during processing
        player_input.disabled = True
        submit_button.disabled = True
        progress_ring.visible = True
        debug_text.visible = False  # Hide previous debug info

        # Add player input to narrative display with better styling
        user_input_container = ft.Container(
            content=ft.Text(
                input_text,
                color=ft.Colors.BLACK,
                weight=ft.FontWeight.W_500,
            ),
            padding=10,
            border_radius=8,
            bgcolor=ft.Colors.BLUE_300,  # Darker blue that works well with black text
            margin=ft.margin.only(top=10, bottom=10),
            width=600,
            alignment=ft.alignment.center_left,
        )
        narrative_column.controls.append(user_input_container)
        page.update()
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
            expand=True,
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
        ft.Container(content=status_bar, padding=ft.padding.only(top=5)),
        ft.Container(content=debug_text, padding=ft.padding.only(top=5), visible=False)
    )

    # Attempt to show initial scene description
    try:
        initial_gemini_prompt = construct_gemini_prompt(
            narrative_text="The adventure begins.",
            game_state=game_state,
            placeholder_template=prompt_templates.get("gemini_placeholder_template", "")
        )
        initial_placeholders = call_gemini_api(gemini_client, google_model_name, initial_gemini_prompt)
        visuals_text.value = initial_placeholders
    except Exception as e:
        print(f"[WARN] Failed initial Gemini call: {e}")
        visuals_text.value = "[ Initial placeholders unavailable ]"

    # Start the UI update loop in a separate thread
    ui_updater_thread = Thread(target=update_ui, daemon=True)
    ui_updater_thread.start()

    page.update()
    player_input.focus()


# --- Run the Flet App ---
if __name__ == "__main__":
    # Make sure PROMPT_DIR is accessible
    if not os.path.exists(PROMPT_DIR):
        print(f"[ERROR] Prompt directory not found: {PROMPT_DIR}")
        print(f"Working directory is: {os.getcwd()}")
    
    ft.app(target=main)