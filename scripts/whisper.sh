#!/bin/bash

# Load environment variables if .env file exists
if [ -f "$(dirname "$(dirname "$0")")/.env" ]; then
    source "$(dirname "$(dirname "$0")")/.env"
fi

# Default values
WHISPER_CPP_PATH=${WHISPER_CPP_PATH}
model_path="models/ggml-large-v3-turbo.bin"
language="en"
enable_chunking=false
verbose=false
input_files=()
output_format="txt" # Default output format is text
initial_prompt=""   # New variable for the initial prompt
max_length=0       # Default max segment length in characters

# Function to show usage
show_usage() {
    echo "Usage: $0 -i <input_file> [-i <input_file2> ...] [-o <output_path>] [-l <language>] [-c] [-v]"
    echo "  -i : Input file(s) (mp3, mp4, wav, m4a, m3u8, mov) or HTTP/HTTPS URL"
    echo "       Can be specified multiple times for multiple input files"
    echo "  -o : Output path (default: 'whisper_output' or first input filename without extension)"
    echo "  -l : Language code (default: en)"
    echo "       Examples: en, zh, es, fr, de, ja, ko, etc."
    echo "  -c : Enable chunking mode (split audio at silences)"
    echo "  -v : Verbose mode (show more detailed output)"
    echo "  -m : Model path (default: $model_path)"
    echo "  -f : Output format (default: txt)"
    echo "       Options: txt (text), srt (subtitles), j (JSON), lrc (lyrics)"
    echo "  --max-length : Maximum segment length in characters"
    echo "  --prompt : Initial prompt to guide the transcription"
    exit 1
}

# Function to log messages
log() {
    local level=$1
    shift
    if [[ "$level" == "ERROR" ]] || [[ "$verbose" == true ]]; then
        echo "[$level] $*"
    fi
}

# Function to handle downloads
download_file() {
    local url=$1
    local output_file=$2

    log "INFO" "Downloading $url to $output_file..."

    if command -v curl &> /dev/null; then
        curl -L -o "$output_file" "$url"
    elif command -v wget &> /dev/null; then
        wget -O "$output_file" "$url"
    else
        log "ERROR" "Neither curl nor wget is installed. Cannot download file."
        exit 1
    fi

    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to download the file"
        exit 1
    fi

    log "INFO" "Download complete: $output_file"
}

# Function to concatenate multiple audio files
concatenate_audio_files() {
    local args=("$@")
    local num_args=${#args[@]}
    local output_file="${args[$num_args-1]}" # Last argument is output file
    local num_files=$((num_args - 1))
    local temp_dir=$(dirname "$output_file")
    local concat_file="$temp_dir/concat_list.txt"

    log "INFO" "Concatenating $num_files audio files to $output_file..."

    # Ensure output directory exists
    mkdir -p "$temp_dir"

    # Convert each input file to WAV with same parameters and create concat list
    > "$concat_file"
    for ((i=0; i<num_files; i++)); do
        local input="${args[$i]}"
        local temp_wav="$temp_dir/temp_$(printf "%03d" $i).wav"

        log "INFO" "Converting input file $((i+1))/$num_files: $input"

        ffmpeg -i "$input" -ar 16000 -ac 1 -c:a pcm_s16le "$temp_wav"

        if [ $? -ne 0 ]; then
            log "ERROR" "Failed to convert $input to WAV format"
            return 1
        fi

        echo "file '$(basename "$temp_wav")'" >> "$concat_file"
    done

    # Concatenate all converted files
    (cd "$temp_dir" && ffmpeg -f concat -safe 0 -i concat_list.txt -c copy "$(basename "$output_file")")

    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to concatenate audio files"
        return 1
    fi

    log "INFO" "Successfully concatenated $num_files audio files to $output_file"
    return 0
}

# Function to convert audio to the required format
convert_audio() {
    local input=$1
    local output=$2
    local extension="${input##*.}"
    extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')

    log "INFO" "Converting $extension file to WAV format..."

    local ffmpeg_cmd="ffmpeg"

    case "$extension" in
        "m3u8")
            local temp_mp4="${output%/*}/temp_video.mp4"
            $ffmpeg_cmd -protocol_whitelist file,http,https,tcp,tls,crypto -i "$input" -c copy "$temp_mp4"
            $ffmpeg_cmd -i "$temp_mp4" -vn -ar 16000 -ac 1 -c:a pcm_s16le "$output"
            ;;
        "mp4"|"m4a"|"mov")
            $ffmpeg_cmd -i "$input" -vn -ar 16000 -ac 1 -c:a pcm_s16le "$output"
            ;;
        "mp3")
            $ffmpeg_cmd -i "$input" -ar 16000 -ac 1 -c:a pcm_s16le "$output"
            ;;
        "wav")
            $ffmpeg_cmd -i "$input" -ar 16000 -ac 1 -c:a pcm_s16le "$output"
            ;;
        *)
            log "ERROR" "Unsupported file format: $extension. Please use M3U8, MP4, MP3, M4A, MOV, or WAV"
            exit 1
            ;;
    esac

    if [ $? -ne 0 ]; then
        log "ERROR" "Audio conversion failed"
        exit 1
    fi

    log "INFO" "Audio conversion complete"
}

