# Endless Novel V0.1: Character Manager Summary

**Date:** [Date - Placeholder]

## 1. Overview

This document summarizes the architecture, components, and functionality of the `CharacterManager` module (`character_manager.py`). Its primary purpose is to centralize the creation, storage, retrieval, and modification of Non-Player Character (NPC) data within the game. It aims to provide a robust structure for handling persistent character state (inventory, location, traits, relationships) and enabling dynamic character generation based on defined archetypes.

## 2. Core Concepts & Architecture

*   **Centralized Management:** The module provides a single point of interaction (`CharacterManager` class) for all character-related data operations, preventing logic scattering across other game modules.
*   **Direct State Manipulation:** The `CharacterManager` instance holds a direct reference to the relevant dictionary within the main `game_state` (e.g., `game_state['companions']`), allowing it to modify the live game state directly, ensuring in-session persistence.
*   **Archetype-Based System:** Characters are categorized by an `archetype` string (e.g., 'townsperson', 'companion', 'foe'). This allows for:
    *   Organized configuration (`ARCHETYPE_CONFIG`).
    *   Rule-based, randomized generation specific to the archetype.
    *   Potential for future archetype-specific behaviors or interaction rules.
*   **Class-Based Structure:** A `CharacterManager` class encapsulates the data reference and provides a clear API through its methods.

## 3. Key Components

*   **`CharacterManager` Class:**
    *   The main interface for character operations.
    *   Initialized with a reference to the character data dictionary in `game_state`.
    *   Provides methods for creating, generating, retrieving, and (eventually) modifying character data.

*   **`ARCHETYPE_CONFIG` (Dictionary):**
    *   Located within `character_manager.py`.
    *   Defines the parameters and data pools for generating characters of different archetypes. Includes:
        *   Lists of possible `traits`.
        *   Lists of possible starting `items`.
        *   Configuration for randomization (trait count, item count range, gender odds).
        *   Default starting `initial_trust` values.
        *   Potential `name_prefixes`.

*   **Character Data Structure (within `game_state['companions']`):**
    Each character is represented by a dictionary keyed by a unique `character_id`:
    ```python
    '<character_id>': {
        'name': str,              # Display name
        'description': str,       # Brief text description
        'archetype': str,         # e.g., 'companion', 'townsperson'
        'traits': list[str],      # Behavioral/personality keywords
        'location': str,          # Current location ID/name
        'inventory': list[str],   # Items possessed
        'memory': {
            'dialogue_history': list, # Specific dialogue turns with player
            # Future: 'key_facts_learned', etc.
        },
        'relationships': {
            'player': {           # Relationship towards the player
                'trust': int,     # Score (-100 to 100)
                'temporary_statuses': dict # e.g., {'anger': {'duration': 5}}
            },
            # Future: relationships with other NPCs
        }
    }
    ```
    *Note: Character presence in a location is determined dynamically by comparing `game_state['location']` with the character's `location` field, not stored as a boolean.*

*   **Key Methods:**
    *   `__init__(self, character_data_dict)`: Stores reference to game state character data.
    *   `create_character(...)`: Adds a character to the state with *explicitly provided* details. Used internally by `generate_character`.
    *   `generate_character(self, archetype, location, name_hint=None)`: The primary method for dynamic creation. Looks up `ARCHETYPE_CONFIG`, performs randomization (name, gender, traits, items), generates description and ID, sets initial trust, and calls `create_character` to add the new character to the game state.
    *   `_get_character_ref(self, character_id)`: Internal helper for safe dictionary access.
    *   `get_character_data(self, character_id)`: Retrieves the full data dictionary for a character.
    *   `get_all_character_ids(self)`: Returns a list of all managed character IDs.
    *   `get_name(self, character_id)`: Retrieves character name.
    *   `get_location(self, character_id)`: Retrieves character location.
    *   `set_location(self, character_id, location)`: Sets character location.
    *   `get_inventory(self, character_id)`: Retrieves character inventory list.
    *   `add_item(self, character_id, item)`: Adds item to character inventory.
    *   `remove_item(self, character_id, item)`: Removes item from character inventory (checks existence).
    *   `has_item(self, character_id, item)`: Checks if character has item.
    *   `_get_relationship_ref(...)`: Internal helper for relationship data.
    *   `get_trust(self, character_id, target_id='player')`: Retrieves trust score.
    *   `update_trust(self, character_id, change, target_id='player')`: Updates trust score (with clamping).
    *   `set_status(self, character_id, status_name, duration, target_id='player')`: Sets/updates a temporary status.
    *   `remove_status(self, character_id, status_name, target_id='player')`: Removes a temporary status.
    *   `get_active_statuses(self, character_id, target_id='player')`: Retrieves active status dictionary.
    *   `decrement_statuses(self, character_id, target_id='player')`: Decrements status durations, removes expired ones.
    *   *(Future Work)*: Prompt helper strings (e.g., `get_relationship_prompt_summary`, `get_inventory_string`).

