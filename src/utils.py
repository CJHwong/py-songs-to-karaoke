#!/usr/bin/env python3
"""Utility functions for the Songs to Karaoke application."""

import os
import shutil
import tempfile
from typing import Dict, Optional, Tuple


def create_temp_dir() -> str:
    """Create a temporary directory for processing files.

    Returns:
        Path to the created temporary directory
    """
    return tempfile.mkdtemp(prefix="songs_to_karaoke_")


def cleanup_temp_dir(temp_dir: Optional[str] = None) -> None:
    """Clean up the temporary directory.

    Args:
        temp_dir: Path to the temporary directory to clean up
    """
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def create_project_dir(input_file: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """Create a project directory for output files.

    Args:
        input_file: Path to the input file
        output_dir: Optional custom output directory

    Returns:
        Tuple of (project_dir, base_name)
    """
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    if output_dir:
        project_dir = os.path.abspath(output_dir)
    else:
        # Create a directory in the same location as the input file
        input_dir = os.path.dirname(os.path.abspath(input_file))
        project_dir = os.path.join(input_dir, f"{base_name}")

    os.makedirs(project_dir, exist_ok=True)
    return project_dir, base_name


def load_env_file(env_path: Optional[str] = None) -> Dict[str, str]:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file, if None will look for .env in project root

    Returns:
        Dictionary with environment variables
    """
    if env_path is None:
        # Try to find .env in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, ".env")

    env_vars: Dict[str, str] = {}

    if os.path.exists(env_path):
        with open(env_path) as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    # Expand user directory if needed (e.g., ~/path/to/dir)
                    if "~" in value:
                        value = os.path.expanduser(value)
                    env_vars[key] = value

    return env_vars


def get_env_path(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a path from environment variables, expanding user directory if needed.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Path string or default
    """
    env_vars = load_env_file()

    # Check if exists in loaded .env file
    if key in env_vars:
        value = env_vars[key]
        return os.path.expanduser(value) if "~" in value else value

    # Fall back to system environment variables
    value = os.environ.get(key, default)
    return os.path.expanduser(value) if value and "~" in value else value
