# Endless Novel V0: Dialogue Engine Summary

**Date:** [Date - Placeholder]

## 1. Overview

This document summarizes the architecture, components, and workflow of the dialogue system implemented in `endlessnovelgem/game_v0.py`. The primary goal of this system is to enable seamless transitions between narrative gameplay and direct, stateful conversations with companion characters, ensuring that conversation history influences interactions and the game state accurately reflects dialogue initiation and conclusion.

The system leverages the Anthropic Claude 3.7 Sonnet model via its Messages API, specifically utilizing its **Tool Use** capabilities for managing dialogue state transitions.

## 2. Core Architecture & Concepts

The dialogue system operates based on these core principles:

*   **State Machine:** The main game loop (`main` function) acts as a simple state machine, primarily driven by the `game_state['dialogue_active']` boolean flag. This flag determines whether player input should be processed as a narrative action or a dialogue utterance.
*   **LLM-Driven Transitions:** Entering and exiting dialogue mode is primarily handled by the LLM (Claude) calling specific **Tools** (`start_dialogue`, `end_dialogue`) based on narrative context or conversational cues.
*   **Separate Contexts:** Two distinct conversation histories are maintained:
    *   `conversation_history`: Stores the main narrative interaction history (player actions, narrative descriptions, tool calls/results originating from narrative turns). Used as context for Claude during narrative turns.
    *   `game_state['companions'][id]['memory']['dialogue_history']`: Stores the specific back-and-forth utterances between the player and an individual companion. Used as context for Claude during dialogue turns with that companion.
*   **Centralized Response Processing:** A single function (`handle_claude_response`) is responsible for interpreting the raw response from the Claude API, regardless of whether the call originated from a narrative or dialogue turn. This function handles text extraction, tool detection, tool execution logic (updating game state), and preparing the final output for the player.
*   **Tool Use Compliance:** The system ensures strict adherence to the Anthropic API's requirement that a `tool_use` block in an assistant message must be followed immediately by a `tool_result` block in a user message within the *same* conversation history. This is crucial for the main `conversation_history`.

## 3. Key Components & Functionality

*   **Game State (`game_state` dictionary):**
    *   `dialogue_active` (bool): If `True`, the game is in dialogue mode.
    *   `dialogue_partner` (str | None): Stores the unique ID of the companion the player is currently talking to (e.g., `'varnas_the_skeptic'`). `None` if `dialogue_active` is `False`.
    *   `companions[id]['memory']['dialogue_history']` (list): A list of dictionaries `{'speaker': 'player'|'<companion_id>', 'utterance': str}` storing the conversation with a specific companion.

*   **Tools (Defined for Claude):**
    *   `start_dialogue_tool`: Allows Claude (during narrative turns) to initiate dialogue. Takes `character_id` as input. Processed by `handle_claude_response` to set `dialogue_active=True`.
    *   `end_dialogue_tool`: Allows Claude (during dialogue turns) to end the conversation. Takes no input. Processed by `handle_claude_response` to set `dialogue_active=False` and trigger summarization.
    *   `update_game_state_tool`: Used for general narrative state changes (location, inventory, flags). Not directly part of dialogue *flow*, but handled by the same response processing logic.
    *   **`exchange_item_tool` (NEW - Dialogue Only):** Allows Claude (during dialogue turns, after agreement) to transfer items between the player and the dialogue partner. Calls `CharacterManager` methods for inventory updates.
    *   **`update_relationship_tool` (NEW - Dialogue Only):** Allows Claude (during dialogue turns, for significant moments) to modify trust or apply/remove statuses (like anger) for the dialogue partner. Calls `CharacterManager` methods for relationship updates.
    *   **`create_character_tool` (NEW - Narrative Only):** Allows Claude (during narrative turns) to generate a new character using `CharacterManager`.

