# Endless Novel - Intent Document (Version 0)

## 1. Project Goal (Version 0: Text-Based Narrative Engine)

**Vision:** To create the foundational text-only engine for "Endless Novel," an AI-driven narrative game. This initial version is focused on generating a coherent and engaging story with dialogue, using placeholder text to represent visual and audio elements planned for future versions.

**Core Functionality:**
*   Process player text commands.
*   Maintain a simple game state.
*   Utilize Large Language Models (LLMs) to generate narrative descriptions and character dialogue based on player actions and game state.
*   Utilize a separate LLM to generate descriptive placeholder text for future visual/audio assets (e.g., `IMAGE: [description]`, `SOUND: [description]`).
*   Present the narrative, dialogue, and placeholders to the player via a simple command-line interface.

**Success Metric:** A user can play for a short session (e.g., 5-10 minutes), experiencing a logically consistent and somewhat engaging narrative flow driven by their choices, purely through text interaction.

## 2. Core Architecture (v0)

*   **Language:** Python 3.x
*   **Interface:** Command-Line Interface (CLI) using standard input/output.
*   **State Management:** Simple Python dictionary (`game_state`) holding key information (location, characters present, inventory snippets, relevant narrative flags).
*   **LLM Integration:** API calls to Anthropic (for Claude 3.7 Sonnet) and Google AI (for Gemini 2.5 Pro).
*   **Core Loop:**
    1.  Get player input (`get_player_input`).
    2.  Update game state based on input (`update_game_state`).
    3.  Call Claude 3.7 Sonnet for narration/dialogue based on state & input (`call_claude_api`). Providing context from previous turns and dialogue summaries in the prompt is important for coherence.
    4.  Call Gemini 2.5 Pro to generate descriptive placeholders based on Claude's output and/or game state (`call_gemini_api`).
    5.  Display combined output to the player (`display_output`).

## 3. LLM Roles & Strategy (REVISED)

This project utilizes two LLMs with distinct, specialized roles:

1.  **Anthropic Claude 3.7 Sonnet (The Storyteller & Director):**
    *   **Primary Function:** Drives the core narrative, generates character dialogue, reacts to player actions, manages plot progression, and maintains the overall tone and consistency of the story.
    *   **Interaction with State:** Claude actively influences the game state. When the narrative dictates a change to the game's mechanics (e.g., finding an item, changing location, character relationship shifts, status effects), Claude will use the **`update_game_state` Tool** (see Section 5) to send a structured request to the Python game loop, directing it to modify the `game_state` dictionary accordingly.
    *   **Input:** Receives the current `game_state` context, conversation history (if applicable), system prompt defining its role, and the last player action.
    *   **Output:** Generates narrative text, dialogue, and potentially `tool_use` requests for state updates.

2.  **Google AI Gemini (The World Detailer):**
    *   **Primary Function:** Generates specific, descriptive text *on demand* when requested by the Python game loop. This typically involves descriptions of locations, items, characters, or other elements based on the current game state.
    *   **Interaction with State:** Gemini *reads* relevant parts of the `game_state` provided in its prompt by the game loop but does *not* directly modify the state or use tools to request state changes. Its role is purely generative based on the context it's given.
    *   **Input:** Receives specific identifiers (e.g., location ID, item ID), tags, or relevant snippets from the `game_state` provided by the Python game loop.
    *   **Output:** Generates descriptive text (e.g., a room description, item flavor text).

**Coordination Strategy:**

*   **No Direct AI-to-AI Communication:** Claude and Gemini will **not** communicate directly. All interaction and information flow is mediated by the Python game loop (`game_v0.py`) and the central `game_state` dictionary.
*   **Game Loop as Orchestrator:** The game loop:
    1.  Provides Claude with the necessary context.
    2.  Receives Claude's narrative output and potential tool requests.
    3.  Handles tool requests, updating the `game_state`.
    4.  Determines if descriptive detail is needed based on the updated state or player actions (e.g., entering a new room, examining an item).
    5.  If needed, sends a request to Gemini with the relevant state information.
    6.  Receives Gemini's description and presents it to the player alongside Claude's narrative.