# Function to chunk audio at silence points
chunk_audio() {
    local input=$1
    local chunks_dir=$2
    local silence_file=$3

    log "INFO" "Detecting silence for chunking..."

    ffmpeg -i "$input" -af silencedetect=n=-30dB:d=3 -f null - 2>&1 | grep 'silence_end' > "$silence_file"

    timestamps=$(grep 'silence_end:' "$silence_file" | awk '{print $5}')

    local start_time=0
    local count=0

    log "INFO" "Splitting audio into chunks..."
    for end_time in $timestamps; do
        local duration=$(echo "$end_time - $start_time" | bc)
        local output_chunk=$(printf "$chunks_dir/chunk_%03d.wav" $count)

        ffmpeg -i "$input" -ss $start_time -t $duration -c copy "$output_chunk"

        start_time=$end_time
        count=$((count + 1))
    done

    # Handle the last chunk
    local final_chunk=$(printf "$chunks_dir/chunk_%03d.wav" $count)

    ffmpeg -i "$input" -ss $start_time -c copy "$final_chunk"

    log "INFO" "Created $((count + 1)) audio chunks"
}

# Function to transcribe a single audio file
transcribe_file() {
    local input=$1
    local language=$2
    local model=$3

    log "INFO" "Transcribing $input..."

    local max_attempts=3
    local attempts=0

    while [ $attempts -lt $max_attempts ]; do
        if [ -n "$initial_prompt" ]; then
            $WHISPER_CPP_PATH/build/bin/whisper-cli -m "$model" -f "$input" -l "$language" -sns -sow -ml $max_length -o$output_format --prompt "$initial_prompt"
        else
            $WHISPER_CPP_PATH/build/bin/whisper-cli -m "$model" -f "$input" -l "$language" -sns -sow -ml $max_length -o$output_format
        fi
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            log "INFO" "Successfully transcribed $input"
            return 0
        else
            attempts=$((attempts + 1))
            log "WARN" "Failed to transcribe $input (attempt $attempts/$max_attempts). Retrying..."
            sleep 2
        fi
    done

    log "ERROR" "Failed to transcribe $input after $max_attempts attempts"
    return 1
}

# Function to get output file extension based on format
get_output_extension() {
    case "$output_format" in
        "txt") echo "txt" ;;
        "srt") echo "srt" ;;
        "j") echo "json" ;;
        "lrc") echo "lrc" ;;
        *) echo "txt" ;;  # Default to txt for unknown formats
    esac
}

