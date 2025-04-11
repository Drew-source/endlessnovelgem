# Endless Novel - Architecture Overview (v0.5 - State Manager Refactor)

This document outlines the core architecture of the Endless Novel game engine following the refactor that introduced the dedicated State Manager LLM.

## Core Loop Flow (`main.py`)

The main game loop orchestrates the interaction between different modules and LLMs for each turn:

1.  **Get Player Input:** Collects the raw text input from the player.
2.  **Gamemaster Assessment (`gamemaster.py`):**
    *   **Input:** Player input, current game state context.
    *   **Prompt:** `prompts/gamemaster_system.txt`
    *   **LLM (Claude):** Assesses the intended action's difficulty (`odds`) and generates brief `success_message` and `failure_message` flavor texts. Strictly adheres to context (e.g., inventory).
    *   **Output:** JSON object `{ "odds": "...", "success_message": "...", "failure_message": "..." }`
3.  **Action Resolution (`action_resolver.py`):**
    *   **Input:** `odds` from Gamemaster, game state (for potential modifiers).
    *   **Logic:** Performs a weighted random roll based on the odds string (`Impossible`, `Accept`, `Easy`, `Medium`, `Difficult`).
    *   **Output:** Boolean `action_succeeded` flag and the chosen `outcome_message` (either the success or failure message from the Gamemaster).
4.  **Content Generation (Narrative/Dialogue):**
    *   Checks `game_state['dialogue_active']`.
    *   **If Dialogue (`dialogue.py`):**
        *   **Input:** Game state, player input, character context, resolved `outcome_message`.
        *   **Prompt:** `prompts/dialogue_system.txt` (formatted with history, context, and outcome).
        *   **LLM (Claude):** Generates the character's spoken dialogue response, aiming for consistency with the `outcome_message`.
    *   **If Narrative (`narrative.py`):**
        *   **Input:** Game state, narrative history (including player input and `outcome_message`), location/character context.
        *   **Prompt:** `prompts/claude_system.txt`, `prompts/claude_turn_template.txt`.
        *   **LLM (Claude):** Generates the narrative description of the scene and events, incorporating the `outcome_message`.
    *   **Output:** `content_llm_response_text` (the generated text).
5.  **State Manager Translation (`state_manager.py`):**
    *   **Input:** Player input, `content_llm_response_text`, game state context.
    *   **Prompt:** `prompts/state_manager_system.txt`
    *   **LLM (Claude):** Analyzes the *entire* turn's interaction (input + output + outcome implied in output) and translates observed events/actions into a list of structured state update requests. Avoids requests for clearly failed actions.
    *   **Output:** JSON array of request objects `[{"request_name": "...", "parameters": {...}}, ...]`.
6.  **Apply State Updates (`main.py::apply_state_updates`):**
    *   **Input:** List of update requests from State Manager, game state, managers (`CharacterManager`, `LocationManager`), `action_succeeded` flag.
    *   **Logic:** Iterates through the requests. Performs validation checks (e.g., character exists, location valid, item exists, dialogue active/inactive). Modifies `game_state` directly or calls relevant manager methods (`character_manager.add_item`, `location_manager.update_follower_locations`, etc.). Skips updates dependent on `action_succeeded` if the action failed (except for certain requests like dialogue changes). Provides feedback messages.
7.  **Update History (`main.py`):** Appends relevant messages (assistant response) to the correct history (dialogue history via `CharacterManager` or narrative history list).
8.  **Generate Visuals (`visuals.py`):**
    *   **Input:** `content_llm_response_text` (if in narrative mode), game state.
    *   **Prompt:** `prompts/gemini_placeholder_template.txt`
    *   **LLM (Gemini):** Generates descriptive text for visual/audio placeholders.
9.  **Display Output:** Shows the narrative/dialogue text, feedback messages, and visual placeholders to the player.
10. **Loop:** Repeats until quit command or max turns.

## Supporting Managers

*   **`character_manager.py`:** Manages character data (stats, inventory, relationships, dialogue history, status effects, follow status). Provides methods for retrieving and updating this data. Persists data in memory within the `game_state['companions']` structure (or potentially other structures it manages).
*   **`location_manager.py`:** Manages location data (which characters/items are where). Provides methods like `is_valid_location`, `get_characters_at_location`, `is_character_present`, `update_follower_locations`. Relies on internal data structures (likely loaded from configuration or defined statically) and interacts with `CharacterManager`.

## Current State & Next Steps

The architecture successfully separates concerns: assessment (GM), content generation (Narrative/Dialogue), and state change determination (State Manager). The core loop integrates these components. Companion follow status consistency has been improved through code and prompt refinements.

However, recent testing revealed several key areas needing attention:

1.  **`LocationManager` Validation:** The consistent failure of `is_valid_location` for seemingly valid IDs (e.g., `"whispering_forest_higher_ground"`) suggests a bug in the `LocationManager`'s implementation or its underlying location data. This needs code-level debugging.
2.  **State Manager Prompt Refinement:**
    *   **`start_dialogue` Trigger:** The trigger in Narrative mode is still too sensitive, often firing based on NPC lines in the narrative output rather than explicit player intent. Needs further tightening.
    *   **Context/Failure Handling:** While improved, the SM still sometimes ignores clear failure contexts (like `Impossible` odds) or narrative outcomes when generating requests. Reinforcement needed.
    *   **`create_character` Re-triggering:** Needs stronger instruction to only trigger on the *initial* appearance.
    *   **Parameter Formatting:** Needs clearer examples/instructions for complex parameter structures (like the `change` object for `update_relationship` with `anger`).
3.  **Dialogue Prompt Refinement:**
    *   **Outcome Consistency:** The character LLM sometimes contradicts the provided `[Action Outcome: ...]` message. The prompt needs stronger emphasis on adhering to this outcome.

Addressing these points, particularly the `LocationManager` bug and further refining the State Manager's prompt logic, should significantly improve the system's robustness and reliability. 