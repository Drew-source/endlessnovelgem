"""Settings page for Endless Novel using Flet UI framework with enhanced visual integration"""

import flet as ft
import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Callable

# --- Data Models --- #
@dataclass
class UniverseSettings:
    type: str = "fantasy"
    description: str = "A medieval fantasy realm where magic and technology coexist. Ancient castles dot the landscape, while dragons and other mystical creatures roam the wilderness."
    preset: str = "Medieval Fantasy"

@dataclass
class CharacterSettings:
    # Basic character settings
    gender: str = "Male"
    type: str = "Anime"
    consistentAppearance: bool = True
    dynamicClothing: bool = True
    
    # Visual generation settings
    visualStyle: str = "detailed"  # Options: "minimal", "detailed", "atmospheric"
    visualPromptWeight: float = 0.8  # How strongly character appears in scene (0.1-1.0)
    expressionRange: str = "balanced"  # Options: "subtle", "balanced", "exaggerated"
    visualPriority: bool = True  # Prioritize character in visual descriptions
    voiceDescription: str = "default"  # Options: "none", "default", "detailed"
    characterPalette: str = "automatic"  # Or specific color theme

@dataclass
class BackgroundSettings:
    mood: str = "epic"
    dynamicTimeOfDay: bool = True
    weatherEffects: bool = False

# New NPCSettings class for CharacterManager configuration
@dataclass
class NPCSettings:
    # Default trust levels for different archetypes
    trustLevels: Dict[str, int] = field(default_factory=lambda: {
        "townsperson": 0,
        "companion": 20,
        "foe": -50,
        "love_interest": 10
    })
    
    # Character trait preferences
    traitCounts: Dict[str, int] = field(default_factory=lambda: {
        "townsperson": 3,
        "companion": 3,
        "foe": 2,
        "love_interest": 3
    })
    
    # Character generation preferences
    enableRandomGeneration: bool = True
    detailedDescriptions: bool = True
    consistentAppearance: bool = True
    
    # NPC behavior settings
    dynamicBehavior: bool = True
    rememberPlayerActions: bool = True
    relationshipDecay: bool = False
    decayRate: int = 1  # Trust points lost per time period
    
    # Character variety settings
    maxTraitCount: int = 5
    uniqueCharacters: bool = True
    
    # Archetype balance - influence the frequency of different character types
    archetypeBalance: Dict[str, float] = field(default_factory=lambda: {
        "townsperson": 0.6,
        "companion": 0.15,
        "foe": 0.15,
        "love_interest": 0.1
    })

@dataclass
class GameSettings:
    universe: UniverseSettings = field(default_factory=UniverseSettings)
    character: CharacterSettings = field(default_factory=CharacterSettings)
    background: BackgroundSettings = field(default_factory=BackgroundSettings)
    npcs: NPCSettings = field(default_factory=NPCSettings)  # Added new NPCSettings field

# --- Universe Presets --- #
UNIVERSE_PRESETS = [
    {
        "name": "Medieval Fantasy",
        "type": "fantasy",
        "description": "A medieval fantasy realm where magic and technology coexist. Ancient castles dot the landscape, while dragons and other mystical creatures roam the wilderness.",
    },
    {
        "name": "Space Opera",
        "type": "sci-fi",
        "description": "A vast universe where interstellar travel is common, alien civilizations form complex political alliances, and advanced technology borders on magical.",
    },
    {
        "name": "Cyberpunk City",
        "type": "sci-fi",
        "description": "A neon-lit metropolis where corporations rule, technology has become inseparable from humanity, and the divide between rich and poor is measured in augmentations.",
    },
    {
        "name": "Mythological",
        "type": "fantasy",
        "description": "A world where ancient gods walk among mortals, legendary creatures guard sacred treasures, and heroes prove themselves through epic quests.",
    },
    {
        "name": "Wild West",
        "type": "historical",
        "description": "The untamed frontier where law is scarce, gunslingers and outlaws make their own rules, and the promise of gold draws brave souls to lawless towns.",
    },
]

# Character Palettes
CHARACTER_PALETTES = [
    "automatic", "warm", "cool", "vibrant", "muted", 
    "earthy", "pastel", "monochrome", "contrasting"
]

