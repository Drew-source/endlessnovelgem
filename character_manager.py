'''Character Manager: Handles character creation, data storage, and retrieval.'''
import random
import json
import os
import uuid
from config import INITIAL_TRUST # Assuming these are defined

# --- Archetype Configuration (Placeholder) ---
# Define basic configurations for different character types.
ARCHETYPE_CONFIG = {
    'townsperson': {
        'traits': ['friendly', 'suspicious', 'busy', 'curious', 'weary', 'helpful', 'reserved'],
        'items': ['apple', 'bread', 'hammer', 'cloth', 'coin', 'empty bottle', 'wooden bowl'],
        'name_prefixes': ['Farmer', 'Miller', 'Baker', 'Guard', 'Innkeeper', 'Merchant'],
        'gender_odds': 0.5, # Chance of being male
        'trait_count': 3,
        'item_count_range': (1, 4),
        'initial_trust': 0,
    },
    'companion': {
        'traits': ['loyal', 'skeptic', 'brave', 'resourceful', 'cautious', 'optimistic', 'pragmatic'],
        'items': ['short sword', 'healing potion', 'rope', 'waterskin', 'bedroll', 'dried meat'],
        'gender_odds': 0.5,
        'trait_count': 3,
        'item_count_range': (2, 5),
        'initial_trust': 20,
    },
    'foe': {
        'traits': ['aggressive', 'cunning', 'greedy', 'ruthless', 'cowardly', 'territorial'],
        'items': ['rusty dagger', 'crude club', 'tattered rags', 'stolen coin'],
        'gender_odds': 0.6, # Slightly more likely male?
        'trait_count': 2,
        'item_count_range': (1, 3),
        'initial_trust': -50,
    },
    'love_interest': {
        'traits': ['charming', 'shy', 'witty', 'kind', 'mysterious', 'adventurous'],
        'items': ['flower', 'book', 'locket', 'perfume', 'small gift'],
        'gender_odds': 0,
        'trait_count': 3,
        'item_count_range': (1, 2),
        'initial_trust': 10,
    },
}

