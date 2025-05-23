# Karaoke Master: Your Personal Karaoke Studio

Karaoke Master is a Python application that transforms your song library into a fully interactive karaoke experience. It features a user-friendly graphical interface (GUI) for managing songs, importing new tracks, and enjoying synchronized lyric playback. For users who prefer command-line operations or need to batch process songs, a CLI mode is also available.

## Overview

This application allows you to take any audio file, process it to separate vocals and instrumentals, transcribe the lyrics, and then play it back in a karaoke style. The GUI provides an intuitive way to manage your song library, customize the appearance of lyrics, and control playback.

## Features

- **Graphical User Interface (GUI)**: Easy-to-use interface for all main functionalities.
- **Song Import & Processing**:
    - Import audio files (various formats supported via FFmpeg).
    - Option to automatically separate vocals from instrumental tracks using AI-powered `vocal-remover`.
    - Option to automatically transcribe lyrics from the vocal track using `whisper.cpp`.
    - Skip separation or transcription if you have pre-processed files.
- **Song Library Management**:
    - Imported songs are added to a persistent library (`karaoke_library.json`).
    - View and select songs from the library list.
- **Karaoke Playback**:
    - Synchronized display of lyrics with audio playback.
    - Highlighted active lyric line.
    - Toggleable vocals during playback.
- **Customizable Lyric Display**:
    - Adjust lyric font size.
    - Cycle through predefined colors for active lyrics, inactive lyrics, and the lyric background.
- **Audio Visualizer**: Simple volume-based bar visualizer that reacts to the instrumental track.
- **CLI Mode**:
    - Process songs directly via the command line for scripting or batch operations.
    - Outputs processed files (instrumental, vocals, transcription JSON).
- **Language Support**: Tested with English and Chinese for transcription and display. CJK font handling included.

## Requirements

- **Python**: Python 3.10 or higher.
- **Pygame**: For GUI, audio playback, and graphics. (`pygame`)
- **FFmpeg**: Required for audio conversion during song import. Must be installed system-wide and accessible in PATH.
- **ffmpeg-python**: Python bindings for FFmpeg. (`ffmpeg-python`)
- **typing_extensions**: For Python version compatibility (specifically `Self` type).

