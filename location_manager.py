"""Location Manager: Handles character presence, movement, and location data."""

# Import for type hinting
from character_manager import CharacterManager

class LocationManager:
    """Manages character locations, presence checks, and follower updates."""

    def __init__(self, game_state_ref: dict, character_manager_ref: CharacterManager):
        """Initializes the LocationManager.

        Args:
            game_state_ref: A direct reference to the main game_state dictionary.
            character_manager_ref: A reference to the instantiated CharacterManager.
        """
        self._game_state = game_state_ref
        self._character_manager = character_manager_ref
        # Future: Load/initialize location map here if needed
        # self._location_map = self._load_location_data()
        print("[INFO] LocationManager initialized.")

    def is_character_present(self, character_id: str, location_id: str) -> bool:
        """Checks if a specific character is currently at the given location ID.

        Args:
            character_id: The ID of the character to check.
            location_id: The ID of the location to check against.

        Returns:
            True if the character's current location matches the location_id, False otherwise.
        """
        char_loc = self._character_manager.get_location(character_id)
        if char_loc is None:
            # Character might not exist or have a location set
            return False
        return char_loc == location_id

    def get_characters_at_location(self, location_id: str) -> list[str]:
        """Returns a list of character IDs currently present at the specified location.

        Args:
            location_id: The ID of the location to check.

        Returns:
            A list of character IDs present at the location.
        """
        present_character_ids = []
        all_character_ids = self._character_manager.get_all_character_ids()
        for char_id in all_character_ids:
            if self.is_character_present(char_id, location_id):
                present_character_ids.append(char_id)
        return present_character_ids

    def update_follower_locations(self, player_new_location: str):
        """Updates the location of all characters marked as 'following_player'.

        This should be called *after* the player's location in game_state has been updated.

        Args:
            player_new_location: The player's new location ID.
        """
        print(f"[DEBUG LM] Updating follower locations to: {player_new_location}")
        all_character_ids = self._character_manager.get_all_character_ids()
        updated_count = 0
        for char_id in all_character_ids:
            # We need get_follow_status from CharacterManager (Step 2 of plan)
            try:
                is_following = self._character_manager.get_follow_status(char_id) # Assumes method exists
                if is_following:
                    current_char_loc = self._character_manager.get_location(char_id)
                    if current_char_loc != player_new_location:
                        self._character_manager.set_location(char_id, player_new_location)
                        updated_count += 1
                        print(f"  [DEBUG LM] Moved follower {char_id} to {player_new_location}")
            except AttributeError:
                 # This will happen until get_follow_status is implemented
                 # Suppress error for now, but indicates dependency
                 # print(f"[WARN LM] get_follow_status not yet implemented in CharacterManager.")
                 pass # Silently skip if method doesn't exist yet
            except Exception as e:
                 print(f"[ERROR LM] Error updating follower {char_id}: {e}")
        if updated_count > 0:
             print(f"[DEBUG LM] Updated location for {updated_count} followers.")
        
    # --- NEW: Add validation method --- #
    def is_valid_location(self, location_id: str) -> bool:
        """Checks if the given location ID is a valid, known location."""
        # Assuming location data is loaded into self.locations dictionary
        # If the structure is different (e.g., self.location_data), adjust accordingly.
        if not hasattr(self, 'locations') or not isinstance(self.locations, dict):
            print("[WARN] LocationManager: Location data not found or not a dict for validation.")
            # Fallback behavior: Maybe allow any location? Or deny all? Let's deny for safety.
            return False 
        return location_id in self.locations

    # --- Future Methods (Placeholders) ---

    def validate_move(self, current_location_id: str, target_location_id: str) -> bool:
        """(Future) Checks if moving between two locations is possible."""
        print(f"[WARN LM] validate_move({current_location_id}, {target_location_id}) - Not Implemented.")
        # Placeholder: Allow all moves for now
        return True

    def get_adjacent_locations(self, location_id: str) -> list[str]:
        """(Future) Returns locations directly connected to the given location."""
        print(f"[WARN LM] get_adjacent_locations({location_id}) - Not Implemented.")
        # Placeholder: No known adjacencies
        return []

    # --- Private Helper Methods (Example) ---
    # def _load_location_data(self):
    #     """ (Future) Loads location map from a file or defines it. """
    #     pass
