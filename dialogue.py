"""Dialogue Engine: Handles conversation flow, history, and summarization."""
import anthropic
import google.generativeai as genai
from config import end_dialogue_tool # Import the specific tool needed
from utils import call_claude_api
from visuals import call_gemini_api # Needed for summarize_conversation
from character_manager import CharacterManager # Import manager for type hint

# --- Dialogue History Formatting --- #
def format_dialogue_history_for_prompt(history: list) -> str:
    """Formats the dialogue history list into a string suitable for the prompt."""
    formatted_lines = []
    for entry in history:
        speaker = entry.get("speaker", "Unknown").replace("_", " ").title()
        utterance = entry.get("utterance", "...")
        formatted_lines.append(f"{speaker}: {utterance}")
    return "\n".join(formatted_lines)

# --- Dialogue Turn Handling --- #
def handle_dialogue_turn(
    game_state: dict,
    player_utterance: str,
    character_manager: CharacterManager, # Added manager
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    dialogue_template: str # Pass loaded template
) -> tuple[anthropic.types.Message | None, dict]:
    """Prepares and initiates the LLM call for a single dialogue turn.

    Adds player utterance to history, constructs prompt details, calls API
    with the end_dialogue tool enabled, and returns the raw response object
    and the prompt details used.

    Args:
        game_state: The current game state dictionary.
        player_utterance: The raw input string from the player.
        character_manager: The CharacterManager instance.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model.
        dialogue_template: The loaded dialogue system prompt template.

    Returns:
        A tuple containing:
        - The raw Anthropic Message object from the API call, or None on failure.
        - The prompt_details dictionary used for the API call.
    """
    partner_id = game_state.get('dialogue_partner')
    prompt_details_dialogue = {} # Initialize for return in case of early exit
    response_obj = None # Initialize response object

    if not partner_id:
        print("[ERROR] Dialogue active but no partner ID found in game_state.")
        game_state['dialogue_active'] = False
        return None, prompt_details_dialogue

    # Use manager to get character data
    companion_state = character_manager.get_character_data(partner_id)
    if not companion_state:
        print(f"[ERROR] Dialogue active but no valid partner data found for ID '{partner_id}' in handle_dialogue_turn.")
        game_state['dialogue_active'] = False # End dialogue on error
        return None, prompt_details_dialogue

    print(f"[DEBUG] Preparing dialogue turn with partner: {partner_id}")
    memory = companion_state.setdefault('memory', {'dialogue_history': []})
    dialogue_history = memory.setdefault('dialogue_history', [])

    # 1. Add player utterance to history
    dialogue_history.append({"speaker": "player", "utterance": player_utterance})

    # 2. Prepare prompt details for LLM
    try:
        # --- System Prompt Construction --- #
        # Use the passed template and format it
        if "Error:" in dialogue_template:
             print(f"[WARN] Using fallback dialogue system prompt due to template load error: {dialogue_template}")
             # Fallback prompt - similar to the old hardcoded one but less aggressive on ending
             system_context = f"You are {companion_state.get('name', partner_id)}. Respond naturally in character based on history. ONLY provide dialogue. Use end_dialogue tool ONLY for clear farewells."
        else:
            try:
                 system_context = dialogue_template.format(
                     character_name=companion_state.get('name', partner_id),
                     # Use manager to get relationship info - placeholder for now
                     # Need helper functions in manager (e.g., get_relationship_prompt_summary)
                     relation_to_player_summary=f"Trust: {character_manager.get_trust(partner_id) or 0}", # Basic trust for now
                     location=game_state.get('location', 'Unknown'),
                     time_of_day=game_state.get('time_of_day', 'Unknown')
                 )
            except KeyError as e:
                 print(f"[ERROR] Missing key in dialogue system template: {e}. Using fallback prompt.")
                 system_context = f"You are {companion_state.get('name', partner_id)}. Respond naturally. (Template key error: {e})"
            except Exception as e:
                 print(f"[ERROR] Failed to format dialogue system template: {e}. Using fallback prompt.")
                 system_context = f"You are {companion_state.get('name', partner_id)}. Respond naturally. (Template format error)"
        
        # --- Message History Construction --- #
        messages_for_llm = []
        for entry in dialogue_history:
            role = "user" if entry["speaker"] == "player" else "assistant"
            content_block = [{"type": "text", "text": entry["utterance"]}]
            messages_for_llm.append({"role": role, "content": content_block})
        
        # --- Prepare call --- #
        prompt_details_dialogue = {
            "system": system_context,
            "messages": messages_for_llm
        }

        print(f"\n>>> Asking {companion_state.get('name', partner_id)} for response... (End dialogue tool available) <<<")
        dialogue_tools = [end_dialogue_tool] # Use imported tool
        
        # Call API via utility function
        response_obj = call_claude_api(
            claude_client=claude_client,
            model_name=claude_model_name,
            prompt_details=prompt_details_dialogue,
            tools=dialogue_tools
        )

    except Exception as e:
        print(f"[ERROR] Exception during dialogue turn LLM call preparation or invocation: {e}")
        return None, {}

    # 3. Return the RAW response object and prompt details
    return response_obj, prompt_details_dialogue

# --- Dialogue Summarization --- #
def summarize_conversation(
    dialogue_history: list,
    gemini_client: genai.GenerativeModel | None, # Pass client
    gemini_model_name: str | None, # Pass model name
    summarization_template: str # Pass template content
) -> str:
    """Summarizes a given dialogue history using the Gemini LLM.

    Args:
        dialogue_history: List of dialogue entries [{'speaker': ..., 'utterance': ...}].
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
        history_string = format_dialogue_history_for_prompt(dialogue_history) # Reuse helper
        
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
        # import traceback
        # traceback.print_exc() # Uncomment for detailed debugging
        return "(Conversation summary failed due to unexpected error.)"
