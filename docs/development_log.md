# Endless Novel - Development Log

**Project Root:** `/Users/luke/Desktop/Coding/endlessnovelgem`
**Current Team Focus:** Designing and starting implementation of a dialogue system with character memory.
**Suggested Next Steps:** Review the created `docs/dialogue_system_design_v1.md` document and then proceed with implementation step 1 (modifying `INITIAL_GAME_STATE` in `game_v0.py`).
**Blockers:** None.

--- Reference `docs/project_structure.md` for the current file layout. ---

**Log Entries (Newest First):**

**2024-08-04 10:00 (Estimate):** *(Timestamp for this action)*
*   **Goal:** Design a dialogue system with persistent character memory.
*   **Input Context:** User request to implement dialogue distinct from narration, including character-specific memory influencing conversations and routing between dialogue/narrative modes.
*   **Discussion:** Outlined requirements: separate dialogue mode, character memory (starting with history), state flags (`dialogue_active`, `dialogue_partner`), routing logic (enter/exit dialogue, summarization), new LLM prompts for dialogue generation and summarization. Agreed to create a design document.
*   **Affected Files/State:** Created `docs/dialogue_system_design_v1.md` with the proposed design. Updated `docs/project_structure.md` to include the new file. Updated `docs/development_log.md` (this entry, updated project root and focus).
*   **Decision:** Adopted the plan outlined in `docs/dialogue_system_design_v1.md` as the blueprint for implementation.
*   **Next:** Review the design document, then modify `INITIAL_GAME_STATE` in `game_v0.py`.