*   **Prompt Engineering is Key:** The distinct roles, styles, and capabilities of each LLM are defined and controlled through carefully crafted system prompts and instructions managed within the Python code and prompt files.

**V0 Context Management & Future Enhancements:**
*   **Current Approach (V0):** Basic conversation history is maintained by passing a list of the most recent user and assistant messages (using simple truncation based on message count) back to the Claude API on each turn.
*   **Limitations:** Simple truncation can lead to loss of important long-term context, potentially causing inconsistencies or forgotten details in longer play sessions.
*   **Future Work:** For improved long-term memory and coherence, future versions should explore more sophisticated context management techniques, such as:
    *   **LLM-based Summarization:** Periodically summarizing older parts of the conversation history and feeding the summary along with recent turns.
    *   **Retrieval-Augmented Generation (RAG):** Storing conversation history or key facts in a searchable database (e.g., vector store) and retrieving relevant context to inject into the prompt dynamically.

## 4. State Management (Final V0 Structure)

The `game_state` dictionary is the central repository for explicitly tracked game information. It's designed to be minimal for V0, relying on the narrative LLM (Claude) to infer details where possible and signal necessary changes. State updates (beyond `last_player_action`) should primarily occur based on parsing structured data received from Claude's API responses.

The planned structure is:
```python
game_state = {
    # Player Character
    'player': {
        'name': 'Player', # Default, potential for customization later
        'inventory': [], # List[str] of item names
    },

    # World State
    'location': 'start_area_id', # String identifier for the current location
    'time_of_day': 'morning', # String (e.g., 'morning', 'afternoon', 'evening', 'night')
    'current_npcs': [], # List[str] of non-companion NPC IDs/names present

    # Companions (Core Feature)
    'companions': {
        # Dictionary mapping unique companion ID (str) to their state dictionary.
        # Example:
        # 'varnas_the_skeptic': {
        #    'name': 'Varnas the Skeptic',       # String: Full display name
        #    'present': True,                 # Boolean: Is physically with the party?
        #    'inventory': [],             # List[str]: Notable items
        #    'relation_to_player_score': 0.5, # Float: 0.0 (Hate) to 1.0 (Love)
        #    'relation_to_player_summary': "", # String: Brief description
        #    'relations_to_others': {}        # Dict[str, float]: Scores towards other companion IDs
        # }
    },

    # Narrative / Quest Progression
    'narrative_flags': {}, # Dict[str, Any]: Key plot points, knowledge, world states
    'current_chapter': 1, # Int: Tracks broad story progression
    'current_objective': None, # String | None: Optional high-level goal text

    # Interaction / LLM Context
    'dialogue_target': None, # String | None: ID of NPC or Companion currently in dialogue
    'last_player_action': None, # String | None: Raw input from the player for the current turn
    'narrative_context_summary': "" # String: Rolling summary of recent events for LLM context
}
```

Key principles:
*   Keep explicit state minimal.
*   Use clear identifiers (location IDs, companion IDs).
*   Rely on `narrative_flags` for tracking specific event outcomes or knowledge.
*   Define a clear mechanism for Claude to signal required state changes (See Section TBD - State Update Mechanism).

## 5. LLM State Update Mechanism (REVISED: Tool Use)

Initial exploration considered parsing custom JSON blocks from the LLM response. However, based on API documentation review, the preferred and more robust method is to use the **Tool Use / Function Calling** capabilities offered by both Anthropic (Claude) and Google AI (Gemini) APIs.

*   **Approach:** Define a specific tool (e.g., `update_game_state`) that the narrative LLM (Claude) can invoke.
*   **Tool Definition:** This tool will be defined with:
    *   A clear `name`.
    *   A `description` explaining its purpose (updating game state based on narrative events).
    *   An `input_schema` (likely JSON schema) specifying the structure of the state changes (location, inventory add/remove, flag set/delete, companion updates, etc.).
