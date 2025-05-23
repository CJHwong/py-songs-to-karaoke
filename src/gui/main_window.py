import pygame
import sys
import os

# Adjusting import path for SongLibrary assuming src is in PYTHONPATH or the script is run from the root
# If src is not in PYTHONPATH, and you run this file directly, this import might fail.
# It's designed to work when main.py (in the root) runs the GUI.
try:
    from src.library import SongLibrary
except ImportError:
    # This fallback allows running main_window.py directly for testing,
    # assuming library.py is in the parent directory relative to gui/
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    try:
        from library import SongLibrary
    except ImportError:
        # If it still fails, we might be in a situation where src is not recognized.
        # For now, we'll proceed and let it fail at runtime if SongLibrary is truly needed
        # and not found, which is better than a hard crash at import time for this structure.
        print("Warning: SongLibrary could not be imported. Ensure src directory is in PYTHONPATH or accessible.")
        SongLibrary = None # Define it as None to avoid NameError later, but functionality will be limited

try:
    from src.gui.import_dialog import ImportDialog
    from src.audio import AudioProcessor
    from src.transcription import TranscriptionProcessor
    from src.utils import get_env_path
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # one level up to src
    from gui.import_dialog import ImportDialog # if main_window is in gui
    from audio import AudioProcessor
    # from transcription import TranscriptionProcessor # Transcription is loaded in MainApp, not passed to player directly for processing
    from transcription import Transcription, TranscriptionProcessor # Need Transcription for loading
    from utils import get_env_path
    from src.player import KaraokePlayer # Import the refactored KaraokePlayer
    print("Warning: Had to adjust import paths for ImportDialog and processors.")


