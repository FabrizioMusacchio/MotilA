""" 
pip install pytest

In a terminal, run:
pytest
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motila.motila import (
    hello_world,
    calc_projection_range,
    plot_2D_image,
    plot_2D_image_as_tif,
    plot_histogram
)
import numpy as np
import tifffile
import matplotlib.pyplot as plt

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
    result, correction = calc_projection_range(
        projection_center=10,
        projection_layers=5,
        I_shape=(100, 30),  # shape: (y, z)
        log=log
    )
    assert result == [8, 11]
    assert correction == 0
    assert "Projection center: 10" in log.messages[-1]

def test_projection_upper_exceeds():
    log = MockLogger()
    result, correction = calc_projection_range(
        projection_center=28,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result == [26, 29]
    assert correction == 0 # no out-of-bounds
    assert "Projection center" in log.messages[-1]
    assert len(log.messages) == 1  # No warnings

def test_projection_lower_exceeds():
    log = MockLogger()
    result, correction = calc_projection_range(
        projection_center=1,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result == [0, 2]
    assert correction == 2  # only 3 layers possible
    assert "adjusted as it was below 0" in log.messages[-2]

def test_projection_completely_out_of_bounds():
    log = MockLogger()
    result, correction = calc_projection_range(
        projection_center=40,
        projection_layers=5,
        I_shape=(100, 30),
        log=log
    )
    assert result == [0, 0]
    assert correction == 0
    assert "exceeds image z-dimension" in log.messages[-2]


# plot_2D_image:
def test_plot_2D_image_creates_file(tmp_path):
    # Create a simple 2D image
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

# test_plot_histogram_creates_pdf:
def test_plot_histogram_creates_pdf(tmp_path):
    # Generate test image
    image = np.random.rand(128, 128).astype(np.float32)
    plot_title = "hist_test"
    plot_path = tmp_path

    # Call the histogram plotting function
    plot_histogram(image, plot_path, plot_title, fignum=99, title="Histogram Test")

    # Check that the PDF was created
    output_file = plot_path / f"{plot_title}.pdf"
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # Make sure it's not empty
