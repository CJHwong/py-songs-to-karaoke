import json
import os
import uuid
from datetime import datetime

class SongLibrary:
    """Manages a library of songs, storing metadata in a JSON file."""

    def __init__(self, library_path="library.json"):
        """
        Initializes the SongLibrary.

        Args:
            library_path (str): Path to the JSON file where the library data is stored.
        """
        self.library_path = library_path
        self.songs = []
        self.load_library()

    def load_library(self):
        """
        Loads the song library from the JSON file.
        If the file doesn't exist or is invalid, starts with an empty library.
        """
        if os.path.exists(self.library_path):
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    self.songs = json.load(f)
                print(f"Library loaded successfully from {self.library_path}")
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {self.library_path}. Starting with an empty library.")
                self.songs = []
            except IOError as e:
                print(f"Error reading library file {self.library_path}: {e}. Starting with an empty library.")
                self.songs = []
        else:
            print(f"Library file {self.library_path} not found. Starting with an empty library.")
            self.songs = []

    def save_library(self):
        """
        Saves the current state of the song library to the JSON file.
        """
        try:
            with open(self.library_path, 'w', encoding='utf-8') as f:
                json.dump(self.songs, f, indent=4, ensure_ascii=False)
            print(f"Library saved successfully to {self.library_path}")
        except IOError as e:
            print(f"Error writing library file {self.library_path}: {e}")
        except TypeError as e:
            print(f"Error serializing song data to JSON: {e}")


    def add_song(self, song_data: dict) -> str | None:
        """
        Adds a new song to the library.

        Args:
            song_data (dict): A dictionary containing song metadata.
                              Required keys: 'title', 'original_file_path',
                                             'instrumental_file_path', 'lyrics_file_path'.
                              Optional keys: 'artist', 'vocals_file_path', 'cover_art_path'.

        Returns:
            str | None: The ID of the newly added song, or None if addition failed.
        """
        required_keys = ['title', 'original_file_path', 'instrumental_file_path', 'lyrics_file_path']
        for key in required_keys:
            if key not in song_data:
                print(f"Error: Missing required key '{key}' in song_data.")
                return None

        new_song_id = uuid.uuid4().hex
        song_entry = {
            "id": new_song_id,
            "title": song_data.get("title"),
            "artist": song_data.get("artist"),
            "original_file_path": song_data.get("original_file_path"),
            "instrumental_file_path": song_data.get("instrumental_file_path"),
            "vocals_file_path": song_data.get("vocals_file_path"),
            "lyrics_file_path": song_data.get("lyrics_file_path"),
            "cover_art_path": song_data.get("cover_art_path"),
            "date_added": datetime.now().isoformat()
        }
        self.songs.append(song_entry)
        self.save_library()
        print(f"Song '{song_entry['title']}' added with ID: {new_song_id}")
        return new_song_id

    def remove_song(self, song_id: str) -> bool:
        """
        Removes a song from the library by its ID.

        Args:
            song_id (str): The ID of the song to remove.

        Returns:
            bool: True if a song was removed, False otherwise.
        """
        original_length = len(self.songs)
        self.songs = [song for song in self.songs if song.get("id") != song_id]
        if len(self.songs) < original_length:
            self.save_library()
            print(f"Song with ID: {song_id} removed.")
            return True
        print(f"Song with ID: {song_id} not found.")
        return False

    def get_song_by_id(self, song_id: str) -> dict | None:
        """
        Retrieves a song from the library by its ID.

        Args:
            song_id (str): The ID of the song to retrieve.

        Returns:
            dict | None: The song dictionary if found, otherwise None.
        """
        for song in self.songs:
            if song.get("id") == song_id:
                return song
        return None

    def get_all_songs(self) -> list:
        """
        Returns a copy of all songs in the library.

        Returns:
            list: A list of song dictionaries.
        """
        return list(self.songs) # Return a copy

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Create a dummy library file path in a temporary location for testing
    test_library_file = "test_library.json"

    # Ensure a clean state for testing
    if os.path.exists(test_library_file):
        os.remove(test_library_file)

    library = SongLibrary(library_path=test_library_file)

    print("\n--- Initial empty library ---")
    print(f"Songs: {library.get_all_songs()}")

    print("\n--- Adding songs ---")
    song1_data = {
        "title": "Test Song 1",
        "artist": "Artist A",
        "original_file_path": "/path/to/original1.mp3",
        "instrumental_file_path": "/path/to/instrumental1.wav",
        "lyrics_file_path": "/path/to/lyrics1.json",
        "vocals_file_path": "/path/to/vocals1.wav"
    }
    song1_id = library.add_song(song1_data)

    song2_data = {
        "title": "Test Song 2",
        "original_file_path": "/path/to/original2.m4a", # Missing artist
        "instrumental_file_path": "/path/to/instrumental2.wav",
        "lyrics_file_path": "/path/to/lyrics2.json"
    }
    song2_id = library.add_song(song2_data)

    # Test adding a song with missing required data
    song3_data_invalid = {
        "title": "Incomplete Song"
        # Missing other required fields
    }
    library.add_song(song3_data_invalid)


    print(f"\n--- All songs after adding (should be 2) ---")
    for song in library.get_all_songs():
        print(song)

    print(f"\n--- Get song by ID ({song1_id}) ---")
    song = library.get_song_by_id(song1_id)
    if song:
        print(song)
    else:
        print(f"Song with ID {song1_id} not found.")

    print(f"\n--- Get song by ID (non-existent) ---")
    song = library.get_song_by_id("non_existent_id")
    if song:
        print(song)
    else:
        print(f"Song with ID non_existent_id not found.")


    print("\n--- Removing a song ---")
    library.remove_song(song1_id)
    print(f"Songs after removing {song1_id}: {library.get_all_songs()}")

    print("\n--- Removing a non-existent song ---")
    library.remove_song("non_existent_id")
    print(f"Songs: {library.get_all_songs()}")

    print("\n--- Testing persistence (loading from file) ---")
    # Create a new library instance, it should load from test_library.json
    library2 = SongLibrary(library_path=test_library_file)
    print(f"Songs in new library instance (should have Test Song 2):")
    for song_item in library2.get_all_songs():
        print(song_item)
    assert len(library2.get_all_songs()) == 1
    assert library2.get_all_songs()[0]['title'] == "Test Song 2"


    print("\n--- Adding another song to library2 ---")
    song4_data = {
        "title": "Test Song 4 in Lib2",
        "artist": "Artist B",
        "original_file_path": "/path/to/original4.mp3",
        "instrumental_file_path": "/path/to/instrumental4.wav",
        "lyrics_file_path": "/path/to/lyrics4.json",
    }
    library2.add_song(song4_data)
    print(f"Songs in library2: {len(library2.get_all_songs())}") # Should be 2

    # library (original instance) should not be affected until it reloads
    print(f"Songs in original library instance (still 1 until reload): {len(library.get_all_songs())}")
    library.load_library() # Reload
    print(f"Songs in original library instance after reload (now 2): {len(library.get_all_songs())}")


    # Clean up the test library file
    if os.path.exists(test_library_file):
        os.remove(test_library_file)
    print(f"\nCleaned up {test_library_file}")

    print("\n--- Test with non-existent directory for library path (save should fail gracefully) ---")
    library_bad_path = SongLibrary(library_path="non_existent_dir/bad_library.json")
    song_bad_save = {
        "title": "Bad Save Test",
        "original_file_path": "dummy.mp3",
        "instrumental_file_path": "dummy.wav",
        "lyrics_file_path": "dummy.json"
    }
    library_bad_path.add_song(song_bad_save) # This should print an error during save_library()

    print("\n--- Test loading a corrupted JSON file ---")
    corrupted_file_path = "corrupted_library.json"
    with open(corrupted_file_path, 'w') as f:
        f.write("{'invalid_json': ") # Write intentionally broken JSON
    
    corrupted_library = SongLibrary(library_path=corrupted_file_path)
    print(f"Songs in corrupted_library (should be empty): {corrupted_library.get_all_songs()}")

    if os.path.exists(corrupted_file_path):
        os.remove(corrupted_file_path)
    print(f"Cleaned up {corrupted_file_path}")

    print("\n--- End of tests ---")
