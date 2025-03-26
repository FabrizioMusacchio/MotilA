# tests/test_utils.py
from motila.utils import (
    hello_world_utils,
    check_folder_exist_create,
    getfile,
    filterfolder_by_string,
    filterfiles_by_string)
import sys
from unittest import mock



# test_hello_world:
def test_hello_world(capsys):
    hello_world_utils()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, World! Welcome to MotilA (from utils.py)!"

# test_check_folder_exist_create
def test_check_folder_exist_create(tmp_path):
    # tmp_path is a Path object pointing to a unique temp dir
    new_folder = tmp_path / "test_subdir"

    # make sure it doesn't exist yet:
    assert not new_folder.exists()

    # run the function:
    check_folder_exist_create(new_folder, verbose=False)

    # now it should exist:
    assert new_folder.exists()
    assert new_folder.is_dir()

# getfile:
def test_getfile_script():
    with mock.patch.dict('sys.modules', {'__main__': mock.Mock(__file__='/some/script.py')}):
        result = getfile()
        assert result == 'script.py'

def test_getfile_console():
    with mock.patch.dict('sys.modules', {'__main__': mock.Mock(__file__='<input>')}):
        result = getfile()
        assert result == 'console'

def test_getfile_exception():
    with mock.patch.dict('sys.modules', {'__main__': mock.Mock()}):
        del sys.modules['__main__'].__file__
        result = getfile()
        assert result == 'console'
        
# filterfolder_by_string:
def test_filterfolder_by_string(tmp_path):
    (tmp_path / "data_1").mkdir()
    (tmp_path / "data_2").mkdir()
    (tmp_path / "logs").mkdir()

    indices, matching, all_folders = filterfolder_by_string(str(tmp_path) + '/', 'data')

    assert sorted(matching) == ["data_1", "data_2"]
    assert all(f in ["data_1", "data_2", "logs"] for f in all_folders)

# filterfiles_by_string:
def test_filterfiles_by_string(tmp_path):
    (tmp_path / "report_data.txt").write_text("report")
    (tmp_path / "summary_data.csv").write_text("summary")
    (tmp_path / "ignore.me").write_text("meh")

    indices, matching, all_files = filterfiles_by_string(str(tmp_path) + '/', 'data')

    assert sorted(matching) == ["report_data.txt", "summary_data.csv"]
    assert all(f in ["report_data.txt", "summary_data.csv", "ignore.me"] for f in all_files)