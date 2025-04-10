"""Main game app integrating settings page with existing game logic"""

import flet as ft
import json
import os
import traceback
from enum import Enum
from threading import Thread
from queue import Queue, Empty

# Import from your existing game code
from main import (
    initialize_clients,
    INITIAL_GAME_STATE,
    process_game_turn,  # Import the new turn processor
    CharacterManager, # Import CharacterManager
    LocationManager   # Import LocationManager
)
from utils import load_prompt_template
from visuals import call_gemini_api, construct_gemini_prompt
# from narrative import handle_narrative_turn # No longer needed directly

# Import our settings page
from settings import create_settings_page, GameSettings

# --- App State --- #
class AppScreen(Enum):
    GAME = "game"
    SETTINGS = "settings"
    LOADING = "loading"

class GameApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Endless Novel"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#0f0f1e"
        self.page.padding = 20
        
        # Game state
        self.current_screen = AppScreen.LOADING
        self.game_state = INITIAL_GAME_STATE.copy()
        self.conversation_history = []
        self.turn_count = 0
        self.result_queue = Queue()
        
        # Add manager placeholders
        self.character_manager = None
        self.location_manager = None
        
        # Initialize clients and prompts
        print("[DEBUG] Initializing game systems...")
        self.init_game_systems()
        
        # Set up UI
        print("[DEBUG] Setting up UI...")
        self.setup_ui()
        
        # Show initial screen
        self.show_loading_screen("Initializing game...")
        
        # Start a background thread to complete initialization
        print("[DEBUG] Starting initialization thread...")
        Thread(target=self.complete_initialization, daemon=True).start()
        
        # Start UI update loop
        print("[DEBUG] Starting UI update loop...")
        Thread(target=self.ui_update_loop, daemon=True).start()
    
    def init_game_systems(self):
        """Initialize API clients and prompts"""
        try:
            # Initialize clients
            self.claude_client, self.gemini_client, self.claude_model_name, self.gemini_model_name = initialize_clients()
            
            # Load prompt templates
            self.prompt_templates = {
                name: load_prompt_template(f"{name}.txt")
                for name in ["claude_system", "claude_turn_template",
                            "gemini_placeholder_template", "dialogue_system",
                            "summarization", "gamemaster_system", # Add new prompts
                            "state_manager_system"]
            }
            print("[DEBUG] Game systems initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize game systems: {e}")
            traceback.print_exc()
    
    def complete_initialization(self):
        """Complete initialization in background thread"""
        try:
            print("[DEBUG] Starting complete_initialization...")
            
            # Try to load existing game state
            if os.path.exists("game_state.json"):
                print("[DEBUG] Found existing game state file, loading...")
                try:
                    with open("game_state.json", "r") as f:
                        self.game_state = json.load(f)
                    # Check if settings exist in state
                    if "settings" not in self.game_state:
                        print("[DEBUG] No settings in game state, checking for separate settings file...")
                        # Try to load from separate settings file
                        if os.path.exists("game_settings.json"):
                            try:
                                with open("game_settings.json", "r") as sf:
                                    self.game_state["settings"] = json.load(sf)
                                print("[DEBUG] Loaded settings from separate file")
                            except Exception as settings_e:
                                print(f"[ERROR] Failed to load settings file: {settings_e}")
                    self.result_queue.put(("status", "Game state loaded successfully"))
                except Exception as load_e:
                    print(f"[ERROR] Failed to load game state: {load_e}")
                    self.result_queue.put(("status", "Failed to load saved game, starting new game"))
                    # Reset to initial state
                    self.game_state = INITIAL_GAME_STATE.copy()
            else:
                print("[DEBUG] No saved game found, using initial state")
                self.result_queue.put(("status", "No saved game found, starting new game"))
            
            # --- Initialize Managers AFTER loading/setting game state ---
            print("[DEBUG] Initializing Character and Location Managers...")
            try:
                # Ensure 'companions' key exists, default if not found
                if 'companions' not in self.game_state:
                    print("[WARN] 'companions' key missing in game state, initializing empty.")
                    self.game_state['companions'] = {}
                
                self.character_manager = CharacterManager(self.game_state['companions'])
                self.location_manager = LocationManager(self.game_state, self.character_manager)
                print("[DEBUG] Managers initialized successfully.")
            except Exception as manager_e:
                print(f"[ERROR] Failed to initialize managers: {manager_e}")
                traceback.print_exc()
                self.result_queue.put(("error", f"Failed to initialize game managers: {str(manager_e)}"))
                self.result_queue.put(("screen", AppScreen.SETTINGS)) # Go to settings if managers fail
                return # Stop initialization if managers fail
            
            # Generate initial scene description if needed
            if not self.game_state.get("narrative_context_summary"):
                print("[DEBUG] No narrative context found, setting default")
                self.result_queue.put(("status", "Generating initial narrative..."))
                # Set a default narrative if none exists
                self.game_state["narrative_context_summary"] = "You stand at the beginning of your adventure."
            
            # Try to get visual placeholders
            try:
                print("[DEBUG] Calling Gemini for initial placeholders...")
                initial_gemini_prompt = construct_gemini_prompt(
                    narrative_text="The adventure begins.",
                    game_state=self.game_state,
                    placeholder_template=self.prompt_templates.get("gemini_placeholder_template", "")
                )
                initial_placeholders = call_gemini_api(
                    self.gemini_client, 
                    self.gemini_model_name, 
                    initial_gemini_prompt
                )
                print(f"[DEBUG] Got placeholders: {initial_placeholders[:50]}...")
                self.result_queue.put(("placeholders", initial_placeholders))
            except Exception as e:
                print(f"[WARN] Failed Gemini call: {e}")
                self.result_queue.put(("placeholders", "[ Visual placeholders unavailable ]"))
            
            # Switch to game screen
            print("[DEBUG] Initialization complete, switching to game screen")
            self.result_queue.put(("screen", AppScreen.GAME))
        
        except Exception as e:
            print(f"[ERROR] Initialization failed with exception: {e}")
            traceback.print_exc()
            self.result_queue.put(("error", f"Failed to initialize game: {str(e)}"))
            # Fall back to settings screen if game fails to load
            self.result_queue.put(("screen", AppScreen.SETTINGS))
    
    def setup_ui(self):
        """Set up the main UI components"""
        try:
            # Game UI components
            self.narrative_display = ft.Markdown(
                value="",
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                expand=True,
            )
            
            # Wrap the Markdown widget in a scrollable ListView
            self.scrollable_narrative_view = ft.ListView(
                [self.narrative_display],
                expand=True,
                auto_scroll=True,
                spacing=10,
            )
            
            # Container for styling (border, padding) around the scrollable view
            self.narrative_container = ft.Container(
                content=self.scrollable_narrative_view,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=ft.border_radius.all(10),
                padding=20,
                expand=True,
            )
            
            self.visuals_display = ft.Text(
                value="",
                italic=True,
                color=ft.Colors.GREY_400,
            )
            
            self.player_input = ft.TextField(
                label="What do you do?",
                hint_text="Type your action here...",
                expand=True,
                shift_enter=True,
                on_submit=lambda e: self.submit_player_input(e),
                border_color=ft.Colors.GREY_700,
                focused_border_color=ft.Colors.BLUE_500,
            )
            
            self.submit_button = ft.ElevatedButton(
                "Submit",
                on_click=lambda e: self.submit_player_input(e),
                style=ft.ButtonStyle(
                    bgcolor={"": ft.Colors.BLUE_700},
                ),
            )
            
            self.settings_button = ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.SETTINGS),
                    ft.Text("Settings"),
                ]),
                on_click=lambda e: self.navigate_to_settings(),
                style=ft.ButtonStyle(
                    bgcolor={"": ft.Colors.PURPLE_700},
                ),
            )
            
            self.progress_ring = ft.ProgressRing(visible=False, width=20, height=20)
            self.status_bar = ft.Text("", italic=True, size=12)
            
            # Game screen container
            self.game_screen = ft.Column(
                controls=[
                    self.narrative_container,
                    ft.Container(
                        content=self.visuals_display,
                        padding=ft.padding.only(top=10, bottom=10),
                    ),
                    ft.Row(
                        [
                            self.player_input,
                            self.submit_button,
                            self.progress_ring,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            self.status_bar,
                            ft.Container(expand=True),  # Replaced Spacer with Container
                            self.settings_button,
                        ],
                    ),
                ],
                spacing=10,
                expand=True,
            )
            
            # Loading screen
            self.loading_message = ft.Text("Initializing...", size=20)
            self.loading_progress = ft.ProgressRing(width=40, height=40)
            self.debug_message = ft.Text("", size=14, color=ft.Colors.AMBER_400, visible=False)
            
            self.loading_screen = ft.Column(
                [
                    ft.Container(height=100),
                    ft.Row(
                        [self.loading_message],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(height=20),
                    ft.Row(
                        [self.loading_progress],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(height=20),
                    ft.Row(
                        [self.debug_message],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
            
            # Settings screen will be created on demand
            self.settings_screen = None
            
            # Set initial screen
            self.page.controls = [self.loading_screen]
            self.page.update()
            
            print("[DEBUG] UI setup complete")
        except Exception as e:
            print(f"[ERROR] UI setup failed: {e}")
            traceback.print_exc()
    
    def ui_update_loop(self):
        """Process updates from result queue to update UI"""
        print("[DEBUG] UI update loop started")
        while True:
            try:
                message_type, data = self.result_queue.get(timeout=0.1)
                # Removed print statement here to reduce noise
                # print(f"[DEBUG] UI message received: {message_type}")

                if message_type == "status":
                    # Update status bar and debug message
                    self.status_bar.value = data
                    self.loading_message.value = data
                    # Display on debug message too during loading
                    if self.current_screen == AppScreen.LOADING:
                        self.debug_message.value = f"Status: {data}"
                        self.debug_message.visible = True
                    self.page.update()

                elif message_type == "screen":
                    # Change current screen
                    print(f"[DEBUG] Navigating to screen: {data}")
                    self.navigate_to_screen(data)

                elif message_type == "placeholders":
                    # Update visual placeholders
                    self.visuals_display.value = data
                    self.page.update()

                elif message_type == "narrative":
                    # Update narrative display
                    self.narrative_display.value = data
                    self.page.update()

                elif message_type == "game_state":
                    # Update game state
                    self.game_state = data
                    self.save_game_state()
                    # No page update needed just for saving state unless UI depends on it directly

                elif message_type == "turn_complete":
                    # Turn is complete, enable input
                    self.player_input.disabled = False
                    self.submit_button.disabled = False
                    self.progress_ring.visible = False
                    self.player_input.focus()
                    self.page.update()

                elif message_type == "error":
                    # Display error
                    self.status_bar.value = f"Error: {data}"
                    self.loading_message.value = f"Error: {data}"
                    self.debug_message.value = f"ERROR: {data}"
                    self.debug_message.visible = True
                    self.page.update()

            except Empty: # Specifically catch queue.Empty
                # Queue was empty, this is expected when idle, do nothing.
                pass
            except Exception as e:
                # Log other unexpected errors
                print(f"[ERROR] Unexpected UI update loop error: {repr(e)}")
                traceback.print_exc() # Print full traceback for debugging
    
    def navigate_to_screen(self, screen: AppScreen):
        """Navigate to the specified screen"""
        try:
            print(f"[DEBUG] Navigating to screen: {screen}")
            self.current_screen = screen
            
            if screen == AppScreen.GAME:
                # Update narrative display with current state
                narrative_text = self.game_state.get("narrative_context_summary", "Your adventure begins...")
                print(f"[DEBUG] Setting narrative: {narrative_text[:50]}...")
                self.narrative_display.value = narrative_text
                
                # Show game screen
                self.page.controls = [self.game_screen]
                self.status_bar.value = "Ready for your next action"
                self.player_input.disabled = False
                self.submit_button.disabled = False
                # Update the page *before* trying to focus
                self.page.update()
                self.player_input.focus()
            
            elif screen == AppScreen.SETTINGS:
                # Create settings screen if needed
                print("[DEBUG] Creating settings screen")
                if not self.settings_screen:
                    self.settings_screen = create_settings_page(
                        self.page,
                        on_save_callback=self.handle_settings_save,
                        on_back_callback=lambda: self.navigate_to_screen(AppScreen.GAME)
                    )
                else:
                    # Refresh settings page (in case we want to rebuild the UI)
                    self.settings_screen.build()
                
                # Settings UI is handled by the settings_page module
            
            elif screen == AppScreen.LOADING:
                # Show loading screen
                self.page.controls = [self.loading_screen]
            
            self.page.update()
            print(f"[DEBUG] Navigation to {screen} complete")
        except Exception as e:
            print(f"[ERROR] Navigation to {screen} failed: {e}")
            traceback.print_exc()
            # Try to show an error on whatever screen we're currently on
            self.debug_message.value = f"Navigation error: {str(e)}"
            self.debug_message.visible = True
            self.page.update()
    
    def navigate_to_settings(self):
        """Navigate to settings screen"""
        self.navigate_to_screen(AppScreen.SETTINGS)
    
    def handle_settings_save(self, settings: dict, is_new_game: bool):
        """Handle settings save from settings page"""
        try:
            print(f"[DEBUG] Handling settings save, new game: {is_new_game}")
            # Update game state with new settings
            self.game_state["settings"] = settings
            
            # If this is a new game, reset state
            if is_new_game:
                # Keep settings but reset other state
                old_settings = self.game_state["settings"]
                self.game_state = INITIAL_GAME_STATE.copy()
                self.game_state["settings"] = old_settings
                self.conversation_history = []
                self.turn_count = 0
            
            # Save game state
            self.save_game_state()
            
            # Navigate back to game
            self.navigate_to_screen(AppScreen.GAME)
        except Exception as e:
            print(f"[ERROR] Settings save failed: {e}")
            traceback.print_exc()
    
    def save_game_state(self):
        """Save game state to file"""
        try:
            with open("game_state.json", "w") as f:
                json.dump(self.game_state, f, indent=2)
            print("[INFO] Game state saved")
        except Exception as e:
            print(f"[ERROR] Failed to save game state: {e}")
    
    def submit_player_input(self, e):
        """Process player input"""
        # Get player input
        input_text = self.player_input.value.strip()
        if not input_text:
            return
        
        # Clear input field
        self.player_input.value = ""
        
        # Disable input during processing
        self.player_input.disabled = True
        self.submit_button.disabled = True
        self.progress_ring.visible = True
        self.status_bar.value = "Processing your action..."
        self.page.update()
        
        # Add player input to narrative display
        current_narrative = self.narrative_display.value
        self.narrative_display.value = f"{current_narrative}\n\n> **{input_text}**\n\n*Processing...*"
        self.page.update()
        
        # Ensure settings are available in game_state before processing
        if "settings" not in self.game_state and os.path.exists("game_settings.json"):
            try:
                with open("game_settings.json", "r") as f:
                    self.game_state["settings"] = json.load(f)
                print("[INFO] Loaded settings from file into game state")
            except Exception as e:
                print(f"[ERROR] Failed to load settings: {e}")
        
        # Process in background thread
        Thread(target=self.process_player_turn, args=(input_text,), daemon=True).start()
    
    def process_player_turn(self, input_text: str):
        """Process a player turn in the background using the new process_game_turn"""
        try:
            # Ensure managers are initialized
            if not self.character_manager or not self.location_manager:
                print("[ERROR] Managers not initialized before processing turn.")
                self.result_queue.put(("error", "Game managers failed to initialize."))
                self.result_queue.put(("turn_complete", True))
                return

            # Increment turn counter
            self.turn_count += 1
            self.result_queue.put(("status", f"Processing Turn {self.turn_count}..."))

            # Call the consolidated game turn processing function
            (
                updated_game_state,
                updated_conversation_history,
                narrative_text,
                placeholder_text,
                feedback_messages,
                stop_processing_flag # We might use this later if needed
            ) = process_game_turn(
                game_state=self.game_state,
                player_input_raw=input_text,
                conversation_history=self.conversation_history,
                character_manager=self.character_manager,
                location_manager=self.location_manager,
                claude_client=self.claude_client,
                claude_model_name=self.claude_model_name,
                gemini_client=self.gemini_client,
                gemini_model_name=self.gemini_model_name,
                prompt_templates=self.prompt_templates
            )

            # Update state based on results
            self.game_state = updated_game_state
            self.conversation_history = updated_conversation_history

            # --- Queue UI Updates ---

            # Combine narrative and feedback for display
            full_narrative_output = narrative_text or ""
            if feedback_messages:
                feedback_str = "\\n".join(filter(None, feedback_messages)) # Join with newlines
                # Remove the *Processing...* placeholder before adding feedback
                current_narrative_no_processing = self.narrative_display.value.replace("*Processing...*", "").strip()
                full_narrative_output = f"{current_narrative_no_processing}\\n\\n{narrative_text}\\n\\n*System Feedback:*\\n{feedback_str}"

            # If narrative is empty, use a placeholder
            if not narrative_text and not feedback_messages:
                 full_narrative_output = self.narrative_display.value.replace("*Processing...*", "(No response generated)")


            self.result_queue.put(("narrative", full_narrative_output))

            # Update visuals if provided
            if placeholder_text:
                self.result_queue.put(("placeholders", placeholder_text))
            else:
                # Clear placeholders if none were generated (optional)
                self.result_queue.put(("placeholders", ""))

            # Save the updated game state
            self.result_queue.put(("game_state", self.game_state))

            # Turn is complete
            self.result_queue.put(("status", f"Turn {self.turn_count} complete. Ready for your next action."))
            self.result_queue.put(("turn_complete", True))

        except Exception as e:
            import traceback
            print(f"[ERROR] Turn processing failed in Flet app: {e}")
            traceback.print_exc()
            # Try to recover gracefully by showing the error and re-enabling input
            self.result_queue.put(("error", f"Failed to process turn: {str(e)}"))
            # Also update the narrative display with the error
            error_narrative = self.narrative_display.value.replace("*Processing...*", f"**[ERROR]** {str(e)}")
            self.result_queue.put(("narrative", error_narrative))
            self.result_queue.put(("turn_complete", True)) # Still mark turn as complete to re-enable input
    
    def show_loading_screen(self, message: str):
        """Show loading screen with message"""
        self.loading_message.value = message
        self.current_screen = AppScreen.LOADING
        self.page.controls = [self.loading_screen]
        self.page.update()


# --- Main entry point --- #
def main(page: ft.Page):
    try:
        print("[DEBUG] Starting main app")
        GameApp(page)
    except Exception as e:
        # If we get an error during app startup, display it
        print(f"[CRITICAL] App startup error: {e}")
        traceback.print_exc()
        
        error_text = ft.Text(f"Critical error: {str(e)}", color=ft.Colors.RED)
        page.add(error_text)
        page.update()

if __name__ == "__main__":
    ft.app(target=main)