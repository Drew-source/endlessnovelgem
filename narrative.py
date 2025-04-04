"""Narrative Engine: Handles narrative turns, state updates, and prompt construction."""
import json
import anthropic
from utils import call_claude_api
from config import update_game_state_tool, start_dialogue_tool, end_dialogue_tool # Import tools

# --- Game State Update Logic --- #
def apply_tool_updates(tool_input: dict, game_state: dict) -> tuple[bool, list]:
    """Applies updates to the game_state based on the input from the update_game_state tool.

    Directly modifies the game_state dictionary.

    Args:
        tool_input: The dictionary representing the tool call input.
        game_state: The current game state dictionary.

    Returns:
        A tuple (updates_applied (bool), state_changed_summary (list)).
    """
    print("\n[DEBUG] Applying tool updates:", json.dumps(tool_input, indent=2))
    updates_applied = False
    state_changed_summary = []

    # Location
    if "location" in tool_input:
        old_loc = game_state.get('location', 'None')
        new_loc = tool_input['location']
        if old_loc != new_loc:
            game_state['location'] = new_loc
            change_str = f"Location: {old_loc} -> {new_loc}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True

    # Time of Day
    if "time_of_day" in tool_input:
        old_time = game_state.get('time_of_day', 'None')
        new_time = tool_input['time_of_day']
        if old_time != new_time:
            game_state['time_of_day'] = new_time
            change_str = f"Time: {old_time} -> {new_time}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True

    # Player Inventory Add
    if "player_inventory_add" in tool_input:
        items_to_add = tool_input.get("player_inventory_add", [])
        if isinstance(items_to_add, list):
            added = []
            player_inventory = game_state['player'].setdefault('inventory', [])
            for item in items_to_add:
                if item not in player_inventory:
                    player_inventory.append(item)
                    added.append(item)
            if added:
                change_str = f"Player Inventory Add: {added}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Player Inventory Remove
    if "player_inventory_remove" in tool_input:
        items_to_remove = tool_input.get("player_inventory_remove", [])
        removed = []
        if isinstance(items_to_remove, list):
            player_inventory = game_state['player'].setdefault('inventory', [])
            current_inv = list(player_inventory)
            for item in items_to_remove:
                if item in current_inv:
                    try:
                        player_inventory.remove(item)
                        removed.append(item)
                    except ValueError: pass
            if removed:
                change_str = f"Player Inventory Remove: {removed}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Narrative Flags Set/Update
    if "narrative_flags_set" in tool_input:
        flags_to_set = tool_input.get("narrative_flags_set", {})
        narrative_flags = game_state.setdefault('narrative_flags', {})
        if isinstance(flags_to_set, dict) and flags_to_set:
            updated_flags = {k:v for k,v in flags_to_set.items() if narrative_flags.get(k) != v}
            if updated_flags:
                 narrative_flags.update(updated_flags)
                 change_str = f"Narrative Flags Set/Update: {updated_flags}"
                 print(f"  [State Update] {change_str}")
                 state_changed_summary.append(change_str)
                 updates_applied = True

    # Narrative Flags Delete
    if "narrative_flags_delete" in tool_input:
        flags_to_delete = tool_input.get("narrative_flags_delete", [])
        deleted = []
        narrative_flags = game_state.setdefault('narrative_flags', {})
        if isinstance(flags_to_delete, list):
            for flag_key in flags_to_delete:
                if flag_key in narrative_flags:
                    del narrative_flags[flag_key]
                    deleted.append(flag_key)
            if deleted:
                change_str = f"Narrative Flags Delete: {deleted}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Current NPCs Add
    if "current_npcs_add" in tool_input:
        npcs_to_add = tool_input.get("current_npcs_add", [])
        added = []
        current_npcs = game_state.setdefault('current_npcs', [])
        if isinstance(npcs_to_add, list):
            for npc in npcs_to_add:
                if npc not in current_npcs:
                    current_npcs.append(npc)
                    added.append(npc)
            if added:
                change_str = f"NPCs Add: {added}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Current NPCs Remove
    if "current_npcs_remove" in tool_input:
        npcs_to_remove = tool_input.get("current_npcs_remove", [])
        removed = []
        current_npcs = game_state.setdefault('current_npcs', [])
        if isinstance(npcs_to_remove, list):
             current_npcs_list = list(current_npcs)
             for npc in npcs_to_remove:
                 if npc in current_npcs_list:
                    try:
                         current_npcs.remove(npc)
                         removed.append(npc)
                    except ValueError: pass
             if removed:
                change_str = f"NPCs Remove: {removed}"
                print(f"  [State Update] {change_str}")
                state_changed_summary.append(change_str)
                updates_applied = True

    # Companion Updates
    if "companion_updates" in tool_input:
        companion_changes = tool_input.get("companion_updates", {})
        companions = game_state.setdefault('companions', {})
        if isinstance(companion_changes, dict):
            comp_updates_applied = False
            for comp_id, updates in companion_changes.items():
                comp_change_summary = []
                if comp_id in companions and isinstance(updates, dict):
                    companion_state = companions[comp_id]
                    if "present" in updates and companion_state.get('present') != updates['present']:
                        companion_state['present'] = updates['present']
                        comp_change_summary.append(f"present={updates['present']}")
                        comp_updates_applied = True
                    if "inventory_add" in updates:
                         added_items = []
                         comp_inv = companion_state.setdefault('inventory', [])
                         for item in updates.get("inventory_add", []):
                             if item not in comp_inv:
                                 comp_inv.append(item)
                                 added_items.append(item)
                         if added_items: comp_change_summary.append(f"inv_add={added_items}")
                         if added_items: comp_updates_applied = True
                    if "inventory_remove" in updates:
                         removed_items = []
                         comp_inv = companion_state.setdefault('inventory', [])
                         current_comp_inv = list(comp_inv)
                         for item in updates.get("inventory_remove", []):
                             if item in current_comp_inv:
                                 try:
                                    comp_inv.remove(item)
                                    removed_items.append(item)
                                 except ValueError: pass
                         if removed_items: comp_change_summary.append(f"inv_remove={removed_items}")
                         if removed_items: comp_updates_applied = True
                    # Ensure relation structure exists
                    relation_state = companion_state.setdefault('relation_to_player', {})
                    if "relation_to_player_score" in updates and relation_state.get('score') != updates['relation_to_player_score']:
                        relation_state['score'] = updates['relation_to_player_score']
                        comp_change_summary.append(f"rel_score={updates['relation_to_player_score']}")
                        comp_updates_applied = True
                    if "relation_to_player_summary" in updates and relation_state.get('summary') != updates['relation_to_player_summary']:
                        relation_state['summary'] = updates['relation_to_player_summary']
                        comp_change_summary.append("rel_summary_updated")
                        comp_updates_applied = True
                    if "relations_to_others_set" in updates:
                        others_set = updates.get("relations_to_others_set", {})
                        if isinstance(others_set, dict) and others_set:
                           rels_others = companion_state.setdefault('relations_to_others', {})
                           updated_rels = {k:v for k,v in others_set.items() if rels_others.get(k) != v}
                           if updated_rels:
                               rels_others.update(updated_rels)
                               comp_change_summary.append(f"rels_others_set={updated_rels}")
                               comp_updates_applied = True
                if comp_change_summary:
                     change_str = f"Companion Update ({comp_id}): {'; '.join(comp_change_summary)}"
                     print(f"  [State Update] {change_str}")
                     state_changed_summary.append(change_str)
            if comp_updates_applied: updates_applied = True

    # Current Objective Update
    if "current_objective" in tool_input:
        old_obj = game_state.get('current_objective', None)
        new_obj = tool_input['current_objective']
        if old_obj != new_obj:
            game_state['current_objective'] = new_obj
            change_str = f"Objective: {old_obj} -> {new_obj}"
            print(f"  [State Update] {change_str}")
            state_changed_summary.append(change_str)
            updates_applied = True
            
    if not updates_applied:
        print("  [State Update] Tool call received, but no actual changes applied.")

    return updates_applied, state_changed_summary