*   **`main()` Function (Game Loop):**
    *   Checks `game_state['dialogue_active']` at the start of each turn.
    *   **Narrative Branch (`else` block):**
        *   Appends player input to `conversation_history`.
        *   Calls `call_claude_api` with all narrative tools (`start_dialogue`, `update_game_state`, `create_character`).
        *   Calls `handle_claude_response` to process the result.
        *   **Crucially, updates `conversation_history` with the full Assistant(`tool_use`) -> User(`tool_result: ...`) sequence if a tool was used.**
        *   Calls Gemini for placeholders if `stop_processing_flag` is False.
    *   **Dialogue Branch (`if` block):**
        *   Calls `handle_dialogue_turn`.
        *   Calls `handle_claude_response` to process the result.
        *   Updates the *character's* `dialogue_history` with the assistant's utterance *only if* the `stop_processing_flag` is False (i.e., `end_dialogue` wasn't called).
        *   Suppresses Gemini calls.

*   **`handle_dialogue_turn()` Function:**
    *   Called only when `dialogue_active` is `True`.
    *   Constructs a dialogue-specific prompt using character details (fetched via `CharacterManager`, including inventory, trust, statuses) and their `dialogue_history`. Includes system instructions encouraging appropriate tool use (`end_dialogue`, `exchange_item`, `update_relationship`).
    *   Calls `call_claude_api` passing all dialogue tools (`end_dialogue`, `exchange_item`, `update_relationship`).
    *   Returns the raw API response object (`Message`) and prompt details.

*   **`handle_claude_response()` Function:**
    *   Receives the raw `Message` object from `call_claude_api` (from either narrative or dialogue branch).
    *   Checks `initial_response.stop_reason`.
    *   If `"tool_use"`:
        *   Identifies the tool (`start_dialogue`, `end_dialogue`, `update_game_state`, `create_character`, `exchange_item`, `update_relationship`).
        *   Executes state changes (modifies `game_state['dialogue_active']`, `dialogue_partner`, calls `CharacterManager` methods for character creation, inventory, or relationship updates).
        *   Calls `summarize_conversation` if `end_dialogue` is used.
        *   Adds appropriate feedback text (e.g., "(Conversation ends.)", "(Item exchange attempted.)") to the `processed_text`.
        *   Sets `stop_processing_flag = True` for state-changing tools (`start_dialogue`, `end_dialogue`, `create_character`, `exchange_item`, `update_relationship`).
        *   Handles the second API call logic only for `update_game_state` (if it wasn't flagged to stop).
    *   Extracts text content from the appropriate response object (initial or second call).
    *   Returns a 5-tuple `(processed_text, initial_response_obj, tool_results_content_sent, final_response_obj_after_tool, stop_processing_flag)` containing all necessary info for the main loop.

*   **`summarize_conversation()` Function:**
    *   Called by `handle_claude_response` when `end_dialogue` tool is processed.
    *   Takes the character's `dialogue_history`.
    *   Calls the Gemini API using a summarization prompt template.
    *   Appends the returned summary to `game_state['narrative_context_summary']`.

*   **History Management:**
    *   The separation of `conversation_history` (narrative) and `dialogue_history` (character-specific) is key.
    *   The narrative branch meticulously reconstructs the `Assistant(tool_use) -> User(tool_result)` sequence in `conversation_history` to maintain API compliance and ensure correct context for subsequent narrative turns.
    *   The dialogue branch only modifies the specific character's history, keeping the main narrative history clean during conversations.

## 4. Workflow Examples

*   **Entering Dialogue:**
    1.  Player enters command like "talk to varnas" (Narrative Turn).
    2.  `main` appends command to `conversation_history`.
    3.  `call_claude_api` sends history + tools (`start_dialogue`, etc.).
    4.  Claude responds with text + `tool_use: start_dialogue`.
    5.  `handle_claude_response` detects tool, sets `dialogue_active=True`, `dialogue_partner='varnas...'`, sets `stop_processing_flag=True`, returns feedback text and response objects.
    6.  `main` updates `conversation_history` with Assistant(tool_use) -> User(tool_result: "Dialogue started...") sequence.
    7.  `main` displays feedback "(You begin...)". Next turn enters the dialogue branch.

*   **During Dialogue:**
    1.  Player enters utterance (Dialogue Turn).
    2.  `main` calls `handle_dialogue_turn`.
    3.  `handle_dialogue_turn` appends player utterance to Varnas's `dialogue_history`, calls `call_claude_api` with Varnas's history and `end_dialogue` tool.
    4.  Claude responds with dialogue text only (no tool use).
    5.  `handle_claude_response` processes response, extracts text, `stop_processing_flag` remains `False`. Returns text and response objects.
    6.  `main` checks `stop_processing_flag` (it's `False`), appends Claude's response to Varnas's `dialogue_history`.
    7.  `main` displays Varnas's response. Game remains in dialogue mode.

*   **Exiting Dialogue:**
    1.  Player enters "goodbye" (Dialogue Turn).
    2.  `main` calls `handle_dialogue_turn`.
    3.  `handle_dialogue_turn` appends "goodbye" to Varnas's history, calls `call_claude_api` with history and `end_dialogue` tool.
    4.  Claude responds with farewell text + `tool_use: end_dialogue`.
    5.  `handle_claude_response` detects tool, sets `dialogue_active=False`, `dialogue_partner=None`, calls `summarize_conversation`, sets `stop_processing_flag=True`, returns feedback text "(Conversation ends.)" and response objects.
    6.  `main` checks `stop_processing_flag` (it's `True`), *does not* update Varnas's `dialogue_history`.
    7.  `main` displays "(Conversation ends.)". Next turn enters the narrative branch. The main `conversation_history` was not modified during this dialogue turn.

## 5. Design Choices & Rationale

*   **Tool Use for Transitions:** Chosen over text parsing ("talk to", "goodbye") because it's more robust, less prone to misinterpretation by the LLM or the parser, aligns with modern LLM capabilities, and provides explicit intent.
*   **Centralized `handle_claude_response`:** Avoids duplicating tool detection and processing logic in both the narrative and dialogue branches of the main loop. Promotes consistency.
*   **Separate History Lists:** Essential for maintaining correct context for each mode (narrative vs. dialogue) and crucial for satisfying the API's strict requirement for `tool_result` messages following `tool_use` messages in the main narrative history.
*   **Explicit `stop_processing_flag`:** Provides a clear signal from the response handler back to the main loop to control subsequent actions (like Gemini calls or history updates) when a state transition occurs via a tool.
*   **Summarization on Exit:** Captures the essence of the conversation for the broader narrative context without cluttering the main history with every dialogue turn. Uses Gemini as a potentially different "voice" suitable for summarization.

## 6. Current Status & Future Work

*   **Status:** The dialogue system meets the V1 goals: reliable entry/exit, persistent character-specific history influencing dialogue, and correct handling of API requirements for tool use sequences.
*   **Future Work:**
    *   Extensive testing and prompt refinement (especially dialogue system prompts).
    *   Handling potential edge cases.
    *   Exploring more sophisticated memory systems beyond simple history (e.g., key facts, relationship scores influencing dialogue generation).
    *   Integrating other game mechanics with dialogue (e.g., inventory checks/transfers via conversation).
