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
    """Class to play audio with synchronized lyrics."""

    def __init__(self) -> None:
        """Initialize the karaoke player with UI and audio components."""
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)  # Set more channels for flexibility

        # Initialize screen
        pygame.display.set_caption("Songs to Karaoke")
        self.WIDTH, self.HEIGHT = 800, 600
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))

        # Text display parameters
        self.text_margin = 80  # Horizontal margin for text (40px on each side)
        self.max_text_width = self.WIDTH - self.text_margin

        # Font setup
        pygame.font.init()
        self._setup_fonts()

        # Colors
        self.WHITE = (255, 255, 255)
        self.BRIGHT_WHITE = (255, 255, 255)
        self.DIM_WHITE = (150, 150, 150)
        self.BLACK = (0, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GRAY = (150, 150, 150)
        self.YELLOW = (255, 255, 0)

        # Playback state
        self.playing = False
        self.current_position = 0.0
        self.total_duration = 0.0  # Track total duration of the song
        self.vocals_enabled = False
        self.instrumental_sound: Optional[pygame.mixer.Sound] = None
        self.vocals_sound: Optional[pygame.mixer.Sound] = None
        self.transcription = None
        # Track channels for easier control
        self.instrumental_channel: Optional[pygame.mixer.Channel] = None
        self.vocals_channel: Optional[pygame.mixer.Channel] = None

        # Variables to handle pause/resume timing
        self.start_time = 0.0
        self.pause_time = 0.0
        self.accumulated_pause_time = 0.0

    def _setup_fonts(self) -> None:
        """Set up fonts with CJK character support.

        Attempts to find suitable fonts for the current platform that support
        both Latin and CJK characters.
        """
        try:
            default_font = None
            # Use a well-supported CJK font directly based on the platform
            if sys.platform == "darwin":  # macOS
                # Try multiple macOS fonts with good Unicode coverage in this order
                fonts = [
                    "Hiragino Sans GB",
                    "PingFang SC",
                    "STHeiti",
                    "AppleGothic",
                    "Osaka",
                ]
            elif sys.platform == "win32":  # Windows typically has these fonts
                fonts = [
                    "Microsoft JhengHei",
                    "Microsoft YaHei",
                    "Yu Gothic UI",
                    "Meiryo",
                    "Malgun Gothic",
                ]
            # Linux and others, try a common font
            else:
                fonts = [
                    "Noto Sans CJK TC",
                    "Noto Sans CJK SC",
                    "WenQuanYi Zen Hei",
                    "Noto Sans CJK JP",
                    "Noto Sans CJK KR",
                ]

            # Try each font until we find one that works
            for font in fonts:
                try:
                    test_font = pygame.font.SysFont(font, 32)
                    # Test render with some challenging unicode characters
                    test = test_font.render("測試 测试 テスト 한글", True, (255, 255, 255))
                    if test and test.get_width() > 10:  # Valid render check
                        default_font = font
                        break
                except Exception:
                    continue

            if not default_font:  # If none of the specific fonts worked, try the system default
                default_font = pygame.font.get_default_font()

            # Create fonts with direct CJK support
            self.font_large = pygame.font.SysFont(default_font, 36)  # Larger font for active lyric
            self.font = pygame.font.SysFont(default_font, 32)
            self.small_font = pygame.font.SysFont(default_font, 24)
            print(f"Using font: {default_font}")

            # Verify the font can render CJK characters
            test = self.font.render("测试 テスト 한글", True, (255, 255, 255))
            if test.get_width() < 10:  # If rendering failed or produced something too small
                raise Exception("Font cannot properly render CJK characters")

        except Exception as e:
            # If specific font fails, try to use default system font
            print(f"Error loading CJK font: {e}. Using system default font")
            try:
                default_font = pygame.font.get_default_font()
                self.font_large = pygame.font.Font(default_font, 36)
                self.font = pygame.font.Font(default_font, 32)
                self.small_font = pygame.font.Font(default_font, 24)
            except Exception as e:
                print(f"Error loading default font: {e}")
                # If even that fails, fall back to SysFont with Arial
                print("Falling back to Arial (may not display all characters correctly)")
                self.font_large = pygame.font.SysFont("Arial", 36)
                self.font = pygame.font.SysFont("Arial", 32)
                self.small_font = pygame.font.SysFont("Arial", 24)

    def load_audio(self, instrumental_path: str, vocals_path: Optional[str] = None) -> bool:
        """Load audio files for playback.

        Args:
            instrumental_path: Path to the instrumental audio track
            vocals_path: Optional path to the separated vocals track

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            print(f"Loading instrumental audio: {instrumental_path}")
            self.instrumental_sound = pygame.mixer.Sound(instrumental_path)
            # Reserve channel 0 for instrumental
            self.instrumental_channel = pygame.mixer.Channel(0)

            if vocals_path and os.path.exists(vocals_path):
                print(f"Loading vocals audio: {vocals_path}")
                self.vocals_sound = pygame.mixer.Sound(vocals_path)
                # Reserve channel 1 for vocals
                self.vocals_channel = pygame.mixer.Channel(1)
            else:
                self.vocals_sound = None
                self.vocals_channel = None

            # Set total duration of the song
            if self.instrumental_sound:
                self.total_duration = self.instrumental_sound.get_length()
                print(f"Total song duration: {int(self.total_duration//60):02d}:{int(self.total_duration%60):02d}")

            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False

    def load_transcription(self, transcription: Any) -> None:
        """Load transcription for display.

        Args:
            transcription: Transcription object containing timing and lyrics
        """
        self.transcription = transcription

    def toggle_vocals(self) -> None:
        """Toggle vocals on/off by changing volume."""
        self.vocals_enabled = not self.vocals_enabled

        if self.vocals_channel and self.vocals_sound:
            if self.vocals_enabled:
                self.vocals_channel.set_volume(1.0)
                print("Vocals enabled")
            else:
                self.vocals_channel.set_volume(0.0)
                print("Vocals disabled")

    def play(self) -> None:
        """Start playback and run the main display loop."""
        if not self.instrumental_sound:
            print("No audio loaded")
            return

        self.playing = True

        # Reset timing variables
        self.start_time = time.time()
        self.accumulated_pause_time = 0.0
        self.current_position = 0.0

        # Play instrumental on channel 0
        if self.instrumental_channel:
            self.instrumental_channel.play(self.instrumental_sound)

        # Always play vocals but control volume
        if self.vocals_sound and self.vocals_channel:
            self.vocals_channel.play(self.vocals_sound)
            # Set initial volume based on vocals_enabled state
            self.vocals_channel.set_volume(1.0 if self.vocals_enabled else 0.0)

        # Main playback loop
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Toggle pause/play
                        if self.playing:
                            # Store pause time when pausing
                            self.pause_time = time.time()
                            pygame.mixer.pause()
                        else:
                            # Calculate accumulated pause time when resuming
                            pause_duration = time.time() - self.pause_time
                            self.accumulated_pause_time += pause_duration
                            pygame.mixer.unpause()
                        self.playing = not self.playing
                    elif event.key == pygame.K_v:
                        # Toggle vocals
                        self.toggle_vocals()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            # Update current position if playing
            if self.playing:
                # Calculate current position considering accumulated pause time
                self.current_position = time.time() - self.start_time - self.accumulated_pause_time

                # Check if playback is still active
                if pygame.mixer.get_busy():
                    if self.current_position > self.total_duration:
                        # We've reached the end of the track
                        self.current_position = self.total_duration
                        running = False
                elif self.playing:
                    # If mixer is not busy but we think we're playing, playback has ended
                    running = False

                # Ensure current position doesn't exceed total duration
                if self.current_position > self.total_duration:
                    self.current_position = self.total_duration

            self._render_ui()
            pygame.display.flip()
            pygame.time.wait(50)  # ~20 FPS

            # Check if playback has finished
            if (not pygame.mixer.get_busy() and self.playing) or (self.current_position >= self.total_duration):
                running = False

        pygame.mixer.stop()
        self.playing = False

    def _render_ui(self) -> None:
        """Render the player UI including lyrics and controls."""
        # Clear screen with a gradient background
        self.screen.fill(self.BLACK)

        # Draw translucent overlay at the top for info display
        overlay_rect = pygame.Rect(0, 0, self.WIDTH, 70)
        overlay_surface = pygame.Surface((self.WIDTH, 70), pygame.SRCALPHA)
        overlay_surface.fill((20, 20, 30, 180))  # Dark blue with alpha
        self.screen.blit(overlay_surface, overlay_rect)

        # Draw progress bar background
        progress_bg_rect = pygame.Rect(20, 50, self.WIDTH - 40, 10)
        pygame.draw.rect(self.screen, (60, 60, 70), progress_bg_rect, border_radius=5)

        # Calculate and draw progress bar fill
        if self.total_duration > 0:
            progress_width = int((self.current_position / self.total_duration) * (self.WIDTH - 40))
            progress_rect = pygame.Rect(20, 50, progress_width, 10)
            progress_color = (100, 170, 255) if self.playing else (150, 150, 150)
            pygame.draw.rect(self.screen, progress_color, progress_rect, border_radius=5)

        # Format and draw time display (current/total)
        current_mins, current_secs = divmod(int(self.current_position), 60)
        total_mins, total_secs = divmod(int(self.total_duration), 60)

        time_text = f"{current_mins:02d}:{current_secs:02d} / {total_mins:02d}:{total_secs:02d}"
        time_surface = self.font.render(time_text, True, self.WHITE)
        time_rect = time_surface.get_rect(midtop=(self.WIDTH // 2, 10))
        self.screen.blit(time_surface, time_rect)

        # Draw vocals status with icon
        vocals_status = "ON" if self.vocals_enabled else "OFF"
        vocals_color = self.WHITE if self.vocals_enabled else self.GRAY
        vocals_text = f"Vocals: {vocals_status}"
        vocals_surface = self.small_font.render(vocals_text, True, vocals_color)
        vocals_rect = vocals_surface.get_rect(topleft=(20, 15))
        self.screen.blit(vocals_surface, vocals_rect)

        # Draw play/pause status with icon
        play_status = "Playing" if self.playing else "Paused"
        play_color = self.WHITE if self.playing else self.GRAY
        play_text = f"Status: {play_status}"
        play_surface = self.small_font.render(play_text, True, play_color)
        play_rect = play_surface.get_rect(topright=(self.WIDTH - 20, 15))
        self.screen.blit(play_surface, play_rect)

        # Draw lyrics as a flowing stream
        self._render_lyrics()

        # Draw translucent overlay at the bottom for controls
        bottom_overlay_rect = pygame.Rect(0, self.HEIGHT - 40, self.WIDTH, 40)
        bottom_overlay = pygame.Surface((self.WIDTH, 40), pygame.SRCALPHA)
        bottom_overlay.fill((20, 20, 30, 180))  # Dark blue with alpha
        self.screen.blit(bottom_overlay, bottom_overlay_rect)

        # Draw controls help
        controls_text = "[SPACE] Pause/Play  •  [V] Toggle Vocals  •  [ESC] Quit"
        controls_surface = self.small_font.render(controls_text, True, self.WHITE)
        controls_rect = controls_surface.get_rect(center=(self.WIDTH / 2, self.HEIGHT - 20))
        self.screen.blit(controls_surface, controls_rect)

    def _render_lyrics(self) -> None:
        """Render the lyrics with current segment highlighted."""
        if not self.transcription:
            return

        # Get segments around current time (2 before, 3 after)
        segments = self.transcription.get_segments_around_time(self.current_position, 2, 3)

        if not segments:
            return

        # Calculate vertical position to center the active lyrics
        active_index = -1
        for i, segment in enumerate(segments):
            if segment["active"]:
                active_index = i
                break

        # Set vertical spacing between lines for readability
        line_spacing = 60

        # Start position - center the active line vertically
        if active_index >= 0:
            y_center = self.HEIGHT // 2 + 20  # Move down a bit to account for top UI
            y_start = y_center - (active_index * line_spacing)
        else:
            y_start = self.HEIGHT // 2 - ((len(segments) - 1) * line_spacing // 2) + 20

        # Draw each segment
        y_pos = y_start
        for segment in segments:
            text = segment["text"]

            # Choose font and color based on whether this is the active segment
            if segment["active"]:
                font_to_use = self.font_large
                color = self.BRIGHT_WHITE
                # Add highlight effect for active lyrics
                text_width = font_to_use.size(text)[0]
                highlight_rect = pygame.Rect((self.WIDTH - text_width) // 2 - 10, y_pos - 10, text_width + 20, 45)
                highlight_surface = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                highlight_surface.fill((100, 170, 255, 30))  # Light blue with alpha
                self.screen.blit(highlight_surface, highlight_rect)
            else:
                font_to_use = self.font
                # Make segments further away from active more transparent
                distance = abs(segment["index"] - active_index) if active_index >= 0 else 1
                alpha = max(80, 255 - (distance * 50))  # Decrease alpha based on distance
                color = (
                    self.DIM_WHITE[0],
                    self.DIM_WHITE[1],
                    self.DIM_WHITE[2],
                    alpha,
                )

            # Split text into lines if too long
            lines = self.wrap_text(text, font_to_use)

            # Draw each line with additional spacing between multi-line segments
            inner_line_spacing = 40  # Spacing between lines of the same segment
            for line in lines:
                text_surface = font_to_use.render(line, True, color)
                text_rect = text_surface.get_rect(center=(self.WIDTH / 2, y_pos))
                self.screen.blit(text_surface, text_rect)
                y_pos += inner_line_spacing

            # Add extra space between segments
            y_pos += line_spacing - inner_line_spacing

    def wrap_text(self, text: str, font: pygame.font.Font) -> List[str]:
        """Wrap text to fit within the maximum text width.

        Handles both space-separated languages (like English) and character-based
        languages (like Chinese). Also handles very long words by breaking them
        when necessary.

        Args:
            text: The text to wrap
            font: The pygame font to use for size calculations

        Returns:
            List of wrapped text lines
        """
        # For languages without spaces (CJK), we need character-by-character wrapping
        # Check if the text contains mostly CJK characters
        if any(ord(c) > 0x3000 for c in text) and len([c for c in text if ord(c) > 0x3000]) > len(text) * 0.5:
            return self.wrap_cjk_text(text, font)

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Check if adding this word would exceed the width
            test_line = current_line + " " + word if current_line else word

            # If the word by itself is too long, we need to break it
            if font.size(word)[0] >= self.max_text_width:
                if current_line:  # Add the current line if it's not empty
                    lines.append(current_line)

                # Break the word into pieces that fit
                broken_word_lines = self.break_long_word(word, font)
                lines.extend(broken_word_lines)
                current_line = ""
                continue

            # Normal case - add word if it fits, otherwise start a new line
            if font.size(test_line)[0] < self.max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        if current_line:  # Don't forget the last line
            lines.append(current_line)

        return lines

    def wrap_cjk_text(self, text: str, font: pygame.font.Font) -> List[str]:
        """Wrap CJK text (Chinese, Japanese, Korean) character by character.

        CJK languages don't use spaces between words, so we need a different approach.

        Args:
            text: The CJK text to wrap
            font: The pygame font to use for size calculations

        Returns:
            List of wrapped text lines
        """
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

    def break_long_word(self, word: str, font: pygame.font.Font) -> List[str]:
        """Break a very long word into multiple lines.

        Args:
            word: The long word to break
            font: The pygame font to use for size calculations

        Returns:
            List of word fragments that fit within the width
        """
        lines = []
        current_line = ""

        for char in word:
            test_line = current_line + char
            if font.size(test_line)[0] < self.max_text_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    # Even a single character is too wide
                    # Just add it anyway and let it be slightly cut off
                    lines.append(char)
                    current_line = ""

        if current_line:
            lines.append(current_line)

        return lines

    def quit(self) -> None:
        """Clean up pygame resources."""
        pygame.mixer.quit()
        pygame.quit()
