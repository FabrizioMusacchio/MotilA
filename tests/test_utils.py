# tests/test_utils.py
from motila.utils import (
    hello_world_utils,
    check_folder_exist_create)

def test_hello_world(capsys):
    hello_world_utils()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, World! Welcome to MotilA (from utils.py)!"

def test_check_folder_exist_create(tmp_path):
    # tmp_path is a Path object pointing to a unique temp dir
    new_folder = tmp_path / "test_subdir"

    # Make sure it doesn't exist yet
    assert not new_folder.exists()

    # Run the function
    check_folder_exist_create(new_folder, verbose=False)

    # Now it should exist
    assert new_folder.exists()
    assert new_folder.is_dir()
