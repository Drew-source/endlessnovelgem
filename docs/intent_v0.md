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

## 3. LLM Roles & Strategy

*   **Narrator & Dialogue Generation:**
    *   **Model:** Claude 3.7 Sonnet (via Anthropic API)
    *   **Responsibility:** Generating the main story prose, descriptions of locations/events, character dialogue, and potentially player dialogue options. Careful prompting, including relevant game state, player action, and potentially summaries of recent events/dialogue, will be important for maintaining coherence. This may involve separate calls for narration versus active dialogue sequences.
*   **Technical Prompt Generation (Placeholders):**
    *   **Model:** Gemini 2.5 Pro (via Google AI API, referred to as "Gemini" or "the Assistant" in logs)
    *   **Responsibility:** Generating structured placeholder text describing the visual or audio content that would be generated in later versions. Takes input based on the current narrative context (provided by Claude's output) and the game state. Examples: `IMAGE: [Detailed description of a goblin chieftain's appearance]`, `SOUND: [Footsteps echoing in a large cavern]`, `MUSIC: [Tense, suspenseful track]`.

*   **Context Management:** Effective context management is critical for a coherent experience. The intended information flow is:
    *   Player Action -> State Update -> Claude Prompt (State + Action + History Summary) -> Claude Output (Narrative/Dialogue) -> Gemini Prompt (Claude Output + State) -> Gemini Output (Placeholders) -> Final Display.
    *   Summaries of dialogue or key narrative events should be stored (potentially in the `game_state` or a separate context object) and provided as context in subsequent Claude prompts.

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
    1.  The main loop will check if the API response indicates `tool_use` as the stop reason.
    2.  If so, it will extract the tool name (`update_game_state`) and the input data.
    3.  It will call a dedicated Python function (e.g., `handle_state_update_tool`) to apply these changes to the `game_state` dictionary.
    4.  It will then send a `tool_result` message back to the API, confirming the update was processed, allowing Claude to continue its narrative response.
*   **Benefits:** More structured, less error-prone than parsing JSON from free text, aligns with standard API features.
*   **Details:** Specific implementation details (tool definition schema, handling logic) will be refined during coding. Refer to `docs/api_notes_anthropic.md` and `docs/api_notes_google.md` for API specifics.

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