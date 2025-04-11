"""Dialogue Engine: Handles conversation flow and prompt construction."""
import anthropic
import google.generativeai as genai
import copy # Import copy
# Removed tool imports
from utils import call_claude_api
from visuals import call_gemini_api # Needed for summarize_conversation
from character_manager import CharacterManager # Import manager for type hint

# --- Dialogue History Formatting --- #
def format_dialogue_history_for_prompt(history: list, character_manager: CharacterManager) -> str:
    """Formats the dialogue history list into a string suitable for the prompt."""
    formatted_lines = []
    for entry in history:
        speaker = entry.get("speaker", "Unknown")
        utterance = entry.get("utterance", "...")
        if speaker == "player":
            speaker_label = "Player"
        elif speaker == "gamemaster": # Handle GM outcome message
            speaker_label = "System"
            utterance = entry.get("utterance", "(System note)") # Don't just show the raw outcome maybe?
        else:
            speaker_label = character_manager.get_name(speaker) or speaker
        formatted_lines.append(f"{speaker_label}: {utterance}")
    return "\n".join(formatted_lines)

# --- Dialogue Turn Handling --- #
def handle_dialogue_turn(
    game_state: dict,
    player_utterance: str,
    character_manager: CharacterManager, 
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    dialogue_template: str,
    outcome_message: str | None = None # Added argument
) -> tuple[anthropic.types.Message | None, dict]:
    """Prepares and initiates the LLM call for dialogue TEXT ONLY, incorporating GM outcome.

    Adds player utterance and GM outcome (if any) to history copy for prompt context,
    constructs prompt details, calls API, and returns the raw response object
    and the prompt details used.

    Args:
        game_state: The current game state dictionary.
        player_utterance: The raw input string from the player.
        character_manager: The CharacterManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model.
        dialogue_template: The loaded dialogue system prompt template.
        outcome_message: The resolved outcome message from the action resolver.

    Returns:
        A tuple containing:
        - The raw Anthropic Message object from the API call, or None on failure.
        - The prompt_details dictionary used for the API call.
    """
    partner_id = game_state.get('dialogue_partner')
    prompt_details_dialogue = {}
    response_obj = None

    if not partner_id: # Basic validation
        print("[ERROR] Dialogue active but no partner ID.")
        game_state['dialogue_active'] = False
        return None, prompt_details_dialogue

    companion_state = character_manager.get_character_data(partner_id)
    if not companion_state:
        print(f"[ERROR] No valid partner data for ID '{partner_id}'.")
        game_state['dialogue_active'] = False
        return None, prompt_details_dialogue

    print(f"[DEBUG] Preparing dialogue turn with {partner_id}")
    
    # --- History Management for Prompt --- #
    # Work on a COPY of the history for this turn's prompt context
    persistent_history = character_manager.get_dialogue_history(partner_id, ensure_list=True)
    history_for_prompt = copy.deepcopy(persistent_history)
    
    # Add player utterance
    history_for_prompt.append({"speaker": "player", "utterance": player_utterance})
    
    # Add GM outcome message if provided
    if outcome_message:
        print(f"[DEBUG] Injecting GM Outcome for prompt: {outcome_message}")
        history_for_prompt.append({"speaker": "gamemaster", "utterance": f"[Action Outcome: {outcome_message}]"})

    # 2. Prepare prompt details for LLM
    try:
        # --- Fetch & Format Context Data --- #
        character_name = companion_state.get('name', partner_id)
        trust_score = character_manager.get_trust(partner_id) or 0
        active_statuses_dict = character_manager.get_active_statuses(partner_id) or {}
        inventory_list = character_manager.get_inventory(partner_id) or []
        narrative_context_summary = game_state.get('narrative_context_summary', 'Recent events unclear.')
        follow_status = character_manager.get_follow_status(partner_id)

        if trust_score > 50: trust_level_description = "Very High"
        elif trust_score > 10: trust_level_description = "Positive"
        elif trust_score < -50: trust_level_description = "Very Low"
        elif trust_score < -10: trust_level_description = "Negative"
        else: trust_level_description = "Neutral"

        status_strings = [f"{s.capitalize()}({d.get('duration')} turns)" if d.get('duration') else s.capitalize() for s, d in active_statuses_dict.items()]
        active_statuses_str = ", ".join(status_strings) or "Normal"
        inventory_str = ", ".join(inventory_list) or "Nothing"
        follow_status_str = "Yes" if follow_status else "No"
        character_id_str = partner_id
        
        # Format the history *including* player utterance and GM outcome
        formatted_history_string = format_dialogue_history_for_prompt(history_for_prompt, character_manager)

        # --- System Prompt Construction --- #
        
        # Example: create a "tone_directive" that influences how edgy or hostile the character might be
        if trust_score < -20:
            tone_directive = "Your tone is suspicious, edgy, or even hostile. Don't be afraid to show conflict."
        elif trust_score > 50:
            tone_directive = "Your tone is warm and friendly, but you can still be bold or direct if the player challenges you."
        else:
            tone_directive = "You are neutral or mildly wary. You can become edgy or welcoming depending on the player's words."

        # Base system context
        system_context = f"You are {character_name}. Respond naturally."
        if "Error:" not in dialogue_template:
            try:
                 # Format the main template
                 formatted_template = dialogue_template.format(
                     character_name=character_name,
                     character_id=character_id_str,
                     trust_score=trust_score,
                     relation_to_player_summary=trust_level_description,
                     active_statuses=active_statuses_str,
                     character_inventory=inventory_str,
                     location=game_state.get('location', 'Unknown'),
                     time_of_day=game_state.get('time_of_day', 'Unknown'),
                     narrative_context=narrative_context_summary,
                     follow_status_str=follow_status_str,
                     dialogue_history=formatted_history_string, 
                     # player_utterance is now part of the formatted_history_string
                     # Remove player_utterance key if the prompt doesn't expect it separately anymore
                     # Let's assume the prompt was updated to just use dialogue_history
                     # player_utterance="" # Or remove key entirely
                 )
                 # Append the tone directive after the formatted template
                 system_context = f"{formatted_template}\n\n## Tone Directive:\n{tone_directive}"
            except KeyError as e:
                 print(f"[ERROR] Key error formatting dialogue template: {e}. Using fallback.")
                 # Append tone even to fallback?
                 system_context += f"\n\n## Tone Directive:\n{tone_directive}" # Append to fallback context too
            except Exception as e:
                 print(f"[ERROR] Failed formatting dialogue template: {e}. Using fallback.")
                 # Append tone even to fallback?
                 system_context += f"\n\n## Tone Directive:\n{tone_directive}" # Append to fallback context too
        else: # If template itself had error
             system_context += f"\n\n## Tone Directive:\n{tone_directive}" # Append to base context
        
        # --- Message History Construction (for API) --- #
        # Use the history_for_prompt which includes the latest player/GM messages
        messages_for_llm = []
        for entry in history_for_prompt: 
            speaker = entry.get("speaker")
            utterance = entry.get("utterance", "") 
            role = "user" if speaker == "player" or speaker == "gamemaster" else "assistant"
            # Prepend speaker/role for clarity in API history?
            # content_text = f"{speaker_label}: {utterance}" # Use the label from formatter? No, API expects clean text.
            content_block = [{"type": "text", "text": utterance}]
            messages_for_llm.append({"role": role, "content": content_block})
        
        # --- Prepare API call --- #
        prompt_details_dialogue = {
            "system": system_context, 
            "messages": messages_for_llm 
        }

        print(f"\n>>> Asking {character_name} for dialogue text (incorporating outcome)... <<<")
        
        # Call API - NO TOOLS passed to content generator
        response_obj = call_claude_api(
            claude_client=claude_client,
            model_name=claude_model_name,
            prompt_details=prompt_details_dialogue,
            tools=None
        )

    except Exception as e:
        print(f"[ERROR] Exception during dialogue turn prep/call: {e}")
        import traceback
        traceback.print_exc()
        return None, {}

    # Return the RAW response object and prompt details
    return response_obj, prompt_details_dialogue