**YYYY-MM-DD HH:MM:** *(Timestamp for previous actions - potentially backfill later)*
*   **Goal:** Setup Python development environment and fetch project code.
*   **Input Context:** User request to pull repo and setup environment.
*   **Discussion:** Cloned repo. Identified dependencies (`anthropic`, `google-generativeai`, `python-dotenv`) from `game_v0.py`. Created Python virtual environment (`venv`). Installed dependencies. Generated `requirements.txt`. Created `.env` with placeholders. Added user-provided API keys to `.env`. Added `venv/` and `.env` to `.gitignore`. Troubleshot and successfully ran `game_v0.py`.
*   **Affected Files/State:** Cloned repo into `endlessnovelgem/`. Created `endlessnovelgem/venv/`. Created `endlessnovelgem/requirements.txt`. Created and populated `endlessnovelgem/.env`. Modified `endlessnovelgem/.gitignore`. Ran `endlessnovelgem/game_v0.py`.
*   **Decision:** Standard Python virtual environment setup completed.
*   **Next:** Proceed with feature development (Dialogue System).

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Create a dedicated file to track project structure and remove outdated snapshots from the log.
*   **Input Context:** User observation that log structure snapshots were outdated and suggestion for a dedicated file.
*   **Discussion:** Agreed to create `docs/project_structure.md` as the canonical source for file layout. Removed outdated "Key Context Snapshot" sections from previous log entries. Added a note at the top of this log referencing the new file.
*   **Affected Files/State:** Created `docs/project_structure.md`. Modified `docs/development_log.md` (removed snapshots, added reference).
*   **Decision:** Adopted `docs/project_structure.md` for tracking file layout.
*   **Next:** Implement `apply_updates_recursive` function.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Finalize V0 `game_state` structure.
*   **Input Context:** Collaborative discussion following HTR, defining minimal companion state requirements (including inventory and relationships).
*   **Discussion:** Agreed on the final `game_state` dictionary structure, incorporating player, world, detailed companion state (incl. relationships), narrative tracking, and interaction context. Companion-companion relationships tracked via numerical scores within each companion's state.
*   **Affected Files/State:** Updated `game_state` definition in `game_v0.py`. Updated Section 4 ('State Management') in `docs/intent_v0.md`.
*   **Decision:** Adopted the finalized `game_state` structure for V0.
*   **Next:** Simplify `update_game_state` function in `game_v0.py`.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Define V0 gameplay loop & feel based on HTR.
*   **Input Context:** Human Tool Response detailing desired gameplay.
*   **Discussion:** Solidified V0 focus: D&D/BG-style narrative adventure emphasizing exploration, object/character interaction, simple puzzles, potential adult content, chapter-based progression, and **core persistent companions**. Combat explicitly deferred. Agreed this definition should drive `game_state` requirements.
*   **Affected Files/State:** `docs/development_log.md` (this entry).
*   **Decision:** Adopted the companion-centric narrative adventure model for V0.
*   **Next:** Define minimal necessary state for companions in V0, then finalize overall `game_state` structure.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Define the necessary `game_state` structure based on desired V0 gameplay.
*   **Input Context:** User response to Human Assistance Request, pointing out that state depends on desired gameplay.
*   **Discussion:** Agreed that defining the target V0 gameplay experience (exploration, dialogue, puzzles, etc.) must precede finalising the `game_state` structure. Retracted previous minimal state proposal. Initiated discussion on core V0 gameplay loop and feel.
*   **Affected Files/State:** `docs/development_log.md` (this entry).
*   **Decision:** Shift focus to defining V0 gameplay before finalizing `game_state`.
*   **Next:** Collaboratively define V0 gameplay loop and feel.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Refactor prompt construction to use external template files.
*   **Input Context:** User feedback requesting separation of prompts from code for clarity and maintainability.
*   **Discussion:** Agreed to move prompts to `prompts/` directory. Created initial templates (`claude_system.txt`, `claude_turn_template.txt`, `gemini_placeholder_template.txt`). Refactored `construct_claude_prompt` and `construct_gemini_prompt` in `game_v0.py` to load and format these templates using a new `load_prompt_template` utility function.
*   **Affected Files/State:** Created `prompts/` directory and files within. Modified `game_v0.py` (added `load_prompt_template`, refactored prompt construction functions).
*   **Decision:** Adopted externalized prompt template approach.
*   **Next:** Define minimal necessary `game_state` for LLM-driven logic and simplify `update_game_state` accordingly.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Log future development idea.
*   **Input Context:** User suggestion during architectural discussion.
*   **Discussion:** Noted the idea of potentially using curated game playthroughs as examples or fine-tuning data ("archetypal rails") for the narrative LLM in later development stages to improve coherence and guide story progression.
*   **Affected Files/State:** `docs/development_log.md`
*   **Decision:** Logged for future consideration.
*   **Next:** Implement prompt separation.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Formalize a mechanism for AI to request human assistance.
*   **Input Context:** User proposal for a "uhuman tool".
*   **Discussion:** Agreed on the value of an explicit protocol for AI to request human input/action for tasks outside its scope. Defined the `**REQUEST FOR HUMAN ASSISTANCE:**` invocation format.
*   **Affected Files/State:** Modified `docs/intent_v0.md`: Renamed Section 6 to "Development Practices & Collaboration" and added a subsection defining the "Explicit Human Assistance Requests" protocol.
*   **Decision:** Integrated the "Uhuman Tool" protocol into the project's intent document.
*   **Next:** Proceed with development, utilizing this protocol as needed.

**2024-07-27 10:00 (Estimate):** *(Manually back-filled based on initial setup conversation)*
*   **Goal:** Establish initial project documentation (`intent_v0.md`, `development_log.md`, `AI_START_HERE.md`) and Python skeleton (`game_v0.py`).
*   **Input Context:** Initial project discussion covering vision, AI development challenges (consistency, context loss, debugging), LLM selection (Claude 3.7 Sonnet for narrative, Gemini 2.5 Pro for prompts), decision for text-only v0, and agreement on a structured, collaborative documentation approach.
*   **Discussion:** Defined structures for `intent_v0.md`, `development_log.md`, and `AI_START_HERE.md` focusing on clarity, persistent context, and supporting AI-human collaboration. Agreed on practices like proactive context gathering before edits.
*   **Affected Files/State:** Created `docs/` directory. Created `docs/intent_v0.md`, `docs/development_log.md`, `docs/AI_START_HERE.md`. Created `game_v0.py` skeleton.
*   **Decision:** Adopted the structured documentation approach and initial file setup.
*   **Next:** Refine document tone and content for clarity and collaboration.

