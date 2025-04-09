"""Dialogue Engine: Handles conversation flow, history, and summarization."""
import anthropic
import google.generativeai as genai
from config import end_dialogue_tool # Import the specific tool needed
from utils import call_claude_api
from visuals import call_gemini_api # Needed for summarize_conversation

# --- Dialogue History Formatting --- #

# Add this function after the imports in dialogue.py
def construct_dialogue_prompt(game_state: dict,
                            player_utterance: str,
                            dialogue_template: str) -> dict:
    """Constructs the dialogue prompt for Claude.
    
    Args:
        game_state: The current game state dictionary.
        player_utterance: The player's dialogue utterance.
        dialogue_template: The dialogue system prompt template.
        
    Returns:
        A dictionary with prompt components.
    """
    # Extract basic dialogue information
    partner_id = game_state.get('dialogue_partner', '')
    if not partner_id or partner_id not in game_state.get('companions', {}):
        print(f"[ERROR] Invalid dialogue partner ID: {partner_id}")
        return {"system": "", "messages": []}
    
    # Get partner information
    partner = game_state['companions'][partner_id]
    partner_name = partner.get('name', partner_id)
    
    # Get dialogue history if available
    dialogue_history = partner.get('memory', {}).get('dialogue_history', [])
    previous_exchanges = []
    
    # Format dialogue history
    for entry in dialogue_history[-5:]:  # Last 5 exchanges
        if entry.get('speaker') == 'player':
            previous_exchanges.append(f"Player: {entry.get('utterance', '')}")
        else:
            previous_exchanges.append(f"{partner_name}: {entry.get('utterance', '')}")
    
    previous_exchanges_text = "\n".join(previous_exchanges) if previous_exchanges else "No previous dialogue."
    
    # Extract universe settings
    universe_settings = game_state.get('settings', {}).get('universe', {})
    background_settings = game_state.get('settings', {}).get('background', {})
    
    # Prepare context for dialogue
    context = {
        'player_name': game_state.get('player', {}).get('name', 'Player'),
        'partner_name': partner_name,
        'partner_id': partner_id,
        'location': game_state.get('location', 'an unknown place'),
        'time_of_day': game_state.get('time_of_day', 'daytime'),
        'previous_dialogue': previous_exchanges_text,
        'player_utterance': player_utterance,
        'relationship_score': partner.get('relation_to_player_score', 0.5),
        'relationship_summary': partner.get('relation_to_player_summary', 'Neutral'),
        # Add universe context
        'universe_type': universe_settings.get('type', 'fantasy'),
        'universe_description': universe_settings.get('description', 'A medieval fantasy realm'),
        'universe_preset': universe_settings.get('preset', 'Medieval Fantasy'),
        'background_mood': background_settings.get('mood', 'epic')
    }
    
    try:
        # Format system prompt with context
        system_prompt = dialogue_template.format(**context)
    except KeyError as e:
        print(f"[ERROR] Missing key in dialogue template: {e}")
        system_prompt = f"Error: Dialogue prompt construction failed. Missing key: {e}"
    except Exception as e:
        print(f"[ERROR] Failed to format dialogue template: {e}")
        system_prompt = "Error: Dialogue prompt construction failed."
    
    # Construct the messages
    messages = [{"role": "user", "content": player_utterance}]
    
    return {
        "system": system_prompt,
        "messages": messages
    }

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

    if not partner_id or partner_id not in game_state['companions']:
        print("[ERROR] Dialogue active but no valid partner found in handle_dialogue_turn.")
        game_state['dialogue_active'] = False # End dialogue on error
        return None, prompt_details_dialogue

    print(f"[DEBUG] Preparing dialogue turn with partner: {partner_id}")
    companion_state = game_state['companions'][partner_id]
    memory = companion_state.setdefault('memory', {'dialogue_history': []})
    dialogue_history = memory.setdefault('dialogue_history', [])

    # 1. Add player utterance to history
    dialogue_history.append({"speaker": "player", "utterance": player_utterance})

    # 2. Prepare prompt details for LLM
  # 2. Prepare prompt details for LLM
    try:
        # Use the new construct_dialogue_prompt function
        prompt_details_dialogue = construct_dialogue_prompt(
            game_state=game_state,
            player_utterance=player_utterance,
            dialogue_template=dialogue_template
        )
        
        # If we got back an empty prompt (error condition), handle it
        if not prompt_details_dialogue.get("system"):
            print("[ERROR] Failed to construct dialogue prompt. Using fallback.")
            prompt_details_dialogue = {
                "system": f"You are {companion_state.get('name', partner_id)}. Respond naturally in character. Use end_dialogue tool ONLY for clear farewells.",
                "messages": [{"role": "user", "content": player_utterance}]
            }
        
        # --- Message History Construction for proper history --- #
        # The construct_dialogue_prompt function doesn't handle this part well, so we need to set it up
        messages_for_llm = []
        for entry in dialogue_history:
            role = "user" if entry["speaker"] == "player" else "assistant"
            content_block = [{"type": "text", "text": entry["utterance"]}]
            messages_for_llm.append({"role": role, "content": content_block})
        
        # Update the messages in prompt_details
        prompt_details_dialogue["messages"] = messages_for_llm

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