# --- Prompt Construction --- #
def construct_claude_prompt(current_state: dict,
                              conversation_history: list,
                              prompt_templates: dict) -> dict:
    """Constructs the Claude prompt components for a narrative turn.

    Args:
        current_state: The current game state dictionary.
        conversation_history: List of previous message dicts.
        prompt_templates: Dictionary containing loaded prompt template strings.

    Returns a dictionary containing system prompt, user turn prompt,
    and conversation history for the API call.
    """
    system_prompt = prompt_templates.get("claude_system", "Error: System prompt missing.")
    turn_template = prompt_templates.get("claude_turn_template", "Error: Turn template missing.")

    if "Error:" in system_prompt or "Error:" in turn_template:
        print("[ERROR] Cannot construct Claude prompt due to missing templates.")
        # Return a minimal structure or raise an error
        return {"system_prompt": "", "user_prompt": "Error in prompt construction.", "history": conversation_history}

    # Prepare context dictionary
    present_companions = {comp_id: comp for comp_id, comp in current_state.get('companions', {}).items() if comp.get('present')}
    companion_names_present = ', '.join([comp['name'] for comp_id, comp in present_companions.items()]) or "None"
    companion_ids_present = ', '.join(present_companions.keys()) or "None"
    
    context = {
        'player_location': current_state.get('location', 'an unknown place'),
        'characters_present': ', '.join(current_state.get('current_npcs', []) or ["None"]),
        'companions_present': companion_names_present,
        'companion_ids_present': companion_ids_present,
        'time_of_day': current_state.get('time_of_day', 'unknown'),
        'key_information': '; '.join([f"{k}: {v}" for k, v in current_state.get('narrative_flags', {}).items()] or ["None"]),
        'recent_events_summary': current_state.get('narrative_context_summary', 'The story has just begun.'),
        'current_objective': current_state.get('current_objective', 'None stated.'),
        'last_player_action': current_state.get('last_player_action', 'None')
    }

    try:
        user_turn_prompt = turn_template.format(**context)
    except KeyError as e:
        print(f"[ERROR] Missing key in Claude turn template: {e}. Template: \n{turn_template}")
        user_turn_prompt = f"Describe the situation based on context. (Template error: {e})"
    except Exception as e:
        print(f"[ERROR] Failed to format Claude turn template: {e}")
        user_turn_prompt = "Describe the situation based on context. (Formatting error)"

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_turn_prompt,
        "history": conversation_history
    }

