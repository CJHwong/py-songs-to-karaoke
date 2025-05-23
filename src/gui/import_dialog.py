import pygame
import sys
import os

# Assuming src.utils, src.audio, src.transcription are accessible
# This structure is designed to be called from main_window.py, which is in the same directory
try:
    from src.utils import create_project_dir, create_temp_dir, cleanup_temp_dir, get_env_path
    from src.audio import AudioProcessor
    from src.transcription import Transcription, TranscriptionProcessor
    from src.library import SongLibrary # Though library instance is passed in
except ImportError:
    # Fallback for direct testing if needed, adjust paths accordingly
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..')) # Go up to project root
    from src.utils import create_project_dir, create_temp_dir, cleanup_temp_dir, get_env_path
    from src.audio import AudioProcessor
    from src.transcription import Transcription, TranscriptionProcessor
    from src.library import SongLibrary

# Default constants (similar to main.py, consider centralizing these)
DEFAULT_WHISPER_MODEL_GUI = "models/ggml-large-v2.bin"
DEFAULT_WHISPER_SH_PATH_GUI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "whisper.sh")


class ImportDialog:
    """A dialog for importing new songs into the library."""

    def __init__(self, screen: pygame.Surface, song_library: SongLibrary,
                 audio_processor: AudioProcessor, transcription_processor: TranscriptionProcessor,
                 parent_colors: dict, parent_fonts: dict):
        """
        Initializes the ImportDialog.

        Args:
            screen: The main Pygame screen surface to draw on.
            song_library: Instance of SongLibrary to add songs to.
            audio_processor: Instance of AudioProcessor.
            transcription_processor: Instance of TranscriptionProcessor.
            parent_colors: Dictionary of colors from the parent app.
            parent_fonts: Dictionary of fonts from the parent app.
        """
        self.screen = screen
        self.song_library = song_library
        self.audio_processor = audio_processor
        self.transcription_processor = transcription_processor
        self.colors = parent_colors
        self.fonts = parent_fonts
        
        pygame.font.init() # Ensure font module is initialized

        # Dialog dimensions and position
        self.dialog_width = 600
        self.dialog_height = 450
        self.dialog_rect = pygame.Rect(
            (self.screen.get_width() - self.dialog_width) // 2,
            (self.screen.get_height() - self.dialog_height) // 2,
            self.dialog_width,
            self.dialog_height
        )

        # UI Elements (rects will be defined in _render)
        self.title_text = "Import New Song"
        self.file_path_input_rect = None
        self.language_selector_rect = None
        self.skip_separation_checkbox_rect = None
        self.skip_separation_label_rect = None
        self.skip_transcription_checkbox_rect = None
        self.skip_transcription_label_rect = None
        self.import_button_rect = None
        self.cancel_button_rect = None
        self.clickable_elements = {}

        # State variables
        self.active = False # Controls the dialog's run loop
        self.file_path_text = "" # For actual input, this would be more complex
        self.input_active = False # Is the file_path_input field active
        self.available_languages = ["en", "zh"]
        self.selected_language_idx = 0
        self.skip_separation_checked = False
        self.skip_transcription_checked = False
        self.feedback_message = ""
        self.feedback_message_color = self.colors.get("text_primary", (230,230,230))
        self.is_processing = False # To disable buttons during import

        # --- TEMP: Hardcoded for now for testing file input ---
        self.test_file_paths = [
            # Add paths to actual audio files in your project for testing
            # e.g., "/app/assets/audio/your_song.mp3",
            # Make sure these files exist if you uncomment and use them.
        ]
        self.current_test_file_idx = 0
        if self.test_file_paths:
            self.file_path_text = self.test_file_paths[self.current_test_file_idx]
        else:
            self.file_path_text = "/path/to/your/song.mp3" # Default placeholder


    def _render(self):
        """Renders the dialog UI elements."""
        if not self.active:
            return

        # Draw semi-transparent overlay for modality
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Darken background
        self.screen.blit(overlay, (0,0))

        # Dialog background
        pygame.draw.rect(self.screen, self.colors.get("bg_secondary", (30,30,50)), self.dialog_rect)
        pygame.draw.rect(self.screen, self.colors.get("accent", (100,100,255)), self.dialog_rect, 2) # Border

        self.clickable_elements.clear()

        # Title
        title_surf = self.fonts.get("font_title", pygame.font.Font(None, 36)).render(self.title_text, True, self.colors.get("text_primary"))
        self.screen.blit(title_surf, (self.dialog_rect.centerx - title_surf.get_width() // 2, self.dialog_rect.y + 20))

        y_offset = self.dialog_rect.y + 70
        padding = 15
        input_height = 35
        label_font = self.fonts.get("font_primary", pygame.font.Font(None, 30))
        input_font = self.fonts.get("font_secondary", pygame.font.Font(None, 24))

        # File Path Input
        fp_label_surf = label_font.render("Audio File Path:", True, self.colors.get("text_primary"))
        self.screen.blit(fp_label_surf, (self.dialog_rect.x + padding, y_offset))
        y_offset += fp_label_surf.get_height() + 5
        self.file_path_input_rect = pygame.Rect(self.dialog_rect.x + padding, y_offset, self.dialog_width - 2 * padding, input_height)
        pygame.draw.rect(self.screen, self.colors.get("white", (255,255,255)) if self.input_active else self.colors.get("button", (70,70,90)), self.file_path_input_rect)
        pygame.draw.rect(self.screen, self.colors.get("black", (0,0,0)), self.file_path_input_rect, 1) # border
        fp_text_surf = input_font.render(self.file_path_text, True, self.colors.get("black", (0,0,0)))
        self.screen.blit(fp_text_surf, (self.file_path_input_rect.x + 5, self.file_path_input_rect.y + (self.file_path_input_rect.height - fp_text_surf.get_height()) // 2))
        self.clickable_elements["file_path_input"] = self.file_path_input_rect
        y_offset += input_height + padding

        # Language Selector
        lang_label_surf = label_font.render("Language:", True, self.colors.get("text_primary"))
        self.screen.blit(lang_label_surf, (self.dialog_rect.x + padding, y_offset))
        self.language_selector_rect = pygame.Rect(self.dialog_rect.x + padding + lang_label_surf.get_width() + 10, y_offset, 100, input_height)
        pygame.draw.rect(self.screen, self.colors.get("button", (70,70,90)), self.language_selector_rect)
        lang_text = self.available_languages[self.selected_language_idx]
        lang_surf = input_font.render(lang_text.upper(), True, self.colors.get("text_primary"))
        self.screen.blit(lang_surf, (self.language_selector_rect.centerx - lang_surf.get_width() // 2, self.language_selector_rect.centery - lang_surf.get_height() // 2))
        self.clickable_elements["language_selector"] = self.language_selector_rect
        y_offset += input_height + padding

        # Checkboxes
        checkbox_size = 20
        self.skip_separation_checkbox_rect = pygame.Rect(self.dialog_rect.x + padding, y_offset, checkbox_size, checkbox_size)
        self.skip_separation_label_rect = pygame.Rect(self.dialog_rect.x + padding + checkbox_size + 10, y_offset, self.dialog_width - (2*padding + checkbox_size + 10), input_height)
        pygame.draw.rect(self.screen, self.colors.get("button", (70,70,90)), self.skip_separation_checkbox_rect)
        if self.skip_separation_checked:
            pygame.draw.line(self.screen, self.colors.get("accent"),(self.skip_separation_checkbox_rect.left+3, self.skip_separation_checkbox_rect.centery), (self.skip_separation_checkbox_rect.centerx-2, self.skip_separation_checkbox_rect.bottom-3),2)
            pygame.draw.line(self.screen, self.colors.get("accent"),(self.skip_separation_checkbox_rect.centerx-2, self.skip_separation_checkbox_rect.bottom-3), (self.skip_separation_checkbox_rect.right-3, self.skip_separation_checkbox_rect.top+3),2)
        sep_label_surf = label_font.render("Skip Vocal Separation", True, self.colors.get("text_primary"))
        self.screen.blit(sep_label_surf, (self.skip_separation_label_rect.x, self.skip_separation_label_rect.y + (input_height - sep_label_surf.get_height())//2))
        self.clickable_elements["skip_separation_checkbox"] = self.skip_separation_checkbox_rect
        self.clickable_elements["skip_separation_label"] = self.skip_separation_label_rect # Click label also
        y_offset += input_height + padding

        self.skip_transcription_checkbox_rect = pygame.Rect(self.dialog_rect.x + padding, y_offset, checkbox_size, checkbox_size)
        self.skip_transcription_label_rect = pygame.Rect(self.dialog_rect.x + padding + checkbox_size + 10, y_offset, self.dialog_width - (2*padding + checkbox_size + 10), input_height)
        pygame.draw.rect(self.screen, self.colors.get("button", (70,70,90)), self.skip_transcription_checkbox_rect)
        if self.skip_transcription_checked:
            pygame.draw.line(self.screen, self.colors.get("accent"),(self.skip_transcription_checkbox_rect.left+3, self.skip_transcription_checkbox_rect.centery), (self.skip_transcription_checkbox_rect.centerx-2, self.skip_transcription_checkbox_rect.bottom-3),2)
            pygame.draw.line(self.screen, self.colors.get("accent"),(self.skip_transcription_checkbox_rect.centerx-2, self.skip_transcription_checkbox_rect.bottom-3), (self.skip_transcription_checkbox_rect.right-3, self.skip_transcription_checkbox_rect.top+3),2)
        trans_label_surf = label_font.render("Skip Transcription", True, self.colors.get("text_primary"))
        self.screen.blit(trans_label_surf, (self.skip_transcription_label_rect.x, self.skip_transcription_label_rect.y + (input_height - trans_label_surf.get_height())//2))
        self.clickable_elements["skip_transcription_checkbox"] = self.skip_transcription_checkbox_rect
        self.clickable_elements["skip_transcription_label"] = self.skip_transcription_label_rect
        y_offset += input_height + padding + 10 # Extra padding before buttons

        # Feedback Message
        if self.feedback_message:
            feedback_surf = self.fonts.get("font_secondary", pygame.font.Font(None, 24)).render(self.feedback_message, True, self.feedback_message_color)
            self.screen.blit(feedback_surf, (self.dialog_rect.centerx - feedback_surf.get_width() // 2, y_offset))
        y_offset += input_height # Make space for feedback or move buttons up if no feedback

        # Buttons
        button_width = 120
        button_height = 40
        self.import_button_rect = pygame.Rect(
            self.dialog_rect.centerx - button_width - padding // 2,
            self.dialog_rect.bottom - button_height - padding,
            button_width, button_height
        )
        self.cancel_button_rect = pygame.Rect(
            self.dialog_rect.centerx + padding // 2,
            self.dialog_rect.bottom - button_height - padding,
            button_width, button_height
        )

        # Import Button
        import_btn_color = self.colors.get("button_hover") if self.is_processing else self.colors.get("button")
        pygame.draw.rect(self.screen, import_btn_color, self.import_button_rect)
        import_text_surf = label_font.render("Import", True, self.colors.get("text_primary"))
        self.screen.blit(import_text_surf, (self.import_button_rect.centerx - import_text_surf.get_width() // 2, self.import_button_rect.centery - import_text_surf.get_height() // 2))
        self.clickable_elements["import_button"] = self.import_button_rect
        
        # Cancel Button
        cancel_btn_color = self.colors.get("button_hover") if self.is_processing else self.colors.get("button")
        pygame.draw.rect(self.screen, cancel_btn_color, self.cancel_button_rect)
        cancel_text_surf = label_font.render("Cancel", True, self.colors.get("text_primary"))
        self.screen.blit(cancel_text_surf, (self.cancel_button_rect.centerx - cancel_text_surf.get_width() // 2, self.cancel_button_rect.centery - cancel_text_surf.get_height() // 2))
        self.clickable_elements["cancel_button"] = self.cancel_button_rect

        pygame.display.flip() # Update only the dialog area if possible, or full flip

    def _set_feedback(self, message, is_error=False):
        self.feedback_message = message
        self.feedback_message_color = self.colors.get("red") if is_error else self.colors.get("text_primary")
        self._render() # Re-render to show feedback immediately
        if not self.is_processing: # Don't wait if it's an intermediate processing message
            pygame.time.wait(1500 if is_error else 1000) # Longer wait for errors

    def _handle_event(self, event):
        if not self.active:
            return None

        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    self.input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.file_path_text = self.file_path_text[:-1]
                else:
                    self.file_path_text += event.unicode
                return None # Consume event
            elif event.key == pygame.K_ESCAPE:
                if not self.is_processing:
                    self.active = False
                    return {"status": "cancelled"}
            # TEMP: Cycle through test file paths with TAB if input not active
            elif event.key == pygame.K_TAB and self.test_file_paths and not self.input_active:
                self.current_test_file_idx = (self.current_test_file_idx + 1) % len(self.test_file_paths)
                self.file_path_text = self.test_file_paths[self.current_test_file_idx]
                self._set_feedback(f"Selected test file: {os.path.basename(self.file_path_text)}")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_processing: # Ignore clicks if already processing
                return None

            mouse_pos = event.pos
            
            # Check file path input activation
            if self.file_path_input_rect.collidepoint(mouse_pos):
                self.input_active = True
                self._set_feedback("Enter audio file path (or TAB for test files if available)")
                return None
            else:
                self.input_active = False # Deactivate if clicked outside

            for element_name, rect in self.clickable_elements.items():
                if rect.collidepoint(mouse_pos):
                    if element_name == "language_selector":
                        self.selected_language_idx = (self.selected_language_idx + 1) % len(self.available_languages)
                        self._set_feedback(f"Language set to: {self.available_languages[self.selected_language_idx].upper()}")
                        return None
                    elif element_name == "skip_separation_checkbox" or element_name == "skip_separation_label":
                        self.skip_separation_checked = not self.skip_separation_checked
                        return None
                    elif element_name == "skip_transcription_checkbox" or element_name == "skip_transcription_label":
                        self.skip_transcription_checked = not self.skip_transcription_checked
                        return None
                    elif element_name == "import_button":
                        return self._process_import()
                    elif element_name == "cancel_button":
                        self.active = False
                        return {"status": "cancelled"}
        return None


    def _process_import(self):
        self.is_processing = True
        self._set_feedback("Starting import...", False) # This will render and immediately continue
        # Ensure "Importing..." stays visible
        self.feedback_message = "Processing... Please wait." 
        self.feedback_message_color = self.colors.get("accent", (100,100,255))
        self._render() # Re-render to show "Processing..."

        input_file = self.file_path_text
        lang = self.available_languages[self.selected_language_idx]

        if not os.path.exists(input_file):
            self._set_feedback(f"Error: Input file not found: {input_file}", True)
            self.is_processing = False
            return {"status": "error", "message": "File not found"}

        try:
            output_dir = self.song_library.library_path.replace(".json", "_songs") # Store songs near library
            project_dir, base_name = create_project_dir(input_file, output_dir)
            os.makedirs(project_dir, exist_ok=True) # create_project_dir might not make it if output_dir is specific
            
            temp_dir = create_temp_dir()
            self._set_feedback(f"Created project dir: {project_dir}")

            wav_path = os.path.join(temp_dir, f"{base_name}.wav")
            self._set_feedback("Converting to WAV...")
            if not self.audio_processor.convert_to_wav(input_file, wav_path):
                raise Exception("Failed to convert to WAV.")
            
            final_instrumental_path = wav_path # Default if separation skipped
            final_vocals_path = None

            if not self.skip_separation_checked:
                self._set_feedback("Separating vocals...")
                # Ensure vocal_remover_path is set in audio_processor
                if not self.audio_processor.vocal_remover_path:
                     raise Exception("Vocal remover path not configured in AudioProcessor.")
                
                # separate_vocals now returns paths in project_dir
                separated_instrumental, separated_vocals = self.audio_processor.separate_vocals(wav_path, project_dir)
                if not separated_instrumental: # It returns None, None on failure
                    self._set_feedback("Warning: Vocal separation failed. Using original audio as instrumental.", True)
                    # No change to final_instrumental_path, final_vocals_path remains None
                else:
                    final_instrumental_path = separated_instrumental
                    final_vocals_path = separated_vocals
                    self._set_feedback("Vocal separation complete.")
            else:
                self._set_feedback("Skipping vocal separation.")
                # Copy original wav to project_dir as instrumental if separation is skipped
                # This makes sure the instrumental is in the project folder
                proj_instrumental_path = os.path.join(project_dir, f"{base_name}_Instruments.wav")
                import shutil
                shutil.copy(wav_path, proj_instrumental_path)
                final_instrumental_path = proj_instrumental_path


            final_lyrics_path = None
            if not self.skip_transcription_checked:
                self._set_feedback("Transcribing lyrics...")
                # Ensure whisper paths are set in transcription_processor
                if not self.transcription_processor.whisper_model_path or \
                   not self.transcription_processor.whisper_cpp_path or \
                   not self.transcription_processor.whisper_sh_path:
                    raise Exception("Whisper paths not configured in TranscriptionProcessor.")

                audio_for_transcription = final_vocals_path if final_vocals_path and os.path.exists(final_vocals_path) else wav_path
                
                # TranscriptionProcessor saves files in output_dir specified (project_dir/whisper_output)
                whisper_out_dir = os.path.join(project_dir, "whisper_output")
                transcription_obj = self.transcription_processor.transcribe(
                    audio_for_transcription, lang, output_dir=whisper_out_dir
                )
                if transcription_obj:
                    # Save transcription to a known location in project_dir
                    final_lyrics_path = os.path.join(project_dir, f"{base_name}_transcription.json")
                    transcription_obj.save_to_file(final_lyrics_path)
                    self._set_feedback("Transcription complete.")
                else:
                    raise Exception("Transcription failed.")
            else:
                self._set_feedback("Skipping transcription.")

            # Add to library
            song_data = {
                "title": base_name.replace("_", " ").title(), # Basic title from filename
                "artist": "Unknown Artist", # Placeholder
                "original_file_path": input_file, # Store original path
                "project_directory": project_dir, # Store project path for easy access to all files
                "instrumental_file_path": final_instrumental_path,
                "vocals_file_path": final_vocals_path,
                "lyrics_file_path": final_lyrics_path,
                # cover_art_path can be added later
            }
            song_id = self.song_library.add_song(song_data)
            if song_id:
                self._set_feedback(f"Song '{song_data['title']}' imported successfully!", False)
                pygame.time.wait(1000) # Show success briefly
                self.active = False
                cleanup_temp_dir(temp_dir)
                self.is_processing = False
                return {"status": "imported", "song_id": song_id, "song_data": song_data}
            else:
                raise Exception("Failed to add song to library.")

        except Exception as e:
            error_msg = f"Import Error: {e}"
            print(error_msg) # Also print to console for more details
            self._set_feedback(error_msg, True)
            if 'temp_dir' in locals() and os.path.exists(temp_dir): # Check if temp_dir was defined
                cleanup_temp_dir(temp_dir)
            self.is_processing = False
            return {"status": "error", "message": str(e)}


    def run(self):
        """Runs the dialog loop, making it modal."""
        self.active = True
        self.is_processing = False
        self.feedback_message = "" # Clear feedback from previous run
        # Consider setting a default file path or clearing previous one
        # self.file_path_text = "/path/to/your/song.mp3" 

        # If using test paths, initialize with the first one
        if self.test_file_paths and not self.file_path_text:
             self.file_path_text = self.test_file_paths[self.current_test_file_idx]


        result = None
        while self.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: # Allow quitting app from dialog
                    self.active = False
                    pygame.quit()
                    sys.exit()
                
                res = self._handle_event(event)
                if res: # If event handled and returned a status (e.g. import done/cancelled)
                    result = res
                    # self.active will be set to False by handler if dialog should close

            self._render()
            pygame.time.Clock().tick(30) # Keep UI responsive

        return result


if __name__ == '__main__':
    # --- Example Usage for testing ImportDialog directly ---
    pygame.init()
    pygame.font.init()
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Import Dialog Test")

    # Mock parent app's colors and fonts
    colors = {
        "bg_primary": (20, 20, 40), "bg_secondary": (30, 30, 50),
        "text_primary": (230, 230, 230), "text_secondary": (180, 180, 200),
        "accent": (100, 100, 255), "highlight": (150, 150, 255),
        "button": (70, 70, 90), "button_hover": (90, 90, 120),
        "white": (255,255,255), "black": (0,0,0), "red": (255,50,50)
    }
    fonts = {
        "font_primary": pygame.font.SysFont("Arial", 24),
        "font_secondary": pygame.font.SysFont("Arial", 18),
        "font_title": pygame.font.SysFont("Arial", 30, bold=True)
    }

    # Setup for AudioProcessor and TranscriptionProcessor (adjust paths as needed)
    # These paths would typically be loaded from env or config in the main app
    VOCAL_REMOVER_PATH = get_env_path("VOCAL_REMOVER_PATH", "/app/models/vocal-remover") # Example default
    WHISPER_CPP_PATH = get_env_path("WHISPER_CPP_PATH", "/app/models/whisper.cpp")       # Example default
    
    # Ensure dummy/test models exist for testing if you run this directly
    # Or point to your actual models
    if not os.path.exists(VOCAL_REMOVER_PATH) or not os.path.isdir(VOCAL_REMOVER_PATH):
        print(f"Warning: VOCAL_REMOVER_PATH '{VOCAL_REMOVER_PATH}' does not exist or is not a directory. Vocal separation might fail.")
    if not os.path.exists(WHISPER_CPP_PATH) or not os.path.isdir(WHISPER_CPP_PATH):
        print(f"Warning: WHISPER_CPP_PATH '{WHISPER_CPP_PATH}' does not exist or is not a directory. Transcription might fail.")
    if not os.path.exists(DEFAULT_WHISPER_MODEL_GUI):
        print(f"Warning: Default Whisper model '{DEFAULT_WHISPER_MODEL_GUI}' not found.")
    if not os.path.exists(DEFAULT_WHISPER_SH_PATH_GUI):
         print(f"Warning: Whisper script '{DEFAULT_WHISPER_SH_PATH_GUI}' not found.")


    audio_processor = AudioProcessor(vocal_remover_model_path=VOCAL_REMOVER_PATH)
    transcription_processor = TranscriptionProcessor(
        whisper_sh_path=DEFAULT_WHISPER_SH_PATH_GUI,
        whisper_model_path=DEFAULT_WHISPER_MODEL_GUI, # This is the model file, not dir
        whisper_cpp_path=WHISPER_CPP_PATH # This is the directory for whisper.cpp executable
    )
    
    # Create a dummy library file for testing
    test_lib_file = "temp_dialog_test_library.json"
    if os.path.exists(test_lib_file): os.remove(test_lib_file)
    if os.path.exists(test_lib_file.replace(".json","_songs")):
        import shutil
        shutil.rmtree(test_lib_file.replace(".json","_songs"))

    song_library_instance = SongLibrary(library_path=test_lib_file)

    # Create a dummy audio file for testing
    # IMPORTANT: You need an actual audio file (e.g. mp3, wav) for the import to fully work.
    # Create a dummy assets/audio directory if it doesn't exist
    os.makedirs("assets/audio", exist_ok=True)
    dummy_audio_file = "assets/audio/test_song.mp3" # Replace with a real audio file path
    
    # Create a minimal valid dummy MP3 or WAV file if one doesn't exist
    # This is tricky. For now, we'll assume the user provides one for testing.
    # Or, the user can use the TAB functionality to cycle if test_file_paths is populated
    # with existing files.
    if not os.path.exists(dummy_audio_file):
        print(f"Warning: Test audio file '{dummy_audio_file}' not found. Please create it for full import testing.")
        print("You can still test the dialog UI. To test full import, provide a valid audio file.")
        # Fallback to prevent crash if file doesn't exist, but import will fail for this path
        # import_dialog.file_path_text = "dummy_non_existent.mp3"
    
    import_dialog = ImportDialog(screen, song_library_instance, audio_processor, transcription_processor, colors, fonts)
    
    # Add the dummy file to the test paths for easy selection with TAB
    import_dialog.test_file_paths.append(dummy_audio_file)
    import_dialog.file_path_text = import_dialog.test_file_paths[0]


    # Main loop for testing the dialog
    running_test = True
    show_dialog_button_rect = pygame.Rect(screen_width // 2 - 100, screen_height // 2 - 25, 200, 50)

    while running_test:
        screen.fill(colors["bg_primary"])
        
        # Button to open the dialog
        pygame.draw.rect(screen, colors["button"], show_dialog_button_rect)
        btn_text = fonts["font_primary"].render("Open Import Dialog", True, colors["text_primary"])
        screen.blit(btn_text, (show_dialog_button_rect.centerx - btn_text.get_width()//2, show_dialog_button_rect.centery - btn_text.get_height()//2))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_test = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if show_dialog_button_rect.collidepoint(event.pos):
                    print("Opening import dialog...")
                    result = import_dialog.run() # This will block until dialog is closed
                    print(f"Dialog closed with result: {result}")
                    if result and result.get("status") == "imported":
                        print(f"Song '{result['song_data']['title']}' added to library.")
                        print(f"All songs: {song_library_instance.get_all_songs()}")

        pygame.display.flip()
        pygame.time.Clock().tick(30)

    pygame.quit()
    # Clean up dummy files
    if os.path.exists(test_lib_file): os.remove(test_lib_file)
    if os.path.exists(test_lib_file.replace(".json","_songs")):
        import shutil
        shutil.rmtree(test_lib_file.replace(".json","_songs"))
    # if os.path.exists(dummy_audio_file): os.remove(dummy_audio_file) # Don't remove if it was a real file
    print(f"Cleaned up {test_lib_file} and its song directory.")
    sys.exit()