**For Song Processing (Import Functionality):**
- **whisper.cpp**: For speech recognition (lyric transcription).
    - Requires a compiled version of [whisper.cpp](https://github.com/ggerganov/whisper.cpp).
    - Pre-trained Whisper models (e.g., `ggml-large-v2.bin`).
- **vocal-remover**: For separating vocals and instrumentals.
    - Requires a local installation of [vocal-remover](https://github.com/tsurumeso/vocal-remover) and its associated models.

## Installation & Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/karaoke-master.git # Replace with actual repo URL
    cd karaoke-master
    ```

2.  **Create a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python Dependencies**:
    A `requirements.txt` file is provided.
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is not available, install manually:
    ```bash
    pip install pygame ffmpeg-python typing_extensions
    ```

4.  **Install External Dependencies (for song processing features)**:
    *   **FFmpeg**: Download and install from [ffmpeg.org](https://ffmpeg.org/download.html). Ensure it's added to your system's PATH.
    *   **whisper.cpp**: Follow the [whisper.cpp installation instructions](https://github.com/ggerganov/whisper.cpp) to clone the repository and build it. You will also need to download a suitable model (e.g., `ggml-large-v2.bin`).
    *   **vocal-remover**: Follow the [vocal-remover setup instructions](https://github.com/tsurumeso/vocal-remover) to clone its repository and download its pre-trained models.

5.  **Configure Environment Variables**:
    Create a `.env` file in the project root (you can copy `.env.example` if provided). Edit it with the correct paths:
    ```env
    # Path to the main directory of your compiled whisper.cpp
    WHISPER_CPP_PATH=/path/to/your/whisper.cpp

    # Path to the pre-trained Whisper model file (e.g., .bin file)
    WHISPER_MODEL_PATH=/path/to/your/models/ggml-large-v2.bin 

    # Path to the root directory of your vocal-remover installation
    VOCAL_REMOVER_PATH=/path/to/your/vocal-remover
    ```
    These paths are crucial for the song import processing to work correctly.

## Usage

### GUI Mode (Recommended)

Run the application using:
```bash
python main.py
```
or explicitly:
```bash
python main.py --gui
```

**Interactions:**
*   **Importing Songs**:
    *   Click the "Import Songs" button in the Song Library panel.
    *   An "Import New Song" dialog will appear.
    *   **File Path**: Enter the path to your audio file (e.g., MP3, WAV, M4A). (Note: Real file dialogs are not yet implemented; use TAB to cycle test paths if available in the dialog or type/paste the full path).
    *   **Language**: Select the language of the song's lyrics (e.g., "en" for English, "zh" for Chinese).
    *   **Skip Vocal Separation**: Check this if your song is already instrumental or if you don't want to separate vocals.
    *   **Skip Transcription**: Check this if you have an existing `.srt` or `.json` lyric file or don't need lyrics.
    *   Click "Import". The application will process the song (this may take some time). Feedback messages will appear in the dialog.
*   **Song Library**:
    *   Imported songs appear in the "Song Library" list on the left.
    *   Click on a song to select it.
*   **Playback Controls**:
    *   **Play/Pause**: Plays the selected song. If a song is playing, it pauses. If paused, it resumes. (Spacebar also toggles Play/Pause).
    *   **Stop**: Stops the current song.
    *   **VOC**: Toggles the original vocals on/off during playback of the instrumental track.
    *   **Volume**: Use keyboard `+` (plus/equals) and `-` (minus) keys to adjust the master volume.
*   **Lyric Customization** (Controls located in a bar above playback controls):
    *   **Font +/-**: Increase or decrease the lyric font size.
    *   **Active Col**: Cycle through predefined colors for the currently sung lyric line.
    *   **Inactive Col**: Cycle through predefined colors for other visible lyric lines.
    *   **BG Col**: Cycle through predefined background colors for the lyric display area.

### CLI Mode

For direct processing of a song without the GUI:
```bash
python main.py /path/to/your_song.mp3 [options]
```
This will process the song (convert, separate, transcribe based on options) and save the output files (instrumental WAV, vocals WAV, transcription JSON) in a project directory. It will then launch a simple Pygame-based player for that single song.

**CLI Options:**
```
usage: main.py [-h] [--gui] [--vocal-remover VOCAL_REMOVER_PATH] [--whisper-model WHISPER_MODEL] [--language {en,zh}] [--output OUTPUT_DIR] [--skip-separation] [--skip-transcription] [input_file]

Songs to Karaoke - Create karaoke versions with transcribed lyrics

positional arguments:
  input_file            Input audio or video file (optional, for CLI mode)

options:
  -h, --help            show this help message and exit
  --gui                 Force GUI mode
  --vocal-remover VOCAL_REMOVER_PATH
                        Path to vocal-remover directory (default: value from .env or /app/models/vocal-remover)
  --whisper-model WHISPER_MODEL
                        Whisper model name (default: models/ggml-large-v2.bin)
  --language {en,zh}    Language code for transcription (en=English, zh=Chinese)
  --output OUTPUT_DIR   Output directory for generated files
  --skip-separation     Skip vocal separation step
  --skip-transcription  Skip transcription step
```

## Screenshots

[Placeholder for Screenshot of Main GUI - e.g., Song Library, Lyric Display, Visualizer]

## Project Structure

- `main.py`: Main application entry point, handles mode switching (GUI/CLI).
- `src/`: Contains the core application modules.
    - `gui/`: GUI-related modules.
        - `main_window.py`: Defines the `MainApp` class for the main GUI.
        - `import_dialog.py`: Defines the `ImportDialog` class for song import.
    - `library.py`: `SongLibrary` class for managing song metadata.
    - `player.py`: `KaraokePlayer` class for audio playback and lyric synchronization.
    - `audio.py`: `AudioProcessor` class for WAV conversion and vocal separation.
    - `transcription.py`: `Transcription` and `TranscriptionProcessor` classes for lyric handling.
    - `utils.py`: Utility functions (e.g., environment variable loading, file paths).
- `scripts/`: Shell scripts, e.g., `whisper.sh` for interfacing with `whisper.cpp`.
- `models/`: Placeholder for downloaded AI models (e.g., Whisper models).
- `tests/`: Unit tests.
- `.env.example`: Example environment variable configuration file.

## Development

### Setting up for development

```bash
# (After cloning and setting up virtual environment)
# Install development dependencies (if any, e.g., pytest)
pip install pytest pre-commit black ruff # Example dev tools

# Set up pre-commit hooks (optional)
pre-commit install
```

### Running tests

```bash
python -m unittest discover -s tests -v
```
Or, if using pytest:
```bash
pytest
```

## Troubleshooting

- **`ffmpeg` not found**: Ensure FFmpeg is installed and its executable is in your system's PATH.
- **`ModuleNotFoundError: No module named 'ffmpeg'` (Python error)**: Make sure `ffmpeg-python` is installed (`pip install ffmpeg-python`).
- **No transcription / Vocal separation issues**:
    - Double-check the paths in your `.env` file for `WHISPER_CPP_PATH`, `WHISPER_MODEL_PATH`, and `VOCAL_REMOVER_PATH`.
    - Ensure `whisper.cpp` is compiled and `vocal-remover` has its models downloaded as per their respective instructions.
- **Font rendering issues (especially CJK characters)**: The application attempts to find suitable system fonts. If specific characters don't render well, you might need to install additional fonts on your system that provide broader Unicode coverage (e.g., Noto Sans CJK).
- **ALSA errors on headless Linux (for tests)**: If running tests that initialize `pygame.mixer` on a headless Linux server, you might encounter ALSA errors. The tests for `KaraokePlayer` text utilities mock mixer initialization to avoid this.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
Areas for improvement:
-   Proper file dialogs for song import.
-   More sophisticated audio visualizer.
-   User-configurable settings persistence (beyond library).
-   Packaging the application (e.g., with PyInstaller).

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgements

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for speech recognition.
- [vocal-remover](https://github.com/tsurumeso/vocal-remover) for vocal separation.
- [Pygame](https://www.pygame.org/) for GUI and audio.