**YYYY-MM-DD HH:MM:** *(Timestamp for session end)*
*   **Goal:** Conclude current development session.
*   **Input Context:** User signing off for the night.
*   **Discussion:** Confirmed the current state: core V0 logic framework implemented, including LLM-driven state update parsing (`_apply_updates_internal`). Documentation is synchronized. Awaiting API keys/docs for next steps.
*   **Affected Files/State:** `docs/development_log.md` (this entry).
*   **Decision:** Pause development. User to provide API keys/docs before next session.
*   **Next:** Implement actual API calls (`call_claude_api`, `call_gemini_api`) using provided credentials and begin testing/refinement.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Capture Anthropic API setup/usage info.
*   **Input Context:** User provided URL to Anthropic setup guide and indicated API keys were stored.
*   **Discussion:** Used `web_search` to extract Python installation and basic usage examples for Anthropic API. Created `docs/api_notes_anthropic.md` to store this information. Updated `docs/project_structure.md`.
*   **Affected Files/State:** Created `docs/api_notes_anthropic.md`. Updated `docs/project_structure.md`.
*   **Decision:** Store API-specific setup notes in dedicated doc files.
*   **Next:** Gather similar information for Google AI (Gemini) API.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Capture Google AI (Gemini) API setup/usage info and model name.
*   **Input Context:** User confirmation of `.env` file location and content.
*   **Discussion:** Read `.env` file to get Google API key and model name (`gemini-2.5-pro-exp-03-25`). Used `web_search` for basic `google-generativeai` Python SDK usage. Created `docs/api_notes_google.md` with setup and usage examples. Updated `docs/api_notes_anthropic.md` with correct model name. Updated `docs/project_structure.md`.
*   **Affected Files/State:** Read `env`. Created `docs/api_notes_google.md`. Updated `docs/api_notes_anthropic.md`, `docs/project_structure.md`.
*   **Decision:** Store Google AI API notes. Confirmed model names.
*   **Next:** Implement actual API calls in `game_v0.py`.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Store API credentials in standard `.env` file for ease of use.
*   **Input Context:** User direction prioritizing developer convenience over strict key handling for this low-risk project.
*   **Discussion:** Agreed to create a standard `.env` file. Wrote keys and model names to `.env`. Deleted the old `env` file. Updated `docs/project_structure.md`.
*   **Affected Files/State:** Created `.env`. Deleted `env`. Updated `docs/project_structure.md`.
*   **Decision:** Use standard `.env` file for credentials in this project.
*   **Next:** Implement actual API calls in `game_v0.py`.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Verify basic API connectivity before implementing calls in main game logic.
*   **Input Context:** User agreement to test connectivity first.
*   **Discussion:** Created temporary script `api_test.py` to load credentials from `.env` and make minimal calls to both Anthropic and Google AI APIs. Installed necessary libraries (`python-dotenv`, `anthropic`, `google-genai`).
*   **Affected Files/State:** Created `api_test.py`. Updated project dependencies (via pip).
*   **Decision:** Proceed with running the test script.
*   **Next:** Run `api_test.py` and analyze results.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Confirm basic API connectivity.
*   **Input Context:** Previous decision to test connectivity before implementation.
*   **Discussion:** Ran `api_test.py`. Received successful 'Hello' responses from both Anthropic (Claude 3.7 Sonnet) and Google AI (Gemini 2.5 Pro), confirming keys and model access are working. Deleted `api_test.py` as per protocol.
*   **Affected Files/State:** Ran `api_test.py`. Deleted `api_test.py`.
*   **Decision:** Basic API connectivity verified.
*   **Next:** Research advanced API features (multi-turn, structured output, etc.) before implementing calls in `game_v0.py`.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Process user-gathered Google AI API info and update documentation.
*   **Input Context:** User provided `docs/human_gathered_api_info_google` file.
*   **Discussion:** Read the provided document. Identified key relevant features: multi-turn Chat object, configuration parameters (temp, tokens, etc.), system instructions, vision/code execution potential. Critically noted the likelihood of a Function Calling/Tool Use feature being superior to our planned `<state_update>` JSON method, requiring further investigation. Updated `docs/api_notes_google.md` with these findings.
*   **Affected Files/State:** Read `docs/human_gathered_api_info_google`. Updated `docs/api_notes_google.md`.
*   **Decision:** Prioritize investigating function calling/tool use features for state updates before implementing the JSON parsing method.
*   **Next:** User to provide similar gathered info for Anthropic API.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Process user-gathered Anthropic API info and revise state update strategy.
*   **Input Context:** User provided `docs/human_gathered_api_claude` file.
*   **Discussion:** Read the provided document. Identified key relevant features: multi-turn via `messages`, `system` prompt parameter, **Tool Use mechanism**, streaming, config params, vision. Confirmed Tool Use is the preferred method for state updates, replacing the previous JSON block parsing plan. Updated `docs/api_notes_anthropic.md` with findings. Updated `docs/intent_v0.md` (Section 5) to reflect the strategic shift to Tool Use.
*   **Affected Files/State:** Read `docs/human_gathered_api_claude`. Updated `docs/api_notes_anthropic.md`, `docs/intent_v0.md`.
*   **Decision:** Adopt Tool Use/Function Calling as the primary mechanism for LLM-driven state updates.
*   **Next:** Implement actual API calls in `game_v0.py`, starting with `call_claude_api` and incorporating the Tool Use handling logic.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Implement Claude API Tool Use handling in `game_v0.py`.
*   **Input Context:** Refined understanding of Tool Use flow, previous implementation of basic `call_claude_api`.
*   **Discussion:** Agreed on the need for a new state update function (`apply_tool_updates`) tailored to the tool schema and a response handler (`handle_claude_response`) to manage the two-call process for tool invocation. Decided to omit the `tools` parameter on the second call.
*   **Affected Files/State:** Modified `game_v0.py`: Added `apply_tool_updates` and `handle_claude_response` functions. Updated the `main` loop to use the new handler. Removed the old `parse_and_apply_state_updates` and `_apply_updates_internal` functions. Updated Section 5 of `docs/intent_v0.md` to reflect the implementation details.
*   **Decision:** Proceeded with implementing the core Tool Use handling logic.
*   **Next:** Test the implementation, refine prompts to encourage tool use, implement history management, and integrate Gemini.

**YYYY-MM-DD HH:MM:** *(Timestamp for this action)*
*   **Goal:** Implement conversation history management for Claude.
*   **Input Context:** Working game loop with Tool Use handling.
*   **Discussion:** Implemented basic history by passing recent messages back to Claude. Modified `construct_claude_prompt` to accept history, `call_claude_api` to use it (with simple truncation), and `main` loop to manage the history list. Discussed limitations of simple truncation and the potential for future enhancements (Summarization, RAG) for better long-term memory, deciding to defer these more complex approaches.
*   **Affected Files/State:** Modified `game_v0.py` (main loop, call_claude_api, construct_claude_prompt, handle_claude_response). Updated `docs/intent_v0.md` (Section 3) to note current approach and future work on context management.
*   **Decision:** Proceed with simple truncation for V0 history management; document need for future enhancements.
*   **Next:** Test history implementation. Refine prompts or add other features. 