*   **Invocation:** When Claude determines a state update is needed, it will generate a request to use the `update_game_state` tool, providing the necessary update data structured according to the `input_schema`.
*   **Handling in `game_v0.py`:**
    1.  The main loop calls `call_claude_api` (which includes the tool definition).
    2.  The response is processed by a new function, `handle_claude_response`.
    3.  If this function detects `stop_reason == 'tool_use'`, it extracts the `update_game_state` tool input.
    4.  It calls a dedicated function, `apply_tool_updates`, to modify the `game_state` dictionary based on the tool input schema.
    5.  It then constructs and sends a `tool_result` message back to the API via a second call to `claude_client.messages.create` (without the `tools` parameter) to get the final narrative.
    6.  If the initial stop reason was not `tool_use`, `handle_claude_response` simply extracts the narrative text.
*   **Implementation Status:** The functions `handle_claude_response` and `apply_tool_updates` have been implemented in `game_v0.py` as of YYYY-MM-DD (Assistant's current timestamp). The old `parse_and_apply_state_updates` function has been removed.
*   **Benefits:** More structured, less error-prone than parsing JSON from free text, aligns with standard API features.
*   **Details:** Specific implementation details (tool definition schema, handling logic) are now present in `game_v0.py`. Refer also to `docs/api_notes_anthropic.md` for API specifics.

## 6. API Integration Notes

*   API keys for Anthropic and Google AI will need to be secured and managed appropriately (e.g., environment variables, config file - specific method TBD).
*   Robust error handling for API calls (e.g., handling timeouts, rate limits, content filtering errors) should be implemented.
*   Careful design of prompt structures is recommended to maximize desired output quality and minimize ambiguity. This is expected to be an iterative process.

## 7. Development Practices & Collaboration

To support smooth development and effective AI-human collaboration:

*   **Recommended Debugging Approach: In-File Debugging:** When possible, using temporary print statements, commented-out code blocks, or temporary functions within the main `.py` files is often the clearest approach.
*   **Using Temporary Test Scripts (`test_*.py`):**
    *   If a separate test script is needed to isolate complex logic, it's requested that its creation be logged in `docs/development_log.md`, noting the file tested and the specific logic being isolated.
    *   The objective after successful testing is to integrate the working logic back into the main file(s) and then remove the temporary test script to keep the codebase clean.
    *   This integration and removal should then be prioritized as the next task in the development log.
    *   Leaving temporary test scripts unintegrated can introduce technical debt over time.
*   **Proactive Context Gathering (AI):** To ensure shared understanding, it's helpful if the assisting AI (Gemini) mentions the files reviewed (`read_file`) or listed (`list_dir`) before proposing code edits, especially for non-trivial changes.
*   **Explicit Human Assistance Requests (AI -> Human):**
    *   **Purpose:** Formal mechanism for the AI assistant (Gemini) to request specific actions, information, or decisions from the human collaborator when encountering tasks outside its current capabilities (e.g., API access, subjective judgment, real-world actions, ambiguous instructions).
    *   **Invocation:** The AI will clearly state `**REQUEST FOR HUMAN ASSISTANCE:**` followed by:
        *   A precise description of the task/information needed.
        *   The context/reason why it is needed.
        *   Relevant information the AI already possesses.
        *   (Optional) What the AI plans to do once the request is fulfilled.
    *   **Tracking:** These requests should ideally be noted in the `docs/development_log.md` for visibility.

## 8. Glossary & Naming Conventions

*(This section will be populated as we define core components)*

*   **`game_state`:** (dict) The primary dictionary holding the current state of the game world and player. Please use this exact name for consistency.
*   **`player_input`:** (str) The raw text command entered by the player. Please use this exact name for consistency.
*   **`narrative_context`:** (TBD - str or dict) Information passed between turns or calls to maintain story coherence (e.g., summaries, dialogue state).
*   ... (Add more as they arise)

## 9. Development Notes & Open Questions

*(Running log of decisions, ideas, and things to figure out)*

*   Need to finalize the precise structure for passing context (summaries, dialogue state) between LLM calls.
*   How to handle player choice generation (e.g., dialogue options)? Does Claude generate them?
*   Initial prompt design for Claude (narration) needs drafting.
*   API key management strategy.
*   Error handling details for API calls. 