# Project Structure

This document provides the canonical representation of the project's directory and file structure. It should be updated whenever files or directories are added, removed, or significantly reorganized.

```
.
├── .env                        # API keys and model names (DO NOT COMMIT)
├── .gitignore                  # Specifies intentionally untracked files (e.g., venv, .env)
├── endlessnovelgem/
│   ├── config.py               # Constants, tool definitions
│   ├── utils.py                # Utility functions (prompt loading, API calls)
│   ├── visuals.py              # Gemini API interaction for placeholders
│   ├── dialogue.py             # Dialogue turn handling, summarization
│   ├── narrative.py            # Narrative turn handling
│   ├── character_manager.py    # Manages character state and actions
│   ├── location_manager.py     # Manages locations and character presence
│   ├── gamemaster.py           # Gamemaster LLM assessment logic
│   ├── action_resolver.py      # Python logic for resolving action success/failure
│   ├── state_manager.py        # State Manager LLM translation logic
│   ├── main.py                 # Main game execution script (entry point)
│   ├── game_v0_backup.py       # Original monolithic script (backup)
│   ├── prompts/                # Directory for LLM prompt templates
│   │   ├── claude_system.txt             # System prompt for Claude narrative
│   │   ├── claude_turn_template.txt      # Turn prompt template for Claude narrative
│   │   ├── gemini_placeholder_template.txt # Placeholder generation for Gemini
│   │   ├── dialogue_system.txt           # System prompt for Claude dialogue
│   │   ├── summarization.txt             # Summarization prompt for Gemini
│   │   ├── gamemaster_system.txt         # System prompt for Gamemaster LLM
│   │   ├── state_manager_system.txt      # System prompt for State Manager LLM
│   │   └── location_generator.txt        # Prompt for generating new locations
│   ├── docs/                   # Project documentation
│   │   ├── AI_START_HERE.md          # AI Assistant orientation guide
│   │   ├── development_log.md        # Chronological log of actions and decisions
│   │   ├── intent_v0.md              # Project blueprint, goals, protocols
│   │   ├── project_structure.md      # This file: Current file/directory layout
│   │   ├── architecture_overview.md  # High-level system architecture
│   │   ├── dialogue_system_design_v1.md # Design for dialogue & memory
│   │   ├── dialogue_engine_summary.md # Summary of refactored dialogue engine
│   │   ├── character_manager_summary.md # Summary of CharacterManager module
│   │   ├── api_notes_anthropic.md    # Setup/usage notes for Anthropic API
│   │   └── api_notes_google.md       # Setup/usage notes for Google AI API
│   └── venv/                   # Python virtual environment (if used)
└── requirements.txt            # Python package dependencies
```

*Note: The `endlessnovelgem/` sub-directory reflects the project structure within the workspace.*