# Endless Novel - Development Log

**Project Root:** `C:\Users\Marcus\Documents\Cursor\Endless Novel\` *(Please verify if this path has changed)*
**Current Team Focus:** Preparing to implement state update parsing logic (`apply_updates_recursive`).
**Suggested Next Steps:** Implement the `apply_updates_recursive` function in `game_v0.py`.
**Blockers:** None currently noted (API key setup will be needed later).

--- Reference `docs/project_structure.md` for the current file layout. ---

**Log Entries (Newest First):**

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