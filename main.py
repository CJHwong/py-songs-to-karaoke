#!/usr/bin/env python3
"""Songs to Karaoke - A tool to create karaoke versions of songs with time-synced lyrics."""

import argparse
import os
import sys

# Import local modules
from src.audio import AudioProcessor
from src.player import KaraokePlayer
from src.transcription import Transcription, TranscriptionProcessor
from src.utils import (
    cleanup_temp_dir,
    create_project_dir,
    create_temp_dir,
    get_env_path,
)

# Default constants
DEFAULT_WHISPER_MODEL = "models/ggml-large-v2.bin"  # Have best results for both English and Chinese
DEFAULT_WHISPER_SH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "whisper.sh")


def run_gui_application():
    """Initializes and runs the GUI application."""
    print("GUI mode activated. Launching Karaoke Master GUI...")
    try:
        from src.gui.main_window import MainApp
        app = MainApp(library_path="karaoke_library.json") # Default library path for GUI
        app.run()
        return 0
    except ImportError as e:
        print(f"Error importing GUI components: {e}")
        print("Please ensure that Pygame is installed and all GUI modules are correctly placed.")
        return 1
    except Exception as e:
        print(f"An unexpected error occurred while running the GUI: {e}")
        return 1


def run_cli_processing(args) -> int:
    """Runs the command-line interface processing for the application.

    Args:
        args: Parsed command-line arguments.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Load environment variables (already loaded in main and passed via args where needed or accessed globally)
    whisper_cpp_path = get_env_path("WHISPER_CPP_PATH")
    # vocal_remover_path is already part of args

    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    # Create a project directory
    project_dir, base_name = create_project_dir(args.input_file, args.output_dir)

    # Create temp directory
    temp_dir = create_temp_dir()
    print(f"Using temporary directory: {temp_dir}")

    # Set up the expected file paths
    wav_path = os.path.join(temp_dir, f"{base_name}.wav")
    instrumental_path = os.path.join(project_dir, f"{base_name}_Instruments.wav")
    vocals_path = os.path.join(project_dir, f"{base_name}_Vocals.wav")
    transcription_file = os.path.join(project_dir, f"{base_name}_transcription.json")
    whisper_output_dir = os.path.join(project_dir, "whisper_output")

    # Check if all target files exist already
    if (
        os.path.exists(instrumental_path)
        and os.path.exists(vocals_path)
        and os.path.exists(transcription_file)
        and not args.skip_separation
    ):
        print("All target files found. Loading directly...")
        transcription = Transcription().load_from_file(transcription_file)
        if not transcription:
            print(f"Error loading transcription from {transcription_file}")
            return 1
    else:
        # Convert input to WAV
        audio_processor = AudioProcessor(args.vocal_remover_path)
        if not audio_processor.convert_to_wav(args.input_file, wav_path):
            print("Error converting input file to WAV format")
            return 1

        instrumental_path = wav_path
        vocals_path = None

        # Separate vocals if requested
        if not args.skip_separation:
            if not args.vocal_remover_path:
                print("Warning: vocal-remover path not specified, skipping separation")
            else:
                instrumental_path, vocals_path = audio_processor.separate_vocals(wav_path, project_dir)
                if not instrumental_path:
                    print("Warning: Vocal separation failed, using original audio")
                    instrumental_path = wav_path

        # Process transcription
        if not args.skip_transcription:
            # Check if whisper_output_dir exists and no valid transcription is found,
            # if so, delete it to ensure a fresh transcription
            if os.path.exists(whisper_output_dir) and not os.path.exists(transcription_file):
                print(f"Removing old whisper output directory: {whisper_output_dir}")
                try:
                    import shutil

                    shutil.rmtree(whisper_output_dir)
                except Exception as e:
                    print(f"Warning: Failed to remove old whisper output directory: {e}")

            transcription_processor = TranscriptionProcessor(
                DEFAULT_WHISPER_SH_PATH,
                args.whisper_model,
                whisper_cpp_path=whisper_cpp_path,
            )
            transcription_audio = vocals_path if vocals_path else wav_path
            print(f"Using audio for transcription: {transcription_audio}")

            # Pass the whisper_output_dir to ensure output is saved in the project folder
            transcription = transcription_processor.transcribe(
                transcription_audio, args.language, output_dir=whisper_output_dir
            )

            if transcription:
                transcription.save_to_file(transcription_file)
            else:
                print("Error: Transcription failed")
                return 1
        else:
            # Try to load existing transcription
            if os.path.exists(transcription_file):
                transcription = Transcription().load_from_file(transcription_file)
                if not transcription:
                    print(f"Error loading transcription from {transcription_file}")
                    return 1
            else:
                print(f"Error: No transcription file found at {transcription_file} and --skip-transcription specified")
                return 1

    # Start karaoke player
    player = KaraokePlayer()
    player.load_audio(instrumental_path, vocals_path)
    player.load_transcription(transcription)
    player.play()
    player.quit()

    # Clean up temporary directory
    cleanup_temp_dir(temp_dir)

    return 0


def main() -> int:
    """Run the main application flow.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Load environment variables
    # whisper_cpp_path = get_env_path("WHISPER_CPP_PATH") # Moved to CLI logic where it's used
    vocal_remover_path = get_env_path("VOCAL_REMOVER_PATH")

    parser = argparse.ArgumentParser(description="Songs to Karaoke - Create karaoke versions with transcribed lyrics")
    # Changed "input_file" to have nargs='?' to make it optional
    parser.add_argument("input_file", nargs='?', help="Input audio or video file (optional, for CLI mode)")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument(
        "--vocal-remover",
        dest="vocal_remover_path",
        default=vocal_remover_path,
        help=f"Path to vocal-remover directory (default: {vocal_remover_path})",
    )
    parser.add_argument(
        "--whisper-model",
        dest="whisper_model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model name (default: {DEFAULT_WHISPER_MODEL})",
    )
    parser.add_argument(
        "--language",
        default="en",
        choices=["en", "zh"],
        help="Language code for transcription (en=English, zh=Chinese)",
    )
    parser.add_argument("--output", dest="output_dir", help="Output directory for generated files")
    parser.add_argument(
        "--skip-separation",
        dest="skip_separation",
        action="store_true",
        help="Skip vocal separation step",
    )
    parser.add_argument(
        "--skip-transcription",
        dest="skip_transcription",
        action="store_true",
        help="Skip transcription step",
    )

    args = parser.parse_args()

    # Determine mode: GUI or CLI
    # If --gui is specified, or if no input_file is given, run GUI.
    # Otherwise, run CLI.
    if args.gui or not args.input_file:
        if args.input_file:
            print("Warning: input_file argument provided with --gui flag or without other CLI args. Prioritizing GUI mode.")
            # Or, could choose to error out:
            # parser.error("Cannot specify an input file when running in GUI mode unless other CLI processing args are present.")
        return run_gui_application()
    else:
        # Ensure input_file is present for CLI mode (argparse with nargs='?' makes it optional)
        if not args.input_file:
            parser.print_help()
            print("\nError: input_file is required for CLI mode.")
            return 1
        return run_cli_processing(args)


if __name__ == "__main__":
    sys.exit(main())