## 4. Workflow Examples

*   **Initialization:** In `main.py`, `character_manager = CharacterManager(game_state['companions'])` is called after `game_state` is initialized.
*   **Character Generation:**
    1.  Narrative LLM (Claude) decides a character should appear.
    2.  Claude calls `create_character_tool` with `archetype` (required) and optionally `location` / `name_hint`.
    3.  `main.py::handle_claude_response` detects the tool call.
    4.  It calls `character_manager.generate_character(archetype=..., location=..., name_hint=...)`.
    5.  `generate_character` uses `ARCHETYPE_CONFIG` for rules, performs randomization, determines details (name, traits, items, ID, description, trust).
    6.  `generate_character` calls `character_manager.create_character(...)` to add the new character dictionary directly into `game_state['companions']`.
    7.  `handle_claude_response` receives the new `character_id`, gets the name via `character_manager.get_name()`, provides feedback text to the player (e.g., "(A new character arrives: Bob the Farmer)"), and sets `stop_processing_flag=True`.
*   **Data Retrieval for Prompts:**
    *   `narrative.py::construct_claude_prompt` calls `character_manager.get_all_character_ids()`, then loops calling `character_manager.get_location()` and `character_manager.get_name()` to determine which characters are present at `game_state['location']` to populate the context.
    *   `dialogue.py::handle_dialogue_turn` calls `character_manager.get_character_data()` for the `dialogue_partner` and uses fetched data (e.g., name, trust score via `get_trust`) to format the dialogue system prompt.
*   **Presence Checking:**
    *   Logic in `main.py::handle_claude_response` (for `start_dialogue_tool`) compares `game_state['location']` with `character_manager.get_location(character_id)` to verify the target character is present before starting dialogue.
    *   `narrative.py::construct_claude_prompt` uses the same location comparison logic to list characters present.

## 5. Integration with Other Modules

*   **`main.py`:** Initializes the `CharacterManager`. Passes the instance to other modules/functions. Handles the `create_character_tool` call by invoking the manager's generation method. Uses manager for presence checks in `start_dialogue`.
*   **`narrative.py`:** Uses the `CharacterManager` within `construct_claude_prompt` to get information about present characters. Includes `create_character_tool` in its list of available tools passed to Claude.
*   **`dialogue.py`:** Uses the `CharacterManager` within `handle_dialogue_turn` to retrieve data about the dialogue partner for prompt construction.
*   **`config.py`:** Defines the JSON schema for the `create_character_tool` used by Claude and processed by `main.py`.
*   **`game_state` (Implicit):** The manager operates directly on the dictionary passed during initialization (typically `game_state['companions']`), making it the central hub for this part of the state.

## 6. Design Rationale

*   **Centralization:** Avoids scattering character logic (creation rules, data access) across multiple files, improving maintainability and organization.
*   **Archetype Field:** Using a simple `archetype` string field provides flexibility for initial implementation and allows easy addition of new types without requiring complex class inheritance structures immediately.
*   **Rule-Based Generation:** Initial generation relies on defined configurations (`ARCHETYPE_CONFIG`) and randomization, providing controllable and predictable (within randomness) character creation suitable for the current stage. LLM-assisted generation could be explored later.
*   **Direct State Reference:** Simplifies state management by having the manager directly modify the live game state dictionary passed to it, eliminating the need for complex state synchronization mechanisms for now.

## 7. Current Status & Future Work

*   **Status:**
    *   `CharacterManager` class structure implemented.
    *   `ARCHETYPE_CONFIG` defined with initial data for four archetypes.
    *   `create_character` method implemented for adding characters with specified data.
    *   `generate_character` method implemented with randomization based on archetype config.
    *   Core getter and modifier methods for inventory and relationships implemented.
    *   Integration points updated in `main.py`, `narrative.py`, `dialogue.py`.
    *   `create_character_tool` defined and handled in `main.py`.
*   **Future Work:**
    *   Refine Generation: Improve name generation, potentially add more variety to descriptions, link item/trait pools more closely.
    *   Prompt Helpers: Implement helper methods in the manager to return formatted strings suitable for LLM prompts (e.g., `get_relationship_prompt_summary`, `get_inventory_string`).
    *   File Persistence: Explore saving/loading character state (potentially the whole `game_state`) to/from files for persistence between sessions.
    *   Testing: Thoroughly test the implemented dialogue interaction tools (exchange, relationship updates).
    *   Integrate with Dialogue Features: *(Completed)* Core logic for dialogue-driven inventory exchange and relationship updates is now implemented via tool handling in `main.py` and `CharacterManager` methods.
