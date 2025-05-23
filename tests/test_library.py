import unittest
import os
import json
import uuid
from datetime import datetime
import time # For unique filenames if needed

# Adjust path to import SongLibrary from src
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.library import SongLibrary

class TestSongLibrary(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Create a unique temporary library file name for each test run
        # to prevent interference if tests run very quickly or if cleanup fails.
        self.test_library_file = f"temp_test_library_{uuid.uuid4().hex}.json"
        self.library = SongLibrary(library_path=self.test_library_file)

        # Sample song data for reuse
        self.song_data1 = {
            "title": "Test Song 1", "artist": "Artist A",
            "original_file_path": "path/to/original1.mp3",
            "instrumental_file_path": "path/to/instrumental1.wav",
            "lyrics_file_path": "path/to/lyrics1.json",
            "vocals_file_path": "path/to/vocals1.wav",
            "cover_art_path": "path/to/cover1.jpg"
        }
        self.song_data2 = {
            "title": "Test Song 2", "artist": "Artist B",
            "original_file_path": "path/to/original2.m4a",
            "instrumental_file_path": "path/to/instrumental2.wav",
            "lyrics_file_path": "path/to/lyrics2.json"
            # Missing optional fields
        }

    def tearDown(self):
        """Tear down after test methods."""
        if os.path.exists(self.test_library_file):
            try:
                os.remove(self.test_library_file)
            except Exception as e:
                print(f"Error removing test library file {self.test_library_file}: {e}")
        
        # Clean up associated songs directory if created by ImportDialog tests (though not directly tested here)
        songs_dir = self.test_library_file.replace(".json", "_songs")
        if os.path.exists(songs_dir):
            try:
                import shutil
                shutil.rmtree(songs_dir)
            except Exception as e:
                print(f"Error removing test songs directory {songs_dir}: {e}")


    def test_initialization_new_file_starts_empty(self):
        """Test that a new library starts empty and the file is not created until save."""
        self.assertEqual(len(self.library.get_all_songs()), 0)
        self.assertFalse(os.path.exists(self.test_library_file), "Library file should not exist before first save.")

    def test_save_library_creates_file(self):
        """Test that saving the library creates the JSON file."""
        self.library.add_song(self.song_data1) # Adding a song triggers save
        self.assertTrue(os.path.exists(self.test_library_file))
        with open(self.test_library_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], self.song_data1['title'])

    def test_load_existing_library(self):
        """Test loading an existing library file."""
        # Manually create a library file
        song_id_manual = uuid.uuid4().hex
        date_manual = datetime.now().isoformat()
        manual_data = [{
            "id": song_id_manual, "title": "Manual Song", "artist": "Manual Artist",
            "original_file_path": "manual/original.mp3",
            "instrumental_file_path": "manual/instrumental.wav",
            "lyrics_file_path": "manual/lyrics.json",
            "date_added": date_manual
        }]
        with open(self.test_library_file, 'w') as f:
            json.dump(manual_data, f)

        # Create new library instance to load this file
        library2 = SongLibrary(library_path=self.test_library_file)
        self.assertEqual(len(library2.get_all_songs()), 1)
        loaded_song = library2.get_song_by_id(song_id_manual)
        self.assertIsNotNone(loaded_song)
        self.assertEqual(loaded_song['title'], "Manual Song")

    def test_load_corrupt_json_file(self):
        """Test that a corrupt JSON file leads to an empty library without crashing."""
        with open(self.test_library_file, 'w') as f:
            f.write("{'invalid_json': True,") # Intentionally corrupt JSON

        # Suppress print messages during this test for cleaner output
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            library_corrupt = SongLibrary(library_path=self.test_library_file)
        finally:
            sys.stdout.close() # Make sure to close the stream
            sys.stdout = original_stdout # Restore stdout

        self.assertEqual(len(library_corrupt.get_all_songs()), 0, "Library should be empty after loading corrupt JSON.")
        # The corrupt file should still exist, SongLibrary doesn't delete it
        self.assertTrue(os.path.exists(self.test_library_file))


    def test_add_song_valid(self):
        """Test adding a valid song."""
        song_id = self.library.add_song(self.song_data1)
        self.assertIsNotNone(song_id)
        self.assertEqual(len(self.library.get_all_songs()), 1)
        
        added_song = self.library.get_song_by_id(song_id)
        self.assertIsNotNone(added_song)
        self.assertEqual(added_song['title'], self.song_data1['title'])
        self.assertEqual(added_song['artist'], self.song_data1['artist'])
        self.assertIn('id', added_song)
        self.assertEqual(added_song['id'], song_id)
        self.assertIn('date_added', added_song)
        try:
            datetime.fromisoformat(added_song['date_added'])
        except ValueError:
            self.fail("date_added is not a valid ISO format datetime string.")

    def test_add_song_missing_required_fields(self):
        """Test adding a song with missing required fields."""
        invalid_data = {"title": "Incomplete Song"} # Missing other required fields
        song_id = self.library.add_song(invalid_data)
        self.assertIsNone(song_id, "Song ID should be None for invalid data.")
        self.assertEqual(len(self.library.get_all_songs()), 0, "Song should not be added if required fields are missing.")

    def test_add_song_generates_unique_ids(self):
        """Test that adding multiple songs generates unique IDs."""
        song_id1 = self.library.add_song(self.song_data1)
        song_id2 = self.library.add_song(self.song_data2)
        self.assertIsNotNone(song_id1)
        self.assertIsNotNone(song_id2)
        self.assertNotEqual(song_id1, song_id2)
        self.assertEqual(len(self.library.get_all_songs()), 2)

    def test_remove_song_existing(self):
        """Test removing an existing song."""
        song_id = self.library.add_song(self.song_data1)
        self.assertIsNotNone(song_id)
        
        removal_result = self.library.remove_song(song_id)
        self.assertTrue(removal_result)
        self.assertEqual(len(self.library.get_all_songs()), 0)
        self.assertIsNone(self.library.get_song_by_id(song_id))

    def test_remove_song_non_existent(self):
        """Test removing a non-existent song ID."""
        self.library.add_song(self.song_data1)
        non_existent_id = uuid.uuid4().hex
        
        removal_result = self.library.remove_song(non_existent_id)
        self.assertFalse(removal_result)
        self.assertEqual(len(self.library.get_all_songs()), 1) # Library should be unchanged

    def test_get_song_by_id_non_existent(self):
        """Test get_song_by_id for a non-existent song."""
        self.assertIsNone(self.library.get_song_by_id(uuid.uuid4().hex))

    def test_get_all_songs_empty_and_filled(self):
        """Test get_all_songs on an empty and then filled library."""
        self.assertEqual(self.library.get_all_songs(), [])
        
        self.library.add_song(self.song_data1)
        self.library.add_song(self.song_data2)
        
        all_songs = self.library.get_all_songs()
        self.assertEqual(len(all_songs), 2)
        # Check if it returns a copy, not the original list
        all_songs.append("modification_test")
        self.assertEqual(len(self.library.get_all_songs()), 2, "get_all_songs should return a copy.")


    def test_save_and_load_persistence(self):
        """Test that data persists correctly after saving and loading."""
        song1_id = self.library.add_song(self.song_data1)
        song2_id = self.library.add_song(self.song_data2)

        # Create a new library instance loading from the same file
        library2 = SongLibrary(library_path=self.test_library_file)
        self.assertEqual(len(library2.get_all_songs()), 2)

        loaded_song1 = library2.get_song_by_id(song1_id)
        self.assertIsNotNone(loaded_song1)
        self.assertEqual(loaded_song1['title'], self.song_data1['title'])

        loaded_song2 = library2.get_song_by_id(song2_id)
        self.assertIsNotNone(loaded_song2)
        self.assertEqual(loaded_song2['title'], self.song_data2['title'])
        self.assertIsNone(loaded_song2.get('cover_art_path')) # Was not in song_data2

    def test_song_data_optional_fields(self):
        """Test adding songs where optional fields are None or not present."""
        song_data_minimal = {
            "title": "Minimal Song",
            "original_file_path": "path/original.mp3",
            "instrumental_file_path": "path/instrumental.wav",
            "lyrics_file_path": "path/lyrics.json",
            # artist, vocals_file_path, cover_art_path are optional
        }
        song_id = self.library.add_song(song_data_minimal)
        self.assertIsNotNone(song_id)
        added_song = self.library.get_song_by_id(song_id)
        self.assertIsNotNone(added_song)
        self.assertIsNone(added_song.get('artist'))
        self.assertIsNone(added_song.get('vocals_file_path'))
        self.assertIsNone(added_song.get('cover_art_path'))

    def test_library_file_not_found_on_init(self):
        """Test SongLibrary initialization when the library file does not exist."""
        non_existent_file = f"non_existent_library_{uuid.uuid4().hex}.json"
        # Suppress print messages for cleaner output
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            lib_new = SongLibrary(library_path=non_existent_file)
        finally:
            sys.stdout.close()
            sys.stdout = original_stdout
        
        self.assertEqual(len(lib_new.get_all_songs()), 0)
        # Ensure it doesn't create the file on init, only on save
        self.assertFalse(os.path.exists(non_existent_file))


if __name__ == '__main__':
    unittest.main()
