#!/usr/bin/env python3
"""
Test cases for utils.py module
"""

import os
import unittest.mock as mock

from utils import cleanup_temp_dir, create_project_dir, create_temp_dir, get_env_path, load_env_file


class TestUtils:
    """Test cases for utility functions in utils.py"""

    @mock.patch("utils.tempfile.mkdtemp")
    def test_create_temp_dir(self, mock_mkdtemp):
        """Test creating a temporary directory"""
        # Setup
        mock_mkdtemp.return_value = "/tmp/songs_to_karaoke_123456"

        # Execute
        result = create_temp_dir()

        # Assert
        assert result == "/tmp/songs_to_karaoke_123456"
        mock_mkdtemp.assert_called_once_with(prefix="songs_to_karaoke_")

    @mock.patch("utils.shutil.rmtree")
    @mock.patch("utils.os.path.exists")
    def test_cleanup_temp_dir(self, mock_exists, mock_rmtree):
        """Test cleaning up a temporary directory"""
        # Setup
        temp_dir = "/tmp/songs_to_karaoke_123456"
        mock_exists.return_value = True

        # Execute
        cleanup_temp_dir(temp_dir)

        # Assert
        mock_exists.assert_called_once_with(temp_dir)
        mock_rmtree.assert_called_once_with(temp_dir)

    @mock.patch("utils.shutil.rmtree")
    @mock.patch("utils.os.path.exists")
    def test_cleanup_temp_dir_nonexistent(self, mock_exists, mock_rmtree):
        """Test cleaning up a non-existent directory"""
        # Setup
        temp_dir = "/tmp/songs_to_karaoke_123456"
        mock_exists.return_value = False

        # Execute
        cleanup_temp_dir(temp_dir)

        # Assert
        mock_exists.assert_called_once_with(temp_dir)
        mock_rmtree.assert_not_called()

    @mock.patch("utils.os.makedirs")
    def test_create_project_dir_with_output_dir(self, mock_makedirs):
        """Test creating a project directory with custom output directory"""
        # Setup
        input_file = "/path/to/input/song.mp3"
        output_dir = "/custom/output/dir"

        # Execute
        project_dir, base_name = create_project_dir(input_file, output_dir)

        # Assert
        assert project_dir == "/custom/output/dir"
        assert base_name == "song"
        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)

    @mock.patch("utils.os.makedirs")
    @mock.patch("utils.os.path.dirname")
    @mock.patch("utils.os.path.abspath")
    def test_create_project_dir_default_location(self, mock_abspath, mock_dirname, mock_makedirs):
        """Test creating a project directory in default location"""
        # Setup
        input_file = "/path/to/input/song.mp3"
        mock_abspath.return_value = input_file
        mock_dirname.return_value = "/path/to/input"

        # Execute
        project_dir, base_name = create_project_dir(input_file)

        # Assert
        assert project_dir == "/path/to/input/song"
        assert base_name == "song"
        mock_makedirs.assert_called_once_with("/path/to/input/song", exist_ok=True)

    @mock.patch("builtins.open")
    @mock.patch("utils.os.path.exists")
    @mock.patch("utils.os.path.dirname")
    @mock.patch("utils.os.path.abspath")
    def test_load_env_file_custom_path(self, mock_abspath, mock_dirname, mock_exists, mock_open):
        """Test loading environment variables from a custom .env file path"""
        # Setup
        env_path = "/custom/path/.env"
        mock_exists.return_value = True
        mock_file = mock.mock_open(read_data="KEY1=value1\nKEY2=~/path/value2\n# Comment\n\nKEY3=value3")
        mock_open.side_effect = mock_file

        # Execute
        with mock.patch("utils.os.path.expanduser", lambda x: x.replace("~", "/home/user")):
            result = load_env_file(env_path)

        # Assert
        assert result == {"KEY1": "value1", "KEY2": "/home/user/path/value2", "KEY3": "value3"}
        mock_exists.assert_called_once_with(env_path)
        mock_open.assert_called_once_with(env_path)

    @mock.patch("builtins.open")
    @mock.patch("utils.os.path.exists")
    @mock.patch("utils.os.path.dirname")
    @mock.patch("utils.os.path.abspath")
    def test_load_env_file_default_path(self, mock_abspath, mock_dirname, mock_exists, mock_open):
        """Test loading environment variables from default .env file path"""
        # Setup
        # First called for __file__, then for project root calculation
        mock_abspath.side_effect = ["/project/src/utils.py", "/project/src"]
        # Called twice, once for each dirname call
        mock_dirname.side_effect = ["/project/src", "/project"]
        mock_exists.return_value = True
        mock_file = mock.mock_open(read_data="KEY1=value1\nKEY2=value2")
        mock_open.side_effect = mock_file

        # Execute
        result = load_env_file()

        # Assert
        assert result == {"KEY1": "value1", "KEY2": "value2"}
        # Check that it looked for .env in the project root
        expected_path = os.path.join("/project", ".env")
        mock_exists.assert_called_once_with(expected_path)

    @mock.patch("utils.os.path.exists")
    def test_load_env_file_not_found(self, mock_exists):
        """Test loading environment variables when .env file doesn't exist"""
        # Setup
        mock_exists.return_value = False

        # Execute
        result = load_env_file("/nonexistent/.env")

        # Assert
        assert result == {}
        mock_exists.assert_called_once_with("/nonexistent/.env")

    @mock.patch("utils.load_env_file")
    @mock.patch("utils.os.environ.get")
    def test_get_env_path_from_env_file(self, mock_environ_get, mock_load_env_file):
        """Test getting environment path from .env file"""
        # Setup
        mock_load_env_file.return_value = {"TEST_PATH": "/path/from/env/file"}

        # Execute
        result = get_env_path("TEST_PATH", "/default/path")

        # Assert
        assert result == "/path/from/env/file"
        mock_load_env_file.assert_called_once()
        mock_environ_get.assert_not_called()  # Should not fall back to os.environ

    @mock.patch("utils.load_env_file")
    @mock.patch("utils.os.environ.get")
    def test_get_env_path_from_system_env(self, mock_environ_get, mock_load_env_file):
        """Test getting environment path from system environment variables"""
        # Setup
        mock_load_env_file.return_value = {}  # Empty .env file
        mock_environ_get.return_value = "/path/from/system/env"

        # Execute
        result = get_env_path("TEST_PATH", "/default/path")

        # Assert
        assert result == "/path/from/system/env"
        mock_load_env_file.assert_called_once()
        mock_environ_get.assert_called_once_with("TEST_PATH", "/default/path")

    @mock.patch("utils.load_env_file")
    @mock.patch("utils.os.environ.get")
    def test_get_env_path_default(self, mock_environ_get, mock_load_env_file):
        """Test getting default path when environment variable not found"""
        # Setup
        mock_load_env_file.return_value = {}  # Empty .env file
        # Return the default we pass to it
        mock_environ_get.side_effect = lambda key, default: default

        # Execute
        result = get_env_path("TEST_PATH", "/default/path")

        # Assert
        assert result == "/default/path"
        mock_load_env_file.assert_called_once()
        mock_environ_get.assert_called_once_with("TEST_PATH", "/default/path")

    @mock.patch("utils.load_env_file")
    @mock.patch("utils.os.path.expanduser")
    def test_get_env_path_with_tilde(self, mock_expanduser, mock_load_env_file):
        """Test expanding user directory in environment path"""
        # Setup
        mock_load_env_file.return_value = {"TEST_PATH": "~/path/to/dir"}
        mock_expanduser.return_value = "/home/user/path/to/dir"

        # Execute
        result = get_env_path("TEST_PATH")

        # Assert
        assert result == "/home/user/path/to/dir"
        mock_expanduser.assert_called_once_with("~/path/to/dir")