# --- Dialogue Summarization --- #
def summarize_conversation(
    dialogue_history: list,
    character_manager: CharacterManager, # Added manager
    gemini_client: genai.GenerativeModel | None, # Pass client
    gemini_model_name: str | None, # Pass model name
    summarization_template: str # Pass template content
) -> str:
    """Summarizes a given dialogue history using the Gemini LLM.

    Args:
        dialogue_history: List of dialogue entries [{'speaker': ..., 'utterance': ...}].
        character_manager: The CharacterManager instance.
        gemini_client: Initialized Google AI client.
        gemini_model_name: Name of the Gemini model to use.
        summarization_template: The loaded content of the summarization prompt template.

    Returns:
        A concise summary string, or an error/fallback string if summarization fails.
    """
    if not dialogue_history:
        return "(No conversation took place.)" # Nothing to summarize
    if not gemini_client:
        print("[WARN] Gemini client not available for summarization.")
        return "(Conversation summary unavailable - Gemini client missing.)"
    if not gemini_model_name:
         print("[WARN] Gemini model name not provided for summarization.")
         return "(Conversation summary unavailable - Gemini model unknown.)"
    if "Error:" in summarization_template:
        print("[ERROR] Summarization prompt template failed to load.")
        return f"(Conversation summary unavailable due to template error: {summarization_template})"

    print("\n>>> Summarizing conversation... <<<")
    try:
        # Format history for the prompt
        history_string = format_dialogue_history_for_prompt(dialogue_history, character_manager) # Reuse helper
        
        # Format the passed template
        try:
            # Use .replace for simple template, or .format if using named placeholders
            # Assuming template uses {{dialogue_history}}
            prompt_text = summarization_template.replace("{{dialogue_history}}", history_string)
        except Exception as format_e:
            print(f"[ERROR] Failed to format summarization template: {format_e}")
            return f"(Conversation summary failed - template format error)"

        # Call Gemini API using the function from the visuals module
        summary = call_gemini_api(gemini_client, gemini_model_name, prompt_text)

        # Check if the API call itself returned an error string
        if summary.startswith("[") and summary.endswith("]"):
            print(f"[WARN] Gemini API call for summarization returned: {summary}")
            return f"(Conversation summary failed - {summary})"
        
        print(f"[DEBUG] Conversation summary generated: {summary}")
        return summary

    except Exception as e:
        print(f"[ERROR] Failed to summarize conversation: {e}")
        import traceback
        traceback.print_exc() # Uncomment for detailed debugging
        return "(Conversation summary failed due to unexpected error.)"
