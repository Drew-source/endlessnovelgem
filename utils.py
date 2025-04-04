"""Utility functions for Endless Novel V0."""
import os
import anthropic # Required for Message type hint
from config import PROMPT_DIR, MAX_HISTORY_MESSAGES # Import history limit

# --- Prompt Loading Utility ---
def load_prompt_template(filename: str) -> str:
    """Loads a prompt template from the PROMPT_DIR."""
    filepath = os.path.join(PROMPT_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] Prompt file not found: {filepath}")
        # Return a fallback string or raise an error
        return f"Error: Prompt template '{filename}' not found."
    except Exception as e:
        print(f"[ERROR] Failed to load prompt file {filepath}: {e}")
        return f"Error loading prompt: {filename}"

# --- Core API Call Functions --- #
def call_claude_api(claude_client: anthropic.Anthropic | None,
                      model_name: str | None,
                      prompt_details: dict,
                      tools=None) -> anthropic.types.Message | None:
    """Calls the Claude API using the Messages endpoint.

    Handles system prompt, user message, and optional tools.
    Returns the raw Message object or None on failure.
    Accepts either a pre-constructed 'messages' list in prompt_details OR
    constructs messages from 'history' and 'user_prompt'.

    Args:
        claude_client: Initialized Anthropic client instance.
        model_name: Name of the Claude model to use.
        prompt_details: A dictionary containing prompt components.
                        Expected keys: 'system' and 'messages' OR
                        'system_prompt', 'user_prompt', and 'history'.
        tools: Optional list of tools to provide to the API.

    Returns:
        The Anthropic Message object containing the response, or None on failure.
    """
    if not claude_client:
        print("[ERROR] Anthropic client not initialized. Cannot call Claude API.")
        return None
    if not model_name:
        print("[ERROR] Anthropic model name not configured.")
        return None

    # Determine message construction method
    if 'messages' in prompt_details and 'system' in prompt_details:
        system_prompt = prompt_details.get('system', "")
        messages = prompt_details.get('messages', [])
        history_len_debug = len(messages)
        print(f"--- Calling Claude ({model_name}) for Dialogue (History: {history_len_debug} msgs) --- ")
    elif 'history' in prompt_details and 'user_prompt' in prompt_details:
        system_prompt = prompt_details.get('system_prompt', "")
        user_prompt = prompt_details.get('user_prompt', "")
        history = prompt_details.get('history', [])

        # Use MAX_HISTORY_MESSAGES from config for truncation
        # Note: This assumes MAX_HISTORY_MESSAGES is the total number of messages (turns)
        truncated_history = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history
        history_len_debug = len(truncated_history)
        if len(history) > len(truncated_history):
            print(f"[DEBUG] Truncating history from {len(history)} to {len(truncated_history)} messages internally for API call.")

        messages = truncated_history + [
            {"role": "user", "content": user_prompt}
        ]
        print(f"--- Calling Claude ({model_name}) for Narrative (Tools: {bool(tools)}, History: {history_len_debug} msgs) --- ")
    else:
        print("[ERROR] Invalid prompt_details structure for call_claude_api.")
        return None

    try:
        api_args = {
            "model": model_name,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            api_args["tools"] = tools

        response = claude_client.messages.create(**api_args)
        print("[DEBUG] Claude API call initiated (might result in tool use).")
        return response

    except anthropic.APIConnectionError as e:
        print(f"[ERROR] Anthropic API connection error: {e}")
    except anthropic.RateLimitError as e:
        print(f"[ERROR] Anthropic rate limit exceeded: {e}")
    except anthropic.APIStatusError as e:
        print(f"[ERROR] Anthropic API status error: {e.status_code} - {e.response}")
        try: 
            print(f"[ERROR] Response Body: {e.response.text}")
        except Exception: pass
    except Exception as e:
        print(f"[ERROR] Unexpected error calling Claude API: {e}")

    return None