# Default constants for processors (consider centralizing these if used elsewhere)
# These are simplified for now; a real app might use a config file or more robust env var handling
DEFAULT_VOCAL_REMOVER_PATH = get_env_path("VOCAL_REMOVER_PATH", "/app/models/vocal-remover")
DEFAULT_WHISPER_MODEL_MAIN = get_env_path("WHISPER_MODEL_PATH", "models/ggml-large-v2.bin")
DEFAULT_WHISPER_SH_PATH_MAIN = get_env_path("WHISPER_SH_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "whisper.sh"))
DEFAULT_WHISPER_CPP_PATH = get_env_path("WHISPER_CPP_PATH", "/app/models/whisper.cpp")


class MainApp:
    """Main application class for the Karaoke Master GUI."""

    def __init__(self, library_path="karaoke_library.json"):
        """Initializes the Pygame application, screen, and UI elements."""
        if not pygame.get_init(): pygame.init()
        if not pygame.font.get_init(): pygame.font.init()  # Explicitly initialize font module

        # Screen dimensions
        self.screen_width = 1024
        self.screen_height = 768
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Karaoke Master")

        # Song Library
        if SongLibrary:
            self.song_library = SongLibrary(library_path=library_path)
        else:
            self.song_library = None # Will be an issue if not imported
            print("CRITICAL: SongLibrary is None. Most functionality will fail.")

        # Initialize Processors for ImportDialog
        self.audio_processor = AudioProcessor(vocal_remover_model_path=DEFAULT_VOCAL_REMOVER_PATH)
        self.transcription_processor = TranscriptionProcessor(
            whisper_sh_path=DEFAULT_WHISPER_SH_PATH_MAIN,
            whisper_model_path=DEFAULT_WHISPER_MODEL_MAIN,
            whisper_cpp_path=DEFAULT_WHISPER_CPP_PATH
        )
        
        # Check if paths for processors are valid, print warnings if not (for ImportDialog)
        if not os.path.exists(DEFAULT_VOCAL_REMOVER_PATH) and DEFAULT_VOCAL_REMOVER_PATH != "/app/models/vocal-remover": # avoid warning for default placeholder
            print(f"Warning: Default Vocal Remover path does not exist: {DEFAULT_VOCAL_REMOVER_PATH}")
        if not os.path.exists(DEFAULT_WHISPER_MODEL_MAIN) and DEFAULT_WHISPER_MODEL_MAIN != "models/ggml-large-v2.bin":
            print(f"Warning: Default Whisper Model path does not exist: {DEFAULT_WHISPER_MODEL_MAIN}")
        # script path is relative, so check might be tricky if cwd is not root.
        # if not os.path.exists(DEFAULT_WHISPER_SH_PATH_MAIN):
        #     print(f"Warning: Default Whisper Script path does not exist: {DEFAULT_WHISPER_SH_PATH_MAIN}")
        if not os.path.exists(DEFAULT_WHISPER_CPP_PATH) and DEFAULT_WHISPER_CPP_PATH != "/app/models/whisper.cpp":
            print(f"Warning: Default Whisper CPP path does not exist: {DEFAULT_WHISPER_CPP_PATH}")

        # Karaoke Player Instance
        self.karaoke_player = KaraokePlayer() # Will use its own internal font loading
        self.current_song_playing_data = None
        self.is_song_loaded = False
        self.master_volume = 0.5 # Initial volume for the player (0.0 to 1.0)
        self.karaoke_player.set_volume(self.master_volume)

        # Lyric Customization Settings
        self.lyric_font_size = 32
        self.lyric_active_colors = [(255, 255, 0), (0, 255, 255), (0, 255, 0), (255, 165, 0)] # Yellow, Cyan, Green, Orange
        self.lyric_inactive_colors = [(150, 150, 150), (120, 120, 180), (100, 140, 100), (180, 120, 80)] # Gray, Lavender, Dark Green, Brownish
        self.lyric_bg_colors = [(30, 30, 50), (10, 10, 10), (50, 30, 30), (30, 50, 30)] # Default Dark Blue, Black, Dark Red, Dark Green
        
        self.current_active_color_idx = 0
        self.current_inactive_color_idx = 0
        self.current_lyric_bg_color_idx = 0

        # Apply initial settings to KaraokePlayer
        self.karaoke_player.set_lyric_font_size(self.lyric_font_size)
        self.karaoke_player.set_active_lyric_color(self.lyric_active_colors[self.current_active_color_idx])
        self.karaoke_player.set_inactive_lyric_color(self.lyric_inactive_colors[self.current_inactive_color_idx])
        # Lyric panel BG color is handled by MainApp directly

        # Colors
        self.colors = {
            "bg_primary": (20, 20, 40),
            "bg_secondary": (30, 30, 50),
            "text_primary": (230, 230, 230),
            "text_secondary": (180, 180, 200),
            "accent": (100, 100, 255),
            "highlight": (150, 150, 255),
            "button": (70, 70, 90),
            "button_hover": (90, 90, 120),
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "red": (255, 50, 50),
        }

        # Fonts
        try:
            self.font_primary = pygame.font.SysFont("Arial", 24)
            self.font_secondary = pygame.font.SysFont("Arial", 18)
            self.font_title = pygame.font.SysFont("Arial", 30, bold=True)
        except Exception as e: # Fallback to default font
            print(f"Error loading system font Arial: {e}. Using default font.")
            self.font_primary = pygame.font.Font(None, 30) 
            self.font_secondary = pygame.font.Font(None, 24)
            self.font_title = pygame.font.Font(None, 36)


        # UI State
        self.running = True
        self.selected_song_id = None
        self.playback_status = "stopped"  # "playing", "paused", "stopped"
        self.current_song_list_scroll_offset = 0
        self.song_list_item_height = 30
        self.max_visible_songs = 15 # Example, adjust based on panel height

        # UI Element Rectangles (will be defined in _render_ui or a dedicated setup method)
        self.song_list_panel_rect = None
        self.playback_controls_panel_rect = None
        self.lyric_display_panel_rect = None
        self.import_button_rect = None
        self.play_button_rect = None
        self.pause_button_rect = None
        self.stop_button_rect = None
        self.next_button_rect = None
        self.prev_button_rect = None
        self.volume_slider_rect = None
        self.progress_bar_rect = None
        self.vocal_toggle_button_rect = None 
        
        # Lyric customization UI elements
        self.font_size_plus_rect = None
        self.font_size_minus_rect = None
        self.active_color_rect = None
        self.inactive_color_rect = None
        self.bg_color_rect = None
        self.lyric_options_y_start = 0 

        # Visualizer properties
        self.visualizer_bar_count = 10
        self.visualizer_bar_colors = [
            (50, 50, 150), (60, 60, 170), (70, 70, 190), (80, 80, 210), (90, 90, 230),
            (100, 100, 255), (110, 110, 250), (120, 120, 240), (130, 130, 220), (140, 140, 200)
        ] # Example: Shades of blue/purple
        self.visualizer_area_rect = None
        self.last_rms_levels = [0.0] * self.visualizer_bar_count # For smoothing/animation
        self.visualizer_smoothing_factor = 0.3 # 0.0 = no smoothing, 1.0 = instant

        # Store clickable rects for event handling
        self.clickable_elements = {} 

        # Import Dialog instance (created when needed)
        self.import_dialog = None
        
        # Surface for lyrics - created once
        self.lyric_panel_surface = None


    def _render_ui(self):
        """Renders all UI elements onto the screen."""
        self.screen.fill(self.colors["bg_primary"])
        self.clickable_elements.clear() 

        # Define panel dimensions
        song_list_width = int(self.screen_width * 0.3)
        # Reduce playback controls height slightly to make space for lyric options
        playback_controls_height = int(self.screen_height * 0.12) 
        lyric_options_height = int(self.screen_height * 0.05) 
        visualizer_height = int(self.screen_height * 0.04) # Additional space for visualizer
        self.lyric_options_y_start = self.screen_height - playback_controls_height - lyric_options_height - visualizer_height
        
        self.song_list_panel_rect = pygame.Rect(0, 0, song_list_width, self.lyric_options_y_start) 
        
        lyric_panel_x = song_list_width
        lyric_panel_y = 0
        lyric_panel_width = self.screen_width - song_list_width
        lyric_panel_height = self.lyric_options_y_start 
        self.lyric_display_panel_rect = pygame.Rect(lyric_panel_x, lyric_panel_y, lyric_panel_width, lyric_panel_height)
        
        if self.lyric_panel_surface is None or \
           self.lyric_panel_surface.get_width() != lyric_panel_width or \
           self.lyric_panel_surface.get_height() != lyric_panel_height:
            self.lyric_panel_surface = pygame.Surface((lyric_panel_width, lyric_panel_height))

        # Visualizer Area (below lyric options, above playback controls)
        self.visualizer_area_rect = pygame.Rect(0, self.lyric_options_y_start + lyric_options_height, self.screen_width, visualizer_height)

        # Lyric Options Panel
        self.lyric_options_panel_rect = pygame.Rect(0, self.lyric_options_y_start, self.screen_width, lyric_options_height)

        self.playback_controls_panel_rect = pygame.Rect(0, self.screen_height - playback_controls_height, self.screen_width, playback_controls_height)

        # Draw panels
        pygame.draw.rect(self.screen, self.colors["bg_secondary"], self.song_list_panel_rect)
        current_lyric_bg = self.lyric_bg_colors[self.current_lyric_bg_color_idx]
        self.lyric_panel_surface.fill(current_lyric_bg) 
        
        pygame.draw.rect(self.screen, self.colors["black"], self.lyric_options_panel_rect) 
        pygame.draw.rect(self.screen, self.colors["black"], self.visualizer_area_rect) # Visualizer bg
        pygame.draw.rect(self.screen, self.colors["black"], self.playback_controls_panel_rect) 

        # --- Song List Panel ---
        list_title_text = self.font_title.render("Song Library", True, self.colors["text_primary"])
        self.screen.blit(list_title_text, (self.song_list_panel_rect.x + 10, self.song_list_panel_rect.y + 10))

        self.import_button_rect = pygame.Rect(self.song_list_panel_rect.x + 10, self.song_list_panel_rect.y + 50, song_list_width - 20, 40)
        pygame.draw.rect(self.screen, self.colors["button"], self.import_button_rect)
        import_text = self.font_primary.render("Import Songs", True, self.colors["text_primary"])
        self.screen.blit(import_text, (self.import_button_rect.centerx - import_text.get_width() // 2, self.import_button_rect.centery - import_text.get_height() // 2))
        self.clickable_elements["import_songs"] = self.import_button_rect
        
        song_display_y_start = self.import_button_rect.bottom + 20
        if self.song_library:
            songs = self.song_library.get_all_songs() 
            if not songs:
                placeholder_text = self.font_secondary.render("No songs in library.", True, self.colors["text_secondary"])
                self.screen.blit(placeholder_text, (self.song_list_panel_rect.x + 10, song_display_y_start))
            else:
                available_height_for_list = self.song_list_panel_rect.height - (song_display_y_start - self.song_list_panel_rect.y) - 10 
                self.max_visible_songs = max(1, available_height_for_list // self.song_list_item_height)
                
                if len(songs) > 0:
                     self.current_song_list_scroll_offset = max(0, min(self.current_song_list_scroll_offset, len(songs) - self.max_visible_songs))
                else:
                    self.current_song_list_scroll_offset = 0

                for i, song in enumerate(songs[self.current_song_list_scroll_offset : self.current_song_list_scroll_offset + self.max_visible_songs]):
                    song_rect = pygame.Rect(self.song_list_panel_rect.x + 10, song_display_y_start + (i * self.song_list_item_height), self.song_list_panel_rect.width - 20, self.song_list_item_height)
                    color = self.colors["text_primary"]
                    is_currently_playing = self.current_song_playing_data and song.get("id") == self.current_song_playing_data.get("id")
                    
                    if is_currently_playing and self.playback_status == 'playing':
                        color = self.colors["accent"] # Color for the playing song
                        pygame.draw.rect(self.screen, self.colors["highlight"], song_rect.inflate(-2,-2),1)
                    elif song.get("id") == self.selected_song_id:
                        color = self.colors["highlight"]
                        pygame.draw.rect(self.screen, self.colors["accent"], song_rect.inflate(-4, -4)) 
                    
                    title = song.get("title", "Unknown Title")
                    artist = song.get("artist", "Unknown Artist")
                    display_text = f"{title} - {artist}"
                    song_text_surf = self.font_secondary.render(display_text, True, color)
                    self.screen.blit(song_text_surf, (song_rect.x + 5, song_rect.y + (self.song_list_item_height - song_text_surf.get_height()) // 2))
                    self.clickable_elements[f"song_{song.get('id')}"] = song_rect
        else:
            placeholder_text = self.font_secondary.render("Library not loaded.", True, self.colors["red"])
            self.screen.blit(placeholder_text, (self.song_list_panel_rect.x + 10, song_display_y_start))

        # --- Playback Controls Panel ---
        control_button_size = 45 # Slightly smaller buttons
        padding = 15
        # Adjusted start_x for 6 buttons: Prev, Play/Pause, Stop, Vocals, (Vol Up), (Vol Down)
        # For now, vol up/down are not actual buttons but placeholders for where they might go or for key controls
        num_buttons = 4 # Prev, Play/Pause, Stop, Vocals
        total_buttons_width = num_buttons * control_button_size + (num_buttons - 1) * padding
        start_x = self.playback_controls_panel_rect.centerx - total_buttons_width // 2
        
        button_y = self.playback_controls_panel_rect.centery - control_button_size // 2 - 10 # Shift up for progress bar

        self.prev_button_rect = pygame.Rect(start_x, button_y, control_button_size, control_button_size)
        self.play_button_rect = pygame.Rect(start_x + control_button_size + padding, button_y, control_button_size, control_button_size)
        self.pause_button_rect = self.play_button_rect # Same rect, content changes
        self.stop_button_rect = pygame.Rect(start_x + 2 * (control_button_size + padding), button_y, control_button_size, control_button_size)
        self.vocal_toggle_button_rect = pygame.Rect(start_x + 3 * (control_button_size + padding), button_y, control_button_size, control_button_size)
        # self.next_button_rect is removed for now, can be re-added if needed

        # Draw buttons
        pygame.draw.rect(self.screen, self.colors["button"], self.prev_button_rect)
        prev_text = self.font_primary.render("PREV", True, self.colors["text_primary"])
        self.screen.blit(prev_text, (self.prev_button_rect.centerx - prev_text.get_width()//2, self.prev_button_rect.centery - prev_text.get_height()//2))
        self.clickable_elements["prev_button"] = self.prev_button_rect

        play_pause_text_str = "PLAY"
        if self.playback_status == "playing":
            play_pause_text_str = "PAUSE"
            pygame.draw.rect(self.screen, self.colors["button_hover"], self.pause_button_rect)
            self.clickable_elements["pause_button"] = self.pause_button_rect
        else: # Paused or stopped
            pygame.draw.rect(self.screen, self.colors["button"], self.play_button_rect)
            self.clickable_elements["play_button"] = self.play_button_rect
        
        play_pause_text = self.font_primary.render(play_pause_text_str, True, self.colors["text_primary"])
        self.screen.blit(play_pause_text, (self.play_button_rect.centerx - play_pause_text.get_width()//2, self.play_button_rect.centery - play_pause_text.get_height()//2))

        pygame.draw.rect(self.screen, self.colors["button"], self.stop_button_rect)
        stop_text = self.font_primary.render("STOP", True, self.colors["text_primary"])
        self.screen.blit(stop_text, (self.stop_button_rect.centerx - stop_text.get_width()//2, self.stop_button_rect.centery - stop_text.get_height()//2))
        self.clickable_elements["stop_button"] = self.stop_button_rect
        
        vocal_btn_color = self.colors["button_hover"] if self.karaoke_player and self.karaoke_player.vocals_enabled else self.colors["button"]
        pygame.draw.rect(self.screen, vocal_btn_color, self.vocal_toggle_button_rect)
        vocal_text_str = "VOC" # Short for vocals
        vocal_text = self.font_primary.render(vocal_text_str, True, self.colors["text_primary"])
        self.screen.blit(vocal_text, (self.vocal_toggle_button_rect.centerx - vocal_text.get_width()//2, self.vocal_toggle_button_rect.centery - vocal_text.get_height()//2))
        self.clickable_elements["toggle_vocals"] = self.vocal_toggle_button_rect

        # Progress Bar & Time Display (now uses KaraokePlayer state)
        self.progress_bar_rect = pygame.Rect(self.playback_controls_panel_rect.x + padding, self.playback_controls_panel_rect.bottom - 30, self.playback_controls_panel_rect.width - 2*padding, 15)
        pygame.draw.rect(self.screen, self.colors["button"], self.progress_bar_rect) # Background
        
        current_pos_secs = 0
        total_dur_secs = 0
        if self.is_song_loaded and self.karaoke_player:
            current_pos_secs = self.karaoke_player.current_position
            total_dur_secs = self.karaoke_player.total_duration
            if total_dur_secs > 0:
                progress_ratio = current_pos_secs / total_dur_secs
                progress_fill_width = int(self.progress_bar_rect.width * progress_ratio)
                pygame.draw.rect(self.screen, self.colors["accent"], (self.progress_bar_rect.x, self.progress_bar_rect.y, progress_fill_width, self.progress_bar_rect.height))

        time_text = f"{int(current_pos_secs // 60):02d}:{int(current_pos_secs % 60):02d} / {int(total_dur_secs // 60):02d}:{int(total_dur_secs % 60):02d}"
        time_surface = self.font_secondary.render(time_text, True, self.colors["text_secondary"])
        time_text_rect = time_surface.get_rect(centerx=self.progress_bar_rect.centerx, bottom=self.progress_bar_rect.top - 5)
        self.screen.blit(time_surface, time_text_rect)
        
        # --- Lyric Options Panel Rendering ---
        opts_padding = 10
        opts_button_height = self.lyric_options_panel_rect.height - 2 * opts_padding
        opts_button_width = 100 # Adjust as needed
        
        # Font Size Controls
        self.font_size_minus_rect = pygame.Rect(self.lyric_options_panel_rect.x + opts_padding, self.lyric_options_panel_rect.y + opts_padding, 40, opts_button_height)
        pygame.draw.rect(self.screen, self.colors["button"], self.font_size_minus_rect)
        minus_text = self.font_primary.render("-", True, self.colors["text_primary"])
        self.screen.blit(minus_text, (self.font_size_minus_rect.centerx - minus_text.get_width()//2, self.font_size_minus_rect.centery - minus_text.get_height()//2))
        self.clickable_elements["font_minus"] = self.font_size_minus_rect
        
        font_size_display_x = self.font_size_minus_rect.right + opts_padding
        font_size_text = self.font_secondary.render(f"Font: {self.lyric_font_size}pt", True, self.colors["text_primary"])
        self.screen.blit(font_size_text, (font_size_display_x, self.lyric_options_panel_rect.centery - font_size_text.get_height()//2))
        
        self.font_size_plus_rect = pygame.Rect(font_size_display_x + font_size_text.get_width() + opts_padding, self.lyric_options_panel_rect.y + opts_padding, 40, opts_button_height)
        pygame.draw.rect(self.screen, self.colors["button"], self.font_size_plus_rect)
        plus_text = self.font_primary.render("+", True, self.colors["text_primary"])
        self.screen.blit(plus_text, (self.font_size_plus_rect.centerx - plus_text.get_width()//2, self.font_size_plus_rect.centery - plus_text.get_height()//2))
        self.clickable_elements["font_plus"] = self.font_size_plus_rect

        current_x_offset = self.font_size_plus_rect.right + opts_padding * 2

        # Color Cycle Buttons
        color_button_configs = [
            ("active_color_cycle", "Active Col", self.lyric_active_colors[self.current_active_color_idx]),
            ("inactive_color_cycle", "Inactive Col", self.lyric_inactive_colors[self.current_inactive_color_idx]),
            ("bg_color_cycle", "BG Col", current_lyric_bg) # Use the already fetched current_lyric_bg
        ]

        for key, text, color_val in color_button_configs:
            btn_rect = pygame.Rect(current_x_offset, self.lyric_options_panel_rect.y + opts_padding, opts_button_width, opts_button_height)
            pygame.draw.rect(self.screen, self.colors["button"], btn_rect) # Button background
            pygame.draw.rect(self.screen, color_val, btn_rect.inflate(-15, -15)) # Color preview swatch
            btn_text_surf = self.font_secondary.render(text, True, self.colors["text_primary"])
            self.screen.blit(btn_text_surf, (btn_rect.centerx - btn_text_surf.get_width()//2, btn_rect.y + 2)) # Text above swatch
            self.clickable_elements[key] = btn_rect
            current_x_offset += opts_button_width + opts_padding
            if key == "active_color_cycle": self.active_color_rect = btn_rect
            elif key == "inactive_color_cycle": self.inactive_color_rect = btn_rect
            elif key == "bg_color_cycle": self.bg_color_rect = btn_rect
            

        # --- Visualizer Rendering ---
        self._render_visualizer(self.screen) # Render directly onto the main screen within visualizer_area_rect

        # --- Lyric Display Panel ---
        if self.is_song_loaded and self.karaoke_player and self.lyric_panel_surface:
            self.karaoke_player.render_lyrics_onto_surface(self.lyric_panel_surface)
        elif self.lyric_panel_surface: 
             lyrics_placeholder_text = self.font_primary.render("Select a song and press Play.", True, self.colors["text_secondary"])
             self.lyric_panel_surface.blit(lyrics_placeholder_text, 
                                     (self.lyric_panel_surface.get_width() // 2 - lyrics_placeholder_text.get_width() // 2, 
                                      self.lyric_panel_surface.get_height() // 2 - lyrics_placeholder_text.get_height() // 2))
        
        if self.lyric_panel_surface:
            self.screen.blit(self.lyric_panel_surface, self.lyric_display_panel_rect.topleft)

        pygame.display.flip()

    def _render_visualizer(self, target_surface: pygame.Surface):
        """Renders the audio visualizer bars."""
        if not self.visualizer_area_rect:
            return

        bar_area_width = self.visualizer_area_rect.width
        bar_area_height = self.visualizer_area_rect.height
        padding = 5 # Padding around the visualizer area and between bars
        
        num_bars = self.visualizer_bar_count
        # Total width for bars = area_width - 2*padding
        # Width per bar = (total_width_for_bars - (num_bars-1)*padding_between_bars) / num_bars
        bar_total_alloc_width = (bar_area_width - 2 * padding) / num_bars
        bar_width = int(bar_total_alloc_width * 0.7) # 70% of allocated space for the bar itself
        bar_spacing = bar_total_alloc_width - bar_width # Remaining is spacing

        start_x = self.visualizer_area_rect.left + padding + (bar_total_alloc_width - bar_width) / 2 # Center first bar in its allocation

        current_rms = 0.0
        if self.is_song_loaded and self.karaoke_player and self.karaoke_player.playing:
            current_rms = self.karaoke_player.get_current_instrumental_rms_level()

        # Update all bars based on the single RMS value with some variation/smoothing
        # For this simple version, all bars will use a smoothed version of the same RMS.
        # A more advanced version could try to make them slightly different.
        
        # Smooth the RMS value for all bars
        for i in range(num_bars):
            # Apply smoothing: new_value = old_value * (1-factor) + new_rms_value * factor
            # This makes the bars change height more gradually.
            # Add a slight variation per bar for visual interest (e.g. using sin wave or small random offset)
            phase = (i / num_bars) * (3.14159 * 2) # Phase based on bar index
            rms_variation_factor = 0.8 + 0.2 * abs(pygame.math.Vector2(1,0).rotate_rad(phase).y) # Simple variation
            effective_rms = current_rms * rms_variation_factor

            self.last_rms_levels[i] = self.last_rms_levels[i] * (1 - self.visualizer_smoothing_factor) + \
                                      effective_rms * self.visualizer_smoothing_factor
        
        for i in range(num_bars):
            bar_height_normalized = max(0.0, min(1.0, self.last_rms_levels[i]))
            # Min height of 1px for visibility even at low RMS
            bar_height = max(1, int(bar_height_normalized * (bar_area_height - 2 * padding))) 
            
            bar_x = start_x + i * bar_total_alloc_width
            bar_y = self.visualizer_area_rect.bottom - padding - bar_height
            
            color_index = i % len(self.visualizer_bar_colors)
            bar_color = self.visualizer_bar_colors[color_index]
            
            pygame.draw.rect(target_surface, bar_color, (bar_x, bar_y, bar_width, bar_height))


    def _handle_event(self, event):
        """Handles a single Pygame event."""
        if event.type == pygame.QUIT:
            self.running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE: 
                if self.is_song_loaded and self.karaoke_player:
                    self.karaoke_player.pause_resume()
                    self.playback_status = "playing" if self.karaoke_player.playing else "paused"
                elif self.selected_song_id: 
                    self._play_selected_song()
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS: 
                self.lyric_font_size = min(72, self.lyric_font_size + 2)
                if self.karaoke_player: self.karaoke_player.set_lyric_font_size(self.lyric_font_size)
            elif event.key == pygame.K_MINUS: 
                self.lyric_font_size = max(16, self.lyric_font_size - 2)
                if self.karaoke_player: self.karaoke_player.set_lyric_font_size(self.lyric_font_size)
            elif event.key == pygame.K_v: 
                if self.karaoke_player: self.karaoke_player.toggle_vocals()


        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                mouse_pos = event.pos
                for element_name, rect in self.clickable_elements.items():
                    if rect.collidepoint(mouse_pos):
                        if element_name == "import_songs":
                            # ... (import logic remains same)
                            if not self.song_library: print("Error: SongLibrary not initialized.") ; return
                            if not self.audio_processor or not self.transcription_processor: print("Error: Processors not initialized.") ; return
                            self.import_dialog = ImportDialog(self.screen, self.song_library, self.audio_processor, self.transcription_processor, self.colors, self.fonts)
                            import_result = self.import_dialog.run()
                            if import_result and import_result.get("status") == "imported":
                                print(f"Successfully imported: {import_result.get('song_data', {}).get('title')}")
                            self.import_dialog = None
                        
                        elif element_name == "play_button":
                            if self.is_song_loaded and self.karaoke_player and not self.karaoke_player.playing: 
                                self.karaoke_player.pause_resume()
                                self.playback_status = "playing"
                            elif self.selected_song_id: 
                                self._play_selected_song()
                                
                        elif element_name == "pause_button": 
                            if self.is_song_loaded and self.karaoke_player and self.karaoke_player.playing:
                                self.karaoke_player.pause_resume()
                                self.playback_status = "paused"

                        elif element_name == "stop_button":
                            if self.is_song_loaded and self.karaoke_player:
                                self.karaoke_player.stop()
                                self.playback_status = "stopped"
                                self.is_song_loaded = False 
                        
                        elif element_name == "toggle_vocals":
                            if self.karaoke_player: self.karaoke_player.toggle_vocals()
                        elif element_name == "prev_button": print("Previous button clicked (placeholder)")
                        elif element_name == "volume_slider": print("Volume slider clicked (placeholder)")

                        elif element_name == "font_plus":
                            self.lyric_font_size = min(72, self.lyric_font_size + 2)
                            if self.karaoke_player: self.karaoke_player.set_lyric_font_size(self.lyric_font_size)
                        elif element_name == "font_minus":
                            self.lyric_font_size = max(16, self.lyric_font_size - 2)
                            if self.karaoke_player: self.karaoke_player.set_lyric_font_size(self.lyric_font_size)
                        
                        elif element_name == "active_color_cycle":
                            self.current_active_color_idx = (self.current_active_color_idx + 1) % len(self.lyric_active_colors)
                            if self.karaoke_player: self.karaoke_player.set_active_lyric_color(self.lyric_active_colors[self.current_active_color_idx])
                        elif element_name == "inactive_color_cycle":
                            self.current_inactive_color_idx = (self.current_inactive_color_idx + 1) % len(self.lyric_inactive_colors)
                            if self.karaoke_player: self.karaoke_player.set_inactive_lyric_color(self.lyric_inactive_colors[self.current_inactive_color_idx])
                        elif element_name == "bg_color_cycle":
                            self.current_lyric_bg_color_idx = (self.current_lyric_bg_color_idx + 1) % len(self.lyric_bg_colors)
                            # Background color is applied directly in _render_ui via self.lyric_panel_surface.fill()

                        elif element_name.startswith("song_"):
                            song_id = element_name.split("_")[1]
                            self.selected_song_id = song_id
                            selected_song_details = self.song_library.get_song_by_id(song_id)
                            print(f"Selected song: {selected_song_details.get('title') if selected_song_details else 'Unknown'}")
                        break 
            
            if self.song_list_panel_rect and self.song_list_panel_rect.collidepoint(event.pos):
                if event.button == 4: 
                    self.current_song_list_scroll_offset = max(0, self.current_song_list_scroll_offset -1)
                elif event.button == 5: 
                    if self.song_library:
                        num_songs = len(self.song_library.get_all_songs())
                        if num_songs > self.max_visible_songs: 
                             self.current_song_list_scroll_offset = min(num_songs - self.max_visible_songs , self.current_song_list_scroll_offset + 1)

    def _play_selected_song(self):
        """Helper function to load and play the currently selected song."""
        # Explicitly stop any current playback and reset MainApp's playback state first
        if self.karaoke_player:
            self.karaoke_player.stop() # Ensures player is fully stopped

        self.is_song_loaded = False
        self.playback_status = "stopped"
        self.current_song_playing_data = None # Clear previous song data

        if not self.selected_song_id or not self.song_library or not self.karaoke_player:
            print("Cannot play: No song selected, or library/player not available.")
            return

        song_data = self.song_library.get_song_by_id(self.selected_song_id)
        if not song_data:
            print(f"Error: Could not find song data for ID {self.selected_song_id}")
            return

        lyrics_path = song_data.get('lyrics_file_path')
        instrumental_path = song_data.get('instrumental_file_path')
        vocals_path = song_data.get('vocals_file_path') # Optional

        if not lyrics_path or not os.path.exists(lyrics_path):
            print(f"Error: Lyrics file not found for {song_data.get('title')}: {lyrics_path}")
            # Optionally display this error to the user via a GUI message
            # self.show_error_message(f"Lyrics file missing for {song_data.get('title')}")
            return
        if not instrumental_path or not os.path.exists(instrumental_path):
            print(f"Error: Instrumental file not found for {song_data.get('title')}: {instrumental_path}")
            # self.show_error_message(f"Instrumental file missing for {song_data.get('title')}")
            return
        if vocals_path and not os.path.exists(vocals_path):
            print(f"Warning: Vocals file specified but not found: {vocals_path}. Playing without vocals.")
            vocals_path = None # Proceed without vocals

        try:
            transcription = Transcription().load_from_file(lyrics_path)
            if not transcription:
                print(f"Error: Failed to load/parse transcription from {lyrics_path}")
                # self.show_error_message(f"Cannot load lyrics for {song_data.get('title')}")
                return
        except Exception as e:
            print(f"Error loading transcription {lyrics_path}: {e}")
            # self.show_error_message(f"Error with lyrics file for {song_data.get('title')}")
            return

        # Now, attempt to play the new song
        if self.karaoke_player.play_song(instrumental_path, vocals_path, transcription):
            self.current_song_playing_data = song_data # Set this only on successful play
            self.is_song_loaded = True
            self.playback_status = "playing"
            print(f"Playing: {song_data.get('title')}")
        else:
            # KaraokePlayer.play_song should ideally print its own errors.
            # Ensure MainApp state reflects that nothing is playing.
            print(f"Error starting playback for {song_data.get('title')} via KaraokePlayer.")
            self.current_song_playing_data = None # Keep consistent
            self.is_song_loaded = False
            self.playback_status = "stopped"
            # self.show_error_message(f"Could not play {song_data.get('title')}")


    def run(self):
        """Main loop for the application."""
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)
            
            if self.is_song_loaded and self.karaoke_player:
                player_status = self.karaoke_player.update()
                if player_status == "SONG_ENDED":
                    self.playback_status = "stopped"
                    self.is_song_loaded = False 
                    # Decide if current_song_playing_data should be cleared or if we allow "replay"
                    # For now, keep it selected, but not "loaded" for playback.
                    print(f"Song '{self.current_song_playing_data.get('title', '')}' finished.")
            
            self._render_ui() 
            
            clock.tick(30)

        if self.karaoke_player:
            self.karaoke_player.quit_player()
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    if SongLibrary:
        temp_lib_path = "temp_karaoke_library.json"
        temp_lib_songs_dir = temp_lib_path.replace(".json", "_songs")
        if os.path.exists(temp_lib_path): os.remove(temp_lib_path)
        if os.path.exists(temp_lib_songs_dir):
            import shutil
            shutil.rmtree(temp_lib_songs_dir)

        app_library = SongLibrary(library_path=temp_lib_path)
        if not app_library.get_all_songs():
            print("Adding dummy songs to new temp library for testing UI...")
            # These require actual dummy files to be playable by the integrated player
            # For testing, ensure these paths are valid or use the import dialog.
            # app_library.add_song({
            #     "title": "Dummy Song A (Pre-loaded)", "artist": "Test Dummy",
            #     "original_file_path": "dummy/a.mp3", 
            #     "instrumental_file_path": "assets/audio/dummy_instrumental.wav", # Needs real file
            #     "lyrics_file_path": "assets/audio/dummy_lyrics.json" # Needs real file
            # })
        
        main_app = MainApp(library_path=temp_lib_path)
    else:
        print("CRITICAL: Running MainApp without SongLibrary functionality due to import error.")
        main_app = MainApp() 
    
    main_app.run()

    if SongLibrary: # Cleanup
        if os.path.exists(temp_lib_path): os.remove(temp_lib_path)
        if os.path.exists(temp_lib_songs_dir):
            import shutil
            shutil.rmtree(temp_lib_songs_dir)
            print(f"Cleaned up {temp_lib_songs_dir}")
