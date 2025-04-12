#!/usr/bin/env python3
"""
Test cases for audio.py module
"""

import unittest.mock as mock

import pytest

from audio import AudioProcessor


class TestAudioProcessor:
    """Test cases for the AudioProcessor class"""

    @pytest.fixture
    def audio_processor(self):
        """Fixture to create an AudioProcessor instance"""
        return AudioProcessor(vocal_remover_path="/path/to/vocal_remover")

    @mock.patch("audio.ffmpeg")
    def test_convert_to_wav_success(self, mock_ffmpeg, audio_processor):
        """Test successful conversion to WAV format"""
        # Setup
        input_file = "input.mp3"
        output_file = "output.wav"

        # Execute
        result = audio_processor.convert_to_wav(input_file, output_file)

        # Assert
        assert result is True
        mock_ffmpeg.input.assert_called_once_with(input_file)
        mock_ffmpeg.input.return_value.output.assert_called_once()
        mock_ffmpeg.input.return_value.output.return_value.run.assert_called_once()

    @mock.patch("audio.ffmpeg")
    def test_convert_to_wav_error_with_fallback(self, mock_ffmpeg, audio_processor):
        """Test WAV conversion with initial error but successful fallback"""
        # Setup
        input_file = "input.mp3"
        output_file = "output.wav"

        # Create a new mock for each call to ffmpeg.input
        first_input_mock = mock.MagicMock()
        second_input_mock = mock.MagicMock()

        # Set up the side effects for mock_ffmpeg.input to return different mocks for each call
        mock_ffmpeg.input.side_effect = [first_input_mock, second_input_mock]

        # First call to run() raises exception, second succeeds
        first_input_mock.output.return_value.run.side_effect = Exception("High quality failed")
        second_input_mock.output.return_value.run.return_value = None

        # Execute
        result = audio_processor.convert_to_wav(input_file, output_file)

        # Assert
        assert result is True
        assert mock_ffmpeg.input.call_count == 2
        first_input_mock.output.return_value.run.assert_called_once()
        second_input_mock.output.return_value.run.assert_called_once()

    @mock.patch("audio.ffmpeg")
    def test_convert_to_wav_complete_failure(self, mock_ffmpeg, audio_processor):
        """Test WAV conversion with complete failure"""
        # Setup
        input_file = "input.mp3"
        output_file = "output.wav"

        # Make both runs fail
        mock_ffmpeg.input.return_value.output.return_value.run.side_effect = Exception("Conversion failed")

        # Execute
        result = audio_processor.convert_to_wav(input_file, output_file)

        # Assert
        assert result is False

    @mock.patch("audio.subprocess.Popen")
    @mock.patch("audio.os.path.exists")
    def test_separate_vocals_success(self, mock_exists, mock_popen, audio_processor):
        """Test successful vocal separation"""
        # Setup
        input_file = "input.wav"
        output_dir = "/output/dir"
        base_name = "input"
        instrumental_path = f"/output/dir/{base_name}_Instruments.wav"
        vocals_path = f"/output/dir/{base_name}_Vocals.wav"

        # Initial check for existing files should return False, then True after "processing"
        mock_exists.side_effect = lambda path: False

        # Mock process execution
        process_mock = mock.MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Output", b"")
        mock_popen.return_value = process_mock

        # After the subprocess runs, change the mock_exists behavior to find the files
        def exists_side_effect(path):
            # After communicate has been called, files should exist
            if hasattr(process_mock.communicate, "call_count") and process_mock.communicate.call_count > 0:
                return path in [instrumental_path, vocals_path]
            return False

        mock_exists.side_effect = exists_side_effect

        # Execute
        result = audio_processor.separate_vocals(input_file, output_dir)

        # Assert
        assert result == (instrumental_path, vocals_path)
        mock_popen.assert_called_once()
        process_mock.communicate.assert_called_once()

    @mock.patch("audio.subprocess.Popen")
    @mock.patch("audio.os.path.exists")
    @mock.patch("audio.shutil.move")
    def test_separate_vocals_file_relocation(self, mock_move, mock_exists, mock_popen, audio_processor):
        """Test vocal separation with file relocation"""
        # Setup
        input_file = "input.wav"
        output_dir = "/output/dir"
        base_name = "input"
        instrumental_path = f"/output/dir/{base_name}_Instruments.wav"
        vocals_path = f"/output/dir/{base_name}_Vocals.wav"

        # Files exist in different location first, then in expected location after move
        mock_exists.side_effect = lambda path: (
            path in [f"./{base_name}_Instruments.wav", f"./{base_name}_Vocals.wav"]
            or (path in [instrumental_path, vocals_path] and mock_move.call_count > 0)
        )

        # Mock process execution
        process_mock = mock.MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Output", b"")
        mock_popen.return_value = process_mock

        # Execute
        result = audio_processor.separate_vocals(input_file, output_dir)

        # Assert
        assert result == (instrumental_path, vocals_path)
        assert mock_move.call_count == 2

    @mock.patch("audio.subprocess.Popen")
    def test_separate_vocals_error(self, mock_popen, audio_processor):
        """Test vocal separation with error"""
        # Setup
        input_file = "input.wav"
        output_dir = "/output/dir"

        # Mock process execution with error
        process_mock = mock.MagicMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Error")
        mock_popen.return_value = process_mock

        # Execute
        result = audio_processor.separate_vocals(input_file, output_dir)

        # Assert
        assert result == (None, None)