class CharacterManager:
    """Manages character data, including stats, inventory, relationships, and memory."""

    def __init__(self, initial_companions_state: dict):
        self.characters = initial_companions_state
        # Ensure essential nested structures exist for initial characters
        for char_id, data in self.characters.items():
            data.setdefault('memory', {})
            data['memory'].setdefault('dialogue_history', [])
            data.setdefault('relationships', {})
            data['relationships'].setdefault('player', {})
            data['relationships']['player'].setdefault('trust', INITIAL_TRUST)
            data['relationships']['player'].setdefault('temporary_statuses', {})
            data.setdefault('inventory', [])
            data.setdefault('stats', {}) # Ensure stats dict exists
            data.setdefault('following_player', False) # Ensure following status exists
            data.setdefault('location', None) # Ensure location exists

        print(f"[DEBUG CM] Initialized with {len(self.characters)} characters.")

    def _get_character_ref(self, character_id: str) -> dict | None:
        """Safely retrieves a reference to a character's data dictionary."""
        if character_id in self.characters:
            return self.characters[character_id]
        else:
            print(f"[ERROR] Character ID '{character_id}' not found.")
            return None

    def create_character(
        self,
        character_id: str,
        name: str,
        description: str,
        archetype: str,
        traits: list[str],
        location: str,
        inventory: list[str] | None = None,
        initial_trust: int = 0,
        dialogue_history: list | None = None
    ) -> bool:
        """
        Creates a new character with explicitly provided details and adds it 
        to the manager's dictionary.

        Args:
            character_id: The unique identifier for the character.
            name: The display name.
            description: A brief description.
            archetype: The character archetype (e.g., 'townsperson').
            traits: A list of personality/behavioral traits.
            location: The starting location ID/name.
            inventory: A list of starting items. Defaults to empty list.
            initial_trust: The starting trust score towards the player. Defaults to 0.
            dialogue_history: Initial dialogue history. Defaults to empty list.

        Returns:
            True if the character was created successfully, False otherwise 
            (e.g., ID already exists).
        """
        if character_id in self.characters:
            print(f"[ERROR] Character ID '{character_id}' already exists. Cannot create.")
            return False
        if archetype not in ARCHETYPE_CONFIG:
             print(f"[WARN] Creating character '{character_id}' with unknown archetype '{archetype}'.")
             # Allow creation but warn

        new_character = {
            'name': name,
            'description': description,
            'archetype': archetype,
            'traits': list(traits), # Ensure it's a list
            'location': location,
            'inventory': list(inventory) if inventory is not None else [],
            'memory': {
                'dialogue_history': list(dialogue_history) if dialogue_history is not None else [],
                # Add other memory fields here if needed in the future
            },
            'relationships': {
                'player': {
                    'trust': initial_trust,
                    'temporary_statuses': {}
                }
                # Add other relationship targets here later
            },
            'following_player': False, # Default follow status
        }

        self.characters[character_id] = new_character
        print(f"[INFO] Created {archetype} character: '{name}' ({character_id}) at {location}.")
        return True

    # --- Basic Getters ---
    def get_character_data(self, character_id: str) -> dict | None:
        """Returns the full data dictionary for a character, or None if not found."""
        return self._get_character_ref(character_id)

    def get_all_character_ids(self) -> list[str]:
        """Returns a list of all current character IDs."""
        return list(self.characters.keys())

    def get_name(self, character_id: str) -> str | None:
        """Gets the display name of a character."""
        char_ref = self._get_character_ref(character_id)
        return char_ref.get('name') if char_ref else None
    
    def get_location(self, character_id: str) -> str | None:
        """Gets the current location ID of a character."""
        char_ref = self._get_character_ref(character_id)
        return char_ref.get('location') if char_ref else None

    # --- Placeholder for Generation ---
    def generate_character(
        self,
        archetype: str,
        location: str,
        name_hint: str | None = None,
        # context: dict | None = None # Context might be useful later
    ) -> str | None:
        """
        Generates a character based on archetype and adds it to the manager.

        Args:
            archetype: The type of character to generate.
            location: The location where the character should be generated.
            name_hint: An optional hint for the name.

        Returns:
            The character_id of the newly generated character, or None on failure.
        """
        print(f"[DEBUG] Attempting to generate character: archetype={archetype}, location={location}, hint={name_hint}")
        if archetype not in ARCHETYPE_CONFIG:
            print(f"[ERROR] Cannot generate character: Unknown archetype '{archetype}'.")
            return None

        config = ARCHETYPE_CONFIG[archetype]

        # --- Implement Random Generation Logic --- 
        
        # 1. Generate Gender (Simple male/female for description)
        gender = 'male' if random.random() < config.get('gender_odds', 0.5) else 'female'
        gender_str = "man" if gender == 'male' else "woman" # For description

        # 2. Generate Name (Basic Implementation)
        name = name_hint
        if not name:
            prefix = random.choice(config.get('name_prefixes', [archetype.capitalize()]))
            # Simple placeholder name generation - can be expanded later
            # For now, using a generic structure like "Prefix RandomSuffix"
            # Common names list would be better in the future
            name = f"{prefix} {str(uuid.uuid4())[:4]}" 
        
        # 3. Select Traits
        available_traits = config.get('traits', [])
        num_traits = config.get('trait_count', 1)
        traits = random.choices(available_traits, k=min(num_traits, len(available_traits))) if available_traits else []

        # 4. Select Items
        available_items = config.get('items', [])
        min_items, max_items = config.get('item_count_range', (0, 0))
        num_items = random.randint(min_items, max_items)
        items = random.choices(available_items, k=min(num_items, len(available_items))) if available_items and num_items > 0 else []

        # 5. Generate Description
        trait_string = ", ".join(traits) if traits else "nondescript"
        description = f"A {gender_str} {archetype} named {name}. They appear {trait_string}."

        # 6. Generate Unique ID (ensure reasonable uniqueness)
        # Sanitize name slightly for ID use
        sanitized_name = "".join(filter(str.isalnum, name.split()[0])).lower()
        unique_suffix = str(uuid.uuid4())[:6] # Slightly longer suffix
        character_id = f"{archetype}_{sanitized_name}_{unique_suffix}"
        # Ensure ID is truly unique, regenerate suffix if collision (rare)
        while character_id in self.characters:
            unique_suffix = str(uuid.uuid4())[:6]
            character_id = f"{archetype}_{sanitized_name}_{unique_suffix}"

        # 7. Get initial trust
        initial_trust = config.get('initial_trust', 0)

        print(f"[DEBUG] Generated Details: ID={character_id}, Name={name}, Desc={description}, Traits={traits}, Items={items}, Trust={initial_trust}")

        # --- Use create_character to add the generated character ---
        success = self.create_character(
            character_id=character_id,
            name=name,
            description=description,
            archetype=archetype,
            traits=traits,
            location=location,
            inventory=items,
            initial_trust=initial_trust
        )

        return character_id if success else None

    # --- Placeholder for other methods (Inventory, Relationships, etc.) ---
    # We will add these in the next phase after generation is working.
    # pass # Add methods like add_item, update_trust, set_status later 

    # --- Inventory Methods (Placeholders / Basic Getters) ---
    def get_inventory(self, character_id: str) -> list[str] | None:
        """Gets the inventory list of a character."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            return char_ref.setdefault('inventory', [])
        return None

    def add_item(self, character_id: str, item: str) -> bool:
        """Adds an item to a character's inventory."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            inv = char_ref.setdefault('inventory', [])
            inv.append(item)
            print(f"  [State Update] Added '{item}' to inventory of {character_id}.")
            return True
        return False

    def remove_item(self, character_id: str, item: str) -> bool:
        """Removes an item from a character's inventory. Returns True if item was found and removed, False otherwise."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            inv = char_ref.setdefault('inventory', [])
            if item in inv:
                 try:
                     inv.remove(item)
                     print(f"  [State Update] Removed '{item}' from inventory of {character_id}.")
                     return True
                 except ValueError:
                     # Should not happen if 'in' check passed, but handle defensively
                     print(f"[WARN] ValueError removing '{item}' from {character_id} despite 'in' check.")
                     return False 
            else:
                 print(f"[DEBUG] Item '{item}' not found in inventory of {character_id} for removal.")
                 return False # Item not found
        return False

    def has_item(self, character_id: str, item: str) -> bool:
        """Checks if a character has a specific item in their inventory."""
        inv = self.get_inventory(character_id)
        return item in inv if inv is not None else False

    # --- Relationship Methods (Placeholders / Basic Getters) ---
    def _get_relationship_ref(self, character_id: str, target_id: str = 'player') -> dict | None:
        """Internal helper to get the relationship dict for a specific target."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            relationships = char_ref.setdefault('relationships', {})
            return relationships.setdefault(target_id, {'trust': 0, 'temporary_statuses': {}})
        return None

    def get_trust(self, character_id: str, target_id: str = 'player') -> int | None:
        """Gets the trust score of character_id towards target_id (default player)."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        return rel_ref.get('trust', 0) if rel_ref else None # Default to 0 if structure missing

    def update_trust(self, character_id: str, change: int, target_id: str = 'player') -> bool:
        """Updates the trust score of character_id towards target_id."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            current_trust = rel_ref.get('trust', 0)
            new_trust = max(-100, min(100, current_trust + change))
            if new_trust != current_trust:
                rel_ref['trust'] = new_trust
                print(f"  [State Update] Updated trust for {character_id} towards {target_id}: {current_trust} -> {new_trust}")
                return True
            else:
                # No change occurred (already at min/max)
                return True # Still counts as success, just no change
        return False

    def set_status(self, character_id: str, status_name: str, duration: int, target_id: str = 'player') -> bool:
        """Sets or updates a temporary status with a duration."""
        if duration <= 0:
            print(f"[WARN] Attempted to set status '{status_name}' with non-positive duration ({duration}). Removing instead.")
            return self.remove_status(character_id, status_name, target_id)
        
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            statuses[status_name] = {'duration': duration}
            print(f"  [State Update] Set status '{status_name}' for {character_id} towards {target_id} (Duration: {duration})")
            return True
        return False

    def remove_status(self, character_id: str, status_name: str, target_id: str = 'player') -> bool:
        """Removes a temporary status."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            if status_name in statuses:
                del statuses[status_name]
                print(f"  [State Update] Removed status '{status_name}' for {character_id} towards {target_id}.")
                return True
            else:
                # Status wasn't present, but that's not an error in removal
                return True 
        return False

    def get_active_statuses(self, character_id: str, target_id: str = 'player') -> dict | None:
        """Gets the dictionary of temporary statuses of character_id towards target_id."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        return rel_ref.get('temporary_statuses') if rel_ref else None

    def decrement_statuses(self, character_id: str, target_id: str = 'player') -> list[str]:
        """Decrements duration of all active statuses, removes expired ones. Returns list of removed statuses."""
        removed_statuses = []
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            if not statuses: return [] # No statuses to decrement
            
            print(f"[DEBUG] Decrementing statuses for {character_id} -> {target_id}...")
            # Iterate over a copy of keys as we might modify the dict
            for status_name in list(statuses.keys()): 
                if 'duration' in statuses[status_name]:
                    statuses[status_name]['duration'] -= 1
                    print(f"  Status '{status_name}' duration: {statuses[status_name]['duration']}")
                    if statuses[status_name]['duration'] <= 0:
                        del statuses[status_name]
                        removed_statuses.append(status_name)
                        print(f"    Removed status '{status_name}'.")
        return removed_statuses

    # --- Location Method ---
    def set_location(self, character_id: str, location: str) -> bool:
        """Sets the location for a character."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            char_ref['location'] = location
            return True
        return False 

    # --- Follow Status --- #

    def set_follow_status(self, character_id: str, following: bool) -> bool:
        """Sets the character's following_player status."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            char_ref['following_player'] = bool(following) # Ensure boolean
            status_text = "following" if following else "not following"
            print(f"  [DEBUG CM] Set {character_id} status to {status_text} player.")
            return True
        print(f"[WARN CM] Failed to set follow status for non-existent character {character_id}.")
        return False

    def get_follow_status(self, character_id: str) -> bool | None:
        """Gets the character's following_player status.

        Returns:
            The boolean status if the character exists, otherwise None.
        """
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            # Return the status, defaulting to False if somehow not set
            return char_ref.get('following_player', False)
        return None # Character not found 

    # --- Memory / Dialogue History --- #
    
    # *** NEW METHOD ***
    def get_dialogue_history(self, character_id: str, ensure_list: bool = False) -> list | None:
        """Gets the dialogue history list for a character.
        
        Args:
            character_id: The ID of the character.
            ensure_list: If True, returns an empty list if history is missing,
                         otherwise returns None.
                         
        Returns:
            The list of dialogue entries, or None/[] based on ensure_list.
        """
        char_data = self.get_character_data(character_id)
        if char_data:
            memory = char_data.setdefault('memory', {})
            history = memory.get('dialogue_history')
            if history is not None:
                return history
            elif ensure_list:
                memory['dialogue_history'] = [] # Ensure it exists for next time
                return []
            else:
                return None
        elif ensure_list:
             return [] # Character not found, return empty list if requested
        else:
             return None # Character not found

    # *** NEW METHOD ***
    def add_dialogue_entry(self, character_id: str, entry: dict):
        """Adds a new entry to a character's dialogue history.
        
        Args:
            character_id: The ID of the character.
            entry: A dictionary representing the dialogue entry (e.g., {'speaker': ..., 'utterance': ...}).
        """
        if not isinstance(entry, dict) or 'speaker' not in entry or 'utterance' not in entry:
            print(f"[WARN CM] Invalid dialogue entry format for {character_id}: {entry}")
            return False
            
        char_data = self.get_character_data(character_id)
        if char_data:
            memory = char_data.setdefault('memory', {})
            history = memory.setdefault('dialogue_history', [])
            # Optional: Prevent adding exact duplicate of the very last message?
            if history and history[-1] == entry:
                print(f"[DEBUG CM] Skipping duplicate dialogue entry for {character_id}.")
                return True # Still consider it success
            history.append(entry)
            # print(f"[DEBUG CM] Added dialogue entry for {character_id}: {entry['speaker']}")
            return True
        else:
            print(f"[WARN CM] Cannot add dialogue entry for unknown character: {character_id}")
            return False

    # --- Character Generation --- #
    def _generate_unique_id(self, name_hint: str | None = None) -> str:
        """Generates a unique ID, potentially using a hint."""
        base_id = "char"
        if name_hint:
            # Basic sanitization for ID
            sanitized_hint = "".join(c for c in name_hint.lower() if c.isalnum() or c == '_').replace(" ", "_")
            if sanitized_hint:
                base_id = sanitized_hint
        
        unique_id = base_id
        counter = 1
        while unique_id in self.characters:
            unique_id = f"{base_id}_{counter}"
            counter += 1
        return unique_id

    def generate_character(self, archetype: str, location: str, name_hint: str | None = None) -> str | None:
        """Generates a new character based on archetype rules (basic example)."""
        # Basic archetype stats/info (Expand this significantly)
        archetype_data = {}
        if archetype == "merchant":
            archetype_data = {
                'name': name_hint or "Traveling Merchant",
                'stats': {'strength': 8, 'charisma': 14},
                'inventory': ['health_potion', 'mana_potion', 'rope', 'coins'],
                'description': "A merchant carrying a large backpack."
            }
        elif archetype == "guard":
             archetype_data = {
                'name': name_hint or "City Guard",
                'stats': {'strength': 14, 'charisma': 9},
                'inventory': ['spear', 'chainmail', 'helmet'],
                 'description': "A stern-faced guard in city livery."
            }
        elif archetype == "foe":
             archetype_data = {
                'name': name_hint or "Shadowy Figure",
                'stats': {'strength': 12, 'charisma': 7},
                'inventory': ['dagger', 'dark_cloak'],
                 'description': "A figure lurking in the shadows."
            }
        else: # Default / Unknown
            print(f"[WARN CM] Unknown archetype: {archetype}. Using default.")
            archetype_data = {
                'name': name_hint or "Mysterious Stranger",
                'stats': {'strength': 10, 'charisma': 10},
                'inventory': [],
                'description': "An unremarkable individual."
            }

        new_id = self._generate_unique_id(archetype_data.get('name'))
        
        self.characters[new_id] = {
            'name': archetype_data.get('name', "Unknown"),
            'archetype': archetype,
            'description': archetype_data.get('description', ""),
            'traits': [], # Add traits based on archetype?
            'location': location,
            'inventory': archetype_data.get('inventory', []),
            'stats': archetype_data.get('stats', {}),
            'memory': {'dialogue_history': []},
            'relationships': {'player': {'trust': INITIAL_TRUST, 'temporary_statuses': {}}},
            'following_player': False
        }
        print(f"[INFO CM] Generated character '{self.characters[new_id]['name']}' ({new_id}) at {location}.")
        return new_id 