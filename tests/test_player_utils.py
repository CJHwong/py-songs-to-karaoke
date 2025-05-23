import unittest
import pygame
import os
import sys

import unittest.mock as mock # Import mock at module level

# Adjust path to import KaraokePlayer from src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.player import KaraokePlayer

class TestKaraokePlayerTextWrapping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize Pygame font and a KaraokePlayer instance for text wrapping tests."""
        # Mock pygame.mixer.init and set_num_channels to prevent them from running
        cls.mixer_init_patch = mock.patch('pygame.mixer.init')
        cls.mock_mixer_init = cls.mixer_init_patch.start()
        cls.mock_mixer_init.return_value = None

        cls.set_num_channels_patch = mock.patch('pygame.mixer.set_num_channels')
        cls.mock_set_num_channels = cls.set_num_channels_patch.start()
        cls.mock_set_num_channels.return_value = None

        pygame.init() # Pygame.init() also calls pygame.font.init()
        
        # Create a dummy player instance. 
        # Mixer functions are mocked, so it won't try to open audio devices.
        cls.player = KaraokePlayer(width=500, height=100) 
        
        # Set a specific font for consistent testing, Arial is widely available.
        # If Arial is not found, Pygame will use a default system font.
        try:
            cls.test_font_size = 20
            cls.test_font = pygame.font.SysFont("Arial", cls.test_font_size)
        except pygame.error:
            print("Arial font not found, using Pygame default font for player utility tests.")
            cls.test_font = pygame.font.Font(None, cls.test_font_size)
        
        cls.player.font = cls.test_font # Override player's font for consistency
        cls.player.max_text_width = 200 # Set a fixed max width for testing wrapping

    @classmethod
    def tearDownClass(cls):
        """Quit Pygame after tests and stop patches."""
        cls.mixer_init_patch.stop()
        cls.set_num_channels_patch.stop()
        pygame.quit()

    def test_wrap_text_empty_string(self):
        """Test wrapping an empty string."""
        self.assertEqual(self.player.wrap_text("", self.test_font), [])

    def test_wrap_text_short_string_no_wrap(self):
        """Test a short string that doesn't need wrapping."""
        text = "Hello world"
        self.assertEqual(self.player.wrap_text(text, self.test_font), [text])

    def test_wrap_text_long_english_string_needs_wrap(self):
        """Test a longer English string that requires wrapping."""
        # Estimate based on font size and max_text_width. 
        # Arial 20pt, width 200px -> approx 20-25 chars per line.
        text = "This is a long English sentence that should definitely wrap to multiple lines."
        wrapped_lines = self.player.wrap_text(text, self.test_font)
        self.assertTrue(len(wrapped_lines) > 1, "Text should wrap to multiple lines.")
        # Check if any line exceeds max_text_width (approximate check)
        for line in wrapped_lines:
            self.assertTrue(self.test_font.size(line)[0] <= self.player.max_text_width + self.test_font_size, 
                            f"Line '{line}' might be too long: {self.test_font.size(line)[0]}px vs max {self.player.max_text_width}px")
        self.assertEqual(" ".join(wrapped_lines), text)


    def test_wrap_text_single_very_long_word(self):
        """Test wrapping a single word that is longer than max_text_width."""
        long_word = "SupercalifragilisticexpialidociousAndEvenLongerWord"
        wrapped_lines = self.player.wrap_text(long_word, self.test_font)
        self.assertTrue(len(wrapped_lines) > 1, "Long word should be broken into multiple lines.")
        self.assertEqual("".join(wrapped_lines), long_word, "Broken word should reconstruct to original.")
        for line in wrapped_lines:
             self.assertTrue(self.test_font.size(line)[0] <= self.player.max_text_width + self.test_font_size, # Allow for slight overflow due to char break
                            f"Line '{line}' might be too long: {self.test_font.size(line)[0]}px vs max {self.player.max_text_width}px")


    def test_wrap_text_cjk_string(self):
        """Test wrapping a CJK string (no spaces)."""
        # Assuming CJK chars are roughly font_size wide. 200px / 20pt = 10 chars
        text = "一二三四五六七八九十Б十一十二十三十四" # Added a non-CJK char 'Б' to test mixed handling if CJK dominant
        wrapped_lines = self.player.wrap_text(text, self.test_font)
        self.assertTrue(len(wrapped_lines) >= 2, f"CJK text should wrap. Got: {wrapped_lines}")
        self.assertEqual("".join(wrapped_lines), text)
        for line in wrapped_lines:
            self.assertTrue(self.test_font.size(line)[0] <= self.player.max_text_width + self.test_font_size, # Allow for slight overflow
                            f"Line '{line}' might be too long: {self.test_font.size(line)[0]}px vs max {self.player.max_text_width}px")

    def test_wrap_text_mixed_scripts(self):
        """Test wrapping text with mixed English and CJK characters."""
        text = "Hello 世界 how are you? 你好吗？ThisIsAVeryLongEnglishWordInTheMix."
        wrapped_lines = self.player.wrap_text(text, self.test_font)
        self.assertTrue(len(wrapped_lines) > 1)
        # Reconstructing mixed script text is complex due to space handling.
        # Basic check: all original non-space characters should be present.
        original_no_space = "".join(text.split())
        wrapped_no_space = "".join("".join(wrapped_lines).split())
        self.assertEqual(wrapped_no_space, original_no_space)
        for line in wrapped_lines:
            self.assertTrue(self.test_font.size(line)[0] <= self.player.max_text_width + self.test_font_size,
                             f"Line '{line}' might be too long: {self.test_font.size(line)[0]}px vs max {self.player.max_text_width}px")


    def test_wrap_text_multiple_spaces_between_words(self):
        """Test that multiple spaces are condensed to one during wrapping (standard text split behavior)."""
        text = "Word1    Word2  Word3"
        expected = "Word1 Word2 Word3" # How text.split() and join would behave
        
        # Temporarily set a large width to avoid wrapping due to length
        original_max_width = self.player.max_text_width
        self.player.max_text_width = 1000 
        
        wrapped_lines = self.player.wrap_text(text, self.test_font)
        self.assertEqual(len(wrapped_lines), 1)
        self.assertEqual(wrapped_lines[0], expected)
        
        self.player.max_text_width = original_max_width # Restore

    def test_wrap_text_leading_trailing_spaces(self):
        """Test handling of leading/trailing spaces."""
        text = "  leading and trailing spaces  "
        expected_single_line = "leading and trailing spaces" # strip() then wrap
        
        original_max_width = self.player.max_text_width
        self.player.max_text_width = 1000 # Ensure no wrapping due to length

        wrapped_lines = self.player.wrap_text(text, self.test_font)
        self.assertEqual(len(wrapped_lines), 1)
        # The current wrap_text implementation relies on text.split() which handles stripping implicitly
        # when reconstructing. If the first word was "  leading", text.split() makes "leading".
        # If the line was `current_line + " " + word`, leading spaces on the first word of a line are fine.
        # Trailing spaces on the last word of a line are also fine.
        # The key is that `text.split()` removes empty strings from multiple spaces.
        self.assertEqual(wrapped_lines[0].strip(), expected_single_line)

        self.player.max_text_width = original_max_width # Restore

    def test_cjk_wrapping_logic_directly(self):
        """Test the internal CJK wrapping logic more directly."""
        text = "一二三四五六七八九十一二三四五" #15 chars
        self.player.max_text_width = 100 # Approx 5 CJK chars at 20pt
        # Manually trigger CJK path by faking font name (or ensure player's font is CJK)
        # Forcing CJK path by using a text that is CJK dominant
        lines = self.player._wrap_cjk_text_internal(text, self.test_font)
        self.assertEqual(len(lines), 3, f"Expected 3 lines for CJK text, got {len(lines)}: {lines}")
        self.assertEqual("".join(lines), text)

    def test_long_word_breaking_logic_directly(self):
        """Test the internal long word breaking logic."""
        word = "abcdefghijklmnopqrstuvwxyz" # 26 chars
        self.player.max_text_width = 100 # Approx 10-12 'a's at 20pt Arial
        lines = self.player._break_long_word_internal(word, self.test_font)
        # Expected number of lines depends heavily on font metrics.
        # Just check that it's broken and reconstructs.
        self.assertTrue(len(lines) > 1, f"Expected word to break, got {len(lines)} lines: {lines}")
        self.assertEqual("".join(lines), word)


if __name__ == '__main__':
    unittest.main()
