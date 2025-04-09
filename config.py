"""Configuration settings for Endless Novel V0."""

# --- Constants ---
LOG_FILE = "game_log.json"
MAX_TURNS = 50 # Limit game length for testing
PROMPT_DIR = "prompts" # Ensure this is defined
MAX_HISTORY_MESSAGES = 20 # Max messages to keep in narrative history
INITIAL_TRUST = 20 # Default trust level for new relationships

# --- Debugging Flags ---
DEBUG_IGNORE_LOCATION = False # Set to False for normal operation

# --- Tool Definitions Removed --- #
# The following tool definitions are obsolete in the GM Assessor architecture
# as tools are no longer directly called by the Content Generator LLMs.
# The Gamemaster Assessor prompt defines the structure it expects.

# update_game_state_tool = { ... } (Removed)
# start_dialogue_tool = { ... } (Removed)
# end_dialogue_tool = { ... } (Removed)
# create_character_tool = { ... } (Removed)
# exchange_item_tool = { ... } (Removed)
# update_relationship_tool = { ... } (Removed)
# set_follow_status_tool = { ... } (Removed)
