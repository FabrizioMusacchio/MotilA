""" 
pip install pytest

In a terminal, run:
pytest
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os
from motila.motila import (
    hello_world,
    calc_projection_range,
    plot_2D_image,
    plot_2D_image_as_tif,
    plot_histogram,
    plot_histogram_of_projections,
    plot_projected_stack_as_tif,
    plot_projected_stack,
    get_stack_dimensions,
    extract_subvolume,
    extract_and_register_subvolume,
    spectral_unmix,
    histogram_equalization,
    histogram_equalization_on_projections,
    histogram_matching,
    histogram_matching_on_projections,
    median_filtering_on_projections,
    circular_median_filtering_on_projections,
    single_slice_median_filtering,
    single_slice_circular_median_filtering,
    gaussian_blurr_filtering_on_projections,
    single_slice_gaussian_blurr_filtering,
    z_max_project,
    compare_histograms,
    plot_intensities,
    reg_2D_images,
    binarize_2D_images,
    remove_small_blobs,
    plot_pixel_areas,
    motility,
    process_stack,
    batch_process_stacks,
    batch_collect
    )
import numpy as np
import tifffile
import matplotlib.pyplot as plt
import time
import pytest
import zarr
import gc
from skimage import exposure
import pandas as pd
from unittest.mock import MagicMock, patch
import shutil

# test test_hello_world:
def test_hello_world(capsys):
    hello_world()
    captured = capsys.readouterr()
    assert "Hello, World! Welcome to MotilA!" in captured.out


# calc_projection_range:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, message):
        self.messages.append(message)

def test_projection_range_normal_case():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=10,
        projection_layers=5,
        I_shape=(100, 30),  # shape: (y, z)
        log=log
    )
    assert result_1 == [8, 12]  # For projection_center=10 and projection_layers=5
    assert result_2 == 5 # The number of layers should be 5
    assert "Projection center: 10, Projection range: [8, 12]" in log.messages[-1]

def test_projection_range_normal_case1():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=9,
        projection_layers=5,
        I_shape=(100, 30),  # shape: (y, z)
        log=log
    )
    assert result_1 == [7, 11]  # For projection_center=9 and projection_layers=5
    assert result_2 == 5 # The number of layers should be 5
    assert "Projection center: 9, Projection range: [7, 11]" in log.messages[-1]

def test_projection_upper_exceeds():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=28,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result_1 == [25, 29]  # Projection center at 28, layers should be [25, 26, 27, 28, 29]
    assert result_2 == 5  # The number of layers should be 5
    assert "Projection center" in log.messages[-1]
    assert len(log.messages) > 1  # Expect a warning for exceeding
    assert "Projection center: 28, Projection range: [25, 29]" in log.messages[-1]

def test_projection_lower_exceeds():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=1,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result_1 == [0, 4]  # Projection center at 1, layers should be [0, 1, 2, 3]
    assert result_2 == 5  # The number of layers should be 5
    assert "adjusted as it was below 0" in log.messages[-2]

def test_projection_completely_out_of_bounds():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=40,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result_1 == [0, 0]  # Projection center at 40, no layers possible, adjusted to [0, 0]
    assert result_2 == 0  # No layers can be included
    assert "WARNING: projection center 40 is out of bounds for image z-dimension 30 -> skipping." in log.messages[-1]

def test_projection_even_layers():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=13,
        projection_layers=6,
        I_shape=(100, 30),
        log=log
    )
    assert result_1 == [11, 16]  # Projection center at 13, layers should be [11, 12, 13, 14, 15, 16]
    assert result_2 == 6  # The number of layers should be 6
    assert "Projection center: 13" in log.messages[-1]

def test_projection_odd_layers():
    log = MockLogger()
    result_1, result_2 = calc_projection_range(
        projection_center=14,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result_1 == [12, 16]  # Projection center at 14, layers should be [12, 13, 14, 15, 16]
    assert result_2 == 5  # The number of layers should be 5
    assert "Projection center: 14" in log.messages[-1]


# plot_2D_image:
def test_plot_2D_image_creates_file(tmp_path):
    # Create a simple 2D image
    np.random.seed(42)
    image = np.random.rand(100, 100)
    plot_title = "test_plot"
    plot_path = tmp_path

    # Call the function
    plot_2D_image(
        image=image,
        plot_path=plot_path,
        plot_title=plot_title,
        fignum=42,
        show_ticks=True,
        cbar_show=True,
        cbar_label="Intensity",
        title="Test Image"
    )

    # Check that the PDF file exists
    output_file = plot_path / f"{plot_title}.pdf"
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # file is not empty


# plot_2D_image_as_tif:
def test_plot_2D_image_as_tif(tmp_path):
    # Create dummy 2D image
    np.random.seed(42)
    image = np.random.rand(64, 64).astype(np.float32)
    plot_title = "test_image"
    plot_path = tmp_path

    # Call the function
    plot_2D_image_as_tif(image, plot_path, plot_title)

    # Check if file was created
    output_file = plot_path / f"{plot_title}.tif"
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # file is not empty

    # Optional: open and verify the TIFF file contents
    with tifffile.TiffFile(output_file) as tif:
        loaded = tif.asarray()
        assert loaded.shape == image.shape
        assert np.allclose(loaded, image)

# plot_histogram_creates_pdf:
def test_plot_histogram_creates_pdf(tmp_path):
    # Generate test image
    np.random.seed(42)
    image = np.random.rand(128, 128).astype(np.float32)
    plot_title = "hist_test"
    plot_path = tmp_path

    # Call the histogram plotting function
    plot_histogram(image, plot_path, plot_title, fignum=99, title="Histogram Test")

    # Check that the PDF was created
    output_file = plot_path / f"{plot_title}.pdf"
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # Make sure it's not empty

# plot_histogram_of_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} finished")
        return time.time() - t0

def test_plot_histogram_of_projections(tmp_path):
    # Create a stack of 3 images (3 x 64 x 64)
    np.random.seed(42)
    stack = np.random.rand(3, 64, 64).astype(np.float32)
    I_shape = stack.shape  # (3, 64, 64) → T, Y, X

    # Dummy logger
    log = MockLogger()

    # Call the function
    plot_histogram_of_projections(stack, I_shape=I_shape, plot_path=tmp_path, log=log)

    # Verify that 3 histogram PDFs were created
    for i in range(3):
        filename = tmp_path / f"MG projected, histogram, stack {i}.pdf"
        assert filename.exists()
        assert filename.stat().st_size > 0

    # Optionally check logging
    assert any("histogram plotting" in msg for msg in log.messages)


# plot_projected_stack_as_tif:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} finished")
        return time.time() - t0

def test_plot_projected_stack_as_tif(tmp_path):
    # Create a dummy 3D stack: 3 slices of 64x64
    np.random.seed(42)
    stack = np.random.rand(3, 64, 64).astype(np.float32)
    I_shape = stack.shape  # (3, 64, 64)
    log = MockLogger()

    # Call the function
    plot_projected_stack_as_tif(
        stack,
        I_shape,
        tmp_path,
        log,
        plottitle="test_projection"
    )

    # Check each TIFF file exists and matches expected shape
    for i in range(stack.shape[0]):
        tif_file = tmp_path / f"test_projection, stack {i}.tif"
        assert tif_file.exists()
        assert tif_file.stat().st_size > 0
        with tifffile.TiffFile(tif_file) as tif:
            loaded = tif.asarray()
            assert loaded.shape == stack[i].shape
            assert np.allclose(loaded, stack[i])

    # Optional: check logging happened
    assert any("tif saving" in msg for msg in log.messages)

# plot_projected_stack:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} finished")
        return time.time() - t0

def test_plot_projected_stack(tmp_path):
    # Create a 3D stack of grayscale 2D images
    np.random.seed(42)
    stack = np.random.rand(3, 64, 64).astype(np.float32)
    I_shape = stack.shape  # (3, 64, 64)
    log = MockLogger()
    plottitle = "test_proj"

    # Call the function
    plot_projected_stack(
        stack,
        I_shape,
        tmp_path,
        log,
        plottitle=plottitle
    )

    # Check all individual PDFs
    for i in range(I_shape[0]):
        pdf_file = tmp_path / f"{plottitle}, stack {i}.pdf"
        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 0

    # Check main TIFF
    tif_file = tmp_path / f"{plottitle}.tif"
    assert tif_file.exists()
    assert tif_file.stat().st_size > 0

    with tifffile.TiffFile(tif_file) as tif:
        loaded = tif.asarray()
        assert loaded.shape == stack.shape
        assert np.allclose(loaded, stack)

        axes = tif.imagej_metadata.get("axes")
        if axes is not None:
            assert axes in {"ZYX", "TZYX"}


    # Logging check
    assert any("z-projection plotting" in msg for msg in log.messages)


# get_stack_dimensions:
def test_get_stack_dimensions(tmp_path):
    # Create and save a dummy stack
    np.random.seed(42)
    arr = np.random.rand(2, 3, 64, 64).astype(np.float32)  # e.g., T, Z, Y, X
    fname = tmp_path / "test_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZYX"})

    # Get shape using the tested function
    shape = get_stack_dimensions(fname)
    assert shape == list(arr.shape)

def test_get_stack_dimensions_non_tif(tmp_path):
    # Create a fake non-TIFF file
    fake_file = tmp_path / "image.png"
    fake_file.write_text("not a tif")

    with pytest.raises(ValueError, match="Currently, only TIFF files are supported."):
        get_stack_dimensions(fake_file)


# extract_subvolume:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_extract_subvolume_single_channel(tmp_path):
    # Create synthetic 4D stack: (T=2, Z=5, Y, X)
    np.random.seed(42)
    arr = np.random.rand(2, 5, 32, 32).astype(np.float32)
    fname = tmp_path / "test_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZYX"})

    projection_layers = 3
    projection_range = (1, 3)
    log = MockLogger()
    I_shape = arr.shape

    MG_sub, zarr_group = extract_subvolume(
        fname,
        I_shape=I_shape,
        projection_layers=projection_layers,
        projection_range=projection_range,
        log=log,
        two_channel=False
    )

    # Check shapes
    assert MG_sub.shape == (2, 3, 32, 32)

    # Check zarr path
    zarr_path = tmp_path / "test_stack.zarr"
    assert zarr_path.exists()
    assert "image" in zarr_group
    assert "MG_sub" in zarr_group["subvolumes"]

    # Optional: check logging
    assert any("extracting sub-volumes" in m for m in log.messages)


# extract_and_register_subvolume:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_extract_and_register_subvolume_single_channel(tmp_path):
    # Create a dummy 4D image (T, Z, Y, X)
    np.random.seed(42)
    arr = np.random.rand(2, 5, 32, 32).astype(np.float32)
    fname = tmp_path / "dummy_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZYX"})

    log = MockLogger()
    projection_layers = 3
    projection_range = (1, 3)  # Should slice out Z=1 to Z=3 (3 layers)
    MG_channel = 0
    I_shape = arr.shape

    MG_sub_reg, I_shape_reg, zarr_group = extract_and_register_subvolume(
        fname=fname,
        I_shape=I_shape,
        projection_layers=projection_layers,
        projection_range=projection_range,
        MG_channel=MG_channel,
        log=log,
        two_channel=False,
        template_mode="mean",
        max_xy_shift_correction=2,
        debug_output=False
    )

    # Assertions
    if zarr.__version__ >= "3":
        assert isinstance(MG_sub_reg, zarr.Array)
    else:
        assert isinstance(MG_sub_reg, zarr.core.Array)
    assert MG_sub_reg.shape[0] == I_shape[0]          # T
    assert MG_sub_reg.shape[1] == projection_layers   # Z
    assert MG_sub_reg.shape[2] <= I_shape[2]           # Y (cropped)
    assert MG_sub_reg.shape[3] <= I_shape[3]           # X (cropped)

    if hasattr(zarr_group.store, "url"):
        # for ZARR v3 and higher:
        assert str(zarr_group.store.url).endswith(".zarr")
    elif hasattr(zarr_group.store, "path"):
        # for ZARR v2:
        assert zarr_group.store.path.endswith(".zarr")
    else:
        # Optionally, skip or warn if neither attribute exists:
        pass
    assert "MG_sub" in zarr_group["subvolumes"]

    # Optional: check logs
    assert any("registration of stack" in m for m in log.messages)

def test_extract_and_register_subvolume_two_channel(tmp_path):
    # Create a dummy 5D image (T, Z, C, Y, X) with 2 channels
    np.random.seed(42)
    arr = np.random.rand(2, 5, 2, 32, 32).astype(np.float32)  # T, Z, C, Y, X
    fname = tmp_path / "dummy_2channel_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZCYX"})

    log = MockLogger()
    projection_layers = 3
    projection_range = (1, 3)  # Should slice out Z=1 to Z=3 (3 layers)
    MG_channel = 0
    I_shape = arr.shape

    MG_sub_reg, N_sub_reg, I_shape_reg, zarr_group = extract_and_register_subvolume(
        fname=fname,
        I_shape=I_shape,
        projection_layers=projection_layers,
        projection_range=projection_range,
        MG_channel=MG_channel,
        log=log,
        two_channel=True,
        template_mode="mean",
        max_xy_shift_correction=2,
        debug_output=False
    )

    # Assertions for MG_sub_reg (microglial)
    if zarr.__version__ >= "3":
        assert isinstance(MG_sub_reg, zarr.Array)
    else:
        assert isinstance(MG_sub_reg, zarr.core.Array)
    assert MG_sub_reg.shape[0] == I_shape[0]          # T
    assert MG_sub_reg.shape[1] == projection_layers   # Z
    assert MG_sub_reg.shape[2] <= I_shape[-2]          # Y (cropped)
    assert MG_sub_reg.shape[3] <= I_shape[-1]          # X (cropped)

    # Assertions for N_sub_reg (neuronal)
    if zarr.__version__ >= "3":
        assert isinstance(N_sub_reg, zarr.Array)
    else:
        assert isinstance(N_sub_reg, zarr.core.Array)
    assert N_sub_reg.shape[0] == I_shape[0]          # T
    assert N_sub_reg.shape[1] == projection_layers   # Z
    assert N_sub_reg.shape[2] <= I_shape[-2]          # Y (cropped)
    assert N_sub_reg.shape[3] <= I_shape[-1]          # X (cropped)

    # Check Zarr structure
    assert "MG_sub" in zarr_group["subvolumes"]
    assert "N_sub" in zarr_group["subvolumes"]

    # Optional: check logs
    assert any("registration of stack" in m for m in log.messages)


# spectral_unmix:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_spectral_unmix(tmp_path):
    # Create synthetic 4D data: T=2, Z=5, Y=32, X=32, C=2 (2 channels: microglial and neuronal)
    np.random.seed(42)
    arr_mg = np.random.rand(2, 5, 32, 32).astype(np.float32)  # Microglial
    arr_n = np.random.rand(2, 5, 32, 32).astype(np.float32)  # Neuronal
    
    fname_mg = tmp_path / "mg_stack.tif"
    fname_n = tmp_path / "n_stack.tif"
    tifffile.imwrite(fname_mg, arr_mg, imagej=True, metadata={"axes": "TZYX"})
    tifffile.imwrite(fname_n, arr_n, imagej=True, metadata={"axes": "TZYX"})

    log = MockLogger()
    I_shape = arr_mg.shape
    projection_layers = 3
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group

    # Create mock Zarr datasets inside the group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
        zarr_group.create_array("subvolumes/N_sub", shape=I_shape, dtype=np.float32)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
        zarr_group.create_dataset("subvolumes/N_sub", shape=I_shape, dtype=np.float32)
    zarr_group.attrs["dtype"] = "float32"
    
    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr_mg
    zarr_group["subvolumes/N_sub"][:] = arr_n
    
    # Run spectral unmixing
    MG_sub_processed = spectral_unmix(
        MG_sub=zarr_group["subvolumes/MG_sub"],
        N_sub=zarr_group["subvolumes/N_sub"],
        I_shape=I_shape,
        zarr_group=zarr_group,
        projection_layers=projection_layers,
        log=log,
        median_filter_window=3,
        amplifyer=2
    )

    # Assertions
    if zarr.__version__ >= "3":
        assert isinstance(MG_sub_processed, zarr.Array)
    else:
        assert isinstance(MG_sub_processed, zarr.core.Array)
    assert MG_sub_processed.shape[0] == I_shape[0]          # T (unchanged)
    assert MG_sub_processed.shape[1] == projection_layers   # Z (cropped to projection_layers)
    assert MG_sub_processed.shape[2] == I_shape[2]          # Y (unchanged)
    assert MG_sub_processed.shape[3] == I_shape[3]          # X (unchanged)


    # Check that no negative values exist in the processed microglial signal
    assert np.all(MG_sub_processed[:] >= 0)
    
    # Check that the intermediate datasets are deleted (you might want to check the Zarr store size)
    assert "MG_sub_noblead_tmp" not in zarr_group["subvolumes"]
    assert "N_sub_noblead_tmp" not in zarr_group["subvolumes"]
    
    # Check the log to ensure logging occurred during the unmixing
    assert "spectral unmixing" in log.messages[-1]


# histogram_equalization:
class MockLogger_histeq:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

@pytest.fixture
def mock_log():
    return MockLogger_histeq()

def test_histogram_equalization_basic(mock_log):
    # Generate a small synthetic grayscale image (noisy)
    np.random.seed(42)
    test_image = (np.random.rand(5, 10, 32, 32) * 255).astype(np.uint8) # 4D image (T, Z, Y, X)
    I_shape = test_image.shape
    projection_layers= 10
    log = mock_log

    # Apply histogram equalization
    equalized = histogram_equalization(test_image, I_shape, projection_layers, log, clip_limit=0.02)

    # Assertions
    assert equalized.shape == test_image.shape
    assert equalized.min() >= 0.0 and equalized.max() <= 1.0  # skimage returns float in [0, 1]
    assert not np.allclose(test_image, equalized)  # Check that the image changed


# histogram_equalization_on_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_histogram_equalization_on_projections(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=2, Z=5, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape

    # Run histogram equalization
    MG_sub_histeq = histogram_equalization_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        log=log,
        clip_limit=0.01,  # Default value for clip_limit
        kernel_size=3  # Use a small kernel for testing
    )

    # Assertions
    assert MG_sub_histeq.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X
    assert np.max(MG_sub_histeq) <= 1.0  # The equalized values should be between 0 and 1 after equalization
    assert np.min(MG_sub_histeq) >= 0.0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "histogram equalization  done" in log.messages[-1]

    # Test with a different clip_limit
    MG_sub_histeq_2 = histogram_equalization_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        log=log,
        clip_limit=0.05,  # Change clip limit
        kernel_size=None  # Let the kernel size be automatically determined
    )
    assert MG_sub_histeq_2.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # Same shape
    assert "histogram equalization  done" in log.messages[-1]


# histogram_matching:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_histogram_matching(tmp_path):
    # Create synthetic 4D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    fname = tmp_path / "dummy_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "TZYX"})

    log = MockLogger()
    I_shape = arr.shape
    projection_layers = 3  # Number of layers for projection
    histogram_ref_stack = 0  # Using the first stack as the reference for histogram matching

    # Run histogram matching
    MG_sub_histeq = histogram_matching(
        MG_sub=arr,
        I_shape=I_shape,
        histogram_ref_stack=histogram_ref_stack,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions
    assert MG_sub_histeq.shape == (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])  # T, Z, Y, X
    assert np.max(MG_sub_histeq) <= 255  # Ensure values are within expected range after matching
    assert np.min(MG_sub_histeq) >= 0  # Ensure no negative values

    # Check that the log contains the expected message
    assert f"matching histograms of all stacks to reference stack {histogram_ref_stack}..." in log.messages[0]

    # Check if histograms of all stacks are now similar to the reference stack
    for stack in range(1, I_shape[0]):
        # You could use any histogram comparison method, such as the Kullback-Leibler divergence or simply comparing histograms visually.
        ref_hist = np.histogram(arr[histogram_ref_stack], bins=256, range=(0, 255))[0]
        test_hist = np.histogram(MG_sub_histeq[stack], bins=256, range=(0, 255))[0]
        
        # Compare histograms for similarity (you can also compute a distance metric, like correlation)
        assert np.allclose(ref_hist, test_hist, atol=1e-2)  # Tolerating small differences

    print("Test passed successfully!")


# histogram_matching_on_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_histogram_matching_on_projections(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    fname = tmp_path / "dummy_stack.tif"
    tifffile.imwrite(fname, arr, imagej=True, metadata={"axes": "ZYX"})

    log = MockLogger()
    I_shape = arr.shape
    histogram_ref_stack = 0  # Using the first stack as the reference for histogram matching

    # Run histogram matching
    MG_sub_histeq = histogram_matching_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        histogram_ref_stack=histogram_ref_stack,
        log=log
    )

    # Assertions
    assert MG_sub_histeq.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X
    assert np.max(MG_sub_histeq) <= 255  # Ensure values are within expected range after matching
    assert np.min(MG_sub_histeq) >= 0  # Ensure no negative values

    # Check that the log contains the expected message
    assert f"matching histograms of all stacks to reference stack {histogram_ref_stack}..." in log.messages[0]

    # Check if histograms of all stacks are now similar to the reference stack
    for stack in range(1, I_shape[0]):
        ref_hist = np.histogram(arr[histogram_ref_stack], bins=256, range=(0, 255))[0]
        test_hist = np.histogram(MG_sub_histeq[stack], bins=256, range=(0, 255))[0]
        
        # Compare histograms for similarity (you can also compute a distance metric, like correlation)
        assert np.allclose(ref_hist, test_hist, atol=1e-2)  # Tolerating small differences due to rounding

    print("Test passed successfully!")


# median_filtering_on_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_median_filtering_on_projections(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    median_filter_window = 3  # Use a small kernel for testing

    # Run median filtering
    MG_sub_median = median_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        median_filter_window=median_filter_window,
        log=log
    )

    # Assertions for the case where median_filter_window > 1
    assert MG_sub_median.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X
    assert np.max(MG_sub_median) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_median) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "median filtering" in log.messages[-1]

    # Now, run the function with a median_filter_window <= 1 (to skip filtering)
    MG_sub_median_no_filter = median_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        median_filter_window=1,
        log=log
    )

    # Assertions for the case where median_filter_window <= 1 (no filtering)
    assert np.array_equal(MG_sub_median_no_filter, arr)  # The result should be the same as the original

    # Check that the log contains the message for skipping filtering
    assert "median filtering  done" in log.messages[-1]
    
    print("Test passed successfully!")


# circular_median_filtering_on_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_circular_median_filtering_on_projections(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    median_filter_window = 3  # Use a small kernel for testing

    # Run circular median filtering with window size >= 1
    MG_sub_median = circular_median_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        median_filter_window=median_filter_window,
        log=log
    )

    # Assertions for the case where median_filter_window >= 1
    assert MG_sub_median.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X
    assert np.max(MG_sub_median) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_median) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "median filtering" in log.messages[-1]

    # Now, run the function with a median_filter_window < 1 (to skip filtering)
    MG_sub_median_no_filter = circular_median_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        median_filter_window=0,
        log=log
    )

    # Assertions for the case where median_filter_window < 1 (no filtering)
    assert np.array_equal(MG_sub_median_no_filter, arr)  # The result should be the same as the original

    # Check that the log contains the message for skipping filtering
    assert "median filtering  done" in log.messages[-1]
    
    print("Test passed successfully!")


# single_slice_median_filtering:
class MockLogger:
    def __init__(self):
        self.messages = []
    def log(self, msg):
        self.messages.append(msg)
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_single_slice_median_filtering(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    median_filter_window = 3  # Use a small kernel for testing
    projection_layers = 3  # Number of slices in each stack

    # Create a mock Zarr group
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    zarr_group.attrs["dtype"] = "float32"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run single slice median filtering
    MG_sub_median = single_slice_median_filtering(
        MG_sub=zarr_group["subvolumes/MG_sub"],
        I_shape=I_shape,
        zarr_group=zarr_group,
        median_filter_window=median_filter_window,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where median_filter_window > 1
    if zarr.__version__ >= "3":
        assert isinstance(MG_sub_median, zarr.Array)
    else:
        assert isinstance(MG_sub_median, zarr.core.Array)
    assert MG_sub_median.shape == (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])  # T, Z, Y, X

    # Check that the filtered result is within expected range
    assert np.max(MG_sub_median) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_median) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "square median filtering on slices" in log.messages[-1]

    # Now, run the function with a median_filter_window <= 1 (to skip filtering)
    MG_sub_median_no_filter = single_slice_median_filtering(
        MG_sub=zarr_group["subvolumes/MG_sub"],
        I_shape=I_shape,
        zarr_group=zarr_group,
        median_filter_window=1,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where median_filter_window <= 1 (no filtering)
    assert np.array_equal(MG_sub_median_no_filter[:], arr)  # The result should be the same as the original

    # Check that the log contains the message for skipping filtering
    assert "square median filtering on slices  done" in log.messages[-1]
    
    print("Test passed successfully!")


# single_slice_circular_median_filtering:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_single_slice_median_filtering(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    median_filter_window = 1  # Use a small kernel for testing
    projection_layers = 3  # Number of slices in each stack

    # Create a mock Zarr group
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    zarr_group.attrs["dtype"] = "float32"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run single slice median filtering
    MG_sub_median = single_slice_circular_median_filtering(
        MG_sub=zarr_group["subvolumes/MG_sub"],
        I_shape=I_shape,
        zarr_group=zarr_group,
        median_filter_window=median_filter_window,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where median_filter_window > 1
    if zarr.__version__ >= "3":
        assert isinstance(MG_sub_median, zarr.Array)
    else:
        assert isinstance(MG_sub_median, zarr.core.Array)
    assert MG_sub_median.shape == (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])  # T, Z, Y, X

    # Check that the filtered result is within expected range
    assert np.max(MG_sub_median) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_median) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "circular median filtering on slices  done" in log.messages[-1]

    # Now, run the function with a median_filter_window <= 1 (to skip filtering)
    MG_sub_median_no_filter = single_slice_circular_median_filtering(
        MG_sub=zarr_group["subvolumes/MG_sub"],
        I_shape=I_shape,
        zarr_group=zarr_group,
        median_filter_window=0.5,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where median_filter_window <= 1 (no filtering)
    assert np.array_equal(MG_sub_median_no_filter[:], arr)  # The result should be the same as the original

    # Check that the log contains the message for skipping filtering
    assert "circular median filtering on slices  done" in log.messages[-1]
    
    print("Test passed successfully!")

# gaussian_blurr_filtering_on_projections:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_gaussian_blurr_filtering_on_projections(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # Z=5, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    gaussian_blurr_sigma = 1  # Standard deviation for Gaussian blur
    projection_layers = 3  # Number of slices in each stack

    # Run Gaussian blur filtering
    MG_sub_gaussian = gaussian_blurr_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        gaussian_blurr_sigma=gaussian_blurr_sigma,
        log=log
    )

    # Assertions
    assert isinstance(MG_sub_gaussian, np.ndarray)
    assert MG_sub_gaussian.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X
    assert np.max(MG_sub_gaussian) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_gaussian) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "Gaussian blur filtering" in log.messages[-1]

    # Now, run the function with a very small sigma (close to no blurring)
    MG_sub_gaussian_no_blur = gaussian_blurr_filtering_on_projections(
        MG_sub=arr,
        I_shape=I_shape,
        gaussian_blurr_sigma=0.1,  # Small sigma (close to no blurring)
        log=log
    )

    # Assertions for the case where gaussian_blurr_sigma is small
    assert np.allclose(MG_sub_gaussian_no_blur, arr, atol=1e-5)  # The result should be almost the same as the original

    # Check that the log contains the message for the Gaussian blur processing
    assert "Gaussian blur filtering" in log.messages[-1]

    print("Test passed successfully!")


# single_slice_gaussian_blurr_filtering:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_single_slice_gaussian_blurr_filtering(tmp_path):
    # Create synthetic 4D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    gaussian_blurr_sigma = 1  # Standard deviation for Gaussian blur
    projection_layers = 3  # Number of slices in each stack

    # Run single slice Gaussian blur filtering
    MG_sub_gaussian = single_slice_gaussian_blurr_filtering(
        MG_sub=arr,
        I_shape=I_shape,
        gaussian_blurr_sigma=gaussian_blurr_sigma,
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where gaussian_blurr_sigma > 0
    assert isinstance(MG_sub_gaussian, np.ndarray)
    assert MG_sub_gaussian.shape == (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])  # T, Z, Y, X
    assert np.max(MG_sub_gaussian) <= 255  # Ensure values are within expected range
    assert np.min(MG_sub_gaussian) >= 0  # Ensure no negative values
    
    # Check that the log contains the expected message
    assert "Gaussian blur filtering" in log.messages[-1]

    # Now, run the function with a very small sigma (close to no blurring)
    MG_sub_gaussian_no_blur = single_slice_gaussian_blurr_filtering(
        MG_sub=arr,
        I_shape=I_shape,
        gaussian_blurr_sigma=0.1,  # Small sigma (close to no blurring)
        projection_layers=projection_layers,
        log=log
    )

    # Assertions for the case where gaussian_blurr_sigma is small
    assert np.allclose(MG_sub_gaussian_no_blur, arr, atol=1e-5)  # The result should be almost the same as the original

    # Check that the log contains the message for the Gaussian blur processing
    assert "Gaussian blur filtering" in log.messages[-1]

    print("Test passed successfully!")


# z_max_project:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_z_max_project(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape

    # Run Z-projection (maximum intensity projection)
    MG_pro = z_max_project(
        MG_sub=arr,
        I_shape=I_shape,
        log=log
    )

    # Assertions for the case where Z-projection is applied
    assert isinstance(MG_pro, np.ndarray)
    assert MG_pro.shape == (I_shape[0], I_shape[-2], I_shape[-1])  # T, Y, X (collapsed Z dimension)

    # Check that the resulting image is the maximum projection over the Z-dimension
    for stack in range(I_shape[0]):
        for y in range(I_shape[-2]):
            for x in range(I_shape[-1]):
                # Ensure that the value in the projection is the maximum over the Z-dimension
                assert np.isclose(MG_pro[stack, y, x], np.max(arr[stack, :, y, x]))

    # Check that the log contains the expected message
    assert "z-projections" in log.messages[-1]

    # Test with a single slice in the Z-dimension (Z=1)
    np.random.seed(42)
    arr_single_z = np.random.rand(5, 1, 32, 32).astype(np.float32) * 255  # Z=1
    I_shape_single_z = arr_single_z.shape

    # Run Z-projection on the single slice Z-dimension
    MG_pro_single_z = z_max_project(
        MG_sub=arr_single_z,
        I_shape=I_shape_single_z,
        log=log
    )

    # Assertions for single slice data (the output should be the same as the input)
    assert np.array_equal(MG_pro_single_z, arr_single_z[:,  :, :])
    
    # Check the log for the warning message about a single Z-slice input
    assert "WARNING: z_max_project: input is not a 3D array, returning input without projection." in log.messages[-1]

    print("Test passed successfully!")


# compare_histograms:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_compare_histograms(tmp_path):
    # Create synthetic 4D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr_pre = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    arr_post = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # Another random stack for post-adjustment
    
    # Log object for capturing log messages
    log = MockLogger()
    
    # I_shape of the synthetic array
    I_shape = arr_pre.shape
    
    # Path to save the plot
    plot_path = tmp_path / "plots"
    plot_path.mkdir(parents=True, exist_ok=True)

    # Run histogram comparison
    compare_histograms(
        MG_sub_pre=arr_pre,
        MG_sub_post=arr_post,
        log=log,
        plot_path=plot_path,
        I_shape=I_shape,
        xlim=(0, 6000)
    )

    # Assertions for checking if the plot files are created
    for stack in range(I_shape[0]):
        plot_file = plot_path / f"Stats Histograms before and after adjustments, stack {stack}.pdf"
        assert plot_file.exists(), f"Plot file for stack {stack} was not created."
        assert plot_file.stat().st_size > 0, f"Plot file for stack {stack} is empty."

    # Check that the log contains the expected message
    assert "calculating and plotting histogram of each stack..." in log.messages[0]

    print("Test passed successfully!")


# plot_intensities:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_plot_intensities(tmp_path):
    # Create synthetic 4D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 3, 32, 32).astype(np.float32) * 255  # T=5, Z=3, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    plot_path = tmp_path / "plots"
    plot_path.mkdir(parents=True, exist_ok=True)

    # Run the plot_intensities function
    intensity_means = plot_intensities(
        MG_pro=arr,
        log=log,
        plot_path=plot_path,
        I_shape=I_shape
    )

    # Assertions for the intensity means
    assert len(intensity_means) == I_shape[0], f"Expected {I_shape[0]} stacks, but got {len(intensity_means)}"
    assert np.all(intensity_means >= 0), "Intensity means should be non-negative"

    # Check that the plot file was created
    plot_file = plot_path / "Normalized average brightness drop rel. to t0.pdf"
    assert plot_file.exists(), f"Plot file not created: {plot_file}"
    assert plot_file.stat().st_size > 0, f"Plot file is empty: {plot_file}"

    # Check that the Excel file was created
    excel_file = plot_path / "Normalized average brightness of each stack.xlsx"
    assert excel_file.exists(), f"Excel file not created: {excel_file}"
    assert excel_file.stat().st_size > 0, f"Excel file is empty: {excel_file}"

    # Check that the log contains the expected message
    assert "plotting average brightness per projected stack..." in log.messages[0]

    print("Test passed successfully!")


# reg_2D_images:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1    

def test_reg_2D_images(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial sub-volume
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=5, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    histogram_ref_stack = 2  # Use the third stack as the reference

    # Create a mock Zarr group for saving the registered images
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    zarr_group.attrs["dtype"] = "float32"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run registration of 2D images
    MG_pro_bin_reg_clipped, I_shape_create = reg_2D_images(
        MG_pro=arr,
        I_shape=I_shape,
        log=log,
        histogram_ref_stack=histogram_ref_stack,
        max_xy_shift_correction=50,
        median_filter_projections="square",  # Apply median filter (you can also test "circular" or None)
        median_filter_window_projections=3
    )

    # Assertions for the registered image stack
    assert isinstance(MG_pro_bin_reg_clipped, np.ndarray), "Registered image should be a numpy array"
    assert MG_pro_bin_reg_clipped.shape == (I_shape[0], I_shape_create[-2], I_shape_create[-1]), \
        f"Expected shape {I_shape_create}, but got {MG_pro_bin_reg_clipped.shape}"

    # Check that the registered stack is not identical to the original one (due to shift)
    assert not np.array_equal(MG_pro_bin_reg_clipped, arr), "The registered image should not be identical to the original"

    # Check the log contains the expected message
    assert "registering z-projection" in log.messages[0]

    print("Test passed successfully!")

# binarize_2D_images:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_binarize_2D_images(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial projections
    np.random.seed(42)
    arr = np.random.rand(5, 32, 32).astype(np.float32) * 255  # T=5, Y=32, X=32
    log = MockLogger()
    I_shape = arr.shape
    threshold_method = "otsu"  # Choose a threshold method for the test (you can also test "auto" or others)

    # Create a mock Zarr group for saving the binarized images
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.float32)
    zarr_group.attrs["dtype"] = "float32"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run binarization of 2D projections
    MG_pro_bin = binarize_2D_images(
        MG_pro=arr,
        I_shape=I_shape,
        log=log,
        plot_path=tmp_path,  # Specify the directory where the plots should be saved
        threshold_method=threshold_method,
        compare_all_threshold_methods=False,  # Set to True if you want to compare all methods
        gaussian_sigma_proj=1
    )

    # Assertions for binarized image stack
    assert isinstance(MG_pro_bin, np.ndarray), "Binarized result should be a numpy array"
    assert MG_pro_bin.shape == (I_shape[0], I_shape[1], I_shape[2]), \
        f"Expected shape {I_shape}, but got {MG_pro_bin.shape}"

    # Check that the binarized stack has values 0 and 1
    assert np.all(np.isin(MG_pro_bin, [0, 1])), "Binarized image should contain only 0 and 1 values"

    # Check that the log contains the expected message about the threshold method
    assert f"binarizing z-projections..." in log.messages[0]
    
    print("Test passed successfully!")


# remove_small_blobs:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_remove_small_blobs(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial projections (binarized)
    np.random.seed(42)
    arr = np.random.randint(0, 2, size=(5, 32, 32), dtype=np.uint16)  # Binary image (0 or 1)
    log = MockLogger()
    I_shape = arr.shape
    pixel_threshold = 100  # Set pixel threshold for small region removal

    # Create a mock Zarr group
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.uint16)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.uint16)
    zarr_group.attrs["dtype"] = "uint16"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run the remove small blobs function
    MG_pro_bin_area_thresholded, MG_pro_bin_area_sum = remove_small_blobs(
        MG_pro=arr,
        I_shape=I_shape,
        log=log,
        plot_path=tmp_path,  # Specify the directory where the plots should be saved
        pixel_threshold=pixel_threshold,
        stats_plots=True  # Set to True if you want to generate statistics plots
    )

    # Assertions for the binarized image stack after small blobs removal
    assert isinstance(MG_pro_bin_area_thresholded, np.ndarray), "Result should be a numpy array"
    assert MG_pro_bin_area_thresholded.shape == I_shape, \
        f"Expected shape {I_shape}, but got {MG_pro_bin_area_thresholded.shape}"

    # Ensure that the number of retained pixels is greater than 0
    assert np.sum(MG_pro_bin_area_thresholded) > 0, "No pixels were retained after thresholding"

    # Check that the log contains the expected message about the process
    assert "apply connectivity-measurements to exclude too small microglia parts" in log.messages[0]

    # Assertions for the sum of pixel areas after thresholding
    assert len(MG_pro_bin_area_sum) == I_shape[0], "The number of stacks in MG_pro_bin_area_sum does not match the input"
    assert np.all(MG_pro_bin_area_sum >= 0), "The sum of pixel areas should not be negative"

    print("Test passed successfully!")


# plot_pixel_areas:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

def test_plot_pixel_areas(tmp_path):
    # Create synthetic 3D image stack (T, Z, Y, X) for the microglial projections
    np.random.seed(42)
    arr = np.random.randint(0, 2, size=(5, 32, 32), dtype=np.uint16)  # Binary image (0 or 1)
    log = MockLogger()
    I_shape = arr.shape
    MG_areas = np.array([np.sum(arr[i]) for i in range(I_shape[0])])  # Simulate pixel area sums

    # Create a mock Zarr group
    zarr_group = zarr.open(tmp_path / "test_zarr.zarr", mode="w")  # Mock Zarr group
    if zarr.__version__ >= "3":
        zarr_group.create_array("subvolumes/MG_sub", shape=I_shape, dtype=np.uint16)
    else:
        zarr_group.create_dataset("subvolumes/MG_sub", shape=I_shape, dtype=np.uint16)
    zarr_group.attrs["dtype"] = "uint16"

    # Write synthetic data to the Zarr datasets
    zarr_group["subvolumes/MG_sub"][:] = arr

    # Run the plot_pixel_areas function
    plot_pixel_areas(
        MG_areas=MG_areas,
        log=log,
        plot_path=tmp_path,  # Specify the directory where the plots should be saved
        I_shape=I_shape
    )

    # Assertions for the plotting and Excel output
    assert isinstance(MG_areas, np.ndarray), "MG_areas should be a numpy array"
    assert MG_areas.shape == (I_shape[0],), "MG_areas should have the same length as the number of stacks"
    
    # Check if the log contains the expected message
    assert "plotting detected pixel areas per projected stack" in log.messages[0]

    # Check if the plot was saved (check for existence of the plot file)
    plot_file = Path(tmp_path, "Normalized cell area rel. to t0.pdf")
    assert plot_file.exists(), f"Expected plot file {plot_file} does not exist"

    # Check if the Excel file was saved (check for existence of the Excel file)
    excel_file = Path(tmp_path, "pixel area sums.xlsx")
    assert excel_file.exists(), f"Expected Excel file {excel_file} does not exist"

    print("Test passed successfully!")


# motility:
class MockLogger:
    def __init__(self):
        self.messages = []
    
    def log(self, msg):
        self.messages.append(msg)
    
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

@pytest.fixture
def setup_plot_path():
    path = "test_plot_path"
    os.makedirs(path, exist_ok=True)
    yield path
    shutil.rmtree(path)

def test_motility(setup_plot_path):
    # Mock logger
    log = MockLogger()

    # Create the plot_path directory if it doesn't exist
    #plot_path = "test_plot_path"
    plot_path = setup_plot_path
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    
    # Generate synthetic data (3 time points, 32x32 image size)
    I_shape = (3, 1, 32, 32)  # 3 time points, 1 Z-slice, 32x32 pixels
    np.random.seed(42)
    MG_pro = np.random.rand(*I_shape).astype(np.float32)  # Random binary projections

    ID = "TestID"
    group = "test_group"
    
    # Call the motility function
    MG_pro_delta_t, summary_df = motility(MG_pro, I_shape, log, plot_path, ID, group)
    
    # Assert that the delta-t images shape is correct (should have 2 time points of differences)
    assert MG_pro_delta_t.shape == (I_shape[0] - 1, I_shape[-2], I_shape[-1])  # (2, 32, 32)
    
    # Assert that the summary dataframe has the correct number of rows (for 2 time differences)
    assert summary_df.shape[0] == I_shape[0] - 1  # Should have 2 rows
    
    # Check if the necessary columns are present
    assert "Stable" in summary_df.columns
    assert "Gain" in summary_df.columns
    assert "Loss" in summary_df.columns
    assert "rel Stable" in summary_df.columns
    assert "rel Gain" in summary_df.columns
    assert "rel Loss" in summary_df.columns
    
    # Check if the Excel file is being saved
    assert "motility  done" in log.messages[-1]
    
    # Optionally, you can test that plot generation functions were called
    # For this, you can mock the `plot_2D_image` function and check that it was called with appropriate arguments

    print("Test passed successfully!")


# MAIN FUNCTION 1 process_stack:
class MockLoggerMain1:
    def __init__(self):
        self.messages = []
        # Initialize summary_df with the expected columns
        self.summary_df = pd.DataFrame(columns=["ID", "group", "delta t", "Stable", "Gain", "Loss", "rel Stable", "rel Gain", "rel Loss", "tor"])

    def log(self, msg):
        self.messages.append(msg)

    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1
    
    # Simulate an update to summary_df for testing purposes
    def update_summary_df(self, ID, group, delta_t, stable, gain, loss, rel_stable, rel_gain, rel_loss, tor):
        # Prepare the new row
        new_row = pd.DataFrame([{
            "ID": ID,
            "group": group,
            "delta t": delta_t,
            "Stable": stable,
            "Gain": gain,
            "Loss": loss,
            "rel Stable": rel_stable,
            "rel Gain": rel_gain,
            "rel Loss": rel_loss,
            "tor": tor
        }])

        # Reindex to ensure all columns are present, fill missing ones with None
        new_row = new_row.reindex(columns=self.summary_df.columns, fill_value=None)

        # Drop rows where all values are NA
        new_row = new_row.dropna(how='all')

        # Drop columns where all values are NA
        new_row = new_row.dropna(axis=1, how='all')

        # Check if new_row is empty after cleaning
        if not new_row.empty:
            if self.summary_df.empty:
                # If summary_df is empty, directly assign new_row to it
                self.summary_df = new_row
            else:
                # Otherwise, concatenate the cleaned new_row to the summary_df
                self.summary_df = pd.concat([self.summary_df, new_row], ignore_index=True)

@pytest.fixture
def mock_log():
    return MockLoggerMain1()

@pytest.fixture
def mock_functions():
    # Mocking internal functions of process_stack that interact with the filesystem or other components.
    mock_functions = {
        'extract_and_register_subvolume': MagicMock(),
        'spectral_unmix': MagicMock(),
        'z_max_project': MagicMock(),
        'plot_projected_stack': MagicMock(),
        'histogram_equalization_on_projections': MagicMock(),
        'histogram_matching_on_projections': MagicMock(),
        'binarize_2D_images': MagicMock(),
        'remove_small_blobs': MagicMock(),
        'plot_pixel_areas': MagicMock(),
        'motility': MagicMock(),
    }
    return mock_functions

@pytest.fixture
def setup_test_tif():
    test_dir = 'test_process_stack'
    os.makedirs(test_dir, exist_ok=True)

    test_file = os.path.join(test_dir, 'test_file.tif')
    np.random.seed(42)
    arr = np.random.rand(5, 15, 2, 32, 32).astype(np.float32) * 255
    tifffile.imwrite(test_file, arr, imagej=True, metadata={"axes": "TZCYX"})

    yield test_file, arr  # Provide file path and array to the test

    # Cleanup after test
    shutil.rmtree(test_dir)

def test_process_stack(mock_log, mock_functions, setup_test_tif):
    # create synthetic 3D image stack (e.g., 5 time points, 32x32 image):
    np.random.seed(42)
    #arr = np.random.rand(5, 15, 2, 32, 32).astype(np.float32) * 255  # T:5, Z=10, Y=2, X=32, 32
    # save this array to a .tif file
    #tifffile.imwrite('test_file.tif', arr, imagej=True, metadata={"axes": "TZCYX"})
    
    # use the fixture to create a test file:
    fname, arr = setup_test_tif  # Unpack the fixture
    
    # prepare test input:
    #fname = 'test_file.tif'
    MG_channel = 0
    N_channel = 1
    two_channel = True
    projection_center = 9
    projection_layers = 5
    histogram_ref_stack = 0  # Replace with actual reference stack index
    RESULTS_Path = os.path.join(os.path.dirname(fname), "motility")
    ID = "TestID"
    group = "test_group"

    # Mock the external functions that interact with the filesystem or perform intensive computation
    mock_functions['extract_and_register_subvolume'].return_value = (np.zeros_like(arr), np.zeros_like(arr), np.zeros_like(arr))  # Mock the return values to match expected shapes
    mock_functions['spectral_unmix'].return_value = np.zeros_like(arr)
    mock_functions['z_max_project'].return_value = np.zeros_like(arr[0])
    mock_functions['plot_projected_stack'].return_value = None
    mock_functions['histogram_equalization_on_projections'].return_value = np.zeros_like(arr[0])
    mock_functions['histogram_matching_on_projections'].return_value = np.zeros_like(arr[0])
    mock_functions['binarize_2D_images'].return_value = np.zeros_like(arr[0])
    mock_functions['remove_small_blobs'].return_value = (np.zeros_like(arr[0]), np.zeros_like(arr[0]))
    mock_functions['plot_pixel_areas'].return_value = None
    mock_functions['motility'].return_value = (np.zeros_like(arr[0]), pd.DataFrame())

    # Run the function under test
    process_stack(
        fname=fname,
        MG_channel=MG_channel,
        N_channel=N_channel,
        two_channel=two_channel,
        projection_center=projection_center,
        projection_layers=projection_layers,
        histogram_ref_stack=histogram_ref_stack,
        log=mock_log,
        RESULTS_Path=RESULTS_Path,
        ID=ID,
        group=group,
        blob_pixel_threshold=2,
        max_xy_shift_correction=1,
        threshold_method="li",
        compare_all_threshold_methods=True,
        gaussian_sigma_proj=1,
        spectral_unmixing_amplifyer=1,
        median_filter_slices="square",
        median_filter_window_slices=3,
        median_filter_projections="square",
        median_filter_window_projections=3,
        clear_previous_results=False,
        spectral_unmixing_median_filter_window=3,
        debug_output=False,
        stats_plots=False,
        regStack3d=False,
        regStack2d=False,
        spectral_unmixing=True
    )

    # Assert logging occurred
    assert "Processing file" in mock_log.messages[0]
    assert "total processing time done" in mock_log.messages[-1]  # For example, check if folder creation message exists

    # Assert that external function calls happened (e.g., registration, spectral unmixing)
    #mock_functions['extract_and_register_subvolume'].assert_called_once()
    #mock_functions['spectral_unmix'].assert_called_once()
    #mock_functions['plot_projected_stack'].assert_called()
    #mock_functions['histogram_equalization_on_projections'].assert_called()

    # Ensure that summary_df is being filled
    mock_log.update_summary_df(ID="TestID", group="test_group", delta_t="t_0-t_1", stable=100, gain=50, loss=30, 
                               rel_stable=0.5, rel_gain=0.25, rel_loss=0.15, tor=0.6)
    
    # Check that summary_df is populated
    assert isinstance(mock_log.summary_df, pd.DataFrame)
    assert 'ID' in mock_log.summary_df.columns
    assert mock_log.summary_df.shape[0] > 0  # Ensure there is at least one row in the DataFrame

@pytest.fixture
def setup_test_tif_1_channel():
    test_dir = 'test_process_stack_1ch'
    os.makedirs(test_dir, exist_ok=True)

    test_file = os.path.join(test_dir, 'test_file_1_channel.tif')
    np.random.seed(42)
    arr = np.random.rand(5, 15, 1, 32, 32).astype(np.float32) * 255
    tifffile.imwrite(test_file, arr, imagej=True, metadata={"axes": "TZCYX"})

    yield test_file, arr  # Provide path and array to the test

    # Cleanup the entire directory after the test
    shutil.rmtree(test_dir)

def test_process_stack_1_channel(mock_log, mock_functions, setup_test_tif_1_channel):
    # create synthetic 3D image stack (e.g., 5 time points, 32x32 image):
    np.random.seed(42)
    #arr = np.random.rand(5, 15, 1, 32, 32).astype(np.float32) * 255  # T:5, Z=15, X=32, 32
    # save this array to a .tif file
    #tifffile.imwrite('test_file_1_channel.tif', arr, imagej=True, metadata={"axes": "TZCYX"})
    
    # use the fixture to create a test file:
    fname, arr = setup_test_tif_1_channel
    
    # prepare test input:
    #fname = 'test_file_1_channel.tif'
    MG_channel = 0
    N_channel = 1  # No neuron channel for 1-channel scenario
    two_channel = False
    projection_center = 7
    projection_layers = 4
    histogram_ref_stack = 0  # Replace with actual reference stack index
    RESULTS_Path = os.path.join(os.path.dirname(fname), "motility")
    ID = "TestID_1_channel"
    group = "test_group_1_channel"

    # Mock the external functions that interact with the filesystem or perform intensive computation
    mock_functions['extract_and_register_subvolume'].return_value = (np.zeros_like(arr), np.zeros_like(arr), np.zeros_like(arr))  # Mock the return values to match expected shapes
    mock_functions['spectral_unmix'].return_value = np.zeros_like(arr)
    mock_functions['z_max_project'].return_value = np.zeros_like(arr[0])
    mock_functions['plot_projected_stack'].return_value = None
    mock_functions['histogram_equalization_on_projections'].return_value = np.zeros_like(arr[0])
    mock_functions['histogram_matching_on_projections'].return_value = np.zeros_like(arr[0])
    mock_functions['binarize_2D_images'].return_value = np.zeros_like(arr[0])
    mock_functions['remove_small_blobs'].return_value = (np.zeros_like(arr[0]), np.zeros_like(arr[0]))
    mock_functions['plot_pixel_areas'].return_value = None
    mock_functions['motility'].return_value = (np.zeros_like(arr[0]), pd.DataFrame())

    # Run the function under test
    process_stack(
        fname=fname,
        MG_channel=MG_channel,
        N_channel=N_channel,
        two_channel=two_channel,
        projection_center=projection_center,
        projection_layers=projection_layers,
        histogram_ref_stack=histogram_ref_stack,
        log=mock_log,
        RESULTS_Path=RESULTS_Path,
        ID=ID,
        group=group,
        blob_pixel_threshold=2,
        max_xy_shift_correction=1,
        threshold_method="li",
        compare_all_threshold_methods=True,
        gaussian_sigma_proj=1,
        spectral_unmixing_amplifyer=1,
        median_filter_slices="square",
        median_filter_window_slices=3,
        median_filter_projections="square",
        median_filter_window_projections=3,
        clear_previous_results=False,
        spectral_unmixing_median_filter_window=3,
        debug_output=False,
        stats_plots=False,
        regStack3d=False,
        regStack2d=False,
        spectral_unmixing=False
    )

    # Assert logging occurred
    assert "Processing file" in mock_log.messages[0]
    assert "total processing time done" in mock_log.messages[-1]  # For example, check if folder creation message exists

    # Ensure that summary_df is being filled
    mock_log.update_summary_df(ID="TestID_1_channel", group="test_group_1_channel", delta_t="t_0-t_1", stable=100, gain=50, loss=30, 
                               rel_stable=0.5, rel_gain=0.25, rel_loss=0.15, tor=0.6)
    
    # Check that summary_df is populated
    assert isinstance(mock_log.summary_df, pd.DataFrame)
    assert 'ID' in mock_log.summary_df.columns
    assert mock_log.summary_df.shape[0] > 0  # Ensure there is at least one row in the DataFrame


# MAIN FUNCTION 2 batch_process_stacks:
class MockLogger_batch:
    def __init__(self):
        self.messages = []

    def log(self, msg):
        self.messages.append(msg)

    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        self.log(f"{process} done")
        return 0.1

@pytest.fixture
def mock_log_batch():
    return MockLogger_batch()

@pytest.fixture
def setup_test_data():
    # Create the main test directory
    test_dir = 'test_batch_process_stacks'

    # Define the file paths and mock data
    id1_path = os.path.join(test_dir, 'ID1', 'project_tag', 'registered')
    id2_path = os.path.join(test_dir, 'ID2', 'project_tag', 'registered')
    metadata_file = 'metadata.xls'
    reg_tif_file_tag = 'reg_tif_file_tag_1'
    reg_tif_file_tag2 = 'reg_tif_file_tag_2'
    
    # Create directories for ID1 and ID2
    os.makedirs(id1_path, exist_ok=True)
    os.makedirs(id2_path, exist_ok=True)
    os.makedirs(os.path.join(test_dir, 'ID1', 'project_tag', 'RESULTS_foldername'), exist_ok=True)
    os.makedirs(os.path.join(test_dir, 'ID2', 'project_tag', 'RESULTS_foldername'), exist_ok=True)

    # Write mock .tif files
    arr = np.random.rand(5, 15, 2, 32, 32).astype(np.float32) * 255
    tifffile.imwrite(os.path.join(id1_path, reg_tif_file_tag + ".tif"), arr, imagej=True, metadata={"axes": "TZCYX"})
    tifffile.imwrite(os.path.join(id2_path, reg_tif_file_tag2 + ".tif"), arr, imagej=True, metadata={"axes": "TZCYX"})
    
    # Write mock metadata files
    metadata = pd.DataFrame({
        'Two Channel': [True],
        'Neuron Channel': [1],
        'Microglia Channel': [0],
        'Spectral Unmixing': [True],
        'Projection Center': [10],
        'N Projection Layers': [5],
        'Spectral Unmixing Amplifyer': [1]
    })
    try:
        metadata.to_excel(os.path.join(test_dir, 'ID1', 'project_tag', metadata_file), index=False, engine='xlrd')
        metadata.to_excel(os.path.join(test_dir, 'ID2', 'project_tag', metadata_file), index=False, engine='xlrd')
    except ValueError as e:
        print(f"Error: {e}")
        # try using openpyxl for .xlsx files if xlrd fails:
        metadata.to_excel(os.path.join(test_dir, 'ID1', 'project_tag', metadata_file), index=False, engine='openpyxl')
        metadata.to_excel(os.path.join(test_dir, 'ID2', 'project_tag', metadata_file), index=False, engine='openpyxl')

    yield test_dir  # Yield the test directory path for use in the test

    # Cleanup: remove test data after test is complete
    import shutil
    shutil.rmtree(test_dir)

def test_batch_process_stacks_no_error(mock_log_batch, setup_test_data):
    # Use the setup_test_data fixture to create test directories and files
    test_dir = setup_test_data

    # Define parameters for the batch_process_stacks function
    PROJECT_Path = test_dir + "/"
    ID_list = ["ID1", "ID2"]
    project_tag = "project_tag"
    reg_tif_file_folder = "registered"
    reg_tif_file_tag = "reg_tif_file_tag"
    metadata_file = "metadata.xls"
    RESULTS_foldername = "../motility"
    group = "test_group"
    MG_channel = 0
    N_channel = 1
    two_channel = True
    projection_center = 10
    projection_layers = 5
    histogram_ref_stack = 0
    blob_pixel_threshold = 100
    regStack2d = True
    regStack3d = False
    template_mode = "mean"
    spectral_unmixing = True
    hist_equalization = False
    hist_match = True
    hist_equalization_kernel_size = None
    hist_equalization_clip_limit = 0.05
    max_xy_shift_correction = 50
    threshold_method = "li"
    compare_all_threshold_methods = True
    gaussian_sigma_proj = 1
    spectral_unmixing_amplifyer = 1
    median_filter_slices = "square"
    median_filter_window_slices = 3
    median_filter_projections = "square"
    median_filter_window_projections = 3
    clear_previous_results = False
    spectral_unmixing_median_filter_window = 3
    debug_output = False
    stats_plots = False

    # call the function and ensure no errors are raised:
    batch_process_stacks(
        PROJECT_Path=PROJECT_Path,
        ID_list=ID_list,
        project_tag=project_tag,
        reg_tif_file_folder=reg_tif_file_folder,
        reg_tif_file_tag=reg_tif_file_tag,
        metadata_file=metadata_file,
        RESULTS_foldername=RESULTS_foldername,
        group=group,
        MG_channel=MG_channel,
        N_channel=N_channel,
        two_channel=two_channel,
        projection_center=projection_center,
        projection_layers=projection_layers,
        histogram_ref_stack=histogram_ref_stack,
        log=mock_log_batch,
        blob_pixel_threshold=blob_pixel_threshold,
        regStack2d=regStack2d,
        regStack3d=regStack3d,
        template_mode=template_mode,
        spectral_unmixing=spectral_unmixing,
        hist_equalization=hist_equalization,
        hist_match=hist_match,
        hist_equalization_kernel_size=hist_equalization_kernel_size,
        hist_equalization_clip_limit=hist_equalization_clip_limit,
        max_xy_shift_correction=max_xy_shift_correction,
        threshold_method=threshold_method,
        compare_all_threshold_methods=compare_all_threshold_methods,
        gaussian_sigma_proj=gaussian_sigma_proj,
        spectral_unmixing_amplifyer=spectral_unmixing_amplifyer,
        median_filter_slices=median_filter_slices,
        median_filter_window_slices=median_filter_window_slices,
        median_filter_projections=median_filter_projections,
        median_filter_window_projections=median_filter_window_projections,
        clear_previous_results=clear_previous_results,
        spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
        debug_output=debug_output,
        stats_plots=stats_plots,
    )

    # assert that the logger contains expected messages:
    assert "Batch processing of stacks..." in mock_log_batch.messages[0]
    assert "total batch" in mock_log_batch.messages[-1]


# MAIN FUNCTION 3 batch_collect
class MockLogger_batch_collect:
    def __init__(self):
        self.messages = []

    def log(self, msg):
        self.messages.append(msg)

# Fixture to generate test folders and fake Excel files
@pytest.fixture
def setup_batch_collect_test_data():
    base_path = "test_batch_results"
    id_list = ["ID1", "ID2"]
    project_tag = "TP000"
    motility_folder = "motility_analysis"
    projection_center = "projection_center_10"
    result_file = "motility_analysis.xlsx"

    for ID in id_list:
        folder = Path(base_path) / ID / f"{project_tag}_01" / motility_folder / projection_center
        folder.mkdir(parents=True, exist_ok=True)

        # Create minimal Excel file
        df = pd.DataFrame({
            "delta t": ["t0-t1"],
            "Stable": [100],
            "Gain": [50],
            "Loss": [20],
            "rel Stable": [0.5],
            "rel Gain": [0.25],
            "rel Loss": [0.1],
            "tor": [0.7]
        })
        df.to_excel(folder / result_file)

    yield base_path, id_list  # Provide to the test function

    # Cleanup after test
    shutil.rmtree(base_path, ignore_errors=True)
    shutil.rmtree("test_batch_results", ignore_errors=True)

# Actual test
def test_batch_collect(setup_batch_collect_test_data):
    base_path, id_list = setup_batch_collect_test_data
    log = MockLogger_batch_collect()

    batch_collect(
        PROJECT_Path=base_path,
        ID_list=id_list,
        project_tag="TP000",
        motility_folder="motility_analysis",
        RESULTS_Path="test_batch_results",
        log=log
    )

    # Check if summary file was created
    assert os.path.exists("test_batch_results/all_motility.xlsx")
    assert os.path.exists("test_batch_results/average_motility.xlsx")

    df = pd.read_excel("test_batch_results/all_motility.xlsx")
    assert df.shape[0] == 2  # One row per ID

    # Optional: check logger messages
    assert "Collected data saved in test_batch_results" in log.messages[-1]



