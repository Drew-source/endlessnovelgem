"""Visual/Audio engine using Google Gemini API for placeholder generation."""
import google.generativeai as genai
# from google.api_core import retry # Consider adding retry

# --- Core API Call --- #

def call_gemini_api(gemini_client: genai.GenerativeModel | None,
                      model_name: str | None, # Pass model name for logging
                      prompt: str) -> str:
    """Calls the Gemini API to generate descriptive placeholders.

    Args:
        gemini_client: Initialized Google AI GenerativeModel instance.
        model_name: Name of the Gemini model being used.
        prompt: The prompt string for generation.

    Returns:
        The generated text string, or an error/placeholder string on failure.
    """
    if not gemini_client:
        print("[ERROR] Gemini client not initialized. Cannot call Gemini API.")
        return "[ Gemini API call skipped - client not initialized ]"
    if not model_name:
        print("[ERROR] Gemini model name not configured.")
        return "[ Gemini API call skipped - model name missing ]"

    print(f"--- Calling Gemini ({model_name}) --- ")
    print(f"[DEBUG] Gemini prompt length: {len(prompt)} chars.")

    try:
        # TODO: Consider adding specific retry settings for Gemini
        # @retry.Retry(predicate=retry.if_transient_error)
        response = gemini_client.generate_content(prompt)

        if response.text:
            print("[DEBUG] Gemini API call successful.")
            return response.text
        else:
            finish_reason = "Unknown"
            safety_ratings = "Unknown"
            try:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "No candidates"
                safety_ratings = response.candidates[0].safety_ratings if response.candidates else "No candidates"
            except (IndexError, AttributeError):
                pass # Handle potential issues accessing candidate info
            print(f"[WARNING] Gemini response finished but contains no text. Finish reason: {finish_reason}, Safety: {safety_ratings}")
            return f"[ Gemini generated no text - Reason: {finish_reason} ]"

    except Exception as e:
        print(f"[ERROR] Unexpected error calling Gemini API: {e}")
        return f"[ ERROR calling Gemini: {e} ]"

# --- Prompt Construction --- #

def construct_gemini_prompt(narrative_text: str,
                              game_state: dict,
                              placeholder_template: str) -> str:
    """Constructs the Gemini prompt using a template.

    Args:
        narrative_text: The narrative text from Claude.
        game_state: The current game state dictionary.
        placeholder_template: The loaded prompt template string.

    Returns:
        The formatted prompt string.
    """
    if "Error:" in placeholder_template:
        print(f"[WARN] Using fallback Gemini prompt due to template load error: {placeholder_template}")
        return f"Describe the visuals and sounds for this scene: {narrative_text}"

    context = {
        'narrative_text': narrative_text,
        'player_location': game_state.get('location', 'an unknown place')
        # Add other state info if the template requires it
    }

    try:
        return placeholder_template.format(**context)
    except KeyError as e:
        print(f"[ERROR] Missing key in Gemini placeholder template: {e}. Template: \n{placeholder_template}")
        # Fallback prompt if formatting fails
        return f"Describe the visuals and sounds for this scene (template error): {narrative_text}"
    except Exception as e:
        print(f"[ERROR] Failed to format Gemini prompt template: {e}")
        return f"Describe the visuals and sounds for this scene (formatting error): {narrative_text}"
