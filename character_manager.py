'''Character Manager: Handles character creation, data storage, and retrieval.'''
import random
import uuid

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
    """Manages character data within the game state."""

    def __init__(self, character_data_dict: dict):
        """
        Initializes the CharacterManager.

        Args:
            character_data_dict: A direct reference to the dictionary within the 
                                 game_state that holds all character data 
                                 (e.g., game_state['companions']).
        """
        if not isinstance(character_data_dict, dict):
            raise TypeError("character_data_dict must be a dictionary.")
        self.characters = character_data_dict
        print(f"[INFO] CharacterManager initialized with {len(self.characters)} existing characters.")

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
            }
        }

        self.characters[character_id] = new_character
        print(f"[INFO] Created {archetype} character: '{name}' ({character_id}) at {location}.")
        return True

    # --- Basic Getters ---
    def get_character_data(self, character_id: str) -> dict | None:
        """Retrieves the entire data dictionary for a character."""
        return self._get_character_ref(character_id)

    def get_all_character_ids(self) -> list[str]:
        """Returns a list of all current character IDs."""
        return list(self.characters.keys())

    def get_name(self, character_id: str) -> str | None:
        """Gets the display name of a character."""
        char_ref = self._get_character_ref(character_id)
        return char_ref.get('name') if char_ref else None
    
    def get_location(self, character_id: str) -> str | None:
        """Gets the current location ID/name of a character."""
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
        """Gets the inventory list for a character."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            return char_ref.setdefault('inventory', [])
        return None

    def add_item(self, character_id: str, item: str) -> bool:
        """Adds an item to a character's inventory. (Placeholder)"""
        # TODO: Implement actual logic
        print(f"[TODO] Implement add_item for {character_id}: {item}")
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            inv = char_ref.setdefault('inventory', [])
            inv.append(item) # Simple append for now
            return True
        return False

    def remove_item(self, character_id: str, item: str) -> bool:
        """Removes an item from a character's inventory. (Placeholder)"""
        # TODO: Implement actual logic (check if item exists)
        print(f"[TODO] Implement remove_item for {character_id}: {item}")
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            inv = char_ref.setdefault('inventory', [])
            if item in inv:
                 try:
                     inv.remove(item)
                     return True
                 except ValueError:
                     return False # Should not happen if 'in' check passed
            else:
                 return False # Item not found
        return False

    def has_item(self, character_id: str, item: str) -> bool:
        """Checks if a character has a specific item. (Placeholder)"""
        # TODO: Implement actual logic
        print(f"[TODO] Implement has_item for {character_id}: {item}")
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
        """Gets the trust score towards a specific target (default: player)."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        return rel_ref.get('trust', 0) if rel_ref else None # Default to 0 if structure missing

    def update_trust(self, character_id: str, change: int, target_id: str = 'player') -> bool:
        """Updates the trust score towards a target. (Placeholder)"""
        # TODO: Implement actual logic (apply change, clamp values)
        print(f"[TODO] Implement update_trust for {character_id} -> {target_id}: {change}")
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            current_trust = rel_ref.get('trust', 0)
            new_trust = max(-100, min(100, current_trust + change))
            rel_ref['trust'] = new_trust
            return True
        return False

    def set_status(self, character_id: str, status_name: str, duration: int, target_id: str = 'player') -> bool:
        """Sets a temporary status with a duration. (Placeholder)"""
        # TODO: Implement actual logic
        print(f"[TODO] Implement set_status for {character_id} -> {target_id}: {status_name}={duration}")
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            statuses[status_name] = {'duration': duration}
            return True
        return False

    def remove_status(self, character_id: str, status_name: str, target_id: str = 'player') -> bool:
        """Removes a temporary status. (Placeholder)"""
        # TODO: Implement actual logic
        print(f"[TODO] Implement remove_status for {character_id} -> {target_id}: {status_name}")
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            if status_name in statuses:
                del statuses[status_name]
                return True
        return False

    def get_active_statuses(self, character_id: str, target_id: str = 'player') -> dict | None:
        """Gets the dictionary of active statuses for a target."""
        rel_ref = self._get_relationship_ref(character_id, target_id)
        return rel_ref.get('temporary_statuses') if rel_ref else None

    def decrement_statuses(self, character_id: str, target_id: str = 'player') -> list[str]:
        """Decrements duration of statuses, removes expired ones. (Placeholder)"""
        # TODO: Implement actual logic
        print(f"[TODO] Implement decrement_statuses for {character_id} -> {target_id}")
        removed_statuses = []
        rel_ref = self._get_relationship_ref(character_id, target_id)
        if rel_ref:
            statuses = rel_ref.setdefault('temporary_statuses', {})
            # Iterate over a copy of keys as we might modify the dict
            for status_name in list(statuses.keys()): 
                if 'duration' in statuses[status_name]:
                    statuses[status_name]['duration'] -= 1
                    if statuses[status_name]['duration'] <= 0:
                        del statuses[status_name]
                        removed_statuses.append(status_name)
        return removed_statuses

    # --- Location Method ---
    def set_location(self, character_id: str, location: str) -> bool:
        """Sets the location for a character."""
        char_ref = self._get_character_ref(character_id)
        if char_ref:
            char_ref['location'] = location
            return True
        return False 