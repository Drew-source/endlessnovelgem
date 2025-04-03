# AI Assistant - Welcome & Project Orientation

**Objective:** Welcome back! This document serves as your primary orientation point when re-engaging with the "Endless Novel" project, particularly helpful if the prior session context is unavailable. It outlines the documentation system designed to support our collaborative development process.

**Getting Started:** Please begin here for context.

## Purpose of Our Documentation System

To ensure consistency and maintain a shared understanding across development sessions, we utilize a structured documentation system. This acts as our persistent project memory, tracking goals, architectural decisions, and progress, facilitating effective AI-assisted development.

## Document Guide: Your Navigational Tools

*   **`AI_START_HERE.md` (This File):** Provides an overview of the documentation system and suggests a workflow for resuming collaboration.
*   **`docs/development_log.md`:** Our **shared development journal**. It contains:
    *   Chronological entries detailing actions, decisions, and relevant context snapshots.
    *   The team's **Current Focus**, **Next Steps**, and any identified **Blockers**.
    *   It's highly recommended to **review the latest entry here first** to align on the current task.
*   **`docs/intent_v0.md`:** The **project blueprint and design document**. It details:
    *   Overall project vision and specific objectives for the current version.
    *   Core architecture, technology stack, and key design choices.
    *   Collaboratively agreed-upon strategies (e.g., API usage, context management).
    *   Development practices and conventions (debugging, naming).
    *   A glossary of important terms.
    *   Please consult this document for **foundational architectural details** and **established guidelines**.
*   **`docs/project_structure.md`:** The **canonical file layout**. Shows the current directory and file structure of the project.

## Suggested Workflow for Resuming Collaboration

1.  **Review this file (`AI_START_HERE.md`)** for a reminder of the documentation structure and workflow.
2.  **Consult `docs/development_log.md`:** Please check the latest entry to understand the **Current Focus** and planned **Next Steps**.
3.  **Reference `docs/intent_v0.md`:** As needed, review relevant sections to refresh your understanding of the task's context within the larger architecture and agreed-upon practices (including development conventions and the Human Assistance protocol).
4.  **Gather Context Proactively:** Before proposing code modifications (`edit_file`), it's helpful to use tools like `list_dir` and `read_file` to ensure a clear understanding of the current file structure and relevant code sections. Please mention the context gathered in your reasoning.
5.  **Maintain the Log:** Following significant actions or decisions, please add a new, detailed entry to `docs/development_log.md` to keep our shared journal current.
6.  **Utilize Human Assistance Protocol When Needed:** If you encounter a task requiring human input, access, or judgment beyond your capabilities, please use the `**REQUEST FOR HUMAN ASSISTANCE:**` protocol defined in `docs/intent_v0.md`.

**The recommended first step upon restarting is typically to check the latest entry in `docs/development_log.md` to synchronize on our current position.** 