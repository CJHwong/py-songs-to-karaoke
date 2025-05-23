#!/usr/bin/env python3
"""Transcription module for handling transcription results with timestamps."""

import json
import os
import re
import subprocess
import sys # For version check
from typing import Any, Dict, List, Optional

# Use typing_extensions for Self if Python < 3.11
if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self


class Transcription:
    """Class to handle transcription results with timestamps."""

    def __init__(self) -> None:
        """Initialize an empty transcription object."""
        self.segments: List[Dict[str, Any]] = []  # List of segments with start_time, end_time, text

    def load_from_srt(self, srt_file_path: str) -> Optional[Self]:
        """Load transcription from a SRT subtitle file created by whisper-cli.

        Args:
            srt_file_path: Path to the SRT file

        Returns:
            Self if loaded successfully, None otherwise
        """
        self.segments = []

        try:
            with open(srt_file_path, encoding="utf-8") as f:
                content = f.read()

            # Split the content by subtitle entries
            subtitle_blocks = re.split(r"\n\s*\n", content.strip())

            for block in subtitle_blocks:
                lines = block.strip().split("\n")
                if len(lines) >= 3:  # Each block should have at least 3 lines
                    # Parse the timestamp line (format: 00:00:00,000 --> 00:00:00,000)
                    timestamps = lines[1]
                    time_parts = timestamps.split(" --> ")
                    if len(time_parts) == 2:
                        start_time = self._parse_timestamp(time_parts[0])
                        end_time = self._parse_timestamp(time_parts[1])

                        # Join the remaining lines as the subtitle text
                        text = " ".join(lines[2:])

                        self.segments.append({"start": start_time, "end": end_time, "text": text})

            print(f"Loaded {len(self.segments)} transcript segments from {srt_file_path}")
            return self
        except Exception as e:
            print(f"Error loading transcription from SRT file {srt_file_path}: {e}")
            return None

    def _parse_timestamp(self, timestamp: str) -> float:
        """Convert SRT timestamp format (00:00:00,000) to seconds.

        Args:
            timestamp: SRT format timestamp string

        Returns:
            Timestamp in seconds as a float
        """
        timestamp = timestamp.replace(",", ".")  # Replace comma with dot for float parsing
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        return 0.0

    def load_from_file(self, file_path: str) -> Optional[Self]:
        """Load transcription from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Self if loaded successfully, None otherwise
        """
        try:
            with open(file_path) as f:
                data = json.load(f)
                if "segments" in data:
                    self.segments = data["segments"]
                else:
                    self.segments = data
            return self
        except Exception as e:
            print(f"Error loading transcription from {file_path}: {e}")
            return None

    def save_to_file(self, file_path: str) -> bool:
        """Save transcription to a JSON file.

        Args:
            file_path: Path where the JSON file should be saved

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(file_path, "w") as f:
                json.dump({"segments": self.segments}, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving transcription to {file_path}: {e}")
            return False

    def get_text_at_time(self, current_time: float) -> str:
        """Get the text at the given time.

        Args:
            current_time: Timestamp in seconds

        Returns:
            Text of the segment active at the given time, or empty string if none
        """
        for segment in self.segments:
            if segment["start"] <= current_time <= segment["end"]:
                return segment["text"]
        return ""

    def get_segments_around_time(self, current_time: float, before: int = 2, after: int = 2) -> List[Dict[str, Any]]:
        """Get segments around the current time including past and future segments.

        Args:
            current_time: Timestamp in seconds
            before: Number of segments before the current one to include
            after: Number of segments after the current one to include

        Returns:
            List of segments with additional metadata (active status, index)
        """
        current_segment_idx = None

        # Find the current segment first
        for i, segment in enumerate(self.segments):
            if segment["start"] <= current_time <= segment["end"]:
                current_segment_idx = i
                break

        if current_segment_idx is None:
            # If no current segment found, find the closest upcoming segment
            upcoming = [(i, s) for i, s in enumerate(self.segments) if s["start"] > current_time]
            if upcoming:
                current_segment_idx = min(upcoming, key=lambda x: x[1]["start"])[0]
            else:
                # If no upcoming segment, use the last segment
                current_segment_idx = len(self.segments) - 1 if self.segments else None

        if current_segment_idx is None:
            return []

        # Calculate the range of segments to return
        start_idx = max(0, current_segment_idx - before)
        end_idx = min(len(self.segments) - 1, current_segment_idx + after)

        # Return segments with their index and active status
        result = []
        for i in range(start_idx, end_idx + 1):
            segment = self.segments[i].copy()
            segment["active"] = i == current_segment_idx and segment["start"] <= current_time <= segment["end"]
            segment["index"] = i
            result.append(segment)

        return result


class TranscriptionProcessor:
    """Class to handle transcription of audio using whisper.sh script."""

    def __init__(
        self,
        whisper_sh_path: str,
        model_name: str,
        whisper_cpp_path: Optional[str] = None,
    ) -> None:
        """Initialize the transcription processor.

        Args:
            whisper_sh_path: Path to whisper.sh script
            model_name: Name of the whisper model to use
            whisper_cpp_path: Optional path to whisper.cpp directory
        """
        self.whisper_sh_path = whisper_sh_path
        self.model_name = model_name
        self.whisper_cpp_path = whisper_cpp_path

    def transcribe(
        self, audio_path: str, language: str = "en", output_dir: Optional[str] = None
    ) -> Optional[Transcription]:
        """Transcribe audio file using whisper.sh.

        Args:
            audio_path: Path to the audio file to transcribe
            language: Language code (en, zh)
            output_dir: Optional directory to save the transcription files

        Returns:
            Transcription object if successful, None otherwise
        """
        if not self.whisper_sh_path or not os.path.isfile(self.whisper_sh_path):
            print(f"Error: whisper.sh script not found at {self.whisper_sh_path}")
            return None

        # Validate language is supported
        if language not in ["en", "zh"]:
            print(f"Error: Language '{language}' not supported. Only 'en' (English) and 'zh' (Chinese) are supported.")
            print("Defaulting to English (en)")
            language = "en"

        # Language-specific prompts
        prompts = {
            "en": "This is a song transcription. Lyrics should be poetic and structured.",
            "zh": "這是歌曲轉錄，歌詞應該具有詩意和結構性。",
        }

        # Select prompt based on language
        current_prompt = prompts.get(language, prompts["en"])

        try:
            print(f"Transcribing audio: {audio_path}")
            if not output_dir:
                output_dir = os.path.join(os.path.dirname(audio_path), "whisper_output")

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Language-specific max length based on empirical testing
            max_length = "16" if language == "zh" else "60"

            # Run whisper.sh script
            cmd = [
                "bash",
                self.whisper_sh_path,
                "-m",
                self.model_name,
                "-i",
                audio_path,
                "-o",
                output_dir,
                "-l",
                language,
                "--prompt",
                current_prompt,
                "-f",
                "srt",
                "--max-length",
                max_length,  # Different length for better readability based on language
            ]

            if self.whisper_cpp_path:
                # Export WHISPER_CPP_PATH for the shell script
                os.environ["WHISPER_CPP_PATH"] = self.whisper_cpp_path

            print(f"Running command: {' '.join(cmd)}")

            # Use subprocess with real-time output display
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Display stdout in real-time
            print("\n--- Transcription process output ---")
            for line in process.stdout:
                print(line.strip())

            # Wait for process to complete and get return code
            return_code = process.wait()

            # Get any remaining stderr
            stderr = process.stderr.read()

            print("--- End of transcription output ---\n")

            if return_code != 0:
                print(f"Error transcribing audio: {stderr}")
                return None

            # Find the SRT file created by whisper
            transcription_srt = os.path.join(output_dir, "transcription.srt")
            if not os.path.exists(transcription_srt):
                # Look for any .srt file
                srt_files = [f for f in os.listdir(output_dir) if f.endswith(".srt")]
                if srt_files:
                    transcription_srt = os.path.join(output_dir, srt_files[0])
                else:
                    print("Error: No SRT file found in output directory")
                    return None

            # Parse the SRT file
            transcription = Transcription()
            return transcription.load_from_srt(transcription_srt)

        except Exception as e:
            print(f"Error in transcription process: {e}")
            return None
