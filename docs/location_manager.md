# Endless Novel: Location Manager Module

**Date:** YYYY-MM-DD

## 1. Overview & Purpose

The `LocationManager` module is responsible for managing all aspects of location and spatial relationships within the game world. Its primary goals are:

*   To provide a centralized source of truth for character presence at specific locations.
*   To implement mechanisms for dynamic character movement, both automatic (following) and potentially narrative-driven.
*   To encapsulate location-related logic, separating it from core character attributes (`CharacterManager`) and game flow (`main.py`).
*   To establish a foundation for future features like location validation, adjacency, pathfinding, and dynamic location generation.

This module aims to resolve issues related to static character positions and inconsistent presence checks caused by debug flags, enabling more dynamic and believable character behavior.

## 2. Core Concepts

*   **Location IDs:** Locations are represented by unique string identifiers (e.g., `'whispering_forest_edge'`, `'dark_cave_entrance'`).
*   **Valid Locations:** The `LocationManager` may eventually maintain a list or map of valid locations and potentially their connections, but initially, it will work with locations defined dynamically in the game state.
*   **Character Presence:** Determining which characters are present at the player's location is a key function, replacing the scattered logic and debug flag overrides.
*   **Hybrid Movement Model:** Character location updates follow a hybrid model:
    *   **Follow Tag (`following_player`):** A boolean flag stored within each character's state (managed by `CharacterManager` but utilized by `LocationManager`). If `True`, the `LocationManager` automatically updates the character's location to match the player's whenever the player's location changes.
    *   **Explicit Moves:** Characters not following the player only move when their location is explicitly updated via a dedicated mechanism (e.g., a tool call processed by `narrative.py` that might interact with `LocationManager` or `CharacterManager`).

## 3. Data Storage & Access

The `LocationManager` itself does not primarily *store* location data but rather *accesses* and *manages* it from other parts of the game state:

*   **Player Location:** Accessed directly from `game_state['location']`.
*   **Character Location & Follow Status:** Accessed via the `CharacterManager`, which reads/writes from the character dictionaries within `game_state['companions'][char_id]`. The `following_player` boolean flag will be added to the character's data structure (likely under `memory` or a new `status` key).
*   **(Future) Location Map:** A map defining valid locations and their connections could be stored within the `LocationManager` instance itself.

## 4. Key Functionality / Proposed Methods

The `LocationManager` class will likely include methods such as:

*   `__init__(self, game_state_ref, character_manager_ref)`: Constructor, possibly taking references to the main game state and character manager for easy access.
*   `is_character_present(self, character_id: str, location_id: str) -> bool`: Checks if a specific character is currently at the given location ID. This will replace the logic currently scattered and affected by the debug flag.
*   `get_characters_at_location(self, location_id: str) -> list[str]`: Returns a list of character IDs currently present at the specified location.
*   `update_follower_locations(self, player_new_location: str)`: Iterates through all characters, checks their `following_player` status (via `CharacterManager`), and if `True`, updates their location (via `CharacterManager.set_location`) to match the `player_new_location`. This method should be called *after* the player's location has been successfully updated.
*   `(Future) validate_move(self, current_location_id: str, target_location_id: str) -> bool`: Checks if moving between two locations is possible based on a future location map/graph.
*   `(Future) get_adjacent_locations(self, location_id: str) -> list[str]`: Returns locations directly connected to the given location.

## 5. Interactions with Other Modules

*   **`main.py`:**
    *   Instantiates `LocationManager`.
    *   Calls `location_manager.update_follower_locations()` within `handle_claude_response` after successfully processing a player location change via `update_game_state_tool`.
    *   Uses `location_manager.is_character_present()` within `handle_claude_response` during `start_dialogue_tool` processing (replacing the current check).
*   **`narrative.py`:**
    *   `construct_claude_prompt`: Calls `location_manager.get_characters_at_location(player_location)` to get the accurate list of present characters for the prompt context.
    *   `apply_tool_updates`: Will no longer check `DEBUG_IGNORE_LOCATION` for player moves. Might interact with `LocationManager` in the future if tools for explicit non-follower moves are added.
*   **`dialogue.py`:**
    *   `handle_dialogue_turn`: Continues to fetch player location from `game_state` to provide context to the character.
*   **`character_manager.py`:**
    *   Will need a new method like `set_follow_status(self, character_id: str, following: bool)` and `get_follow_status(self, character_id: str) -> bool` to manage the new flag.
    *   `LocationManager` will call `character_manager.get_follow_status()` and `character_manager.set_location()`.
*   **`config.py`:**
    *   Will need definitions for new tools (e.g., `set_follow_status_tool`).
    *   `DEBUG_IGNORE_LOCATION` can eventually be removed or permanently set to `False`.

## 6. Tools

*   **`update_game_state_tool`:** Remains the primary way for the *player's* location to be changed via narrative. Its processing in `main.py` will trigger `LocationManager.update_follower_locations()`.
*   **`start_dialogue_tool`:** Its processing logic in `main.py` will use `LocationManager.is_character_present()` for validation.
*   **New Tool: `set_follow_status_tool` (Schema TBD):**
    *   **Purpose:** To allow the LLM (in narrative or dialogue) to toggle a character's `following_player` status.
    *   **Parameters:** Likely `character_id` and `following` (boolean).
    *   **Processing:** Handled in `handle_claude_response` by calling `character_manager.set_follow_status()`.

## 7. Future Work

*   Implement a map of valid locations and connections.
*   Implement `validate_move` and `get_adjacent_locations`.
*   Integrate move validation into the processing of the `update_game_state_tool`.
*   Potentially add tools for specific non-follower character moves initiated by the narrative.
*   Explore dynamic location generation.

## 8. Implementation Plan (High-Level)

1.  Create `location_manager.py` with the initial class structure.
2.  Add `following_player` flag logic to `CharacterManager` (`set_follow_status`, `get_follow_status`).
3.  Implement core `LocationManager` methods (`is_character_present`, `get_characters_at_location`, `update_follower_locations`).
4.  Integrate `LocationManager` calls into `main.py` and `narrative.py`, removing old logic.
5.  Define and implement handling for `set_follow_status_tool`.
6.  Update prompts to guide LLM on using `set_follow_status_tool`.
7.  Set `DEBUG_IGNORE_LOCATION = False` and test thoroughly.
8.  Remove `DEBUG_IGNORE_LOCATION` entirely once stable.
