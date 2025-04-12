#!/usr/bin/env python3
"""
Test cases for transcription.py module
"""

import json
import unittest.mock as mock
from io import StringIO

import pytest

from transcription import Transcription, TranscriptionProcessor


class TestTranscription:
    """Test cases for the Transcription class"""

    @pytest.fixture
    def sample_transcription(self):
        """Create a sample transcription object with predefined segments"""
        transcription = Transcription()
        transcription.segments = [
            {"start": 0.0, "end": 2.5, "text": "This is segment one"},
            {"start": 2.5, "end": 5.0, "text": "This is segment two"},
            {"start": 5.0, "end": 7.5, "text": "This is segment three"},
            {"start": 7.5, "end": 10.0, "text": "This is segment four"},
        ]
        return transcription

    def test_load_from_srt(self):
        """Test loading transcription from SRT format"""
        # Setup
        srt_content = """1
00:00:01,000 --> 00:00:02,500
This is segment one

2
00:00:02,500 --> 00:00:05,000
This is segment two
"""
        mock_open = mock.mock_open(read_data=srt_content)

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_srt("fake_path.srt")

        # Assert
        assert result is not None
        assert len(transcription.segments) == 2
        assert transcription.segments[0]["text"] == "This is segment one"
        assert transcription.segments[1]["start"] == 2.5

    def test_load_from_srt_error(self):
        """Test error handling when loading from SRT file"""
        # Setup
        mock_open = mock.mock_open()
        mock_open.side_effect = Exception("File not found")

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_srt("nonexistent_file.srt")

        # Assert
        assert result is None

    def test_load_from_srt_invalid_format(self):
        """Test loading transcription from invalid SRT format"""
        # Setup - Invalid format missing timestamps
        srt_content = """1
This is segment one without timestamp

2
00:00:02,500 --> 00:00:05,000
This is segment two
"""
        mock_open = mock.mock_open(read_data=srt_content)

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_srt("invalid_format.srt")

        # Assert
        assert result is not None
        assert len(transcription.segments) == 1  # Only the valid segment should be loaded

    def test_parse_timestamp(self):
        """Test parsing SRT timestamp format"""
        # Setup
        transcription = Transcription()

        # Execute and Assert
        assert transcription._parse_timestamp("00:00:01,500") == 1.5
        assert transcription._parse_timestamp("01:30:00,000") == 5400.0
        assert transcription._parse_timestamp("00:01:30,250") == 90.25

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp format"""
        # Setup
        transcription = Transcription()

        # Execute and Assert
        assert transcription._parse_timestamp("00:00") == 0.0  # Invalid format returns 0.0

    @mock.patch("json.load")
    def test_load_from_file(self, mock_json_load):
        """Test loading transcription from JSON file"""
        # Setup
        mock_json_load.return_value = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "This is segment one"},
                {"start": 2.5, "end": 5.0, "text": "This is segment two"},
            ]
        }
        mock_open = mock.mock_open()

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_file("fake_path.json")

        # Assert
        assert result is not None
        assert len(transcription.segments) == 2
        assert transcription.segments[1]["text"] == "This is segment two"

    @mock.patch("json.load")
    def test_load_from_file_flat_format(self, mock_json_load):
        """Test loading transcription from JSON file with flat format (no segments key)"""
        # Setup
        mock_json_load.return_value = [
            {"start": 0.0, "end": 2.5, "text": "This is segment one"},
            {"start": 2.5, "end": 5.0, "text": "This is segment two"},
        ]
        mock_open = mock.mock_open()

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_file("fake_path.json")

        # Assert
        assert result is not None
        assert len(transcription.segments) == 2

    @mock.patch("json.load")
    def test_load_from_file_error(self, mock_json_load):
        """Test error handling when loading from JSON file"""
        # Setup
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_open = mock.mock_open()

        # Execute
        with mock.patch("builtins.open", mock_open):
            transcription = Transcription()
            result = transcription.load_from_file("invalid.json")

        # Assert
        assert result is None

    @mock.patch("json.dump")
    def test_save_to_file(self, mock_json_dump):
        """Test saving transcription to JSON file"""
        # Setup
        transcription = Transcription()
        transcription.segments = [
            {"start": 0.0, "end": 2.5, "text": "This is segment one"},
            {"start": 2.5, "end": 5.0, "text": "This is segment two"},
        ]
        mock_open = mock.mock_open()

        # Execute
        with mock.patch("builtins.open", mock_open):
            result = transcription.save_to_file("output.json")

        # Assert
        assert result is True
        mock_open.assert_called_once_with("output.json", "w")
        mock_json_dump.assert_called_once()

    @mock.patch("json.dump")
    def test_save_to_file_error(self, mock_json_dump):
        """Test error handling when saving to JSON file"""
        # Setup
        transcription = Transcription()
        mock_open = mock.mock_open()
        mock_json_dump.side_effect = Exception("Permission denied")

        # Execute
        with mock.patch("builtins.open", mock_open):
            result = transcription.save_to_file("output.json")

        # Assert
        assert result is False

    def test_get_text_at_time(self, sample_transcription):
        """Test getting text at a specific time"""
        # Execute and Assert
        assert sample_transcription.get_text_at_time(1.0) == "This is segment one"
        assert sample_transcription.get_text_at_time(3.0) == "This is segment two"
        assert sample_transcription.get_text_at_time(11.0) == ""  # Outside any segment

    def test_get_segments_around_time(self, sample_transcription):
        """Test getting segments around a specific time"""
        # Execute
        segments_at_3 = sample_transcription.get_segments_around_time(3.0, before=1, after=1)

        # Assert
        assert len(segments_at_3) == 3
        assert segments_at_3[0]["text"] == "This is segment one"
        assert segments_at_3[1]["text"] == "This is segment two"
        assert segments_at_3[1]["active"] is True

        # Test edge case at beginning
        segments_at_start = sample_transcription.get_segments_around_time(0.5, before=1, after=1)
        assert len(segments_at_start) == 2
        assert segments_at_start[0]["active"] is True

        # Test edge case at end
        segments_at_end = sample_transcription.get_segments_around_time(9.0, before=1, after=1)
        assert len(segments_at_end) == 2
        assert segments_at_end[1]["active"] is True

        # Test time not inside any segment but between segments
        segments_between = sample_transcription.get_segments_around_time(11.0, before=1, after=1)
        assert len(segments_between) <= 2
        assert all(not segment.get("active", False) for segment in segments_between)

    def test_get_segments_around_time_empty(self):
        """Test getting segments around a time with empty segments list"""
        # Setup
        transcription = Transcription()  # Empty segments list

        # Execute
        result = transcription.get_segments_around_time(1.0)

        # Assert
        assert result == []

    def test_get_segments_around_time_upcoming(self, sample_transcription):
        """Test getting segments when current time is before the first segment"""
        # Execute - Get segments when time is -1.0 (before first segment)
        result = sample_transcription.get_segments_around_time(-1.0, before=1, after=1)

        # Assert
        assert len(result) > 0
        assert result[0]["text"] == "This is segment one"
        assert result[0]["active"] is False  # Not active because time is before segment


class TestTranscriptionProcessor:
    """Test cases for the TranscriptionProcessor class"""

    @pytest.fixture
    def transcription_processor(self):
        """Create a sample TranscriptionProcessor for testing"""
        return TranscriptionProcessor(whisper_sh_path="/path/to/whisper.sh", model_name="models/test-model.bin")

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    @mock.patch("os.listdir")
    def test_transcribe_success(
        self, mock_listdir, mock_exists, mock_makedirs, mock_isfile, mock_popen, transcription_processor
    ):
        """Test successful transcription process"""
        # Setup
        audio_path = "/path/to/audio.wav"
        output_dir = "/output/dir"

        # Mock file existence checks
        mock_isfile.return_value = True
        mock_exists.side_effect = lambda path: path.endswith("transcription.srt")

        # Mock subprocess
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 0
        process_mock.stderr = StringIO("")
        mock_popen.return_value = process_mock

        # Mock the Transcription.load_from_srt method
        load_from_srt_mock = mock.MagicMock()
        with mock.patch("transcription.Transcription.load_from_srt", load_from_srt_mock) as mock_load:
            # Set the mock to return the Transcription instance
            mock_load.return_value = mock.MagicMock()

            # Execute
            result = transcription_processor.transcribe(audio_path=audio_path, language="en", output_dir=output_dir)

            # Assert
            assert result is not None
            mock_popen.assert_called_once()
            mock_load.assert_called_once()

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    def test_transcribe_whisper_sh_not_found(self, mock_isfile, mock_popen, transcription_processor):
        """Test transcription when whisper.sh script is not found"""
        # Setup
        mock_isfile.return_value = False

        # Execute
        result = transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

        # Assert
        assert result is None
        mock_popen.assert_not_called()

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    def test_transcribe_process_error(self, mock_makedirs, mock_isfile, mock_popen, transcription_processor):
        """Test transcription with process execution error"""
        # Setup
        mock_isfile.return_value = True

        # Mock subprocess with error
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 1  # Error code
        process_mock.stderr = StringIO("Error")
        mock_popen.return_value = process_mock

        # Execute
        result = transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

        # Assert
        assert result is None
        mock_popen.assert_called_once()

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    @mock.patch("os.listdir")
    def test_transcribe_srt_not_found_fallback(
        self, mock_listdir, mock_exists, mock_makedirs, mock_isfile, mock_popen, transcription_processor
    ):
        """Test transcription with fallback to find SRT file"""
        # Setup
        # First check for transcription.srt fails, then finds an alternative SRT file
        mock_exists.side_effect = lambda path: not path.endswith("transcription.srt")
        mock_listdir.return_value = ["alternative.srt"]

        # Mock subprocess
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 0
        process_mock.stderr = StringIO("")
        mock_popen.return_value = process_mock

        mock_isfile.return_value = True

        # Mock the Transcription.load_from_srt method
        load_from_srt_mock = mock.MagicMock()
        with mock.patch("transcription.Transcription.load_from_srt", load_from_srt_mock) as mock_load:
            # Set the mock to return the Transcription instance
            mock_load.return_value = mock.MagicMock()

            # Execute
            result = transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

            # Assert
            assert result is not None
            # Check it was called with the alternative SRT file
            assert "alternative.srt" in mock_load.call_args[0][0]

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    @mock.patch("os.listdir")
    def test_transcribe_no_srt_found(
        self, mock_listdir, mock_exists, mock_makedirs, mock_isfile, mock_popen, transcription_processor
    ):
        """Test transcription when no SRT file is found"""
        # Setup
        mock_isfile.return_value = True
        mock_exists.return_value = False  # No transcription.srt
        mock_listdir.return_value = []  # No alternative SRT files

        # Mock subprocess
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 0
        process_mock.stderr = StringIO("")
        mock_popen.return_value = process_mock

        # Execute
        result = transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

        # Assert
        assert result is None
        mock_popen.assert_called_once()

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    def test_transcribe_unsupported_language(self, mock_makedirs, mock_isfile, mock_popen, transcription_processor):
        """Test transcription with unsupported language"""
        # Setup
        mock_isfile.return_value = True

        # Mock subprocess
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 0
        process_mock.stderr = StringIO("")
        mock_popen.return_value = process_mock

        # Set up load_from_srt mock
        load_from_srt_mock = mock.MagicMock(return_value=mock.MagicMock())

        with mock.patch("os.path.exists", return_value=True), mock.patch(
            "transcription.Transcription.load_from_srt", load_from_srt_mock
        ):
            # Execute - use unsupported language "fr"
            transcription_processor.transcribe(
                audio_path="/path/to/audio.wav",
                language="fr",  # Unsupported language
            )

            # Check that the command was run with "en" instead
            cmd_str = " ".join(arg for arg in mock_popen.call_args[0][0])
            assert " -l en " in cmd_str

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    def test_transcribe_with_exception(self, mock_makedirs, mock_isfile, mock_popen, transcription_processor):
        """Test transcription with general exception"""
        # Setup
        mock_isfile.return_value = True
        mock_popen.side_effect = ValueError("Unexpected error")

        # Execute and Assert
        result = transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

        assert result is None

    @mock.patch("subprocess.Popen")
    @mock.patch("os.path.isfile")
    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    def test_transcribe_with_whisper_cpp_path(
        self, mock_exists, mock_makedirs, mock_isfile, mock_popen, transcription_processor
    ):
        """Test transcription with whisper_cpp_path set"""
        # Setup
        mock_isfile.return_value = True
        mock_exists.return_value = True

        # Set whisper_cpp_path
        transcription_processor.whisper_cpp_path = "/path/to/whisper-cpp"

        # Mock subprocess
        process_mock = mock.MagicMock()
        process_mock.stdout = StringIO("Transcription output\n")
        process_mock.wait.return_value = 0
        process_mock.stderr = StringIO("")
        mock_popen.return_value = process_mock

        # Mock os.environ to verify it's being set
        with mock.patch("transcription.Transcription.load_from_srt", return_value=mock.MagicMock()), mock.patch.dict(
            "os.environ", {}, clear=True
        ) as mock_environ:
            # Execute
            transcription_processor.transcribe(audio_path="/path/to/audio.wav", language="en")

            # Assert whisper_cpp_path was set in environment
            assert "WHISPER_CPP_PATH" in mock_environ
            assert mock_environ["WHISPER_CPP_PATH"] == "/path/to/whisper-cpp"