# Function to merge transcriptions
merge_transcriptions() {
    local source_dir=$1
    local output_file=$2
    local extension=$(get_output_extension)

    log "INFO" "Merging transcriptions into $output_file..."

    > "$output_file"  # Clear previous merged output if it exists

    for file in "$source_dir"/*.$extension; do
        if [ -f "$file" ]; then
            cat "$file" >> "$output_file"
            echo -e "\n" >> "$output_file"
            log "INFO" "Merged $file"
        fi
    done

    log "INFO" "Merged all transcriptions into $output_file"
}

# Function to handle chunked processing
process_chunked() {
    local input=$1
    local chunks_dir=$2
    local silence_file=$3
    local transcription_file=$4
    local language=$5
    local model=$6
    local extension=$(get_output_extension)

    # Create chunks
    chunk_audio "$input" "$chunks_dir" "$silence_file"

    # Process each chunk
    for chunk in "$chunks_dir"/*.wav; do
        transcribe_file "$chunk" "$language" "$model"

        # Move the output file back to our chunks directory
        local base_filename=$(basename "$chunk")
        if [ -f "$base_filename.$extension" ]; then
            mv "$base_filename.$extension" "$chunks_dir/"
        fi
    done

    # Merge results
    merge_transcriptions "$chunks_dir" "$transcription_file"
}

# Function to handle non-chunked processing
process_full() {
    local input=$1
    local transcription_file=$2
    local language=$3
    local model=$4
    local extension=$(get_output_extension)

    transcribe_file "$input" "$language" "$model"

    # Move the output file to the desired location
    local expected_output="${input}.${extension}"

    if [ -f "$expected_output" ]; then
        mv "$expected_output" "$transcription_file"
        log "INFO" "Successfully processed complete audio file"
    else
        log "ERROR" "Output file not found at $expected_output. Check if processing was successful."
        exit 1
    fi
}

# Function to process downloaded URLs
process_urls() {
    local urls=("$@")
    local temp_dir=$1
    local downloaded_files=()

    for url in "${urls[@]}"; do
        url_filename=$(basename -- "$url")
        url_filename=${url_filename%%\?*}
        downloaded_file="$temp_dir/$(basename "$url_filename")"
        download_file "$url" "$downloaded_file"
        downloaded_files+=("$downloaded_file")
    done

    echo "${downloaded_files[@]}"
}

# Main execution starts here

# Parse command line arguments
output_path=""

while getopts "i:o:l:cm:vf:h-:" opt; do
    case $opt in
        i) input_files+=("$OPTARG");;
        o) output_path="$OPTARG";;
        l) language="$OPTARG";;
        c) enable_chunking=true;;
        m) model_path="$OPTARG";;
        v) verbose=true;;
        f) output_format="$OPTARG";;
        h) show_usage;;
        -)
            case "${OPTARG}" in
                prompt)
                    initial_prompt="${!OPTIND}"; OPTIND=$(( OPTIND + 1 ))
                    ;;
                prompt=*)
                    initial_prompt="${OPTARG#*=}"
                    ;;
                max-length)
                    max_length="${!OPTIND}"; OPTIND=$(( OPTIND + 1 ))
                    ;;
                max-length=*)
                    max_length="${OPTARG#*=}"
                    ;;
                *)
                    log "ERROR" "Invalid option: --${OPTARG}"
                    show_usage
                    ;;
            esac
            ;;
        ?) show_usage;;
    esac
done

# Check if at least one input file is provided
if [ ${#input_files[@]} -eq 0 ]; then
    log "ERROR" "At least one input file is required"
    show_usage
fi

# Setup paths and directories
if [ -z "$output_path" ]; then
    if [ ${#input_files[@]} -eq 1 ]; then
        # Use first input filename for output if only one file
        filename=$(basename -- "${input_files[0]}")
        filename_no_ext="${filename%.*}"
        output_path="$filename_no_ext"
    else
        # Default for multiple files
        output_path="whisper_output"
    fi
    log "INFO" "Using default output path: $output_path"
fi

# Create output directory structure
mkdir -p "$output_path"
temp_dir="$output_path/temp"
mkdir -p "$temp_dir"

# Process any URLs in the input files
processed_files=()
for input_file in "${input_files[@]}"; do
    if [[ "$input_file" =~ ^https?:// ]]; then
        downloaded_file="$temp_dir/$(basename -- "${input_file%%\?*}")"
        download_file "$input_file" "$downloaded_file"
        processed_files+=("$downloaded_file")
    else
        if [ ! -f "$input_file" ]; then
            log "ERROR" "Input file '$input_file' does not exist"
            exit 1
        fi
        processed_files+=("$input_file")
    fi
done

# Define file paths
extension=$(get_output_extension)
transcription_file="$output_path/transcription.$extension"
silence_times_file="$temp_dir/silence_times.txt"
working_wav="$temp_dir/working_audio.wav"

# If only one input file, convert directly
if [ ${#processed_files[@]} -eq 1 ]; then
    log "INFO" "Processing single input file"
    convert_audio "${processed_files[0]}" "$working_wav"
else
    log "INFO" "Processing multiple input files (${#processed_files[@]} files)"
    # Create a temporary WAV for each file and concatenate them
    concatenate_audio_files "${processed_files[@]}" "$working_wav"
fi

# Full model path
full_model_path="$WHISPER_CPP_PATH/$model_path"

# Process the audio file based on user selection
if [ "$enable_chunking" = true ]; then
    log "INFO" "Processing audio in chunking mode"
    # Create chunks directory only when using chunking mode
    chunks_dir="$temp_dir/chunks"
    mkdir -p "$chunks_dir"
    process_chunked "$working_wav" "$chunks_dir" "$silence_times_file" "$transcription_file" "$language" "$full_model_path"
else
    log "INFO" "Processing entire audio file without chunking"
    process_full "$working_wav" "$transcription_file" "$language" "$full_model_path"
fi

log "INFO" "Transcription is available at: $transcription_file"

# Optional: Uncomment to clean up temporary files
# rm -rf "$temp_dir"
