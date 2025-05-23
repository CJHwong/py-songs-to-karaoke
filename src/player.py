#!/usr/bin/env python3
"""Player module for handling audio playback with synchronized lyrics."""

import os
import sys
import time
from typing import Any, List, Optional

# Set environment variable to hide pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame  # noqa: E402


class KaraokePlayer:
    """Class to play audio with synchronized lyrics, controllable externally."""

    def __init__(self, screen_surface: Optional[pygame.Surface] = None, width: int = 800, height: int = 600) -> None:
        """
        Initialize the karaoke player.

        Args:
            screen_surface: Optional Pygame surface to render lyrics onto.
                            If None, a new window will be created for standalone testing.
            width: Width of the lyric rendering area (if no screen_surface) or for text wrapping.
            height: Height of the lyric rendering area (if no screen_surface).
        """
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
        if not pygame.font.get_init():
            pygame.font.init()

        if screen_surface:
            self.screen = screen_surface
            self.WIDTH = screen_surface.get_width()
            self.HEIGHT = screen_surface.get_height()
            self.is_standalone = False
        else:
            self.WIDTH, self.HEIGHT = width, height
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT)) # For standalone testing
            pygame.display.set_caption("Karaoke Player (Standalone Test)")
            self.is_standalone = True


        # Text display parameters
        self.text_margin = 80  # Horizontal margin for text (40px on each side)
        self.max_text_width = self.WIDTH - self.text_margin

        # Font setup
        self.lyric_font_size = 32 # Default font size
        self.default_font_name = None # Will be determined by _setup_fonts
        self._setup_fonts(self.lyric_font_size)


        # Colors (can be customized or passed in if needed by MainApp)
        self.active_lyric_color = (255, 255, 0) # Default: Yellow
        self.inactive_lyric_color = (150, 150, 150) # Default: Dim White / Gray
        # self.WHITE = (255, 255, 255) # Replaced by active/inactive
        # self.BRIGHT_WHITE = (255, 255, 255) # Replaced by active_lyric_color
        # self.DIM_WHITE = (150, 150, 150) # Replaced by inactive_lyric_color
        self.BLACK = (0, 0, 0) # Used for background if standalone
        self.LYRIC_HIGHLIGHT_COLOR = (100, 170, 255, 30) # Background highlight for active line, can also be customized later

        # Playback state
        self.playing = False
        self.current_position = 0.0
        self.total_duration = 0.0
        self.vocals_enabled = False # Default to vocals off, or make it a parameter
        self.instrumental_sound: Optional[pygame.mixer.Sound] = None
        self.vocals_sound: Optional[pygame.mixer.Sound] = None
        self.transcription: Optional[Any] = None # Should be Transcription type
        
        self.instrumental_channel: Optional[pygame.mixer.Channel] = None
        self.vocals_channel: Optional[pygame.mixer.Channel] = None

        # Timing variables
        self.start_time = 0.0
        self.pause_time = 0.0
        self.accumulated_pause_time = 0.0
        
        # Default volumes
        self.master_volume = 1.0
        self.instrumental_volume_factor = 1.0
        self.vocals_volume_factor = 1.0 # Separate factor for vocals

        # For visualizer - raw audio data and properties
        self.instrumental_raw_samples = None # array.array of shorts
        self.instrumental_sample_rate = 44100 # Default, try to update from file
        self.instrumental_channels = 2 # Default, try to update from file
        self.rms_chunk_size = 512 # Number of samples to process for RMS


    def _setup_fonts(self, base_font_size: int) -> None:
        """
        Set up fonts with CJK character support based on the provided base size.
        """
        if not pygame.font.get_init():
            pygame.font.init()
            print("KaraokePlayer: Initialized pygame.font module.")

        self.lyric_font_size = base_font_size
        font_size_large = base_font_size + 4 # Active line slightly larger

        # Determine the default font name only once or if it hasn't been set
        if not self.default_font_name:
            try:
                selected_font_name = None
                if sys.platform == "darwin":
                    fonts_to_try = ["Hiragino Sans GB", "PingFang SC", "STHeiti", "AppleGothic", "Osaka"]
                elif sys.platform == "win32":
                    fonts_to_try = ["Microsoft JhengHei", "Microsoft YaHei", "Yu Gothic UI", "Meiryo", "Malgun Gothic"]
                else: # Linux and others
                    fonts_to_try = ["Noto Sans CJK TC", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "Noto Sans CJK JP", "Noto Sans CJK KR"]

                for font_name_try in fonts_to_try:
                    try:
                        # Test with a placeholder size first
                        test_font = pygame.font.SysFont(font_name_try, base_font_size)
                        # Test render with some challenging unicode characters
                        test_render = test_font.render("測試 测试 テスト 한글", True, (0,0,0)) # Use any color for test
                        if test_render and test_render.get_width() > 10:  # Valid render check
                            selected_font_name = font_name_try
                            break
                    except Exception:
                        continue
                
                if not selected_font_name:
                    selected_font_name = pygame.font.get_default_font()
                self.default_font_name = selected_font_name
                print(f"KaraokePlayer: Determined system font: {self.default_font_name}")

            except Exception as e:
                print(f"KaraokePlayer: Critical error finding system font: {e}. Falling back to Arial.")
                self.default_font_name = "Arial" # Ultimate fallback

        # Now create fonts with the determined name and current size
        try:
            self.font = pygame.font.SysFont(self.default_font_name, self.lyric_font_size)
            self.font_large = pygame.font.SysFont(self.default_font_name, font_size_large)
            # Verify CJK rendering with the chosen font and size
            test_render = self.font.render("测试 テスト 한글", True, (0,0,0))
            if test_render.get_width() < 10 and self.default_font_name != "Arial": # Arial might actually fail this for some systems
                print(f"Warning: Font {self.default_font_name} might not render CJK characters well at size {self.lyric_font_size}.")
        except Exception as e:
            print(f"KaraokePlayer: Error loading font {self.default_font_name} at size {self.lyric_font_size}: {e}. Falling back to Arial.")
            self.default_font_name = "Arial" # Fallback if chosen font fails at new size
            self.font = pygame.font.SysFont(self.default_font_name, self.lyric_font_size)
            self.font_large = pygame.font.SysFont(self.default_font_name, font_size_large)
        
        print(f"KaraokePlayer: Fonts re-created. Regular: {self.lyric_font_size}, Large: {font_size_large}")


    def set_lyric_font_size(self, size: int):
        """Sets the base font size for lyrics and reloads fonts."""
        min_font_size = 16
        max_font_size = 72 
        clamped_size = max(min_font_size, min(max_font_size, size))
        if clamped_size != self.lyric_font_size or not hasattr(self, 'font'): # Or if fonts not initialized
            self._setup_fonts(clamped_size) # This will update self.lyric_font_size

    def set_active_lyric_color(self, color: tuple):
        """Sets the color for the active lyric line."""
        self.active_lyric_color = color

    def set_inactive_lyric_color(self, color: tuple):
        """Sets the color for inactive lyric lines."""
        self.inactive_lyric_color = color


    def _load_audio_internal(self, instrumental_path: str, vocals_path: Optional[str] = None) -> bool:
        """Internal method to load audio files.

        Args:
            instrumental_path: Path to the instrumental audio track.
            vocals_path: Optional path to the separated vocals track.

        Returns:
            True if loading was successful, False otherwise.
        """
        self.instrumental_raw_samples = None # Clear previous samples

        try:
            print(f"KaraokePlayer: Loading instrumental audio: {instrumental_path}")
            
            # If it's a WAV, try to get its properties first
            if instrumental_path.lower().endswith(".wav"):
                try:
                    import wave
                    with wave.open(instrumental_path, 'rb') as wf:
                        self.instrumental_sample_rate = wf.getframerate()
                        self.instrumental_channels = wf.getnchannels()
                        # n_frames = wf.getnframes()
                        # samp_width = wf.getsampwidth() # Bytes per sample (e.g., 2 for 16-bit)
                        print(f"KaraokePlayer: WAV properties: SR={self.instrumental_sample_rate}, Channels={self.instrumental_channels}")
                except ImportError:
                    print("KaraokePlayer: 'wave' module not found. Using default sample rate/channels for WAV.")
                    self.instrumental_sample_rate = 44100
                    self.instrumental_channels = 2
                except wave.Error as e:
                    print(f"KaraokePlayer: Error reading WAV properties: {e}. Using defaults.")
                    self.instrumental_sample_rate = 44100
                    self.instrumental_channels = 2
            else: # For MP3 or others, Pygame doesn't easily give this. Assume defaults.
                print("KaraokePlayer: Non-WAV file. Assuming SR=44100, Channels=2 for RMS calculation.")
                self.instrumental_sample_rate = 44100
                self.instrumental_channels = 2

            self.instrumental_sound = pygame.mixer.Sound(instrumental_path)
            
            # Attempt to get raw samples for RMS calculation
            try:
                import array
                raw_bytes = self.instrumental_sound.get_raw()
                # Assuming 16-bit signed samples ('h')
                self.instrumental_raw_samples = array.array('h', raw_bytes)
                print(f"KaraokePlayer: Loaded {len(self.instrumental_raw_samples)} raw samples for instrumental.")
            except ImportError:
                print("KaraokePlayer: 'array' module not found. Cannot process raw samples for visualizer.")
                self.instrumental_raw_samples = None
            except Exception as e:
                print(f"KaraokePlayer: Error getting/processing raw samples: {e}")
                self.instrumental_raw_samples = None


            if not self.instrumental_channel: 
                 self.instrumental_channel = pygame.mixer.Channel(0) 

            if vocals_path and os.path.exists(vocals_path):
                print(f"KaraokePlayer: Loading vocals audio: {vocals_path}")
                self.vocals_sound = pygame.mixer.Sound(vocals_path)
                if not self.vocals_channel: 
                    self.vocals_channel = pygame.mixer.Channel(1) 
            else:
                self.vocals_sound = None
                if self.vocals_channel: self.vocals_channel.stop() 
                self.vocals_channel = None

            if self.instrumental_sound:
                self.total_duration = self.instrumental_sound.get_length()
                print(f"KaraokePlayer: Total song duration: {int(self.total_duration//60):02d}:{int(self.total_duration%60):02d}")
            else: 
                self.total_duration = 0.0
            return True
        except Exception as e:
            print(f"KaraokePlayer: Error loading audio: {e}")
            self.instrumental_sound = None
            self.vocals_sound = None
            self.instrumental_raw_samples = None
            self.total_duration = 0.0
            return False

    def _load_transcription_internal(self, transcription: Any) -> None:
        """Internal method to load transcription."""
        self.transcription = transcription
        print("KaraokePlayer: Transcription loaded.")


    def get_current_instrumental_rms_level(self) -> float:
        """
        Calculates the RMS volume of a small, recent segment of the instrumental audio.
        Requires raw audio data to be pre-loaded into self.instrumental_raw_samples.
        Returns a float value (e.g., 0.0 to 1.0).
        """
        if not self.playing or not self.instrumental_raw_samples or \
           not self.instrumental_sound or self.instrumental_channels == 0:
            return 0.0

        try:
            # Calculate the current sample index
            # current_sample_index = int(self.current_position * self.instrumental_sound.get_framerate()) # This is not available
            current_sample_frame = int(self.current_position * self.instrumental_sample_rate)
            
            # Index in the raw_samples array (interleaved if stereo)
            start_sample_idx = current_sample_frame * self.instrumental_channels
            
            # Ensure we don't read past the buffer
            if start_sample_idx + (self.rms_chunk_size * self.instrumental_channels) > len(self.instrumental_raw_samples):
                # Not enough samples left, or near the end
                # To avoid error, either return 0 or process remaining samples. Let's process remaining if any.
                actual_chunk_size_frames = (len(self.instrumental_raw_samples) - start_sample_idx) // self.instrumental_channels
                if actual_chunk_size_frames <=0: return 0.0
            else:
                actual_chunk_size_frames = self.rms_chunk_size

            chunk_to_process = self.instrumental_raw_samples[
                start_sample_idx : start_sample_idx + (actual_chunk_size_frames * self.instrumental_channels)
            ]

            if not chunk_to_process:
                return 0.0

            # Calculate RMS for the chunk
            # Sum of squares of samples. For stereo, can average channels or pick one.
            # Here, we'll average all samples in the chunk (mixes channels).
            sum_sq = 0.0
            for sample in chunk_to_process:
                sum_sq += sample * sample
            
            mean_sq = sum_sq / len(chunk_to_process)
            rms = mean_sq**0.5

            # Normalize RMS. Max possible for 16-bit signed sample is 32767.
            # This normalization is approximate.
            normalized_rms = rms / 32767.0 
            return min(1.0, normalized_rms * 2.0) # Multiply by 2 as RMS is usually lower than peak. Clamp at 1.0

        except Exception as e:
            # print(f"RMS Error: {e}") # Can be noisy
            return 0.0


    def play_song(self, instrumental_path: str, vocals_path: Optional[str], transcription_object: Any) -> bool:
        """
        Loads and starts playing a new song.

        Args:
            instrumental_path: Path to the instrumental audio track.
            vocals_path: Optional path to the vocals audio track.
            transcription_object: Transcription object for lyrics.

        Returns:
            True if song started successfully, False otherwise.
        """
        self.stop() 

        if not self._load_audio_internal(instrumental_path, vocals_path):
            return False
        self._load_transcription_internal(transcription_object)

        if not self.instrumental_sound:
            print("KaraokePlayer: No instrumental audio loaded to play.")
            return False

        self.playing = True
        self.start_time = time.time()
        self.accumulated_pause_time = 0.0
        self.current_position = 0.0

        if self.instrumental_channel and self.instrumental_sound:
            self.instrumental_channel.set_volume(self.master_volume * self.instrumental_volume_factor)
            self.instrumental_channel.play(self.instrumental_sound)
            print("KaraokePlayer: Instrumental playing.")

        if self.vocals_channel and self.vocals_sound:
            vol = self.master_volume * self.vocals_volume_factor if self.vocals_enabled else 0.0
            self.vocals_channel.set_volume(vol)
            self.vocals_channel.play(self.vocals_sound)
            print(f"KaraokePlayer: Vocals playing (volume: {vol}).")
        
        return True

    def pause_resume(self) -> None:
        """Toggles pause/resume of the current song."""
        if not self.instrumental_sound: # Nothing to pause/resume
            return

        if self.playing: # Currently playing, so pause
            self.pause_time = time.time()
            pygame.mixer.pause() # Pauses all channels
            self.playing = False
            print("KaraokePlayer: Paused.")
        else: # Currently paused, so resume
            if self.start_time == 0: # Song was stopped, not paused, treat as play
                 print("KaraokePlayer: Song was stopped. Call play_song() first.")
                 return

            pause_duration = time.time() - self.pause_time
            self.accumulated_pause_time += pause_duration
            pygame.mixer.unpause() # Unpauses all channels
            self.playing = True
            print("KaraokePlayer: Resumed.")
            # If mixer was stopped entirely (e.g. end of song), unpause might not restart.
            # This simple pause/resume assumes mixer is active but paused.

    def stop(self) -> None:
        """Stops playback and resets position."""
        pygame.mixer.stop() # Stops all channels
        self.playing = False
        self.current_position = 0.0
        self.accumulated_pause_time = 0.0
        self.start_time = 0.0 # Reset start time to indicate stopped state
        self.pause_time = 0.0
        print("KaraokePlayer: Playback stopped.")

    def set_volume(self, master_vol: float, instrumental_factor: Optional[float] = None, vocals_factor: Optional[float] = None):
        """
        Sets the volume for playback.

        Args:
            master_vol: Overall volume level (0.0 to 1.0).
            instrumental_factor: Specific factor for instrumental (0.0 to 1.0). Defaults to current.
            vocals_factor: Specific factor for vocals (0.0 to 1.0). Defaults to current.
        """
        self.master_volume = max(0.0, min(1.0, master_vol))
        if instrumental_factor is not None:
            self.instrumental_volume_factor = max(0.0, min(1.0, instrumental_factor))
        if vocals_factor is not None:
            self.vocals_volume_factor = max(0.0, min(1.0, vocals_factor))

        if self.instrumental_channel:
            self.instrumental_channel.set_volume(self.master_volume * self.instrumental_volume_factor)
        
        if self.vocals_channel:
            vol = self.master_volume * self.vocals_volume_factor if self.vocals_enabled else 0.0
            self.vocals_channel.set_volume(vol)
        
        print(f"KaraokePlayer: Master Volume set to {self.master_volume*100:.0f}%.")
        print(f"  Instrumental effective volume: { (self.master_volume * self.instrumental_volume_factor)*100:.0f}%")
        if self.vocals_sound:
             print(f"  Vocals effective volume (when enabled): { (self.master_volume * self.vocals_volume_factor)*100:.0f}%")


    def toggle_vocals(self) -> None:
        """Toggle vocals on/off by changing their channel's volume."""
        self.vocals_enabled = not self.vocals_enabled
        if self.vocals_channel and self.vocals_sound:
            vol = self.master_volume * self.vocals_volume_factor if self.vocals_enabled else 0.0
            self.vocals_channel.set_volume(vol)
            print(f"KaraokePlayer: Vocals {'enabled' if self.vocals_enabled else 'disabled'}. Volume set to {vol*100:.0f}%.")
        elif not self.vocals_sound:
            print("KaraokePlayer: No vocals track loaded to toggle.")


    def update(self) -> Optional[str]:
        """
        Updates playback state (e.g., current position).
        Should be called periodically by the main GUI loop.

        Returns:
            "SONG_ENDED" if the song has finished, None otherwise.
        """
        if self.playing:
            self.current_position = time.time() - self.start_time - self.accumulated_pause_time
            
            # Check if song ended
            # Using get_busy() is more reliable for end detection than just time for mixed sounds
            # However, if total_duration is accurate, time check is also good.
            # If using instrumental_channel.get_busy(), it only checks that one channel.
            # pygame.mixer.get_busy() checks if ANY channel is busy.
            if not pygame.mixer.get_busy() or (self.total_duration > 0 and self.current_position >= self.total_duration) :
                # Ensure position doesn't exceed duration visually
                if self.total_duration > 0:
                    self.current_position = self.total_duration
                
                # Don't call self.stop() here as it resets start_time, making get_busy() potentially true again if called too quickly by MainApp
                # Instead, set playing to false and let MainApp decide to call stop or play another.
                self.playing = False 
                print("KaraokePlayer: Song ended.")
                return "SONG_ENDED"
            
            # Ensure current position doesn't exceed total duration during normal play
            if self.total_duration > 0 and self.current_position > self.total_duration:
                 self.current_position = self.total_duration

        return None


    def render_lyrics_onto_surface(self, target_surface: pygame.Surface) -> None:
        """
        Renders the current lyrics onto the provided surface.

        Args:
            target_surface: The Pygame surface to draw lyrics on.
        """
        if not self.transcription or not self.playing: 
            return

        current_surface_width = target_surface.get_width()
        current_surface_height = target_surface.get_height()
        self.max_text_width = current_surface_width - self.text_margin 

        segments = self.transcription.get_segments_around_time(self.current_position, num_before=2, num_after=3)

        if not segments:
            return

        active_segment_index_in_list = -1
        for i, segment in enumerate(segments):
            if segment["active"]:
                active_segment_index_in_list = i
                break
        
        # Adjust line spacing based on current font size
        line_spacing = int(self.lyric_font_size * 1.8) 
        inner_line_spacing = int(self.lyric_font_size * 1.2)

        if active_segment_index_in_list != -1:
            height_before_active = sum(len(self.wrap_text(s["text"], self.font if s_idx != active_segment_index_in_list else self.font_large)) * inner_line_spacing + (line_spacing - inner_line_spacing) 
                                       for s_idx, s in enumerate(segments) if s_idx < active_segment_index_in_list)
            y_center = current_surface_height // 2 
            y_start = y_center - height_before_active
            active_lines = self.wrap_text(segments[active_segment_index_in_list]["text"], self.font_large)
            if active_lines:
                 y_start -= self.font_large.size(active_lines[0])[1] // 2
        else: 
            total_estimated_height = sum(len(self.wrap_text(s["text"], self.font)) * inner_line_spacing + (line_spacing - inner_line_spacing) for s in segments)
            if segments: total_estimated_height -= (line_spacing - inner_line_spacing) 
            y_start = (current_surface_height - total_estimated_height) // 2

        y_pos = y_start
        for i, segment in enumerate(segments):
            text = segment["text"]
            is_active = segment["active"]

            font_to_use = self.font_large if is_active else self.font
            
            alpha = 255
            if not is_active and active_segment_index_in_list != -1: 
                distance = abs(i - active_segment_index_in_list)
                alpha = max(80, 255 - (distance * 70)) 

            # Use customizable colors
            color_base = self.active_lyric_color if is_active else self.inactive_lyric_color
            final_color = (color_base[0], color_base[1], color_base[2], alpha if len(color_base) == 3 else color_base[3]) # Use original alpha if provided
            if len(color_base) == 3 and not is_active: # Apply calculated alpha only if base color has no alpha and is inactive
                 final_color = (color_base[0], color_base[1], color_base[2], alpha)


            lines = self.wrap_text(text, font_to_use)

            if is_active and lines:
                max_line_width = 0
                for line_text_surf_check in lines:
                    line_width_check = font_to_use.size(line_text_surf_check)[0]
                    if line_width_check > max_line_width:
                        max_line_width = line_width_check
                
                total_active_block_height = len(lines) * inner_line_spacing
                if lines: total_active_block_height -= (inner_line_spacing - font_to_use.get_height()) 

                highlight_rect_width = max_line_width + 20 
                highlight_rect_height = total_active_block_height + 10 
                
                highlight_x = (current_surface_width - highlight_rect_width) // 2
                highlight_y = y_pos - (font_to_use.get_height() // 2) + (inner_line_spacing //2) - highlight_rect_height//2 # Center highlight around text block
                                
                highlight_surface = pygame.Surface((highlight_rect_width, highlight_rect_height), pygame.SRCALPHA)
                highlight_surface.fill(self.LYRIC_HIGHLIGHT_COLOR) # This color could also be made customizable
                target_surface.blit(highlight_surface, (highlight_x, highlight_y))

            for line_idx, line_text in enumerate(lines):
                text_surface = font_to_use.render(line_text, True, final_color)
                # Center each line horizontally, y_pos is the baseline for the first line of segment
                text_rect = text_surface.get_rect(center=(current_surface_width / 2, y_pos + (line_idx * inner_line_spacing) + font_to_use.get_height() // 2))
                target_surface.blit(text_surface, text_rect)
            
            y_pos += len(lines) * inner_line_spacing # Advance y_pos by the height of the current segment block
            if i < len(segments) -1 : 
                 y_pos += (line_spacing - inner_line_spacing) # Add inter-segment spacing


    def wrap_text(self, text: str, font: pygame.font.Font) -> List[str]:
        """Wrap text to fit within the maximum text width.

        Handles both space-separated languages (like English) and character-based
        languages (like Chinese). Also handles very long words by breaking them.
        `self.max_text_width` must be set before calling this.
        """
        # This method remains largely the same logic but uses self.max_text_width
        # which is now updated based on the target_surface in render_lyrics_onto_surface.
        
        # For languages without spaces (CJK), we need character-by-character wrapping
        # Check if the text contains mostly CJK characters
        # A more robust check might be needed for mixed scripts.
        is_cjk_dominant = any(0x3000 <= ord(c) <= 0x9FFF or  # Common CJK
                              0xAC00 <= ord(c) <= 0xD7AF    # Hangul Syllables
                              for c in text) and \
                          sum(1 for c in text if 0x3000 <= ord(c) <= 0x9FFF or 0xAC00 <= ord(c) <= 0xD7AF) > len(text) * 0.4

        if is_cjk_dominant:
            return self._wrap_cjk_text_internal(text, font)

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            
            if font.size(word)[0] >= self.max_text_width: # Word itself is too long
                if current_line: # Add previous line
                    lines.append(current_line)
                
                broken_word_lines = self._break_long_word_internal(word, font)
                lines.extend(broken_word_lines)
                current_line = "" # Reset current_line as broken word is handled
                continue

            if font.size(test_line)[0] < self.max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        return lines

    def _wrap_cjk_text_internal(self, text: str, font: pygame.font.Font) -> List[str]:
        """Internal CJK text wrapping logic."""

        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if font.size(test_line)[0] < self.max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    def _break_long_word_internal(self, word: str, font: pygame.font.Font) -> List[str]:
        """Internal long word breaking logic."""
        lines = []
        current_line = ""
        for char in word:
            test_line = current_line + char
            if font.size(test_line)[0] < self.max_text_width:
                current_line = test_line
            else:
                if current_line: # If there was something before this char
                    lines.append(current_line)
                current_line = char # Start new line with current char
                # If even a single char is too wide, it will be added alone.
                # This might happen with very narrow max_text_width or huge font.
                if font.size(current_line)[0] >= self.max_text_width:
                    lines.append(current_line)
                    current_line = ""


        if current_line:
            lines.append(current_line)
        return lines

    def quit_player(self) -> None:
        """Stops audio and cleans up player-specific resources.
        Does not quit pygame globally, as MainApp might still be running.
        """
        self.stop() # Ensure all sounds are stopped
        print("KaraokePlayer: Player resources released (mixer channels stopped).")
        # Pygame.mixer.quit() and pygame.font.quit() could be called here
        # if KaraokePlayer was solely responsible for their init.
        # However, if MainApp also uses them, it should manage their lifecycle.
        # For now, just stopping channels is safest.

# Example usage for testing (remove or adapt for final integration)
if __name__ == "__main__":
    # This test needs a Transcription class mock or a real one from src.transcription
    # For simplicity, we'll mock a basic transcription structure.
    class MockTranscription:
        def __init__(self, segments_data):
            self.segments_data = segments_data
            self.current_segment_index = -1

        def get_segments_around_time(self, current_time_sec, num_before, num_after):
            # Find current segment based on time
            self.current_segment_index = -1
            for i, seg in enumerate(self.segments_data):
                if seg["start"] <= current_time_sec < seg["end"]:
                    self.current_segment_index = i
                    break
            
            if self.current_segment_index == -1: # No active segment
                # If time is before first segment
                if self.segments_data and current_time_sec < self.segments_data[0]["start"]:
                    start_idx = 0
                # If time is after last segment
                elif self.segments_data and current_time_sec >= self.segments_data[-1]["end"]:
                    start_idx = max(0, len(self.segments_data) - (num_before + num_after +1))
                else: # In a gap between segments
                    # Find the segment we just passed
                    passed_idx = -1
                    for i, seg in enumerate(self.segments_data):
                        if seg["end"] <= current_time_sec:
                            passed_idx = i
                        else: # First segment that starts after current_time
                            break
                    start_idx = max(0, passed_idx - num_before +1)

            else: # Active segment found
                 start_idx = max(0, self.current_segment_index - num_before)
            
            end_idx = min(len(self.segments_data), start_idx + num_before + num_after + 1)
            
            display_segments = []
            for i in range(start_idx, end_idx):
                seg_copy = self.segments_data[i].copy()
                seg_copy["active"] = (i == self.current_segment_index)
                seg_copy["index"] = i # Original index in full list
                display_segments.append(seg_copy)
            return display_segments

    # --- Test Setup ---
    pygame.init() # MainApp would do this
    pygame.font.init()
    pygame.mixer.init()

    WIDTH, HEIGHT = 800, 250 # Make surface smaller for lyrics test
    test_lyric_surface = pygame.Surface((WIDTH, HEIGHT)) # Surface MainApp would provide for lyrics
    
    # Main screen for the test environment (to see the lyric surface)
    main_screen = pygame.display.set_mode((WIDTH, HEIGHT + 50))
    pygame.display.set_caption("KaraokePlayer Test Environment")

    player = KaraokePlayer() # Initialize player (will create its own fonts, etc.)
    player.WIDTH = WIDTH # Override for test rendering on smaller surface
    player.HEIGHT = HEIGHT
    player.max_text_width = WIDTH - player.text_margin


    # Mock transcription data
    mock_lyrics_data = [
        {"text": "Line one, this is the first line.", "start": 0.0, "end": 3.0},
        {"text": "Line two, a bit longer for wrapping. 一二三四五六七八九十十一十二十三十四十五。", "start": 3.0, "end": 7.0},
        {"text": "Line three, short and sweet.", "start": 7.0, "end": 10.0},
        {"text": "Line four, the final line here.", "start": 10.0, "end": 15.0},
        {"text": "Supercalifragilisticexpialidocious even though the sound of it is something quite atrocious.", "start": 15.0, "end": 20.0},
    ] * 3 # Repeat for longer scroll test
    for i,s in enumerate(mock_lyrics_data): s['id'] = i # Add id for uniqueness if needed by transcription class

    mock_transcription = MockTranscription(mock_lyrics_data)
    player._load_transcription_internal(mock_transcription) # Use internal loader for mock
    
    # Dummy audio files (replace with actual silent WAVs for testing if possible, or expect errors if they don't exist)
    # Create dummy empty files for testing if they don't exist
    DUMMY_INSTRUMENTAL = "dummy_instrumental.wav"
    DUMMY_VOCALS = "dummy_vocals.wav"

    if not os.path.exists(DUMMY_INSTRUMENTAL):
        try:
            import wave
            with wave.open(DUMMY_INSTRUMENTAL, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(b'\x00\x00' * 44100 * 20) # 20 seconds of silence
            print(f"Created dummy file: {DUMMY_INSTRUMENTAL}")
        except Exception as e:
            print(f"Could not create dummy instrumental: {e}")

    # For vocals, it's optional, so we can skip creating it if not needed for a test.
    # if not os.path.exists(DUMMY_VOCALS):
    #     # Create DUMMY_VOCALS similarly if needed for testing vocals toggle

    # Test play_song
    if os.path.exists(DUMMY_INSTRUMENTAL):
        player.play_song(DUMMY_INSTRUMENTAL, DUMMY_VOCALS if os.path.exists(DUMMY_VOCALS) else None, mock_transcription)
        player.set_volume(0.1) # Low volume for testing
    else:
        print(f"Cannot test play_song: {DUMMY_INSTRUMENTAL} not found.")
        player.playing = True # Manually set to true to test lyric rendering without audio
        player.total_duration = 20.0 * 3 # Match mock_lyrics_data duration
        player.start_time = time.time()


    running_test = True
    clock = pygame.time.Clock()
    test_current_time = 0 # For testing without audio playback

    while running_test:
        dt = clock.tick(30) / 1000.0  # Delta time in seconds

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_test = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.pause_resume()
                elif event.key == pygame.K_s:
                    player.stop()
                elif event.key == pygame.K_v:
                    player.toggle_vocals()
                elif event.key == pygame.K_LEFT:
                    if player.playing: # Simple seek back for testing
                        player.start_time += 5 # Effectively moves current_position back by 5s
                        if player.current_position < 0: player.current_position = 0
                elif event.key == pygame.K_RIGHT:
                     if player.playing: # Simple seek forward
                        player.start_time -= 5
                        if player.current_position > player.total_duration : player.current_position = player.total_duration


        status = player.update() # Update player state
        if status == "SONG_ENDED":
            print("Test script: Song ended signal received.")
            # Loop the song for testing
            if os.path.exists(DUMMY_INSTRUMENTAL):
                 player.play_song(DUMMY_INSTRUMENTAL, DUMMY_VOCALS if os.path.exists(DUMMY_VOCALS) else None, mock_transcription)
                 player.set_volume(0.1)
            else: # Manual reset for no-audio test
                player.playing = True
                player.total_duration = 20.0 * 3
                player.start_time = time.time()
                player.current_position = 0.0
                player.accumulated_pause_time = 0.0


        # Simulate MainApp rendering
        main_screen.fill((50, 50, 50)) # Main app background
        test_lyric_surface.fill((10, 10, 20))  # Lyric panel background (dark blue)
        
        player.render_lyrics_onto_surface(test_lyric_surface) # Player renders to its designated surface
        
        main_screen.blit(test_lyric_surface, (0,0)) # MainApp blits this surface

        # Draw mock progress bar and time for test UI
        prog_bar_y = HEIGHT + 10
        if player.total_duration > 0:
            progress_ratio = player.current_position / player.total_duration
            pygame.draw.rect(main_screen, (100,100,100), (10, prog_bar_y, WIDTH-20, 20))
            pygame.draw.rect(main_screen, (150,180,255), (10, prog_bar_y, (WIDTH-20) * progress_ratio, 20))
        
        time_text_str = f"{int(player.current_position // 60):02}:{int(player.current_position % 60):02} / {int(player.total_duration // 60):02}:{int(player.total_duration % 60):02}"
        time_surf_test = pygame.font.SysFont("Arial", 18).render(time_text_str, True, (200,200,200))
        main_screen.blit(time_surf_test, (WIDTH//2 - time_surf_test.get_width()//2, prog_bar_y + 25))


        pygame.display.flip()

    player.quit_player()
    pygame.quit()
    
    # Clean up dummy files
    if os.path.exists(DUMMY_INSTRUMENTAL) and DUMMY_INSTRUMENTAL == "dummy_instrumental.wav":
        os.remove(DUMMY_INSTRUMENTAL)
    if os.path.exists(DUMMY_VOCALS) and DUMMY_VOCALS == "dummy_vocals.wav":
        os.remove(DUMMY_VOCALS)

    sys.exit()