# --- Narrative Turn Handling --- #
def handle_narrative_turn(
    game_state: dict,
    conversation_history: list,
    claude_client: anthropic.Anthropic | None,
    claude_model_name: str | None,
    prompt_templates: dict,
) -> tuple[anthropic.types.Message | None, dict]:
    """Handles a single narrative turn: constructs prompt, calls API.

    Args:
        game_state: The current game state.
        conversation_history: The current narrative history.
        claude_client: Initialized Anthropic client.
        claude_model_name: Name of the Claude model.
        prompt_templates: Dictionary of loaded prompt templates.

    Returns:
        A tuple containing:
        - The raw Anthropic Message object from the API call, or None on failure.
        - The prompt_details dictionary used for the API call.
    """
    print("\n>>> Processing Player Action... Asking Claude for narrative... <<<")
    
    # Construct prompt using the function in this module
    prompt_details = construct_claude_prompt(game_state, conversation_history, prompt_templates)

    # Define available tools for narrative turns
    available_tools = [update_game_state_tool, start_dialogue_tool, end_dialogue_tool]
    
    # Call Claude API using the utility function
    response_obj = call_claude_api(
        claude_client=claude_client,
        model_name=claude_model_name,
        prompt_details=prompt_details,
        tools=available_tools
    )

    return response_obj, prompt_details
