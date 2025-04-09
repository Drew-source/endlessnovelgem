"""Action Resolver: Calculates success probability based on GM odds and stats, then performs the check."""
import random
from character_manager import CharacterManager # For type hints

# --- Configuration: Base Probabilities --- #
BASE_ODDS = {
    "Accept": 1.0,      # Guaranteed success
    "Easy": 0.75,       # High chance of success
    "Medium": 0.50,     # Even chance
    "Difficult": 0.25,  # Low chance of success
    "Impossible": 0.0    # Guaranteed failure
}

# --- Configuration: Stat Buffs (Example) --- #
# These are simple examples; adjust calculation as needed
STRENGTH_BUFF_SCALE = 0.05 # e.g., +5% chance per point above 10
CHARISMA_BUFF_SCALE = 0.03 # e.g., +3% chance per point above 10
TRUST_BUFF_SCALE = 0.01    # e.g., +1% chance per 10 points of trust above 0

# --- Action Resolution Logic --- #
def resolve_action(odds_str: str, game_state: dict, character_manager: CharacterManager) -> bool:
    """Resolves an action based on GM odds and relevant stats/trust.

    Args:
        odds_str: The conceptual odds string from the GM ('Accept', 'Easy', etc.).
        game_state: The current game state.
        character_manager: The CharacterManager instance.

    Returns:
        True if the action succeeded, False otherwise.
    """
    # 1. Get Base Probability
    base_prob = BASE_ODDS.get(odds_str)
    if base_prob is None:
        print(f"[WARN] ActionResolver: Unknown odds string '{odds_str}'. Defaulting to Medium (0.5).")
        base_prob = 0.5

    # Handle absolute success/failure early
    if base_prob >= 1.0: return True
    if base_prob <= 0.0: return False

    # 2. Calculate Modifiers (Buffs/Debuffs)
    modifier = 0.0
    action_type = determine_action_type(game_state) # Helper to guess if it's Str or Cha based

    player_stats = game_state.get('player', {}).get('stats', {})
    
    if action_type == 'physical':
        strength = player_stats.get('strength', 10)
        modifier += (strength - 10) * STRENGTH_BUFF_SCALE
        print(f"  [ResolveAction] Physical action. Strength: {strength}. Modifier: {modifier:.2f}")
    elif action_type == 'social' and game_state.get('dialogue_active'):
        charisma = player_stats.get('charisma', 10)
        modifier += (charisma - 10) * CHARISMA_BUFF_SCALE
        
        partner_id = game_state.get('dialogue_partner')
        if partner_id:
            trust = character_manager.get_trust(partner_id) or 0
            modifier += (trust / 10.0) * TRUST_BUFF_SCALE # Trust bonus per 10 points
            print(f"  [ResolveAction] Social action. Charisma: {charisma}, Trust: {trust}. Modifier: {modifier:.2f}")
    else: # Default or other action types
        print(f"  [ResolveAction] Action type '{action_type}' or not in dialogue. No specific stat buffs applied.")
        pass # Add other checks later (Dexterity, Intelligence etc.)

    # 3. Calculate Final Probability (Clamped between 0 and 1)
    final_prob = max(0.0, min(1.0, base_prob + modifier))
    print(f"  [ResolveAction] Base Prob: {base_prob:.2f}, Modifier: {modifier:.2f}, Final Prob: {final_prob:.2f}")

    # 4. Perform Probabilistic Check (Simulated Dice Roll)
    roll = random.random() # Generates float between 0.0 and 1.0
    success = roll < final_prob
    
    print(f"  [ResolveAction] Roll: {roll:.2f} vs Prob: {final_prob:.2f} -> {'Success' if success else 'Failure'}")
    
    return success

# --- Helper Function (Example) --- #
def determine_action_type(game_state: dict) -> str:
    """Attempts to guess the primary nature of the player's last action.
       This is a placeholder and needs refinement based on actual input parsing or GM hints.
    """
    last_action = game_state.get('last_player_action', '').lower()
    if game_state.get('dialogue_active'):
        # In dialogue, assume social unless keywords suggest otherwise
        if any(verb in last_action for verb in ['attack', 'hit', 'push', 'break', 'climb', 'lift']):
            return 'physical' 
        return 'social'
    else:
        # In narrative, assume physical unless keywords suggest otherwise
        if any(verb in last_action for verb in ['persuade', 'convince', 'ask', 'talk', 'intimidate', 'lie', 'trick']):
            return 'social'
        return 'physical' # Default to physical outside dialogue 