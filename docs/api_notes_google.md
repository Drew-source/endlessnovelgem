# Google AI (Gemini) API Notes

This document contains key setup and usage information for the Google AI API (Gemini 2.5 Pro Experimental) relevant to the Endless Novel project.

## Installation

Use pip, preferably within a Python virtual environment:

```bash
pip install google-genai
# Or to upgrade: pip install -U google-genai
```

## API Key Setup

The SDK can read the API key from the environment variable `GOOGLE_API_KEY`, or it can be passed directly when initializing the client.

**Setting the Environment Variable (Recommended Methods):**
*   **macOS/Linux:** `export GOOGLE_API_KEY='your-api-key-here'`
*   **Windows (Persistent via Command Prompt):** `setx GOOGLE_API_KEY "your-api-key-here"` *(Requires restarting shell/IDE)*

We aim to load the key from the environment, potentially using `.env` and `python-dotenv`.

## Basic Usage (Client Approach)

The recommended way seems to be using the `genai.Client`. Below is the most basic example structure, often found in quickstart guides (omitting error handling for brevity):

```python
from google import genai
# import os <-- Removed as not needed for the minimal example shown

# --- Initialization (Requires API Key available) ---
# Option 1: Client might implicitly use GOOGLE_API_KEY env var (Verify)
# client = genai.Client()

# Option 2: Explicitly pass the key (Recommended if loading from .env)
# import os # <-- os needed for this option
# api_key = os.getenv("GOOGLE_API_KEY") 
# client = genai.Client(api_key=api_key)

# For this minimal example, we assume client is initialized correctly.
# Replace with appropriate initialization from above.
client = genai.Client(api_key="YOUR_GOOGLE_API_KEY_FOR_EXAMPLE") 

# --- Model Selection ---
model_name = "gemini-2.5-pro-exp-03-25"

# --- Generate Content Call ---
# prompt_text = "What is the airspeed velocity of an unladen swallow?"

# Basic call (no error handling shown here), using string literals for clarity
response = client.models.generate_content(
    model="gemini-2.5-pro-exp-03-25", 
    contents="What is the airspeed velocity of an unladen swallow?"
)

# --- Basic Response Access ---
# Assumes successful response with text content
print(response.text)

```

**Note:** This is a highly simplified example for demonstrating the core call structure ONLY.
For our project (`game_v0.py`), we **must**:
*   Load the API key securely from the environment (using `.env` and `python-dotenv`).
*   Use the model name `gemini-2.5-pro-exp-03-25`.
*   Pass the formatted prompt from `construct_gemini_prompt` to `contents`.
*   **Implement robust error handling (`try...except`)** for API calls.
*   **Implement proper response parsing**, checking for potential errors, empty responses, or safety blocks (`response.prompt_feedback`) before accessing `response.text`.

Always refer to the latest official Google AI Python SDK documentation for production-ready code patterns.

## Key Advanced Features (Based on User Research Doc)

### 1. Multi-turn Conversations (Chat)

*   **Mechanism:** Use `client.chats.create(model=...)` to start a chat session.
*   **Sending Messages:** Use `chat.send_message("...")` or `chat.send_message_stream("...")`.
*   **History:** The `chat` object automatically manages history. Access with `chat.get_history()`.
*   **Relevance:** Potentially simplifies managing dialogue context and narrative history compared to manually building summaries. Could replace `narrative_context_summary` and `dialogue_target` state elements if adopted.

```python
# Example Structure
chat = client.chats.create(model=model_name)
response1 = chat.send_message("First message")
response2 = chat.send_message("Second message, context aware")
# History is maintained within chat object
```

### 2. Configuration Parameters

*   **Mechanism:** Pass a `config=types.GenerateContentConfig(...)` object to `generate_content` or potentially `chats.create`.
*   **Key Parameters:**
    *   `temperature` (0.0-2.0): Controls randomness.
    *   `max_output_tokens`: Limits response length.
    *   `stopSequences`: Up to 5 strings that stop generation.
    *   `topP`, `topK`: Control token sampling probability.
*   **Relevance:** Essential for tuning model output quality and style.

```python
from google.genai import types

response = client.models.generate_content(
    model=model_name,
    contents=prompt_text,
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=1024
    )
)
```

### 3. System Instructions

*   **Mechanism:** Set via `system_instruction` within `types.GenerateContentConfig`.
*   **Purpose:** Provides persistent role/persona/context separate from user prompts.
*   **Relevance:** Aligns with our plan to use external system prompts (`prompts/claude_system.txt` equivalent for Gemini if needed).

```python
response = client.models.generate_content(
    model=model_name,
    contents="User prompt here",
    config=types.GenerateContentConfig(
        system_instruction="You are a helpful assistant focused on game design."
    )
)
```

### 4. Vision Capabilities (Future Potential)

*   Can process images (local, base64, multiple), video, PDFs.
*   Relevant for potential future versions (V1+) involving visual input/output.

### 5. Code Execution Tool (Potential Use)

*   Model can generate and run Python code.
*   Enabled via `tools` parameter in `GenerateContentConfig`.
*   Potential for complex logic, calculations, procedural generation later.

### 6. Function Calling / Tool Use (NEEDS FURTHER INVESTIGATION)

*   Mentioned in docs but not detailed in the provided text.
*   **HIGHLY RELEVANT:** This is likely the **preferred mechanism** for signaling structured state updates, potentially replacing our custom `<state_update>` JSON block.
*   **Action Item:** Need to research Google AI's specific function calling implementation. 