# --- Settings Page Class --- #
class SettingsPage:
    def __init__(self, page: ft.Page, on_back_callback: Callable = None, on_save_callback: Callable = None):
        self.page = page
        self.on_back_callback = on_back_callback
        self.on_save_callback = on_save_callback
        
        # Setup page properties
        self.page.title = "Endless Novel - Game Settings"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f0f1e"
        self.page.padding = 20
        
        # Game state and settings
        self.settings = GameSettings()
        self.is_new_game = True
        self.is_loading = False
        self.active_tab = "universe"
        
        # Try to load existing settings
        self.load_settings()
        
        # Build UI
        self.build()
    
    def load_settings(self):
        """Load existing settings from file or game state"""
        try:
            if os.path.exists("game_settings.json"):
                with open("game_settings.json", "r") as f:
                    settings_dict = json.load(f)
                    # Convert dict to nested dataclass structure
                    self.settings = GameSettings(
                        universe=UniverseSettings(**settings_dict.get("universe", {})),
                        character=CharacterSettings(**settings_dict.get("character", {})),
                        background=BackgroundSettings(**settings_dict.get("background", {})),
                        npcs=NPCSettings(**settings_dict.get("npcs", {})) if "npcs" in settings_dict else NPCSettings()
                    )
                    self.is_new_game = False
                    print("[INFO] Loaded settings from file")
            else:
                print("[INFO] No saved settings found, using defaults")
        except Exception as e:
            print(f"[ERROR] Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open("game_settings.json", "w") as f:
                json.dump(asdict(self.settings), f, indent=2)
            print("[INFO] Saved settings to file")
        except Exception as e:
            print(f"[ERROR] Failed to save settings: {e}")
    
    def build_character_tab(self):
        """Build the character settings tab with enhanced visual options"""
        # Character gender selection
        self.male_button = ft.ElevatedButton(
            "Male",
            style=ft.ButtonStyle(
                bgcolor={"": "#2196f3" if self.settings.character.gender == "Male" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=150,
            on_click=lambda e: self.set_character_gender("Male"),
        )
        
        self.female_button = ft.ElevatedButton(
            "Female",
            style=ft.ButtonStyle(
                bgcolor={"": "#f50057" if self.settings.character.gender == "Female" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=150,
            on_click=lambda e: self.set_character_gender("Female"),
        )
        
        gender_row = ft.Row(
            [self.male_button, self.female_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        
        # Character style selection
        self.realistic_button = ft.ElevatedButton(
            "Realistic",
            style=ft.ButtonStyle(
                bgcolor={"": "#ff9800" if self.settings.character.type == "Realistic" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=150,
            on_click=lambda e: self.set_character_type("Realistic"),
        )
        
        self.anime_button = ft.ElevatedButton(
            "Anime",
            style=ft.ButtonStyle(
                bgcolor={"": "#673ab7" if self.settings.character.type == "Anime" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=150,
            on_click=lambda e: self.set_character_type("Anime"),
        )
        
        style_row = ft.Row(
            [self.realistic_button, self.anime_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        
        # Basic character options
        self.consistent_appearance_switch = ft.Switch(
            value=self.settings.character.consistentAppearance,
            active_color="#f06292",
            on_change=lambda e: self.set_character_option("consistentAppearance", e.control.value),
        )
        
        self.dynamic_clothing_switch = ft.Switch(
            value=self.settings.character.dynamicClothing,
            active_color="#f06292",
            on_change=lambda e: self.set_character_option("dynamicClothing", e.control.value),
        )
        
        basic_options_col = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Consistent Character Appearance", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="When enabled, your character will maintain the same appearance throughout the story, with minimal variations.",
                    ),
                    ft.Container(expand=True),
                    self.consistent_appearance_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Row([
                    ft.Text("Dynamic Clothing Based on Story", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Character's outfit will change based on the story context, environment, and activities.",
                    ),
                    ft.Container(expand=True),
                    self.dynamic_clothing_switch,
                ]),
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # Visual Style Dropdown
        self.visual_style_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("minimal", "Minimal - Simple, clean descriptions"),
                ft.dropdown.Option("detailed", "Detailed - Rich, comprehensive visuals"),
                ft.dropdown.Option("atmospheric", "Atmospheric - Mood-focused, artistic"),
            ],
            width=400,
            value=self.settings.character.visualStyle,
            on_change=lambda e: self.set_character_option("visualStyle", e.control.value),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        # Visual Prompt Weight Slider
        self.visual_weight_slider = ft.Slider(
            min=0.1,
            max=1.0,
            divisions=9,
            value=self.settings.character.visualPromptWeight,
            label="{value}",
            on_change=lambda e: self.set_character_option("visualPromptWeight", e.control.value),
            active_color="#e57373",
        )
        
        # Expression Range Buttons
        self.subtle_button = ft.ElevatedButton(
            "Subtle",
            style=ft.ButtonStyle(
                bgcolor={"": "#4caf50" if self.settings.character.expressionRange == "subtle" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=120,
            on_click=lambda e: self.set_character_option("expressionRange", "subtle"),
        )
        
        self.balanced_button = ft.ElevatedButton(
            "Balanced",
            style=ft.ButtonStyle(
                bgcolor={"": "#4caf50" if self.settings.character.expressionRange == "balanced" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=120,
            on_click=lambda e: self.set_character_option("expressionRange", "balanced"),
        )
        
        self.exaggerated_button = ft.ElevatedButton(
            "Exaggerated",
            style=ft.ButtonStyle(
                bgcolor={"": "#4caf50" if self.settings.character.expressionRange == "exaggerated" else "#1e1e2f"},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            width=120,
            on_click=lambda e: self.set_character_option("expressionRange", "exaggerated"),
        )
        
        expression_row = ft.Row(
            [self.subtle_button, self.balanced_button, self.exaggerated_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        
        # Visual Priority Switch
        self.visual_priority_switch = ft.Switch(
            value=self.settings.character.visualPriority,
            active_color="#81c784",
            on_change=lambda e: self.set_character_option("visualPriority", e.control.value),
        )
        
        # Voice Description Dropdown
        self.voice_description_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("none", "None - No voice descriptions"),
                ft.dropdown.Option("default", "Default - Basic voice mentions"),
                ft.dropdown.Option("detailed", "Detailed - Rich voice characterization"),
            ],
            width=400,
            value=self.settings.character.voiceDescription,
            on_change=lambda e: self.set_character_option("voiceDescription", e.control.value),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        # Character Palette Dropdown
        palette_options = [ft.dropdown.Option(p, p.capitalize()) for p in CHARACTER_PALETTES]
        self.character_palette_dropdown = ft.Dropdown(
            options=palette_options,
            width=400,
            value=self.settings.character.characterPalette,
            on_change=lambda e: self.set_character_option("characterPalette", e.control.value),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        visual_options_col = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        "Visual Generation Settings",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#e57373",
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                
                # Visual Style
                ft.Row([
                    ft.Text("Visual Style", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Controls the level of detail in character descriptions.",
                    ),
                ]),
                self.visual_style_dropdown,
                ft.Container(height=10),
                
                # Visual Weight
                ft.Row([
                    ft.Text("Character Prominence", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="How prominently your character appears in scene descriptions (0.1=minimal, 1.0=dominant).",
                    ),
                ]),
                self.visual_weight_slider,
                ft.Container(height=10),
                
                # Expression Range
                ft.Row([
                    ft.Text("Expression Range", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="How emotionally expressive your character appears.",
                    ),
                ]),
                expression_row,
                ft.Container(height=10),
                
                # Visual Priority
                ft.Row([
                    ft.Text("Prioritize in Scene Descriptions", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="When enabled, ensures your character is featured prominently in scene descriptions.",
                    ),
                    ft.Container(expand=True),
                    self.visual_priority_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                # Voice Description
                ft.Row([
                    ft.Text("Voice Description", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="How your character's voice is described in the narrative.",
                    ),
                ]),
                self.voice_description_dropdown,
                ft.Container(height=10),
                
                # Character Palette
                ft.Row([
                    ft.Text("Character Color Palette", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="The color theme used for your character throughout the story.",
                    ),
                ]),
                self.character_palette_dropdown,
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # Assemble character tab
        self.character_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.PERSON, color="#f48fb1", size=24),
                                ft.Text(
                                    "Character Settings", 
                                    size=24, 
                                    weight=ft.FontWeight.BOLD,
                                    color="#f48fb1"
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),
                    ft.Text("Character Gender", weight=ft.FontWeight.W_500),
                    gender_row,
                    ft.Container(height=20),
                    ft.Text("Character Style", weight=ft.FontWeight.W_500),
                    style_row,
                    ft.Container(height=20),
                    basic_options_col,
                    ft.Container(height=20),
                    visual_options_col,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,  # Enable scrolling for the content
            ),
            padding=20,
            bgcolor="#131320",
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            width=600,
            height=600,  # Fixed height with scrolling enabled
            margin=ft.margin.only(bottom=20),
            visible=self.active_tab == "character",
        )
    
    def update_character_ui(self):
        """Update character tab UI based on settings"""
        # Update gender buttons
        self.male_button.style.bgcolor = {"": "#2196f3" if self.settings.character.gender == "Male" else "#1e1e2f"}
        self.female_button.style.bgcolor = {"": "#f50057" if self.settings.character.gender == "Female" else "#1e1e2f"}
        
        # Update type buttons
        self.realistic_button.style.bgcolor = {"": "#ff9800" if self.settings.character.type == "Realistic" else "#1e1e2f"}
        self.anime_button.style.bgcolor = {"": "#673ab7" if self.settings.character.type == "Anime" else "#1e1e2f"}
        
        # Update basic toggle switches
        self.consistent_appearance_switch.value = self.settings.character.consistentAppearance
        self.dynamic_clothing_switch.value = self.settings.character.dynamicClothing
        
        # Update visual generation UI elements
        self.visual_style_dropdown.value = self.settings.character.visualStyle
        self.visual_weight_slider.value = self.settings.character.visualPromptWeight
        
        # Update expression range buttons
        self.subtle_button.style.bgcolor = {"": "#4caf50" if self.settings.character.expressionRange == "subtle" else "#1e1e2f"}
        self.balanced_button.style.bgcolor = {"": "#4caf50" if self.settings.character.expressionRange == "balanced" else "#1e1e2f"}
        self.exaggerated_button.style.bgcolor = {"": "#4caf50" if self.settings.character.expressionRange == "exaggerated" else "#1e1e2f"}
        
        # Update other visual options
        self.visual_priority_switch.value = self.settings.character.visualPriority
        self.voice_description_dropdown.value = self.settings.character.voiceDescription
        self.character_palette_dropdown.value = self.settings.character.characterPalette
    
    def set_character_gender(self, gender: str):
        """Set character gender"""
        self.settings.character.gender = gender
        self.update_character_ui()
        self.page.update()
    
    def set_character_type(self, type_: str):
        """Set character type"""
        self.settings.character.type = type_
        self.update_character_ui()
        self.page.update()
    
    def set_character_option(self, option: str, value: bool | str | float):
        """Set character option"""
        setattr(self.settings.character, option, value)
        self.update_character_ui()
        self.page.update()
    
    def build_npc_tab(self):
        """Build the NPC settings tab for character manager configuration"""
        # Header for the NPC tab
        npc_header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.PEOPLE, color="#ff9800", size=24),
                    ft.Text(
                        "NPC Settings", 
                        size=24, 
                        weight=ft.FontWeight.BOLD,
                        color="#ff9800"
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            margin=ft.margin.only(bottom=20),
        )
        
        # --- Trust Levels Section ---
        # Create sliders for trust level configuration
        self.townsperson_trust_slider = ft.Slider(
            min=-100,
            max=100,
            divisions=20,
            value=self.settings.npcs.trustLevels.get("townsperson", 0),
            label="{value}",
            on_change=lambda e: self.set_npc_trust("townsperson", e.control.value),
            active_color="#ff9800",
        )
        
        self.companion_trust_slider = ft.Slider(
            min=-100,
            max=100,
            divisions=20,
            value=self.settings.npcs.trustLevels.get("companion", 20),
            label="{value}",
            on_change=lambda e: self.set_npc_trust("companion", e.control.value),
            active_color="#ff9800",
        )
        
        self.foe_trust_slider = ft.Slider(
            min=-100,
            max=100,
            divisions=20,
            value=self.settings.npcs.trustLevels.get("foe", -50),
            label="{value}",
            on_change=lambda e: self.set_npc_trust("foe", e.control.value),
            active_color="#ff9800",
        )
        
        self.love_interest_trust_slider = ft.Slider(
            min=-100,
            max=100,
            divisions=20,
            value=self.settings.npcs.trustLevels.get("love_interest", 10),
            label="{value}",
            on_change=lambda e: self.set_npc_trust("love_interest", e.control.value),
            active_color="#ff9800",
        )
        
        # Trust levels container
        trust_levels_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        "Initial Trust Levels",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#ff9800",
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                
                ft.Row([
                    ft.Text("Townsperson", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Starting trust level for townspeople NPCs. Higher values mean more friendly interactions.",
                    ),
                ]),
                self.townsperson_trust_slider,
                ft.Container(height=10),
                
                ft.Row([
                    ft.Text("Companion", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Starting trust level for companion NPCs. Higher values mean more loyal companions.",
                    ),
                ]),
                self.companion_trust_slider,
                ft.Container(height=10),
                
                ft.Row([
                    ft.Text("Foe", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Starting trust level for foe NPCs. Lower negative values mean more hostile enemies.",
                    ),
                ]),
                self.foe_trust_slider,
                ft.Container(height=10),
                
                ft.Row([
                    ft.Text("Love Interest", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Starting trust level for romantic NPCs. Higher values lead to faster relationship development.",
                    ),
                ]),
                self.love_interest_trust_slider,
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # --- Character Trait Configuration ---
        # Create number pickers for trait counts
        self.townsperson_traits = ft.Dropdown(
            options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 6)],
            width=80,
            value=str(self.settings.npcs.traitCounts.get("townsperson", 3)),
            on_change=lambda e: self.set_npc_trait_count("townsperson", int(e.control.value)),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        self.companion_traits = ft.Dropdown(
            options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 6)],
            width=80,
            value=str(self.settings.npcs.traitCounts.get("companion", 3)),
            on_change=lambda e: self.set_npc_trait_count("companion", int(e.control.value)),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        self.foe_traits = ft.Dropdown(
            options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 6)],
            width=80,
            value=str(self.settings.npcs.traitCounts.get("foe", 2)),
            on_change=lambda e: self.set_npc_trait_count("foe", int(e.control.value)),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        self.love_interest_traits = ft.Dropdown(
            options=[ft.dropdown.Option(str(i), str(i)) for i in range(1, 6)],
            width=80,
            value=str(self.settings.npcs.traitCounts.get("love_interest", 3)),
            on_change=lambda e: self.set_npc_trait_count("love_interest", int(e.control.value)),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        # Traits container
        traits_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        "Character Trait Configuration",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#ff9800",
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                
                ft.Row([
                    ft.Text("Townsperson Traits", weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    self.townsperson_traits,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Companion Traits", weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    self.companion_traits,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Foe Traits", weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    self.foe_traits,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Love Interest Traits", weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    self.love_interest_traits,
                ]),
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # --- NPC Behavior Options ---
        self.random_generation_switch = ft.Switch(
            value=self.settings.npcs.enableRandomGeneration,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("enableRandomGeneration", e.control.value),
        )
        
        self.detailed_descriptions_switch = ft.Switch(
            value=self.settings.npcs.detailedDescriptions,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("detailedDescriptions", e.control.value),
        )
        
        self.consistent_appearance_switch = ft.Switch(
            value=self.settings.npcs.consistentAppearance,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("consistentAppearance", e.control.value),
        )
        
        self.dynamic_behavior_switch = ft.Switch(
            value=self.settings.npcs.dynamicBehavior,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("dynamicBehavior", e.control.value),
        )
        
        self.remember_actions_switch = ft.Switch(
            value=self.settings.npcs.rememberPlayerActions,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("rememberPlayerActions", e.control.value),
        )
        
        self.relationship_decay_switch = ft.Switch(
            value=self.settings.npcs.relationshipDecay,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("relationshipDecay", e.control.value),
        )
        
        self.decay_rate_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("1", "Slow (1 point)"),
                ft.dropdown.Option("2", "Medium (2 points)"),
                ft.dropdown.Option("3", "Fast (3 points)"),
                ft.dropdown.Option("5", "Very Fast (5 points)"),
            ],
            width=150,
            value=str(self.settings.npcs.decayRate),
            on_change=lambda e: self.set_npc_option("decayRate", int(e.control.value)),
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
            disabled=not self.settings.npcs.relationshipDecay,
        )
        
        # NPC Behavior container
        behavior_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        "NPC Behavior Settings",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#ff9800",
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                
                ft.Row([
                    ft.Text("Enable Random Generation", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="When enabled, new characters will be randomly generated based on archetype settings.",
                    ),
                    ft.Container(expand=True),
                    self.random_generation_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Detailed NPC Descriptions", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Enables rich, detailed descriptions for NPCs when they are encountered.",
                    ),
                    ft.Container(expand=True),
                    self.detailed_descriptions_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Consistent NPC Appearance", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="NPCs will maintain consistent appearance descriptions throughout the story.",
                    ),
                    ft.Container(expand=True),
                    self.consistent_appearance_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Dynamic NPC Behavior", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="NPCs will react dynamically to game events and player actions.",
                    ),
                    ft.Container(expand=True),
                    self.dynamic_behavior_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("NPCs Remember Player Actions", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="NPCs will remember significant interactions with the player.",
                    ),
                    ft.Container(expand=True),
                    self.remember_actions_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Relationship Decay Over Time", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Trust levels will slowly decrease over time if NPCs are not interacted with.",
                    ),
                    ft.Container(expand=True),
                    self.relationship_decay_switch,
                ]),
                
                ft.Row([
                    ft.Text("Decay Rate:", weight=ft.FontWeight.W_500),
                    ft.Container(width=10),
                    self.decay_rate_dropdown,
                ], visible=self.settings.npcs.relationshipDecay),
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # --- Character Variety Options ---
        self.unique_characters_switch = ft.Switch(
            value=self.settings.npcs.uniqueCharacters,
            active_color="#ff9800",
            on_change=lambda e: self.set_npc_option("uniqueCharacters", e.control.value),
        )
        
        self.max_trait_slider = ft.Slider(
            min=1,
            max=10,
            divisions=9,
            value=self.settings.npcs.maxTraitCount,
            label="{value}",
            on_change=lambda e: self.set_npc_option("maxTraitCount", int(e.control.value)),
            active_color="#ff9800",
        )
        
        # Character variety container
        variety_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        "Character Variety Settings",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="#ff9800",
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                
                ft.Row([
                    ft.Text("Ensure Unique NPCs", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="When enabled, the game will try to avoid creating similar NPCs in the same area.",
                    ),
                    ft.Container(expand=True),
                    self.unique_characters_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                
                ft.Row([
                    ft.Text("Maximum Trait Count", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="The maximum number of traits an NPC can have. Higher values lead to more complex NPCs.",
                    ),
                ]),
                self.max_trait_slider,
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # Assemble NPC tab
        self.npc_container = ft.Container(
            content=ft.Column(
                [
                    npc_header,
                    trust_levels_container,
                    ft.Container(height=20),
                    traits_container,
                    ft.Container(height=20),
                    behavior_container,
                    ft.Container(height=20),
                    variety_container,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,  # Enable scrolling for the content
            ),
            padding=20,
            bgcolor="#131320",
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            width=600,
            height=600,  # Fixed height with scrolling enabled
            margin=ft.margin.only(bottom=20),
            visible=self.active_tab == "npcs",
        )
    
    def update_npc_ui(self):
        """Update NPC tab UI based on settings"""
        # Update trust sliders
        self.townsperson_trust_slider.value = self.settings.npcs.trustLevels.get("townsperson", 0)
        self.companion_trust_slider.value = self.settings.npcs.trustLevels.get("companion", 20)
        self.foe_trust_slider.value = self.settings.npcs.trustLevels.get("foe", -50)
        self.love_interest_trust_slider.value = self.settings.npcs.trustLevels.get("love_interest", 10)
        
        # Update trait count dropdowns
        self.townsperson_traits.value = str(self.settings.npcs.traitCounts.get("townsperson", 3))
        self.companion_traits.value = str(self.settings.npcs.traitCounts.get("companion", 3))
        self.foe_traits.value = str(self.settings.npcs.traitCounts.get("foe", 2))
        self.love_interest_traits.value = str(self.settings.npcs.traitCounts.get("love_interest", 3))
        
        # Update behavior switches
        self.random_generation_switch.value = self.settings.npcs.enableRandomGeneration
        self.detailed_descriptions_switch.value = self.settings.npcs.detailedDescriptions
        self.consistent_appearance_switch.value = self.settings.npcs.consistentAppearance
        self.dynamic_behavior_switch.value = self.settings.npcs.dynamicBehavior
        self.remember_actions_switch.value = self.settings.npcs.rememberPlayerActions
        self.relationship_decay_switch.value = self.settings.npcs.relationshipDecay
        
        # Update decay rate dropdown and visibility
        self.decay_rate_dropdown.value = str(self.settings.npcs.decayRate)
        self.decay_rate_dropdown.disabled = not self.settings.npcs.relationshipDecay
        
        # Update decay rate row visibility
        decay_rate_row = self.decay_rate_dropdown.parent
        if decay_rate_row:
            decay_rate_row.visible = self.settings.npcs.relationshipDecay
        
        # Update character variety settings
        self.unique_characters_switch.value = self.settings.npcs.uniqueCharacters
        self.max_trait_slider.value = self.settings.npcs.maxTraitCount
    
    def set_npc_trust(self, archetype: str, value: float):
        """Set trust level for an NPC archetype"""
        self.settings.npcs.trustLevels[archetype] = int(value)
        self.update_npc_ui()
        self.page.update()
    
    def set_npc_trait_count(self, archetype: str, count: int):
        """Set trait count for an NPC archetype"""
        self.settings.npcs.traitCounts[archetype] = count
        self.update_npc_ui()
        self.page.update()
    
    def set_npc_option(self, option: str, value: Any):
        """Set a general NPC option"""
        setattr(self.settings.npcs, option, value)
        self.update_npc_ui()
        self.page.update()
    
    def build_universe_tab(self):
        """Build the universe settings tab"""
        # Universe type dropdown
        self.universe_type_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("fantasy", "Fantasy World"),
                ft.dropdown.Option("sci-fi", "Science Fiction"),
                ft.dropdown.Option("historical", "Historical"),
                ft.dropdown.Option("modern", "Modern Day"),
                ft.dropdown.Option("post-apocalyptic", "Post-Apocalyptic"),
                ft.dropdown.Option("custom", "Custom Universe"),
            ],
            width=400,
            value=self.settings.universe.type,
            on_change=self.handle_universe_type_change,
            filled=True,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
        )
        
        # Universe description textarea
        self.universe_description_textarea = ft.TextField(
            value=self.settings.universe.description,
            multiline=True,
            min_lines=5,
            max_lines=5,
            bgcolor="#1e1e2f",
            border_color=ft.Colors.WHITE24,
            color=ft.Colors.WHITE,
            filled=True,
            on_change=self.handle_custom_description_change,
            width=400,
        )
        
        # Universe presets
        self.preset_buttons = []
        for preset in UNIVERSE_PRESETS:
            btn = ft.ElevatedButton(
                preset["name"],
                data=preset["name"],  # Store preset name in data
                style=ft.ButtonStyle(
                    bgcolor={"": "#1e1e2f" if preset["name"] != self.settings.universe.preset else "#6200ee"},
                    color={"": ft.Colors.WHITE70 if preset["name"] != self.settings.universe.preset else ft.Colors.WHITE},
                    padding=10,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda e, name=preset["name"]: self.handle_preset_select(e, name),
                scale=1.05 if preset["name"] == self.settings.universe.preset else 1.0,
            )
            self.preset_buttons.append(btn)
        
        # Custom preset button
        self.custom_preset_button = ft.ElevatedButton(
            "Custom",
            style=ft.ButtonStyle(
                bgcolor={"": "#6200ee"},
                color={"": ft.Colors.WHITE},
                padding=10,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            visible=self.settings.universe.preset == "Custom",
            scale=1.05,
        )
        
        # Replace ft.Wrap with a standard Row that will wrap its content
        preset_row = ft.Row(
            [*self.preset_buttons, self.custom_preset_button],
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        
        # Assemble universe tab
        self.universe_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.PUBLIC, color="#b39ddb", size=24),
                                ft.Text(
                                    "Story Universe", 
                                    size=24, 
                                    weight=ft.FontWeight.BOLD,
                                    color="#b39ddb"
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),
                    ft.Text("Universe Type", weight=ft.FontWeight.W_500),
                    self.universe_type_dropdown,
                    ft.Container(height=20),
                    ft.Text("Universe Description", weight=ft.FontWeight.W_500),
                    self.universe_description_textarea,
                    ft.Container(height=20),
                    ft.Text("Quick Universe Presets", weight=ft.FontWeight.W_500),
                    preset_row,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=20,
            bgcolor="#131320",
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            width=600,
            margin=ft.margin.only(bottom=20),
            visible=self.active_tab == "universe",
        )
    
    def build_background_tab(self):
        """Build the background settings tab"""
        # Background mood selection
        mood_options = ["epic", "mysterious", "peaceful", "dark", "vibrant"]
        self.mood_buttons = []
        
        for mood in mood_options:
            btn = ft.ElevatedButton(
                mood.capitalize(),
                data=mood,  # Store mood in data
                style=ft.ButtonStyle(
                    bgcolor={"": "#03a9f4" if self.settings.background.mood == mood else "#1e1e2f"},
                    padding=15,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=lambda e, m=mood: self.set_background_mood(m),
            )
            self.mood_buttons.append(btn)
        
        # Replace ft.Wrap with a standard Row that will wrap its content
        mood_row = ft.Row(
            self.mood_buttons,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        
        # Background options
        self.dynamic_time_switch = ft.Switch(
            value=self.settings.background.dynamicTimeOfDay,
            active_color="#4fc3f7",
            on_change=lambda e: self.set_background_option("dynamicTimeOfDay", e.control.value),
        )
        
        self.weather_effects_switch = ft.Switch(
            value=self.settings.background.weatherEffects,
            active_color="#4fc3f7",
            on_change=lambda e: self.set_background_option("weatherEffects", e.control.value),
        )
        
        options_col = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Dynamic Time of Day", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Background will change between day, dusk, night based on the story timeline.",
                    ),
                    # Use Container with expand instead of Spacer
                    ft.Container(expand=True),
                    self.dynamic_time_switch,
                ]),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Row([
                    ft.Text("Weather Effects", weight=ft.FontWeight.W_500),
                    ft.Container(width=5),
                    ft.Container(
                        content=ft.Text("?", size=12),
                        width=20,
                        height=20,
                        bgcolor=ft.Colors.WHITE24,
                        border_radius=10,
                        alignment=ft.alignment.center,
                        tooltip="Add rain, snow, fog, and other environmental effects based on the story.",
                    ),
                    # Use Container with expand instead of Spacer
                    ft.Container(expand=True),
                    self.weather_effects_switch,
                ]),
            ]),
            padding=20,
            bgcolor="#1e1e2f",
            border_radius=10,
            border=ft.border.all(1, ft.Colors.WHITE10),
        )
        
        # Assemble background tab
        self.background_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.IMAGE, color="#80deea", size=24),
                                ft.Text(
                                    "Background Settings", 
                                    size=24, 
                                    weight=ft.FontWeight.BOLD,
                                    color="#80deea"
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),
                    ft.Text("Atmospheric Mood", weight=ft.FontWeight.W_500),
                    mood_row,
                    ft.Container(height=20),
                    options_col,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=20,
            bgcolor="#131320",
            border_radius=15,
            border=ft.border.all(1, ft.Colors.WHITE10),
            width=600,
            margin=ft.margin.only(bottom=20),
            visible=self.active_tab == "background",
        )
    
    def set_background_mood(self, mood: str):
        """Set background mood"""
        self.settings.background.mood = mood
        self.update_background_ui()
        self.page.update()
    
    def set_background_option(self, option: str, value: bool):
        """Set background option"""
        setattr(self.settings.background, option, value)
        self.update_background_ui()
        self.page.update()
    
    def update_background_ui(self):
        """Update background tab UI based on settings"""
        # Update mood buttons
        for btn in self.mood_buttons:
            mood = btn.data
            btn.style.bgcolor = {"": "#03a9f4" if self.settings.background.mood == mood else "#1e1e2f"}
        
        # Update toggle switches
        self.dynamic_time_switch.value = self.settings.background.dynamicTimeOfDay
        self.weather_effects_switch.value = self.settings.background.weatherEffects
    
    def update_universe_ui(self):
        """Update universe tab UI based on settings"""
        # Update type dropdown
        self.universe_type_dropdown.value = self.settings.universe.type
        
        # Update description text area
        self.universe_description_textarea.value = self.settings.universe.description
        
        # Update preset buttons
        for btn in self.preset_buttons:
            preset_name = btn.data
            if preset_name == self.settings.universe.preset:
                btn.style.bgcolor = {"": "#6200ee"}
                btn.style.color = {"": ft.Colors.WHITE}
                btn.scale = 1.05
            else:
                btn.style.bgcolor = {"": "#1e1e2f"}
                btn.style.color = {"": ft.Colors.WHITE70}
                btn.scale = 1.0
        
        # Update custom preset button
        if self.settings.universe.preset == "Custom":
            self.custom_preset_button.visible = True
            self.custom_preset_button.style.bgcolor = {"": "#6200ee"}
            self.custom_preset_button.style.color = {"": ft.Colors.WHITE}
            self.custom_preset_button.scale = 1.05
        else:
            self.custom_preset_button.visible = False
    
    def handle_preset_select(self, e, preset_name: str):
        """Handle universe preset selection"""
        preset = next((p for p in UNIVERSE_PRESETS if p["name"] == preset_name), None)
        if preset:
            self.settings.universe.type = preset["type"]
            self.settings.universe.description = preset["description"]
            self.settings.universe.preset = preset_name
            self.update_universe_ui()
            self.page.update()
    
    def handle_universe_type_change(self, e):
        """Handle universe type selection"""
        new_type = e.control.value
        
        # If selecting "custom", don't change the description
        if new_type == "custom":
            self.settings.universe.type = new_type
            self.settings.universe.preset = "Custom"
            self.update_universe_ui()
            self.page.update()
            return
        
        # Try to find a matching preset for this universe type
        matching_preset = next((p for p in UNIVERSE_PRESETS if p["type"] == new_type), None)
        
        if matching_preset:
            # If there's a matching preset, use its description
            self.settings.universe.type = new_type
            self.settings.universe.description = matching_preset["description"]
            self.settings.universe.preset = matching_preset["name"]
        else:
            # Otherwise just update the type
            self.settings.universe.type = new_type
            self.settings.universe.preset = "Custom"
        
        self.update_universe_ui()
        self.page.update()
    
    def handle_custom_description_change(self, e):
        """Handle custom description changes"""
        custom_description = e.control.value
        
        # Check if this description matches any preset
        matching_preset = next((p for p in UNIVERSE_PRESETS if p["description"] == custom_description), None)
        
        self.settings.universe.description = custom_description
        # If no matching preset found, set preset to "Custom"
        self.settings.universe.preset = matching_preset["name"] if matching_preset else "Custom"
        
        self.update_universe_ui()
        self.page.update()
    
    def handle_back(self, e):
        """Go back to main game page"""
        if self.on_back_callback:
            self.on_back_callback()
    
    def handle_start_game(self, e):
        """Save settings and start/continue the game"""
        self.is_loading = True
        # Update UI immediately to show loading/disable button
        self.page.update()

        # Save settings to file
        self.save_settings()

        # Call the provided callback if available
        if self.on_save_callback:
            try:
                self.on_save_callback(asdict(self.settings), self.is_new_game)
            finally:
                # Reset loading state *after* callback finishes or errors
                self.is_loading = False
        else:
            # If no callback, just reset loading state
            self.is_loading = False
    
    def handle_tab_change(self, tab: str):
        """Change active tab"""
        self.active_tab = tab
        
        # Update UI
        for t in ["universe", "character", "background", "npcs"]:  # Use "npcs" for button
            container_name = "npc_container" if t == "npcs" else f"{t}_container"
            getattr(self, container_name).visible = (t == tab)
            
            tab_button = getattr(self, f"{t}_tab_button")
            tab_button.bgcolor = "#673ab7" if t == tab else ft.Colors.TRANSPARENT
            tab_button.content.controls[1].color = ft.Colors.WHITE if t == tab else ft.Colors.WHITE70
        
        self.page.update()
    
    def build(self):
        """Build the entire settings page UI"""
        # Header with back button
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.WHITE,
                        on_click=self.handle_back,
                        tooltip="Back to game",
                    ),
                    ft.Text("Game Settings", size=32, weight=ft.FontWeight.BOLD, 
                           color="#b39ddb"),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Text(
                    "Customize your AI-powered adventure experience",
                    size=16,
                    color=ft.Colors.WHITE70,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            margin=ft.margin.only(bottom=20),
        )
        
        # Tab navigation - UPDATED to include NPCs tab
        self.universe_tab_button = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PUBLIC, color=ft.Colors.WHITE, size=18),
                ft.Text("Universe", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE if self.active_tab == "universe" else ft.Colors.WHITE70),
            ], spacing=5),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=8,
            bgcolor="#673ab7" if self.active_tab == "universe" else ft.Colors.TRANSPARENT,
            on_click=lambda e: self.handle_tab_change("universe"),
        )
        
        self.character_tab_button = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=18),
                ft.Text("Character", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE if self.active_tab == "character" else ft.Colors.WHITE70),
            ], spacing=5),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=8,
            bgcolor="#673ab7" if self.active_tab == "character" else ft.Colors.TRANSPARENT,
            on_click=lambda e: self.handle_tab_change("character"),
        )
        
        self.background_tab_button = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.IMAGE, color=ft.Colors.WHITE, size=18),
                ft.Text("Background", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE if self.active_tab == "background" else ft.Colors.WHITE70),
            ], spacing=5),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=8,
            bgcolor="#673ab7" if self.active_tab == "background" else ft.Colors.TRANSPARENT,
            on_click=lambda e: self.handle_tab_change("background"),
        )
        
        # New NPCs tab button
        self.npcs_tab_button = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.WHITE, size=18),
                ft.Text("NPCs", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE if self.active_tab == "npcs" else ft.Colors.WHITE70),
            ], spacing=5),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=8,
            bgcolor="#673ab7" if self.active_tab == "npcs" else ft.Colors.TRANSPARENT,
            on_click=lambda e: self.handle_tab_change("npcs"),
        )
        
        tabs_row = ft.Container(
            content=ft.Row(
                [self.universe_tab_button, self.character_tab_button, 
                 self.background_tab_button, self.npcs_tab_button],  # Added NPCs tab
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=5,
            border_radius=10,
            bgcolor="#1e1e2f",
            margin=ft.margin.only(bottom=20),
        )
        
        # Build tab contents
        self.build_universe_tab()
        self.build_character_tab()
        self.build_background_tab()
        self.build_npc_tab()  # Build the new NPCs tab
        
        # Re-check if it's a new game based on file existence *before* creating button
        self.is_new_game = not os.path.exists("game_settings.json")

        # Action buttons
        start_game_button = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.WHITE),
                    ft.Text(
                        "Begin Your Adventure" if self.is_new_game else "Apply & Return to Game",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            style=ft.ButtonStyle(
                bgcolor={"": "#673ab7"},
                color={"": ft.Colors.WHITE},
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=self.handle_start_game,
            disabled=self.is_loading,
        )
        
        return_button = ft.OutlinedButton(
            "Return Without Changes",
            style=ft.ButtonStyle(
                side=ft.BorderSide(color="#673ab7", width=1),
                padding=15,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=self.handle_back,
            disabled=self.is_loading,
            visible=not self.is_new_game,
        )
        
        buttons_row = ft.Row(
            [start_game_button, return_button] if not self.is_new_game else [start_game_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )
        
        # Assemble full page
        self.page.controls = [
            header,
            tabs_row,
            self.universe_container,
            self.character_container,
            self.background_container,
            self.npc_container,  # Added NPCs container
            ft.Container(content=buttons_row, margin=ft.margin.only(top=30, bottom=30)),
        ]
        
        # Initial tab visibility
        self.universe_container.visible = self.active_tab == "universe"
        self.character_container.visible = self.active_tab == "character"
        self.background_container.visible = self.active_tab == "background"
        self.npc_container.visible = self.active_tab == "npcs"  # Added NPCs visibility
        
        self.page.update()


# --- Integration with main flet_app.py --- #
def create_settings_page(page: ft.Page, on_save_callback=None, on_back_callback=None):
    """Create and return a SettingsPage instance"""
    print("[SETTINGS] Creating settings page...")
    settings_page = SettingsPage(page, on_back_callback, on_save_callback)
    return settings_page


# --- Standalone testing --- #
if __name__ == "__main__":
    def main(page: ft.Page):
        def on_save(settings, is_new_game):
            print(f"Settings saved: {json.dumps(settings, indent=2)}")
            print(f"Is new game: {is_new_game}")
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Settings saved successfully!"),
                bgcolor=ft.Colors.GREEN,
            )
            page.snack_bar.open = True
            page.update()
        
        def on_back():
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Return to game without saving"),
                bgcolor=ft.Colors.ORANGE,
            )
            page.snack_bar.open = True
            page.update()
        
        create_settings_page(page, on_save, on_back)
    
    ft.app(target=main)