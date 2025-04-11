"""Location Manager: Handles dynamic location generation and data management."""
import json
import traceback
import anthropic # For generator call
# import re # <-- REMOVE import for regex
from utils import call_claude_api # For generator call

# Import for type hinting
from character_manager import CharacterManager

# Directions constant
DIRECTIONS = ["north", "east", "south", "west"]
OPPOSITE_DIRECTION = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east"
}

# LLM Prompt Template for Location Generation - REMOVED
# (Now loaded externally)

class LocationManager:
    """Manages dynamically generated locations and their connections."""

    def __init__(self, 
                 game_state_ref: dict, 
                 character_manager_ref: CharacterManager, 
                 claude_client: anthropic.Anthropic | None, 
                 claude_model_name: str | None,
                 generator_template: str): # ADD generator_template parameter
        """Initializes the LocationManager.

        Args:
            game_state_ref: A direct reference to the main game_state dictionary.
            character_manager_ref: A reference to the instantiated CharacterManager.
            claude_client: Initialized Anthropic client for location generation.
            claude_model_name: Name of the Claude model for location generation.
            generator_template: The loaded location generator prompt template string.
        """
        self._game_state = game_state_ref
        self._character_manager = character_manager_ref
        self._claude_client = claude_client
        self._claude_model_name = claude_model_name
        self._generator_template = generator_template # Store template
        
        # { location_id: { "description": str, "connections": {dir: loc_id, ...}, "adjacent_generated": bool } }
        self.location_graph = {}

        # Initialize with the starting location
        start_location_id = game_state_ref.get('location')
        if start_location_id:
            # Use initial summary or a default if summary is missing/short
            start_desc = game_state_ref.get('narrative_context_summary')
            if not start_desc or len(start_desc) < 10: # Basic check
                 start_desc = f"You are at {start_location_id}. The details are hazy."
            self.add_location_node(start_location_id, start_desc)
        else:
            print("[ERROR LM] No starting location defined in initial game state!")

        print("[INFO] LocationManager initialized with dynamic generation.")

    def add_location_node(self, loc_id: str, description: str, connections: dict | None = None, adjacent_generated: bool = False):
        """Adds a new location node to the graph if it doesn't exist."""
        if loc_id not in self.location_graph:
            self.location_graph[loc_id] = {
                "description": description,
                "connections": connections if connections is not None else {},
                "adjacent_generated": adjacent_generated
            }
            print(f"[DEBUG LM] Added location node: {loc_id}")
        # else: Update description? For now, only add if new.
            
    def add_connection(self, from_id: str, direction: str, to_id: str):
        """Adds a directional connection between two locations."""
        if from_id in self.location_graph and to_id in self.location_graph:
            # Only add if not already present to avoid redundant prints/logic
            if direction not in self.location_graph[from_id]["connections"]:
                 self.location_graph[from_id]["connections"][direction] = to_id
                 print(f"[DEBUG LM] Added connection: {from_id} --{direction}--> {to_id}")
            # Add reverse connection automatically
            opposite = OPPOSITE_DIRECTION.get(direction)
            if opposite and opposite not in self.location_graph[to_id]["connections"]:
                 self.location_graph[to_id]["connections"][opposite] = from_id
                 print(f"[DEBUG LM] Added reverse connection: {to_id} --{opposite}--> {from_id}")
        else:
            print(f"[WARN LM] Cannot add connection: {from_id} or {to_id} not in graph.")

    def get_connections(self, location_id: str) -> dict:
        """Returns the connection dictionary for a given location."""
        node = self.location_graph.get(location_id)
        return node['connections'] if node else {}
        
    def get_location_description(self, location_id: str) -> str | None:
        """Returns the description for a given location."""
        node = self.location_graph.get(location_id)
        return node['description'] if node else None

    def ensure_location_generated(self, location_id: str) -> bool:
        """Ensures the adjacent locations for the given location_id have been generated.
           Always asks the LLM to describe N, E, S, W, then ignores already known connections.

        Returns:
            bool: True if generation/processing succeeded or was not needed,
                  False if LLM call or processing failed.
        """
        node = self.location_graph.get(location_id)
        if not node:
            print(f"[ERROR LM] Cannot generate adjacencies for unknown location: {location_id}")
            return False
            
        # Check if already fully generated (all 4 directions present)
        current_connections = node.get('connections', {})
        if len(current_connections) == 4 and node.get('adjacent_generated', False):
            print(f"[DEBUG LM Gen] Connections for {location_id} already fully generated.")
            return True

        # If we reach here, some might be missing or generation hasn't been confirmed.
        # ALWAYS ask for all 4 directions now.
        print(f"[INFO LM] Ensuring all adjacent locations (N, E, S, W) are described for: {location_id}.")
        current_desc = node.get('description', 'an unknown area')

        # --- Build Context for Prompt (Still useful for LLM) --- 
        known_connections_context_lines = []
        for direction in DIRECTIONS: # Iterate through N, E, S, W
            connected_id = current_connections.get(direction) # Check if connection exists
            if connected_id:
                connected_desc = self.get_location_description(connected_id) or "(description unknown)"
                known_connections_context_lines.append(f"{direction.capitalize()} leads to '{connected_id}' ({connected_desc}).")
        
        known_connections_context = "\n".join(known_connections_context_lines) if known_connections_context_lines else "None."
        # REMOVED: directions_to_generate_list - No longer needed

        # --- Prepare and Format Prompt --- 
        if "Error:" in self._generator_template:
             print("[ERROR LM Gen] Location generator prompt template failed to load.")
             return False

        try:
            # --- Manual String Replacement --- (Keep using replace for safety)
            # Retrieve the narrative summary from the game state
            narrative_summary = self._game_state.get('narrative_context_summary', 'No summary available.')
            
            prompt_text = self._generator_template
            prompt_text = prompt_text.replace('{current_loc_id}', str(location_id))
            prompt_text = prompt_text.replace('{current_loc_desc}', str(current_desc))
            prompt_text = prompt_text.replace('{known_connections_context}', str(known_connections_context))
            prompt_text = prompt_text.replace('{narrative_summary}', str(narrative_summary)) # Add replacement for summary
            
            # Basic check for leftover placeholders (less critical now)
            if '{' in prompt_text or '}' in prompt_text:
                 print(f"[WARN LM Gen] Potential unreplaced placeholder detected in prompt text after manual replacement.")

        except Exception as e:
             print(f"[ERROR LM Gen] Failed during manual prompt string construction: {e}")
             return False

        generator_messages = [{"role": "user", "content": prompt_text}]
        generator_prompt_details = { 
            "system": "", 
            "messages": generator_messages 
        }

        generation_successful = False # Track overall success for this attempt
        try:
            # --- Call LLM --- 
            response_obj = call_claude_api(
                claude_client=self._claude_client,
                model_name=self._claude_model_name,
                prompt_details=generator_prompt_details,
                tools=None
            )

            generated_data = None
            if response_obj and response_obj.content:
                resp_text = "".join(block.text for block in response_obj.content if block.type == 'text').strip()
                print(f"[DEBUG LM Gen Raw]:\n{resp_text}")

                # --- JSON Parsing --- 
                json_start = resp_text.find('{')
                json_end = resp_text.rfind('}') + 1
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_str = resp_text[json_start:json_end]
                    try:
                        parsed_data = json.loads(json_str)
                        # --- Validation --- 
                        is_valid = True
                        if not isinstance(parsed_data, dict):
                            print("[ERROR LM Gen Parse] Generated JSON is not a dictionary.")
                            is_valid = False
                        else:
                            # Expect exactly N, E, S, W keys
                            expected_keys = set(DIRECTIONS)
                            returned_keys = set(parsed_data.keys())
                            
                            if returned_keys != expected_keys:
                                print(f"[ERROR LM Gen Parse] JSON keys do not match expected N,E,S,W. Got: {returned_keys}")
                                is_valid = False
                            else:
                                # Validate structure of each direction if keys are correct
                                for direction, dir_data in parsed_data.items():
                                    if not isinstance(dir_data, dict) or \
                                       'id' not in dir_data or \
                                       'desc' not in dir_data or \
                                       not isinstance(dir_data['id'], str) or not dir_data['id'] or \
                                       not isinstance(dir_data['desc'], str) or not dir_data['desc']:
                                        print(f"[ERROR LM Gen Parse] Invalid structure or empty value for returned direction '{direction}'.")
                                        is_valid = False
                                        break 
                        
                        if is_valid:
                            generated_data = parsed_data 

                    except json.JSONDecodeError as e:
                        print(f"[ERROR LM Gen Parse] Failed to decode JSON: {e}\nJSON string: {json_str}")
                    except Exception as e:
                         print(f"[ERROR LM Gen Parse] Unexpected error parsing JSON: {e}")
                else:
                    print("[ERROR LM Gen Parse] No JSON object found in response using find/rfind.")
            else:
                 print(f"[ERROR LM Gen Call] No response content from generator LLM. Stop Reason: {response_obj.stop_reason if response_obj else 'N/A'}")

            # --- Process VALIDATED data --- 
            connections_added_this_run = 0
            if generated_data:
                print(f"[DEBUG LM Gen Parsed]: {generated_data}")
                # Iterate through the N, E, S, W keys returned by the LLM
                for direction in DIRECTIONS: 
                    adj_data = generated_data.get(direction) # Should always exist if validation passed
                    # Check if this connection already exists in the graph
                    if direction in current_connections:
                         print(f"  [DEBUG LM Gen] Skipping direction '{direction}', connection already exists.")
                         continue # Skip processing if connection is already known
                         
                    # If connection doesn't exist, process the generated data
                    adj_id = adj_data['id']
                    adj_desc = adj_data['desc']

                    # Check for duplicate generated ID (against *all* known locations)
                    if self.is_valid_location(adj_id):
                         print(f"[WARN LM Gen] Generated location ID '{adj_id}' for direction '{direction}' already exists. Skipping connection.")
                         continue 

                    # Add node for the adjacent location 
                    self.add_location_node(adj_id, adj_desc, adjacent_generated=False)

                    # Add connections (handles bidirectional)
                    self.add_connection(location_id, direction, adj_id)
                    connections_added_this_run += 1
                
                # If we successfully processed data, mark as generated 
                # (even if some were skipped because they existed or IDs clashed)
                print(f"[INFO LM] Processed LLM generation for {location_id}. Added {connections_added_this_run} new connections.")
                self.location_graph[location_id]['adjacent_generated'] = True
                generation_successful = True
            else:
                print(f"[ERROR LM] Failed to generate/parse valid N,E,S,W data for {location_id}. Adjacencies remain unknown.")
                # Keep adjacent_generated False, generation_successful remains False

        except Exception as e:
            print(f"[ERROR LM] Exception during adjacent location generation call: {e}")
            traceback.print_exc()
            # Keep adjacent_generated False, generation_successful remains False

        return generation_successful

    def is_valid_location(self, location_id: str) -> bool:
        """Checks if the given location ID is a valid, known location in the graph."""
        is_valid = location_id in self.location_graph
        # Optional: Reduce debug noise unless needed
        # if not is_valid:
        #     print(f"[DEBUG LM Validation] Location ID '{location_id}' not found in graph: {list(self.location_graph.keys())}")
        return is_valid

    def is_character_present(self, character_id: str, location_id: str) -> bool:
        """Checks if a specific character is currently at the given location ID."""
        char_loc = self._character_manager.get_location(character_id)
        # Handle case where character might not have a location yet
        return char_loc is not None and char_loc == location_id

    def get_characters_at_location(self, location_id: str) -> list[str]:
        """Returns a list of character IDs currently present at the specified location."""
        present_character_ids = []
        all_character_ids = self._character_manager.get_all_character_ids()
        for char_id in all_character_ids:
            # Rely on is_character_present for the check
            if self.is_character_present(char_id, location_id):
                present_character_ids.append(char_id)
        return present_character_ids

    def update_follower_locations(self, player_new_location: str):
        """Updates the location of all characters marked as 'following_player'."""
        if not self.is_valid_location(player_new_location):
            print(f"[ERROR LM] Cannot update follower locations to invalid location: {player_new_location}")
            return

        print(f"[DEBUG LM] Updating follower locations to: {player_new_location}")
        all_character_ids = self._character_manager.get_all_character_ids()
        updated_count = 0
        for char_id in all_character_ids:
            try:
                is_following = self._character_manager.get_follow_status(char_id)
                if is_following:
                    current_char_loc = self._character_manager.get_location(char_id)
                    if current_char_loc != player_new_location:
                        self._character_manager.set_location(char_id, player_new_location)
                        updated_count += 1
                        print(f"  [DEBUG LM] Moved follower {char_id} to {player_new_location}")
            except Exception as e:
                 # Catching specific errors might be better, but general Exception for now
                 print(f"[ERROR LM] Error processing follower update for {char_id}: {e}")
                 # Continue with other characters
        if updated_count > 0:
             print(f"[DEBUG LM] Updated location for {updated_count} followers.")

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

    # --- Add a get_state method for debugging ---
    def get_state(self) -> dict:
        """Returns the current state of the location graph for debugging."""
        return self.location_graph
