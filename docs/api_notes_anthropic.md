# Anthropic (Claude) API Notes

This document contains key setup and usage information for the Anthropic API (Claude 3.7 Sonnet) relevant to the Endless Novel project.

## Installation

Use pip, preferably within a Python virtual environment:

```bash
python -m venv claude-env # Create environment (standard name from docs)
# Activate environment:
# - macOS/Linux: source claude-env/bin/activate
# - Windows:     claude-env\Scripts\activate
pip install anthropic
```

## API Key Setup

The Python SDK defaults to reading the API key from the environment variable `ANTHROPIC_API_KEY`.

**Setting the Environment Variable (Recommended Methods):**
*   **macOS/Linux (Current Session & potentially profile scripts):**
    ```bash
    export ANTHROPIC_API_KEY='your-api-key-here'
    ```
*   **Windows (Persistent via Command Prompt):**
    ```bash
    setx ANTHROPIC_API_KEY "your-api-key-here"
    ```
    *(Note: Requires restarting the shell/IDE after first use for the variable to be available)*

Alternatively, the key can be passed directly when initializing the client (less recommended for security/portability):
```python
import anthropic
client = anthropic.Anthropic(api_key="YOUR_ANTHROPIC_API_KEY")
```
For this project, we aim to load the key from the environment, potentially using a `.env` file and the `python-dotenv` library for convenience during development.

## Basic Usage (Messages API)

The primary interaction uses the `messages.create` method. Below is a basic example from the Anthropic documentation for reference:

```python
import anthropic

# Assumes ANTHROPIC_API_KEY is set in the environment
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-3-7-sonnet-latest", # Correct model ID from .env file
    max_tokens=1000,
    temperature=1,
    system="You are a world-class poet. Respond only with short poems.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Why is the ocean salty?"
                }
            ]
        }
    ]
)
# Accessing the response content might require indexing, e.g., message.content[0].text
# Refer to current Anthropic docs for exact response structure.
print(message.content) 
```

**Note:** For our project (`game_v0.py`), we will adapt this structure:
*   The `model` is `claude-3-7-sonnet-latest`.
*   The `system` prompt will be loaded from `prompts/claude_system.txt`.
*   The `messages` list will contain our complex, formatted prompt from `construct_claude_prompt`.
*   We will add error handling (`try...except`).
*   We will parse the response structure correctly to extract the narrative text.

Refer to the latest official Anthropic Python SDK documentation for the most accurate details.

## Key Advanced Features (Based on User Research Doc)

### 1. Multi-turn Conversations (Messages API)

*   **Mechanism:** The Messages API is inherently designed for multi-turn conversations. Pass the entire conversation history (alternating `user` and `assistant` roles) in the `messages` list parameter on each call.
*   **Example:** `messages=[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, {"role": "user", "content": "..."}]`
*   **Relevance:** Standard way to maintain context for Claude.

### 2. System Prompt

*   **Mechanism:** Use the top-level `system` parameter when calling `client.messages.create`.
*   **Relevance:** Standard way to set the model's role/persona.

### 3. Tool Use / Function Calling (HIGHLY RELEVANT)

*   **Mechanism:** Define available tools (functions the model can ask your code to run) using the `tools` parameter in `client.messages.create`. Each tool needs a `name`, `description`, and `input_schema` (JSON schema).
*   **Invocation:** When Claude decides to use a tool based on the conversation, the API response will have `stop_reason: "tool_use"` and the `content` list will contain `tool_use` blocks with an `id`, `name`, and JSON `input` matching your schema.
*   **Handling:** Your code must:
    1.  Detect the `tool_use` stop reason and extract the `tool_use` blocks.
    2.  Execute your corresponding Python function based on the tool `name` and `input`.
    3.  Send a **new** message back to the API with `role: "user"` and a `content` block of type `tool_result`, including the original `tool_use_id` and the result of your function call.
*   **Relevance:** This is the **preferred method** for handling LLM-driven game state updates. We will define an `update_game_state` tool for Claude to call with necessary changes.

```python
# Conceptual Example (Tool Definition - passed in 'tools' parameter)
tool_def = {
    "name": "update_game_state",
    "description": "Updates the game state based on narrative events. Use this to change location, inventory, flags, relationships etc.",
    "input_schema": { # Define schema for updates (e.g., using JSON schema format)
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "New location ID"},
            "inventory_add": {"type": "array", "items": {"type": "string"}},
            # ... other state elements based on game_state ...
        },
        "required": [] # Specify required fields if any
    }
}

# Conceptual Example (Handling response if Claude uses the tool)
# if response.stop_reason == "tool_use":
#    for block in response.content:
#        if block.type == "tool_use" and block.name == "update_game_state":
#            tool_input = block.input # This is a dict matching the schema
#            tool_use_id = block.id
#            # --- CALL OUR PYTHON FUNCTION TO APPLY UPDATES ---
#            apply_updates_from_tool(tool_input, game_state) 
#            tool_result_content = "Game state updated successfully."
#            # --- SEND RESULT BACK TO CLAUDE ---
#            client.messages.create(
#                model=model_name,
#                max_tokens=...,
#                messages=existing_messages + [
#                   response.message, # Include Claude's turn that requested the tool
#                   {"role": "user", "content": [
#                       {"type": "tool_result", "tool_use_id": tool_use_id, "content": tool_result_content}
#                   ]}
#                ]
#                # ... other params ...
#            )
```

### 4. Streaming

*   **Mechanism:** Use `client.messages.stream(...)` or set `stream: true` in raw API call.
*   **Handling:** Requires processing server-sent events (SSE) like `message_start`, `content_block_delta` (which can be `text_delta` or `input_json_delta` for tool use), `message_stop` etc.
*   **Relevance:** Useful for improving perceived responsiveness later.

### 5. Configuration Parameters

*   **Mechanism:** Pass directly to `client.messages.create`.
*   **Key Parameters:** `max_tokens`, `temperature` (0.0-1.0), `stop_sequences`, `top_k`, `top_p`.
*   **Relevance:** Tuning output quality.

### 6. Vision Capabilities (Future Potential)

*   Can process base64 images within the `messages` content list.
*   Relevant for V1+.

### 7. Other Features

*   **Extended Thinking:** Shows reasoning steps (less relevant for game).
*   **Token Counting API:** Can count tokens before sending (useful for context limits). 