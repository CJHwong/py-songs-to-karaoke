#!/usr/bin/env python3
"""Audio processing module for handling audio conversion and vocal separation."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import ffmpeg


class AudioProcessor:
    """Class to handle audio processing, conversion and vocal separation."""

    def __init__(self, vocal_remover_path: str):
        """Initialize the audio processor with path to vocal remover.

        Args:
            vocal_remover_path: Path to the vocal-remover directory
        """
        self.vocal_remover_path = vocal_remover_path

    def convert_to_wav(self, input_file: str, output_file: str) -> bool:
        """Convert input file to WAV format suitable for processing while preserving quality.

        Args:
            input_file: Path to the input audio file
            output_file: Path where the output WAV file should be saved

        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Use higher quality settings for better audio fidelity
            high_quality_sample_rate = 44100  # CD quality

            (
                ffmpeg.input(input_file)
                .output(
                    output_file,
                    ar=high_quality_sample_rate,  # CD quality sample rate
                    ac=2,  # Stereo
                    acodec="pcm_s24le",  # 24-bit PCM for better dynamic range
                    format="wav",
                )
                .run(quiet=True, overwrite_output=True)
            )
            print(f"Converted to high-quality WAV: {output_file}")
            return True
        except Exception as e:
            print(f"Error in high-quality conversion: {e}")
            # Fallback to standard quality if high quality fails
            try:
                print("Falling back to standard quality conversion...")
                (
                    ffmpeg.input(input_file)
                    .output(output_file, ar=16000, ac=2, format="wav")
                    .run(quiet=True, overwrite_output=True)
                )
                print("Standard conversion successful")
                return True
            except Exception as e2:
                print(f"Error converting to WAV: {e2}")
                return False

    def separate_vocals(self, input_file: str, output_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """Use vocal-remover to separate vocals from instruments.

        Args:
            input_file: Path to the input WAV file
            output_dir: Directory where separated audio files should be saved

        Returns:
            Tuple containing paths to (instrumental_file, vocals_file) or (None, None) on failure
        """
        try:
            base_name = Path(input_file).stem
            instrumental_path = os.path.join(output_dir, f"{base_name}_Instruments.wav")
            vocals_path = os.path.join(output_dir, f"{base_name}_Vocals.wav")

            # Check if output already exists
            if os.path.exists(instrumental_path) and os.path.exists(vocals_path):
                print(f"Separated files already exist: {instrumental_path} and {vocals_path}")
                return instrumental_path, vocals_path

            # Run vocal-remover
            cmd = [
                "python",
                os.path.join(self.vocal_remover_path, "inference.py"),
                "--input",
                input_file,
                "--tta",
                "--gpu",
                "0",
            ]

            print(f"Separating vocals from instruments: {input_file}")
            process = subprocess.Popen(
                cmd,
                cwd=self.vocal_remover_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Use text mode for better Python 3 compatibility
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"Error separating vocals: {stderr}")
                return None, None

            # Verify files were created
            if not (os.path.exists(instrumental_path) and os.path.exists(vocals_path)):
                print("Warning: Could not find separated files at expected locations")
                # Look for files in the current directory or vocal-remover directory
                potential_locations = [
                    ".",
                    self.vocal_remover_path,
                    os.path.dirname(input_file),
                ]

                for location in potential_locations:
                    instr_path = os.path.join(location, f"{base_name}_Instruments.wav")
                    voc_path = os.path.join(location, f"{base_name}_Vocals.wav")

                    if os.path.exists(instr_path) and os.path.exists(voc_path):
                        # Found the files, move them to the output directory
                        shutil.move(instr_path, instrumental_path)
                        shutil.move(voc_path, vocals_path)
                        print(f"Found and moved separated files to {output_dir}")
                        return instrumental_path, vocals_path

                print("Could not find the separated files in any expected location")
                return None, None

            return instrumental_path, vocals_path
        except Exception as e:
            print(f"Error in vocal separation: {e}")
            return None, None
