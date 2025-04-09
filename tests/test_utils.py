""" 
pip install pytest

In a terminal, run:
pytest
"""
import sys
from motila.utils import (
    hello_world_utils,
    check_folder_exist_create,
    getfile,
    filterfolder_by_string,
    filterfiles_by_string,
    calc_process_time_logger,
    logger_object,
    print_ram_usage, 
    print_ram_usage_in_loop,
    tiff_axes_check_and_correct)
from unittest import mock
from datetime import datetime
import re
import logging
import psutil
import tifffile
from pathlib import Path
import numpy as np
from pathlib import Path
import pytest



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
    
# calc_process_time_logger:
def test_calc_process_time_logger_min():
    with mock.patch("time.time", return_value=160.0):
        dt, out = calc_process_time_logger(t0=100.0, verbose=False, unit="min", process="Test: ")
        assert dt == 60.0
        assert out == "Test: process time: 1.0 min"

def test_calc_process_time_logger_sec_with_leadspace(capsys):
    with mock.patch("time.time", return_value=105.25):
        dt, out = calc_process_time_logger(t0=100.0, verbose=True, unit="sec", leadspaces="  ", process="Run A: ")
        assert round(dt, 2) == 5.25
        assert out == "  Run A: process time: 5.25 sec"

        # Capture printed output
        captured = capsys.readouterr()
        assert "Run A: process time: 5.25 sec" in captured.out

# test_logger_object_basic
def test_logger_object_basic(tmp_path):
    # Mock getfile to return a fixed name
    with mock.patch("motila.utils.getfile", return_value="test_script.py"), \
         mock.patch("motila.utils.datetime") as mock_datetime:

        # Create a fake datetime object with a working strftime method
        fake_now = mock.Mock()
        fake_now.strftime.return_value = "2025-01-01 (10h30m00s)"
        mock_datetime.now.return_value = fake_now

        # Create logger in tmp_path
        logger = logger_object(logger_path=str(tmp_path))

        # Log some messages without printing to console
        logger.log("hello from the logger", spaces=2, printconsole=False)
        logger.logc("chapter start", printconsole=False)
        logger.stop(printconsole=False)

        # Check logfile exists
        logfile = list((tmp_path / "logs").glob("*.log"))[0]
        assert logfile.exists()

        # Verify log contents
        content = logfile.read_text()
        assert "hello from the logger" in content
        assert "chapter start" in content
        assert "===================================================================" in content


# print_ram_usage:
def test_print_ram_usage(capsys):
    # Mock psutil to return a controlled memory usage
    mock_process = mock.Mock()
    mock_process.memory_info.return_value.rss = 150 * 1024 * 1024  # 150 MB
    with mock.patch("psutil.Process", return_value=mock_process):
        print_ram_usage(indent=4)
        captured = capsys.readouterr()
        assert "    Current RAM usage: 150.00 MB" in captured.out


# test_print_ram_usage:
def test_print_ram_usage_in_loop(capsys):
    mock_process = mock.Mock()
    mock_process.memory_info.return_value.rss = 123.45 * 1024 * 1024  # 123.45 MB
    with mock.patch("psutil.Process", return_value=mock_process):
        print_ram_usage_in_loop(indent=2)
        captured = capsys.readouterr()
        assert "\r  Current RAM usage: 123.45 MB" in captured.out


# tiff_axes_check_and_correct:
def test_axes_already_correct_tzyx(tmp_path):
    fname = tmp_path / "already_correct.tif"
    arr = np.random.rand(2, 3, 128, 128).astype(np.float32)  # TZYX
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZYX"})
    
    out = tiff_axes_check_and_correct(fname)
    assert out == fname  # Should return the original
    assert fname.exists()

def test_axes_missing_raises(tmp_path):
    fname = tmp_path / "invalid_axes.tif"
    arr = np.random.rand(2, 128, 128).astype(np.float32)  # CYX — no T/Z
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "CYX"})
    
    with pytest.raises(ValueError, match="Missing required axes"):
        tiff_axes_check_and_correct(fname)

def test_missing_imagej_metadata(tmp_path):
    fname = tmp_path / "no_metadata.tif"
    arr = np.random.rand(2, 3, 1, 128, 128).astype(np.float32)

    tifffile.imwrite(fname, arr, imagej=True)  # no axes metadata

    corrected = tiff_axes_check_and_correct(fname)
    assert corrected.exists()
    assert corrected.name == fname.name or corrected.name.startswith("axes_corrected_")

    with tifffile.TiffFile(corrected) as tif:
        # Only check axes if correction actually happened
        if corrected.name.startswith("axes_corrected_"):
            assert "axes" in tif.imagej_metadata
            assert tif.imagej_metadata["axes"] in {"TZCYX", "TZYX"}
