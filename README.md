# Songs to Karaoke

A Python tool to create karaoke versions of songs with time-synchronized lyrics.

## Overview

Songs to Karaoke is a tool that can:

- Separate vocals from instrumental tracks using advanced AI models
- Transcribe lyrics from songs using whisper.cpp for speech recognition
- Display a karaoke-style playback with time-synced lyrics
- Support both English and Chinese lyrics

## Features

- **Audio Conversion**: Convert various audio/video formats to high-quality WAV
- **Vocal Separation**: Split songs into instrumental and vocal tracks
- **Lyric Transcription**: Automatically generate time-synced lyrics from vocals
- **Karaoke Player**: Interactive player with lyrics display
- **Language Support**: Works with both English and Chinese lyrics
- **CJK Support**: Special handling for Asian character rendering

## Requirements

- Python 3.8 or higher
- FFmpeg
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) - for speech recognition
- [vocal-remover](https://github.com/tsurumeso/vocal-remover) - for separating vocals and instrumentals

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/CJHwong/py-songs-to-karaoke.git
   cd py-songs-to-karaoke
   ```

2. Create and activate a virtual environment and install dependencies using uv:

   ```bash
   uv sync
   ```

3. Install external dependencies:
   - Install [FFmpeg](https://ffmpeg.org/download.html)
   - Clone and build [whisper.cpp](https://github.com/ggerganov/whisper.cpp) following its installation instructions
   - Clone and set up [vocal-remover](https://github.com/tsurumeso/vocal-remover) following its installation instructions

4. Configure environment:

   ```bash
   cp .env.example .env
   # Edit .env to set up your whisper.cpp and vocal-remover paths
   ```

## Configuration

Edit the `.env` file to set the paths to your installations:

```plain
# Path to whisper.cpp installation directory
WHISPER_CPP_PATH=~/path/to/whisper.cpp

# Path to vocal-remover installation directory
VOCAL_REMOVER_PATH=~/path/to/vocal-remover
```

## Usage

### Basic Usage

```bash
uv run main.py your_song_file.mp3
```

This will:

1. Convert the audio file to WAV format
2. Separate vocals from instrumentals using vocal-remover
3. Transcribe the lyrics using whisper.cpp
4. Launch a karaoke player with time-synced lyrics

### Advanced Options

```bash
uv run main.py your_song_file.mp3 --language zh --output your_output_dir
```

Available options:

- `--vocal-remover PATH`: Path to vocal-remover directory
- `--whisper-model PATH`: Path to whisper model (default: models/ggml-large-v3-turbo.bin)
- `--language {en,zh}`: Language code for transcription (en=English, zh=Chinese)
- `--output DIR`: Output directory for generated files
- `--skip-separation`: Skip vocal separation step
- `--skip-transcription`: Skip transcription step

## How It Works

1. **Audio Processing**:
   - The input audio file is converted to WAV format using FFmpeg
   - The WAV file is processed by vocal-remover to separate vocals and instrumentals

2. **Transcription**:
   - The vocals track is sent to whisper.cpp for transcription
   - A language-specific prompt helps whisper generate better lyrics
   - The SRT file output is parsed into a structured JSON format

3. **Karaoke Playback**:
   - The instrumental track is played by default
   - Lyrics are displayed in sync with the music timing
   - The current lyric is highlighted and centered
   - Users can toggle vocal track on/off as needed

## Project Structure

- `main.py`: Main application entry point
- `src/audio.py`: Audio processing and vocal separation
- `src/transcription.py`: Lyrics transcription and processing
- `src/player.py`: Karaoke player implementation
- `src/utils.py`: Utility functions
- `scripts/whisper.sh`: Shell script to interface with whisper.cpp

## Development

### Setting up for development

```bash
# Install development dependencies
uv sync --dev

# Set up pre-commit hooks
pre-commit install
```

### Running tests

```bash
pytest
# With coverage report
pytest --cov=src
```

## Troubleshooting

- **No transcription generated**: Ensure whisper.cpp is properly built and the path is correctly set in `.env`
- **Vocal separation not working**: Check that vocal-remover is properly set up and the path is correct in `.env`
- **Font rendering issues**: The application tries to find suitable fonts for CJK characters; you might need to install additional fonts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for providing the speech recognition capability
- [vocal-remover](https://github.com/tsurumeso/vocal-remover) for the vocal separation algorithm
- [pygame](https://www.pygame.org/) for the audio playback and UI
