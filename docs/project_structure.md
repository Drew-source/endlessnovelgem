# Project Structure

This document provides the canonical representation of the project's directory and file structure. It should be updated whenever files or directories are added, removed, or significantly reorganized.

```
.
├── .env                       # API keys and model names (DO NOT COMMIT)
├── docs/
│   ├── AI_START_HERE.md       # AI Assistant orientation guide
│   ├── development_log.md     # Chronological log of actions and decisions
│   ├── intent_v0.md           # Project blueprint, goals, protocols
│   ├── project_structure.md   # This file: Current file/directory layout
│   ├── api_notes_anthropic.md # Setup/usage notes for Anthropic API
│   └── api_notes_google.md    # Setup/usage notes for Google AI API
├── prompts/
│   ├── claude_system.txt             # System prompt for Claude
│   ├── claude_turn_template.txt      # Turn prompt template for Claude
│   └── gemini_placeholder_template.txt # Placeholder generation template for Gemini
└── game_v0.py                 # Main Python script for V0
```