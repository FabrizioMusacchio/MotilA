""" MotilA: Microglial Motility Analysis Pipeline
=============================================

MotilA is a Python-based pipeline for analyzing microglial fine process motility from in vivo 
4D and 5D time-lapse image stacks. It supports both single-file and batch processing modes, 
and includes optional steps for image registration, spectral unmixing, contrast enhancement, 
and multi-method segmentation.

Core pipeline steps:
--------------------
1. Load image data (supports TIFF in TZCYX and TZYX formats)
2. Extract sub-volumes from the 3D image stack
3. (Optional) Register sub-volumes to correct motion
4. (Optional) Perform spectral unmixing to reduce channel bleed-through
5. z-projection of the sub-volumes for further processing
6. (Optional) Apply histogram equalization and histogram matching for contrast/bleaching correction
7. (Optional) Apply filtering (median, Gaussian) to reduce noise
8. Segment microglial structures via thresholding and blob detection
9. Analyze motility by tracking pixel changes over time

Batch processing steps:
-----------------------
1. Define a project folder containing multiple registered TIFF stacks
2. Apply the core pipeline steps to each stack automatically
3. Store results (plots, metrics, segmentation) per dataset
4. Aggregate results across animals or conditions for cohort-level analysis

Key features:
-------------
- Handles 4D and 5D TIFF stacks (TZXY, TCZXY)
- Supports dual-channel imaging (e.g., microglia and neurons)
- Implements spectral unmixing, histogram equalization and matching
- Includes 2D and 3D motion correction
- Offers multiple thresholding and filtering options
- Computes gain, loss, stability, and turnover rate (TOR) metrics

Dependencies:
-------------
- Python >= 3.9
- numpy, scipy, matplotlib, scikit-image, scikit-learn, pandas
- tifffile, zarr, numcodecs, openpyxl, xlrd
- ipywidgets, ipykernel, ipympl

Installation:
-------------
To install dependencies via conda and mamba:
```bash
conda create -n motila python=3.12 mamba -y
conda activate motila
mamba install -y numpy scipy matplotlib scikit-image scikit-learn pandas tifffile zarr numcodecs openpyxl xlrd ipywidgets ipykernel ipympl
```

Usage:
-------------
1. Configure pipeline parameters (e.g., projection layers, channels, filters).
2. Run process_stack(fname, ...) for single-file or batch_process_stacks(...) for cohort mode with the desired settings.
3. Output includes processed stacks, Excel tables with metrics, and diagnostic plots

Author
-------------
Fabrizio Musacchio (lead developer)
Contributors: Sophie Crux, Felix Nebeling, Nala Gockel, Falko Fuhrmann, Martin Fuhrmann
First created: September 2023

License: GPL-3.0 License
-------------
GPL-3.0 License — see LICENSE file for full terms.

Summary:
* Free to use, modify, and distribute under the same license
* Must retain license and attribution
* Not for use in proprietary/closed-source projects
*  NO WARRANTY provided (see https://www.gnu.org/licenses/gpl-3.0.html)
 
See <https://www.gnu.org/licenses/gpl-3.0.html> for full terms.

Citation
-------------
If you use this software in your research, please cite it as follows:

```
@software{musacchio2025motila,
  author       = {Fabrizio Musacchio and Sophie Crux and Felix Nebeling and Nala Gockel and Martin Fuhrmann},
  title        = {MotilA: A pipeline for microglial fine process motility analysis},
  year         = {2025},
  url          = {https://github.com/FabrizioMusacchio/motila},
  version      = {1.0.0},
  note         = {Accessed: YYYY-MM-DD},
}
```

Contact
-------------
For questions, suggestions, or bug reports, please contact the lead developer:
- Fabrizio Musacchio:
    - Email: fabrizio.musacchio@posteo.de
    - GitHub: https://github.com/FabrizioMusacchio
"""
# %% IMPORTS
import os
import shutil
from pathlib import Path
import glob
import gc

from motila.utils import (
    check_folder_exist_create, 
    filterfolder_by_string,
    filterfiles_by_string,
    logger_object, 
    print_ram_usage_in_loop, 
    print_ram_usage,
    tiff_axes_check_and_correct)

import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
from matplotlib import colors as mcol

from skimage.registration import phase_cross_correlation
from skimage import transform, io, exposure
from pystackreg import StackReg
import tifffile

import skimage.filters as filter
import skimage.exposure as exposure
import skimage.measure as measure
import skimage.morphology

import zarr
from numcodecs import Blosc

from datetime import datetime
import time

# turn off warnings:
import warnings
warnings.filterwarnings("ignore")
# %% ESSENTIAL FUNCTIONS

def hello_world():
    """
    Prints a friendly message to the user.
    """
    print("Hello, World! Welcome to MotilA!")

def calc_projection_range(projection_center, projection_layers, I_shape, log):
    """
    Calculate the projection range for a given center and number of layers, ensuring it fits within the image dimensions.

    Parameters:
    -----------
    projection_center : int
        The central layer index for the projection.
    projection_layers : int
        The total number of layers to include in the projection.
    I_shape : tuple
        The shape of the image stack, where the second element represents the z-dimension.
    log : object
        A logging object with a `log` method for recording warnings and information.

    Returns:
    --------
    tuple
        A tuple containing:
        - projection_range : list
            A list of two integers representing the start and end indices of the projection range.
        - projection_layers : int
            The actual number of layers included in the projection range after boundary adjustments.
    """
    
    """ 
    projection_center = 4
    projection_layers=4 
    """
    
    # check if projection_center is out of bounds:
    if projection_center < 0 or projection_center >= I_shape[1]:
        log.log(f"WARNING: projection center {projection_center} is out of bounds for image z-dimension {I_shape[1]} -> skipping.")
        return [0, 0], 0  # No valid projection range and number of layers therefore 0
    
    projection_half = projection_layers // 2  # integer division for symmetry

    # calculate the projection range:
    if projection_layers % 2 == 1:
        # odd number of layers: symmetric range around projection center
        projection_range = [projection_center - projection_half, projection_center + projection_half]
    else:
        # even number of layers: two possible valid projections
        projection_range = [projection_center - projection_half + 1, projection_center + projection_half]

    # convert to integer:
    projection_range = [int(projection_range[0]), int(projection_range[1])]
    
    """ print(f"projection_center: {projection_center}, projection_layers: {projection_layers}")
    print(projection_range)
    print(f"Projection range: {len(np.arange(projection_range[0], projection_range[1]+1))} layers: {np.arange(projection_range[0], projection_range[1]+1)}")
    print(f"projection_layers: {projection_layers}") """
    
    # validate against stack dimensions:
    projection_layers_correction = 0
    z_layers = I_shape[1]

    # if the projection range exceeds the image boundaries, adjust accordingly:
    if projection_range[0] < 0:
        projection_range[0] = 0
        log.log(f"WARNING: projection range {projection_range} adjusted as it was below 0.")
    if projection_range[1] >= z_layers:
        projection_range[1] = z_layers - 1
        log.log(f"WARNING: projection range {projection_range} exceeds image z-dimension {z_layers} -> adjusted.")

    # calculate the number of layers currently in the range:
    current_layers = projection_range[1] - projection_range[0] + 1

    # adjust the range if there are not enough layers:
    if current_layers < projection_layers:
        # expand the range symmetrically, if possible, starting from the center:
        left_side = projection_range[0]
        right_side = projection_range[1]

        # first try expanding to the left:
        if left_side > 0:
            projection_range[0] -= 1
        # then try expanding to the right if we still have fewer layers:
        if right_side < z_layers - 1:
            projection_range[1] += 1

        # if necessary, shift the range to fit the exact number of layers:
        current_layers = projection_range[1] - projection_range[0] + 1
        if current_layers < projection_layers:
            if projection_range[0] > 0:
                projection_range[0] -= 1
            if projection_range[1] < z_layers - 1:
                projection_range[1] += 1
    
    """ print(projection_range)
    print(f"Projection range: {len(np.arange(projection_range[0], projection_range[1]+1))} layers: {np.arange(projection_range[0], projection_range[1]+1)}")
    print(f"projection_layers: {projection_layers}") """

    log.log(f"Projection center: {projection_center}, Projection range: {projection_range}")

    # update projection_layers if it was adjusted to the actual number of layers:
    projection_layers = projection_range[1] - projection_range[0] + 1

    return projection_range, projection_layers

def plot_2D_image(image, plot_path, plot_title, fignum=1, figsize=(5,5.15),
                  show_ticks=False, show_borders=False, cbar_show=False,
                  cmap=plt.get_cmap('viridis'), cbar_label="",
                  cbar_ticks=[], cbar_ticks_labels="", title=""):
    """
    Plots a 2D image and saves it as a PDF file.

    Parameters:
    -----------
    image : array-like
        The 2D array representing the image to be plotted.
    plot_path : str or Path
        The directory path where the plot will be saved.
    plot_title : str
        The filename for the saved plot (without extension).
    fignum : int, optional
        The figure number for the plot (default is 1).
    cmap : matplotlib.colors.Colormap, optional
        The colormap to be used for the image (default is 'viridis').
    cbar_label : str, optional
        The label for the colorbar (default is an empty string).
    cbar_ticks : list of float, optional
        Tick positions for the colorbar (default is an empty list, meaning automatic ticks).
    cbar_ticks_labels : list of str, optional
        Labels for the colorbar ticks (default is an empty list, meaning no custom labels).
    title : str, optional
        The title of the plot (default is an empty string).

    Returns:
    --------
    None
        This function saves the plot as a PDF file and does not return a value.

    Notes:
    ------
    - The plot is saved in the specified directory as `<plot_title>.pdf` with a resolution of 500 DPI.
    - A colorbar is added if `cbar_label` is provided.
    - The 
    """
    #plt.clf()
    fig = plt.figure(fignum, figsize=figsize)
    plt.clf()
    plt.imshow(image, cmap=cmap)
    if cbar_show:
        cbar = plt.colorbar(label=cbar_label)
        if len(cbar_ticks)>0:
            cbar.set_ticks(cbar_ticks)
        if len(cbar_ticks_labels)>0:
            cbar.set_ticklabels(cbar_ticks_labels)
    if not show_ticks:
        plt.xticks([])
        plt.yticks([])
    if not show_borders:
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['bottom'].set_visible(False)
        plt.gca().spines['left'].set_visible(False)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=500)
    plt.close(fig)

def plot_2D_image_as_tif(image, plot_path, plot_title):
    """
    Saves a 2D image as a compressed TIFF file.

    Parameters:
    -----------
    image : array-like
        The 2D array representing the image to be saved.
    plot_path : str or Path
        The directory where the TIFF file will be saved.
    plot_title : str
        The filename for the saved TIFF file (without extension).

    Returns:
    --------
    None
        This function saves the image as a TIFF file and does not return a value.

    Notes:
    ------
    - The file is saved as `<plot_title>.tif` in the specified directory.
    - The TIFF file is compressed using zlib.
    - The function requires `tifffile` and `os` for file handling.
    """
    TIFF_path = os.path.join(plot_path, plot_title+".tif")
    tifffile.imwrite(TIFF_path, image, compression='zlib')

def plot_histogram(image, plot_path, plot_title, fignum=1, title="histogram"):
    """
    Plots the histogram and cumulative distribution function (CDF) of an image and saves it as a PDF file.

    Parameters:
    -----------
    image : array-like
        The 2D array representing the image for which the histogram is computed.
    plot_path : str or Path
        The directory where the histogram plot will be saved.
    plot_title : str
        The filename for the saved histogram plot (without extension).
    fignum : int, optional
        The figure number for the plot (default is 1).
    title : str, optional
        The title of the plot (default is "histogram").

    Returns:
    --------
    None
        The function saves the histogram plot as a PDF file and does not return a value.

    Notes:
    ------
    - The function computes the histogram and cumulative distribution function (CDF) using `skimage.exposure`.
    - The plot is saved as `<plot_title>.pdf` in the specified directory.
    - The function requires `matplotlib.pyplot` and `skimage.exposure` for plotting.
    """
    fig = plt.figure(fignum)
    plt.clf()
    img_hist, bins = exposure.histogram(image, source_range='image')
    plt.plot(bins, img_hist / img_hist.max())
    img_cdf, bins = exposure.cumulative_distribution(image)
    plt.plot(bins, img_cdf)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=500)
    plt.close(fig)

def plot_histogram_of_projections(image_stack, I_shape, plot_path, log, fignum=1):
    """
    Plots histograms for each projected stack in the given image stack and saves them as PDF files.

    Parameters:
    -----------
    image_stack : array-like
        The stack of 2D images for which histograms will be computed.
    I_shape : tuple
        The shape of the image stack (assumed to be in TZYX or TCZYX format).
    plot_path : str or Path
        The directory where the histogram plots will be saved.
    log : logger_object
        A logging object to record processing steps and timing.
    fignum : int, optional
        The figure number for plotting (default is 1).

    Returns:
    --------
    None
        The function saves histogram plots for each projected stack as PDF files.

    Notes:
    ------
    - Each stack slice is processed separately, and its histogram is saved as `<plot_title>.pdf`.
    - The function logs processing time and status using the provided logger.
    - Uses `plot_histogram()` internally to generate individual plots.
    """
    Process_t0 = time.time()
    print(f"plotting the histograms of the projeted stacks...", end="")

    log.log(f"")
    for stack in range(I_shape[0]):
        plot_histogram(image_stack[stack], plot_path=plot_path, fignum=1,
                       title=f"MG projected, histogram, stack {stack}",
                       plot_title=f"MG projected, histogram, stack {stack}")

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram plotting ")

def plot_projected_stack(image_stack, I_shape, plot_path, log, plottitle="MG projected"):
    """
    Plots and saves z-projected image stacks as grayscale images and a TIFF file.

    Parameters:
    -----------
    image_stack : array-like
        The stack of 2D projected images to be plotted and saved.
    I_shape : tuple
        The shape of the image stack, used to determine the number of stacks.
    plot_path : str or Path
        The directory where the plots and TIFF file will be saved.
    log : logger_object
        A logging object to record processing steps and execution time.
    plottitle : str, optional
        The base title for the saved plots and TIFF file (default is "MG projected").

    Returns:
    --------
    None
        The function saves each projected stack as a grayscale plot and the full stack as a TIFF file.

    Notes:
    ------
    - Individual stacks are plotted as grayscale images and saved as PDFs.
    - The full image stack is saved as a TIFF file with metadata.
    - The function logs the plotting process and execution time.
    """
    Process_t0 = time.time()

    log.log(f"plotting z-projections...")
    for stack in range(I_shape[0]):
        plot_2D_image(image_stack[stack], plot_path, plot_title=plottitle+", stack " + str(stack), 
                      fignum=9, cmap=plt.get_cmap('gist_gray'), cbar_label="",
                      title=f"{plottitle}, stack {stack}", cbar_show=False)
                      # cbar_ticks=np.arange(0,255,10), cbar_ticks_labels=np.arange(0,255,10),
    TIFF_path = os.path.join(plot_path, plottitle+".tif")
    tifffile.imwrite(TIFF_path, image_stack.astype("float32"), 
                        resolution=(image_stack[0].shape[-2], image_stack[0].shape[-1]),
                        metadata={'spacing': 1, 'unit': 'um', 'axes': 'ZYX'},
                        imagej=True, bigtiff=False)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="z-projection plotting ")

def plot_projected_stack_as_tif(image_stack, I_shape, plot_path, log, plottitle="MG projected"):
    """
    Saves z-projected image stacks as TIFF files.

    Parameters:
    -----------
    image_stack : array-like
        The stack of 2D projected images to be saved as TIFF files.
    I_shape : tuple
        The shape of the image stack, used to determine the number of stacks.
    plot_path : str or Path
        The directory where the TIFF files will be saved.
    log : logger_object
        A logging object to record processing steps and execution time.
    plottitle : str, optional
        The base title for the saved TIFF files (default is "MG projected").

    Returns:
    --------
    None
        The function saves each projected stack as an individual TIFF file.

    Notes:
    ------
    - Each stack is saved as a separate TIFF file with a unique filename.
    - The function logs the saving process and execution time.
    """
    Process_t0 = time.time()

    log.log(f"saving z-projections as tif files...")
    for stack in range(I_shape[0]):
        plot_2D_image_as_tif(image=image_stack[stack], plot_path=plot_path,
                             plot_title=plottitle+", stack " + str(stack))

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="z-projection tif saving ")

def get_stack_dimensions(fname):
    """
    Retrieves the dimensions of a TIFF image stack without loading the entire dataset
    (i.e., of all axis, TZCYX or TZYX (ImageJ default order)).

    Parameters:
    -----------
    fname : str or Path
        The path to the TIFF file.

    Returns:
    --------
    list
        A list representing the shape of the image stack, ordered as TZCYX or TZYX.

    Raises:
    -------
    ValueError
        If the provided file is not a TIFF file.

    Notes:
    ------
    - The function reads metadata from the TIFF file to determine its dimensions.
    - The file is opened and closed without loading the image into memory.
    """

    if Path(fname).suffix != ".tif":
        raise ValueError("Currently, only TIFF files are supported.")
    else:
        # get information about the image stack in the TIFF file without reading any image data:
        I = tifffile.TiffFile(fname)
        I_shape = I.series[0].shape
        I.close()
        #convert tuple to list:
        I_shape = list(I_shape)
        
    return I_shape

def extract_subvolume(fname, I_shape, projection_layers, projection_range, log,
                      two_channel=False, channel=0):
    """
    Extracts sub-volumes from a multi-dimensional TIFF image stack and stores them in a Zarr format.

    Parameters:
    -----------
    fname : str or Path
        Path to the TIFF file.
    I_shape : tuple
        Shape of the input image stack.
    projection_layers : int
        Number of layers to extract for projection.
    projection_range : tuple
        The range of layers to be extracted.
    log : logger_object
        Logging object for recording the process.
    two_channel : bool, optional
        Whether the image stack contains two channels (default is False).
    channel : int, optional
        The primary channel index to be extracted (default is 0).

    Returns:
    --------
    tuple
        If `two_channel` is False: 
            - MG_sub (Zarr dataset): Extracted microglial sub-volume.
            - zarr_group (Zarr group): The Zarr group containing the sub-volumes.
        If `two_channel` is True:
            - MG_sub (Zarr dataset): Extracted microglial sub-volume.
            - N_sub (Zarr dataset): Extracted neuronal sub-volume.
            - zarr_group (Zarr group): The Zarr group containing the sub-volumes.

    Raises:
    -------
    ValueError
        If the provided file is not a TIFF file.

    Notes:
    ------
    - The function converts the TIFF file into a Zarr store for efficient memory access.
    - The extracted sub-volumes are saved in the Zarr format to reduce memory consumption.
    - The function supports both single-channel and two-channel extractions.
    """
    Process_t0 = time.time()
    log.log(f"extracting sub-volumes...")
    
    # we assume the input image stack is a 5D (TCZXY) or 4D (TZXY) tif stack:
    
    if Path(fname).suffix != ".tif":
        raise ValueError("Currently, only TIFF files are supported.")
    else:
        # open the tif file as zarr store:
        # tifffile's zarr support works a) for ZARR >= 3.0 and b) not within a Jupyter notebook due to
        # ZARR asynchronous loading of the data, which is not supported in Jupyter notebooks. Thus, we
        # use the following try-except block to handle this:
        try:
            store = tifffile.imread(fname, aszarr=True)
            I = zarr.open(store, mode='r')
            
            # ensure that the zarr store is indeed memory-mapped and not in-memory loaded (which is the default in tifffile):
            if two_channel:
                chunks = (1, 1, 1, I_shape[-2], I_shape[-1])
            else:
                chunks = (1, 1, I_shape[-2], I_shape[-1])
            zarr_path = Path(fname).parent.joinpath(Path(fname).stem + ".zarr")
            #compressor = Blosc(cname='lz4', clevel=5, shuffle=Blosc.SHUFFLE, blocksize=0)
            #compressor = Blosc(cname='zlib', clevel=9, shuffle=Blosc.SHUFFLE, blocksize=0)
            #compressor = Blosc(cname='zstd', clevel=9, shuffle=Blosc.SHUFFLE, blocksize=0)
            # info: we do not compress for speed reasons
            zarr_group = zarr.group(zarr_path, overwrite=True)
            if zarr.__version__ >= "3":
                chunks = tuple(int(x) for x in chunks)
                zarr_group.create_array("image", shape=I.shape, chunks=chunks, 
                                        dtype=I.dtype, overwrite=True)
            else:
                zarr_group.create_dataset("image", shape=I.shape, chunks=chunks, 
                                        dtype=I.dtype)
            zarr_group["image"][:] = I
            zarr_group.attrs["original_file"] = str(fname)
            zarr_group.attrs["ZARR file path"] = str(zarr_path)
            zarr_group.attrs["shape"] = I.shape
            zarr_group.attrs["dtype"] = str(I.dtype)
            store.close()
            
        except:
            # otherwise, we read the tif file using tifffile and convert it to a zarr store:
            I = tifffile.imread(fname)
            
            # ensure that the zarr store is indeed memory-mapped and not in-memory loaded (which is the default in tifffile):
            if two_channel:
                chunks = (1, 1, 1, I_shape[-2], I_shape[-1])
            else:
                chunks = (1, 1, I_shape[-2], I_shape[-1])
            zarr_path = Path(fname).parent.joinpath(Path(fname).stem + ".zarr")
            #compressor = Blosc(cname='lz4', clevel=5, shuffle=Blosc.SHUFFLE, blocksize=0)
            #compressor = Blosc(cname='zlib', clevel=9, shuffle=Blosc.SHUFFLE, blocksize=0)
            #compressor = Blosc(cname='zstd', clevel=9, shuffle=Blosc.SHUFFLE, blocksize=0)
            # info: we do not compress for speed reasons
            zarr_group = zarr.group(zarr_path, overwrite=True)
            if zarr.__version__ >= "3":
                chunks = tuple(int(x) for x in chunks)
                zarr_group.create_array("image", shape=I.shape, chunks=chunks, 
                                        dtype=I.dtype, overwrite=True)
            else:
                zarr_group.create_dataset("image", shape=I.shape, chunks=chunks, 
                                        dtype=I.dtype)
            zarr_group["image"][:] = I
            zarr_group.attrs["original_file"] = str(fname)
            zarr_group.attrs["ZARR file path"] = str(zarr_path)
            zarr_group.attrs["shape"] = I.shape
            zarr_group.attrs["dtype"] = str(I.dtype)

        I = zarr_group["image"]
        #I.info

    subvol_shape = (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])
    subvol_chunks = (1, 1, I_shape[-2], I_shape[-1])  # Efficient chunking for Zarr
    subvol_group = zarr_group.require_group("subvolumes")
    if zarr.__version__ >= "3":
        subvol_shape  = tuple(int(x) for x in subvol_shape)
        subvol_chunks = tuple(int(x) for x in subvol_chunks)
        MG_sub = subvol_group.create_array("MG_sub", shape=subvol_shape, chunks=subvol_chunks, dtype=I.dtype,
                                           overwrite=True)
    else:
        MG_sub = subvol_group.create_dataset("MG_sub", shape=subvol_shape, chunks=subvol_chunks, dtype=I.dtype,
                                            overwrite=True)
    if two_channel:
        if zarr.__version__ >= "3":
            N_sub = subvol_group.create_array("N_sub", shape=subvol_shape, chunks=subvol_chunks, dtype=I.dtype,
                                              overwrite=True)
        else:
            N_sub = subvol_group.create_dataset("N_sub", shape=subvol_shape, chunks=subvol_chunks, dtype=I.dtype,
                                                overwrite=True)
        if channel==0:
            channel_N = 1
        else:
            channel_N = 0
    for stack in range(I_shape[0]):
        if two_channel:
            MG_sub[stack] = I[stack, projection_range[0]:projection_range[1]+1, channel, :, :]
            N_sub[stack] = I[stack, projection_range[0]:projection_range[1]+1, channel_N, :, :]
        else:
            MG_sub[stack] = I[stack, projection_range[0]:projection_range[1]+1, :, :]
    
    del I
    gc.collect()
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process=f" sub-volume extracting ")
    
    if two_channel:
        return MG_sub, N_sub, zarr_group
    else:
        return MG_sub, zarr_group

def extract_and_register_subvolume(fname, I_shape, projection_layers, projection_range,
                                   MG_channel, log, two_channel, template_mode="mean",
                                   max_xy_shift_correction=5, debug_output=False):
    """
    Extracts sub-volumes from a multi-dimensional TIFF image stack, registers them using 
    phase cross-correlation, and saves the results in a Zarr format.

    Parameters:
    -----------
    fname : str or Path
        Path to the TIFF file.
    I_shape : tuple
        Shape of the input image stack.
    projection_layers : int
        Number of layers to extract for projection.
    projection_range : tuple
        The range of layers to be extracted.
    MG_channel : int
        The channel index corresponding to microglial cells.
    log : logger_object
        Logging object for recording the process.
    two_channel : bool
        Whether the image stack contains two channels.
    template_mode : str, optional
        The method to compute the template for registration.
        Options: 'mean', 'median', 'max', 'std', 'var'. Default is 'mean'.
    max_xy_shift_correction : int, optional
        The maximum allowed shift correction in XY directions (default is 5 pixels).

    Returns:
    --------
    tuple
        If `two_channel` is False:
            - MG_sub_reg_cropped (Zarr dataset): Registered and cropped microglial sub-volume.
            - I_shape_reg (tuple): Shape of the registered dataset.
            - zarr_group (Zarr group): The Zarr group containing the sub-volumes.
        If `two_channel` is True:
            - MG_sub_reg_cropped (Zarr dataset): Registered and cropped microglial sub-volume.
            - N_sub_reg_cropped (Zarr dataset): Registered and cropped neuronal sub-volume.
            - I_shape_reg (tuple): Shape of the registered dataset.
            - zarr_group (Zarr group): The Zarr group containing the sub-volumes.

    Raises:
    -------
    ValueError
        If the provided file is not a TIFF file.

    Notes:
    ------
    - The function extracts sub-volumes using `extract_subvolume` and applies 3D registration.
    - Registration is performed via phase cross-correlation using a reference template.
    - The function supports multiple template modes, including mean, median, and variance.
    - The final registered volumes are cropped to remove zero-padding caused by shifts.
    - All intermediate datasets are stored in a Zarr format for efficient access.
    """
    Process_t0 = time.time()
    log.log(f"extracting sub-volumes and register them...")
    
    if two_channel:
        MG_sub, N_sub, zarr_group = extract_subvolume(fname, I_shape, projection_layers, projection_range, log,
                                                        two_channel=True, channel=MG_channel)
    else:
        MG_sub, zarr_group = extract_subvolume(fname, I_shape, projection_layers, projection_range, log,
                                               two_channel=False)

    # register sub-volume:
    subvol_shape = (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])
    subvol_chunks = (1, 1, I_shape[-2], I_shape[-1])  # Efficient chunking for Zarr
    subvol_group = zarr_group["subvolumes"]
    #compressor = Blosc(cname='lz4', clevel=5, shuffle=Blosc.SHUFFLE, blocksize=0)
    if zarr.__version__ >= "3":
        subvol_shape  = tuple(int(x) for x in subvol_shape)
        subvol_chunks = tuple(int(x) for x in subvol_chunks)
        MG_sub_reg = subvol_group.create_array("MG_sub_tmp", shape=subvol_shape, chunks=subvol_chunks, 
                                               dtype=zarr_group.attrs["dtype"], overwrite=True)
    else:
        MG_sub_reg = subvol_group.create_dataset("MG_sub_tmp", shape=subvol_shape, chunks=subvol_chunks, 
                                                dtype=zarr_group.attrs["dtype"])
    if two_channel:
        if zarr.__version__ >= "3":
            N_sub_reg = subvol_group.create_array("N_sub_tmp", shape=subvol_shape, chunks=subvol_chunks, 
                                                  dtype=zarr_group.attrs["dtype"], overwrite=True)
        else:
            N_sub_reg = subvol_group.create_dataset("N_sub_tmp", shape=subvol_shape, chunks=subvol_chunks, 
                                                    dtype=zarr_group.attrs["dtype"])

    # determine template mode:
    if template_mode == "mean":
        template_func = np.mean
    elif template_mode == "median":
        template_func = np.median
    elif template_mode == "max":
        template_func = np.max
    elif template_mode == "std":
        template_func = np.std
    elif template_mode == "var":
        template_func = np.var
    else: 
        template_func = np.mean
    
    # register the sub-volumes:
    max_shifts = np.zeros((I_shape[0], 2))
    for stack in range(I_shape[0]):
        # stack=0
        Process_t0_curr_reg = time.time()
        log.log(f"   registering 3D stack {stack}/{I_shape[0]}...")
        
        if two_channel:
            # calculate the template:
            template_I = template_func(N_sub[stack, :, :, :], axis=0)
        else:
            # calculate the template:
            template_I = template_func(MG_sub[stack, :, :, :], axis=0)
        
        # use phase-correlation to register the current sub-volume:
        shifts = np.zeros((projection_layers, 2))
        for slice in range(projection_layers):
            if debug_output: print_ram_usage_in_loop(indent=3)
            
            if two_channel:
                curr_moving_slice = N_sub[stack, slice, :, :]
            else:
                curr_moving_slice = MG_sub[stack, slice, :, :]
            shifts[slice, :], _, _ = phase_cross_correlation(template_I, curr_moving_slice, upsample_factor=1)
            
            # check if the shifts are within the allowed range:
            if shifts[slice, 0] > max_xy_shift_correction:
                shifts[slice, 0] = max_xy_shift_correction
            elif shifts[slice, 0] < -max_xy_shift_correction:
                shifts[slice, 0] = -max_xy_shift_correction
            if shifts[slice, 1] > max_xy_shift_correction:
                shifts[slice, 1] = max_xy_shift_correction
            elif shifts[slice, 1] < -max_xy_shift_correction:
                shifts[slice, 1] = -max_xy_shift_correction
                
            # apply the shift to the current slice:
            MG_sub_reg[stack, slice, :, :] = transform.warp(MG_sub[stack, slice, :, :],
                                                            transform.SimilarityTransform(translation=shifts[slice, :]),
                                                            preserve_range=True)
            if two_channel:
                N_sub_reg[stack, slice, :, :] = transform.warp(N_sub[stack, slice, :, :],
                                                               transform.SimilarityTransform(translation=shifts[slice, :]),
                                                               preserve_range=True)
        # find the max shifts in both directions; bear in mind, that the shifts can be negative:
        max_shifts[stack, 0] = np.max(shifts[:, 0].__abs__())
        max_shifts[stack, 1] = np.max(shifts[:, 1].__abs__())
        
        _ = log.logt(Process_t0_curr_reg, verbose=True, spaces=5, unit="sec", process=f"registration of stack {str(stack)} ")
    if debug_output: print_ram_usage(indent=2)
    # the now registered stacks are equally sized, but may contain zero-padding; we cut all stacks to the 
    # largest shift in x and y borders:
    # define new shape for the cropped arrays:
    max_shift = np.max(max_shifts, axis=0).astype("int")
    new_shape = (MG_sub_reg.shape[0], MG_sub_reg.shape[1], 
                MG_sub_reg.shape[2] - 2*max_shift[0], 
                MG_sub_reg.shape[3] - 2*max_shift[1])
    # create a new Zarr array for MG_sub_reg:
    subregvol_chunks = (1, 1, new_shape[-2], new_shape[-1])
    # Ensure shape is a tuple of Python ints
    new_shape = tuple(int(x) for x in new_shape)
    subregvol_chunks = tuple(int(x) for x in subregvol_chunks)
    if zarr.__version__ >= "3":
        new_shape = tuple(int(x) for x in new_shape)
        subregvol_chunks = tuple(int(x) for x in subregvol_chunks)
        MG_sub_reg_cropped = subvol_group.create_array("MG_sub", shape=new_shape, 
                                                       chunks=subregvol_chunks, dtype=zarr_group.attrs["dtype"],
                                                       overwrite=True)
    else:
        MG_sub_reg_cropped = subvol_group.create_dataset("MG_sub", shape=new_shape, 
                                                        chunks=subregvol_chunks, dtype=zarr_group.attrs["dtype"],
                                                        overwrite=True)
    MG_sub_reg_cropped[:] = MG_sub_reg[:, :, max_shift[0]:int(MG_sub_reg.shape[-2])-max_shift[0],
                                  max_shift[1]:int(MG_sub_reg.shape[-1])-max_shift[1]]
    
    if two_channel:
        if zarr.__version__ >= "3":
            N_sub_reg_cropped = subvol_group.create_array("N_sub", shape=new_shape, 
                                                          chunks=subregvol_chunks, dtype=zarr_group.attrs["dtype"],
                                                          overwrite=True)
        else:
            N_sub_reg_cropped = subvol_group.create_dataset("N_sub", shape=new_shape, 
                                                            chunks=subregvol_chunks, dtype=zarr_group.attrs["dtype"],
                                                            overwrite=True)
        N_sub_reg_cropped[:] = N_sub_reg[:, :, max_shift[0]:int(N_sub_reg.shape[-2])-max_shift[0],
                                        max_shift[1]:int(N_sub_reg.shape[-1])-max_shift[1]]
    
    
    I_shape_reg = MG_sub_reg.shape
    if debug_output: print_ram_usage(indent=2)
    
    # delete the N_sub_tmp and MG_sub_tmp datasets in the ZARR file:
    del subvol_group["MG_sub_tmp"]
    if two_channel:
        del subvol_group["N_sub_tmp"]
        del N_sub
    
    del MG_sub
    gc.collect()
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="sub-volume extracting + 3D registration")
    if debug_output: print_ram_usage(indent=2)

    if two_channel:
        return MG_sub_reg_cropped, N_sub_reg_cropped, I_shape_reg, zarr_group
    else:
        return MG_sub_reg_cropped, I_shape_reg, zarr_group

def spectral_unmix(MG_sub, N_sub, I_shape, zarr_group, projection_layers, log, 
                   median_filter_window=3, amplifyer=2):
    """
    Performs spectral unmixing to reduce channel bleed-through in microglial image stacks.
    It requires a microglial and a neuronal channel and spectral unmixing is performed by 
    simple subtraction of the neuronal signal from the microglial signal.

    Parameters:
    -----------
    MG_sub : Zarr dataset
        The extracted microglial channel sub-volume.
    N_sub : Zarr dataset
        The extracted neuronal channel sub-volume.
    I_shape : tuple
        Shape of the input image stack.
    zarr_group : Zarr group
        The Zarr group containing the sub-volumes.
    projection_layers : int
        Number of layers used for projection.
    log : logger_object
        Logging object for recording the process.
    median_filter_window : int, optional
        Size of the median filter window for noise reduction (default is 3).
    amplifyer : float, optional
        Amplification factor applied to the neuronal signal before subtraction (default is 2).

    Returns:
    --------
    MG_sub_processed : Zarr dataset
        The spectrally unmixed microglial sub-volume.

    Notes:
    ------
    - The function applies median filtering and Gaussian smoothing to the neuronal channel.
    - The neuronal signal is scaled and subtracted from the microglial channel to remove bleed-through.
    - Negative values are clipped to zero to avoid artificial signals.
    - Intermediate datasets are deleted after processing to free memory.
    """
    Process_t0 = time.time()
    log.log(f"spectral unmixing...")

    # pre-allocate results-ZARR-arrays:
    subvol_group = zarr_group["subvolumes"]
    subvol_shape = (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])
    subvol_chunks = (1, 1, I_shape[-2], I_shape[-1])
    if zarr.__version__ >= "3":
        subvol_shape  = tuple(int(x) for x in subvol_shape)
        subvol_chunks = tuple(int(x) for x in subvol_chunks)
        MG_sub_noblead = subvol_group.create_array("MG_sub_noblead_tmp", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"])
        N_sub_median = subvol_group.create_array("N_sub_noblead_tmp", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"])
        MG_sub_processed = subvol_group.create_array("MG_sub_processed", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"], overwrite=True)
    else:
        MG_sub_noblead = subvol_group.create_dataset("MG_sub_noblead_tmp", shape=subvol_shape, chunks=subvol_chunks,
                                                        dtype=zarr_group.attrs["dtype"])
        N_sub_median = subvol_group.create_dataset("N_sub_noblead_tmp", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"])
        MG_sub_processed = subvol_group.create_dataset("MG_sub_processed", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"], overwrite=True)
    
    # spectral unmixing:
    for stack in range(I_shape[0]):
        log.log(f"  stack {stack}...")
        for slice in range(projection_layers):
            N_sub_median[stack, slice] = sp.ndimage.median_filter(N_sub[stack, slice],
                                                                        median_filter_window)

            N_sub_median[stack, slice] = filter.gaussian(N_sub_median[stack, slice], sigma=2.0)
            

            MG_sub_noblead[stack, slice] = MG_sub[stack, slice]-N_sub_median[stack, slice]*amplifyer
            MG_sub_noblead[stack, slice] = np.clip(MG_sub_noblead[stack, slice], 0,
                                                         MG_sub_noblead[stack, slice].max())
    
    if zarr.__version__ >= "3":
        MG_sub_processed[:] = np.array(MG_sub_noblead)
    else:
        MG_sub_processed[:] = MG_sub_noblead
    
    del MG_sub, N_sub, MG_sub_noblead, N_sub_median
    del subvol_group["MG_sub_noblead_tmp"]
    del subvol_group["N_sub_noblead_tmp"]
    gc.collect()
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="spectral unmixing ")

    return MG_sub_processed

def histogram_equalization(MG_sub, I_shape, projection_layers, log, clip_limit=0.02):
    """
    Applies adaptive histogram equalization to enhance contrast in microglial image stacks.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial sub-volume.
    I_shape : tuple
        Shape of the input image stack.
    projection_layers : int
        Number of layers used for projection.
    log : logger_object
        Logging object for recording the process.
    clip_limit : float, optional
        Clipping limit for contrast limiting adaptive histogram equalization (default is 0.01).

    Returns:
    --------
    MG_sub_histeq : ndarray
        The histogram-equalized microglial sub-volume.

    Notes:
    ------
    - Adaptive histogram equalization improves local contrast while preventing over-amplification of noise.
    - The function processes each stack slice separately.
    - The input image stack is expected to be of type `uint16` before applying equalization.
    """
    Process_t0 = time.time()
    log.log(f"equalizing the histogram within each slice of all stacks ...")

    MG_sub_histeq = np.zeros((I_shape[0], projection_layers, I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_sub_histeq[stack, :, :, :] = exposure.equalize_adapthist(MG_sub[stack].astype("uint16"),
                                                                    clip_limit=clip_limit)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram equalization ")
    return MG_sub_histeq

def histogram_equalization_on_projections(MG_sub, I_shape, log, clip_limit=0.01,
                                          kernel_size=None):
    """
    Applies adaptive histogram equalization to enhance contrast in projected microglial image stacks.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial sub-volume projections.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.
    clip_limit : float, optional
        Clipping limit for contrast limiting adaptive histogram equalization (default is 0.01).
    kernel_size : tuple or None, optional
        Size of the contextual region for adaptive histogram equalization. If None, the kernel size is automatically determined.

    Returns:
    --------
    MG_sub_histeq : ndarray
        The histogram-equalized projected microglial sub-volume.

    Notes:
    ------
    - This function enhances contrast in 2D projections of the microglial image stacks.
    - Adaptive histogram equalization prevents over-amplification of noise while improving local contrast.
    - The input image stack is expected to be of type `uint16` before applying equalization.
    - Each stack is processed independently to maintain consistency across slices.
    """
    Process_t0 = time.time()
    log.log(f"equalizing the histogram for each projected stack ...")

    MG_sub_histeq = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_sub_histeq[stack, :, :] = exposure.equalize_adapthist(MG_sub[stack].astype("uint16"),
                                                                 clip_limit=clip_limit,
                                                                 kernel_size=kernel_size)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram equalization ")
    return MG_sub_histeq

def histogram_matching(MG_sub, I_shape, histogram_ref_stack, projection_layers, log):
    """
    Matches the histogram of each stack in the microglial sub-volume to a reference stack.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial sub-volume containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    histogram_ref_stack : int
        Index of the reference stack to which all other stacks' histograms will be matched.
    projection_layers : int
        Number of projection layers in the image stack.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_histeq : ndarray
        The histogram-matched microglial sub-volume.

    Notes:
    ------
    - Histogram matching ensures that all stacks have similar intensity distributions.
    - This is useful for normalizing intensity variations across different time points or conditions.
    - The reference stack should be representative of the desired intensity distribution.
    - Matching is performed independently for each stack while preserving spatial information.
    """
    Process_t0 = time.time()
    log.log(f"matching histograms of all stacks to reference stack {histogram_ref_stack}...")

    MG_sub_histeq = np.zeros((I_shape[0], projection_layers, I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_sub_histeq[stack, :, :, :] = exposure.match_histograms(MG_sub[stack],
                                                                  MG_sub[histogram_ref_stack])

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram matching ")
    return MG_sub_histeq

def histogram_matching_on_projections(MG_sub, I_shape, histogram_ref_stack, log):
    """
    Matches the histogram of each projected stack to a reference stack.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    histogram_ref_stack : int
        Index of the reference stack to which all other stacks' histograms will be matched.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_histeq : ndarray
        The histogram-matched projected image stacks.

    Notes:
    ------
    - Histogram matching ensures uniform intensity distribution across all projected stacks.
    - Useful for standardizing contrast across different time points or conditions.
    - The reference stack should be selected based on its representativeness of the desired distribution.
    - Matching is performed independently for each stack while maintaining spatial integrity.
    """
    Process_t0 = time.time()
    log.log(f"matching histograms of all stacks to reference stack {histogram_ref_stack}...")

    MG_sub_histeq = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_sub_histeq[stack, :, :] = exposure.match_histograms(MG_sub[stack], MG_sub[histogram_ref_stack])

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram matching ")
    return MG_sub_histeq

def median_filtering_on_projections(MG_sub, I_shape, median_filter_window,  log):
    """
    Applies a median filter to each projected stack to reduce noise, using a square kernel.
    
    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    median_filter_window : int
        Size of the window for median filtering. If ≤1, filtering is skipped.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_median : ndarray
        The median-filtered projected image stacks.

    Notes:
    ------
    - The median filter is a non-linear filter effective for noise removal, especially salt-and-pepper noise.
    - If `median_filter_window` is ≤1, the function skips filtering and returns the original image.
    - The function ensures spatial coherence while preserving important structural features.
    """
    Process_t0 = time.time()
    print(f"median-filtering...", end="")

    MG_sub_median = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))

    # if median_filter_window<=1, the footprint is a single pixel and thus the median filter
    # has no effect and will be is skipped:
    if median_filter_window>1:
        for stack in range(I_shape[0]):
                MG_sub_median[stack,  :, :] = sp.ndimage.median_filter(MG_sub[stack,  :, :],
                                                                            median_filter_window)
    else:
        print(f"  squared median_filter_window <= 1, median filtering skipped.")
        MG_sub_median = MG_sub.copy()

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="median filtering ")
    return MG_sub_median

def circular_median_filtering_on_projections(MG_sub, I_shape, median_filter_window,  log):
    """
    Applies a median filter to each projected stack to reduce noise, using a circular kernel.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    median_filter_window : int
        Radius of the circular structuring element for median filtering. If <1, filtering is skipped.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_median : ndarray
        The median-filtered projected image stacks.

    Notes:
    ------
    - Uses a circular structuring element (`skimage.morphology.disk`) to preserve shape integrity.
    - If `median_filter_window` < 1, the function skips filtering and returns the original image.
    - Effective for reducing noise while maintaining fine structures.
    """
    Process_t0 = time.time()
    print(f"median-filtering...", end="")

    MG_sub_median = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))

    # if median_filter_window < 1, the footprint is a single pixel and thus the median filter 
    # has no effect and will be is skipped:
    if median_filter_window>=1:
        circlemask = skimage.morphology.disk(median_filter_window)
        for stack in range(I_shape[0]):
            MG_sub_median[stack, :, :] = filter.median(MG_sub[stack,  :, :], footprint = circlemask)
    else:
        print(f"  circular median_filter_window < 1, median filtering skipped.")
        MG_sub_median = MG_sub.copy()

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="median filtering ")
    return MG_sub_median

def single_slice_median_filtering(MG_sub, I_shape, zarr_group, median_filter_window, projection_layers, log):
    """
    Applies square median filtering to each slice within the projected stacks.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    zarr_group : zarr group
        The Zarr storage group where the filtered data will be saved.
    median_filter_window : int
        Size of the square structuring element for median filtering. If <=1, filtering is skipped.
    projection_layers : int
        Number of slices in each stack.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_median : zarr dataset
        The median-filtered image stacks stored in Zarr.

    Notes:
    ------
    - The function checks if `median_filter_window` is an integer; if not, it defaults to 1 (no filtering).
    - Uses `scipy.ndimage.median_filter` for noise reduction while preserving structural integrity.
    - If `median_filter_window <= 1`, filtering is skipped, and the original image is returned.
    - The filtered images are stored in a new dataset `MG_sub_median` within the Zarr group.
    """
    Process_t0 = time.time()
    print(f"square median-filtering on slices...", end="")

    # verify that median_filter_window_slices is an integer, otherwise set it to 1:
    if median_filter_window.is_integer():
        median_filter_window = 1
        log.log(f"WARNING: square median_filter_window_slices is not an integer, set to {median_filter_window}\n (Thus, no median filtering is applied.)")

    # create a new Zarr array for MG_sub_median:
    subvol_group = zarr_group["subvolumes"]
    subvol_shape = (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])
    subvol_chunks = (1, 1, I_shape[-2], I_shape[-1])
    if zarr.__version__ >= "3":
        subvol_shape  = tuple(int(x) for x in subvol_shape)
        subvol_chunks = tuple(int(x) for x in subvol_chunks)
        MG_sub_median = subvol_group.create_array("MG_sub_median", shape=subvol_shape, chunks=subvol_chunks,
                                                  dtype=zarr_group.attrs["dtype"], overwrite=True)
    else:
        MG_sub_median = subvol_group.create_dataset("MG_sub_median", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"], overwrite=True)

    # if median_filter_window<=1, the footprint is a single pixel and thus the median filter
    # has no effect and will be is skipped:
    if median_filter_window>1:
        for stack in range(I_shape[0]):
            for slice in range(projection_layers):
                MG_sub_median[stack, slice, :, :] = sp.ndimage.median_filter(MG_sub[stack, slice, :, :],
                                                                             median_filter_window)
    else:
        print(f"  squared median_filter_window <= 1, median filtering skipped.")
        MG_sub_median[:] = MG_sub[:]
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="square median filtering on slices ")
    return MG_sub_median

def single_slice_circular_median_filtering(MG_sub, I_shape, zarr_group, median_filter_window, projection_layers, log):
    """
    Applies circular median filtering to each slice within the projected stacks.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    zarr_group : zarr group
        The Zarr storage group where the filtered data will be saved.
    median_filter_window : int
        Radius of the circular structuring element for median filtering. If <1, filtering is skipped.
    projection_layers : int
        Number of slices in each stack.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_median : zarr dataset
        The median-filtered image stacks stored in Zarr.

    Notes:
    ------
    - Uses `skimage.morphology.disk` to create a circular filter mask.
    - If `median_filter_window < 1`, filtering is skipped, and the original image is returned.
    - Utilizes `skimage.filters.median` for noise reduction while preserving structural details.
    - The filtered images are stored in a new dataset `MG_sub_median` within the Zarr group.
    """
    Process_t0 = time.time()
    print(f"circular median-filtering on slices...", end="")

    # create a new Zarr array for MG_sub_median:
    subvol_group = zarr_group["subvolumes"]
    subvol_shape = (I_shape[0], projection_layers, I_shape[-2], I_shape[-1])
    subvol_chunks = (1, 1, I_shape[-2], I_shape[-1])
    if zarr.__version__ >= "3":
        subvol_shape  = tuple(int(x) for x in subvol_shape)
        subvol_chunks = tuple(int(x) for x in subvol_chunks)
        MG_sub_median = subvol_group.create_array("MG_sub_median", shape=subvol_shape, chunks=subvol_chunks,
                                                  dtype=zarr_group.attrs["dtype"], overwrite=True)
    else:
        MG_sub_median = subvol_group.create_dataset("MG_sub_median", shape=subvol_shape, chunks=subvol_chunks,
                                                    dtype=zarr_group.attrs["dtype"], overwrite=True)
    
    # if median_filter_window < 1, the footprint is a single pixel and thus the median filter 
    # has no effect and will be is skipped:
    if median_filter_window>=1:
        circlemask = skimage.morphology.disk(median_filter_window)
        for stack in range(I_shape[0]):
            for slice in range(projection_layers):
                MG_sub_median[stack, slice, :, :] = filter.median(MG_sub[stack, slice, :, :],
                                                                  footprint = circlemask)
    else:
        print(f"  circular median_filter_window < 1, median filtering skipped.")
        MG_sub_median[:] = MG_sub[:]

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="circular median filtering on slices ")
    return MG_sub_median

def gaussian_blurr_filtering_on_projections(MG_sub, I_shape, gaussian_blurr_sigma, log):
    """
    Applies Gaussian blur filtering to each projected stack.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    gaussian_blurr_sigma : float
        Standard deviation for the Gaussian kernel.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_gaussian : ndarray
        The Gaussian-blurred image stacks.

    Notes:
    ------
    - Uses `skimage.filters.gaussian` to apply Gaussian blurring.
    - Helps in reducing noise while preserving edges to a certain extent.
    - The filter is applied independently to each stack.
    """
    Process_t0 = time.time()
    print(f"Gaussian blur filtering...", end="")

    MG_sub_gaussian = np.zeros((I_shape[0],  I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_sub_gaussian[stack, :, :] = filter.gaussian(MG_sub[stack, :, :], sigma=gaussian_blurr_sigma)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="Gaussian blur filtering ")
    return MG_sub_gaussian

def single_slice_gaussian_blurr_filtering(MG_sub, I_shape, gaussian_blurr_sigma, projection_layers, log):
    """
    Applies Gaussian blur filtering to each individual slice in the image stack.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial image stack.
    I_shape : tuple
        Shape of the input image stack.
    gaussian_blurr_sigma : float
        Standard deviation for the Gaussian kernel.
    projection_layers : int
        Number of layers in the projection stack.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_sub_gaussian : ndarray
        The Gaussian-blurred image stack.

    Notes:
    ------
    - Uses `skimage.filters.gaussian` to apply Gaussian blurring.
    - The filter is applied independently to each slice within each stack.
    - Helps in noise reduction while preserving relevant image structures.
    """
    Process_t0 = time.time()
    print(f"Gaussian blur filtering...", end="")

    MG_sub_gaussian = np.zeros((I_shape[0], projection_layers, I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        for slice in range(projection_layers):
            MG_sub_gaussian[stack, slice, :, :] = filter.gaussian(MG_sub[stack, slice, :, :],
                                                                  sigma=gaussian_blurr_sigma)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="Gaussian blur filtering ")
    return MG_sub_gaussian

def z_max_project(MG_sub, I_shape, log):
    """
    Computes the maximum intensity Z-projection of an image stack.

    Parameters:
    -----------
    MG_sub : array-like
        The input microglial image stack.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.

    Returns:
    --------
    MG_pro : ndarray
        The Z-projected image stack using maximum intensity projection.

    Notes:
    ------
    - This function collapses the Z-dimension by selecting the maximum 
      intensity value for each pixel across all Z-slices.
    - Useful for visualizing microglial structures in a single 2D image.
    - Logs execution time for performance monitoring.
    """
    Process_t0 = time.time()
    print(f"z-projecting...", end="")

    # First, verify that the input is a 3D array, otherwise return the input and a warning:
    if I_shape[1] == 1:
        log.log(f"WARNING: z_max_project: input is not a 3D array, returning input without projection.")
        return MG_sub

    MG_pro = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))

    for stack in range(I_shape[0]):
        MG_pro[stack] = np.max(MG_sub[stack], axis=0)
   
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="z-projections ")
    return MG_pro

def compare_histograms(MG_sub_pre, MG_sub_post, log, plot_path, I_shape, xlim=(0,6000)):
    """
    Compares histograms of projected stacks before and after histogram adjustments.

    Parameters:
    -----------
    MG_sub_pre : array-like
        The image stack before histogram adjustments.
    MG_sub_post : array-like
        The image stack after histogram adjustments.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        The directory path where the histogram plots will be saved.
    I_shape : tuple
        Shape of the input image stack.
    xlim : tuple, optional
        Limits for the x-axis of the histogram (default is (0, 6000)).

    Returns:
    --------
    None
        The function saves the histogram plots as PDF files.

    Notes:
    ------
    - Each stack’s histogram is plotted and saved separately.
    - The function normalizes intensity values before plotting.
    - Uses a logarithmic scale for better visualization of histogram distributions.
    - Logs execution time for performance monitoring.
    """
    Process_t0 = time.time()
    log.log(f"calculating and plotting histogram of each stack...")

    for stack in range(I_shape[0]):
        plt.close(1)
        fig = plt.figure(2, figsize=(8, 5))
        plt.clf()
        if MG_sub_pre[stack].ravel().max() > 1:
            Curr_MG_sub_pre = MG_sub_pre[stack].ravel() / MG_sub_pre[stack].ravel().max()
        else:
            Curr_MG_sub_pre = MG_sub_pre[stack].ravel()
        _,_,_ = plt.hist(Curr_MG_sub_pre,
                                 bins=256, histtype='stepfilled',
                                 color="k", alpha=0.25, label="before adjustments")
        if MG_sub_post[stack].ravel().max()>1:
            Curr_MG_sub_post = MG_sub_post[stack].ravel()/MG_sub_post[stack].ravel().max()
        else:
            Curr_MG_sub_post = MG_sub_post[stack].ravel()
        _, _, _ = plt.hist(Curr_MG_sub_post, bins=256, histtype='stepfilled',
                                   color="lime", alpha=0.45, label="before adjustments")
        ax = plt.gca()
        ax.set_yscale('log')
        #plt.xlim(xlim)
        plt.legend()
        plt.xlabel("normalized brightness bins")
        plt.ylabel("counts (log-scale)")
        title = f"Histograms of projected stack before and after histogram adjustments, stack {stack}"
        plot_title = f"Stats Histograms before and after adjustments, stack {stack}"
        plt.title(title)
        plt.tight_layout()
        plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
        plt.close(fig)

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="histogram comparison ")
    return

def plot_intensities(MG_pro, log, plot_path, I_shape):
    """
    Plots and saves the normalized average brightness per projected stack.

    Parameters:
    -----------
    MG_pro : array-like
        The projected image stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        The directory path where the plot and data file will be saved.
    I_shape : tuple
        Shape of the input image stack.

    Returns:
    --------
    intensity_means : ndarray
        Array containing the mean intensity values for each stack.

    Notes:
    ------
    - The function calculates the average intensity for each projected stack.
    - Normalizes intensity values relative to the first stack.
    - Saves a bar plot of the normalized brightness and an Excel file with values.
    - Includes grid lines for easier comparison.
    - Logs execution time for performance monitoring.
    """
    Process_t0 = time.time()
    log.log(f"plotting average brightness per projected stack...")

    intensity_means = np.zeros(I_shape[0])
    for stack in range(I_shape[0]):
        intensity_means[stack] = MG_pro[stack].mean()

    # plot normalized average brightness drop rel. to stack 0
    plt.close(1)
    fig = plt.figure(2, figsize=(5, 3.5))
    plt.clf()
    plt.axhline(y=130, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=120, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=110, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=100, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=90, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=80, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=66, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=50, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=33, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.axhline(y=25, color="k", linestyle='--', lw=0.75, alpha=0.5)
    plt.bar(np.arange(I_shape[0]), 100 * intensity_means / intensity_means[0], zorder=3)
    max_y_val = np.max(100 *intensity_means / intensity_means[0])
    if np.isnan(max_y_val) or np.isinf(max_y_val):
        max_y_val = 100
    plt.ylim(0, max_y_val+5)
    plt.xlim(-0.5, I_shape[0]-0.5)
    plt.xticks(np.arange(I_shape[0]), labels=[f"$t_{i}$" for i in range(I_shape[0])])
    plt.yticks(np.arange(0,max_y_val+5, 10))
    plt.xlabel("stack")
    plt.ylabel("normalized brightness [%]")
    title = f"Average cell brightness relative to $t_0$"
    plot_title = f"Normalized average brightness drop rel. to t0"
    plt.title(title)
    # turn off right and top axis:
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    # set fontsize to 14 for the current figure:
    plt.setp(plt.gca().get_xticklabels(), fontsize=14)
    plt.setp(plt.gca().get_yticklabels(), fontsize=14)
    plt.gca().title.set_fontsize(14)
    plt.gca().xaxis.label.set_fontsize(14)
    plt.gca().yaxis.label.set_fontsize(14)
    plt.tight_layout()
    plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
    plt.close(fig)

    
    df_out = pd.DataFrame(data=intensity_means,
                 columns=["Normalized (btw. 0 and 1) average brightness of each stack"])
    df_out["t_i"] = np.arange(I_shape[0])
    # move ["t_i"] to the first column:
    cols = df_out.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df_out = df_out[cols]
    df_out.to_excel(os.path.join(plot_path,"Normalized average brightness of each stack.xlsx"))

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="brightness comparison ")
    return intensity_means

def reg_2D_images(MG_pro, I_shape, log, histogram_ref_stack, max_xy_shift_correction=50,
                  median_filter_projections=None, median_filter_window_projections=3,
                  usepystackreg=False):
    """
    Registers 2D z-projection images using phase cross-correlation or pystackreg.

    Parameters:
    -----------
    MG_pro : array-like
        The projected image stack.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.
    histogram_ref_stack : int
        Index of the reference stack for registration.
    max_xy_shift_correction : int, optional
        Maximum allowed XY shift during registration (default is 50 pixels).
    median_filter_projections : str or None, optional
        Type of median filtering applied to projections before registration.
        Options: "circular", "square", or None (default).
    median_filter_window_projections : int, optional
        Window size for median filtering (default is 3).
    usepystackreg : bool, optional
        If True, uses pystackreg (StackReg) for registration instead of phase cross-correlation.

    Returns:
    --------
    MG_pro_bin_reg_clipped : ndarray
        The registered and cropped image stack.
    I_shape_create : tuple
        New shape of the registered stack after cropping.

    Notes:
    ------
    - Uses phase cross-correlation or pystackreg for image alignment.
    - Applies median filtering if not previously performed to enhance registration accuracy.
    - Limits shifts to a defined maximum correction range.
    - Clips image borders to remove misaligned zero-padding regions.
    - Logs execution time for performance tracking.
    """
    Process_t0 = time.time()
    log.log(f"registering z-projection (allowed max. xy-shifts:{max_xy_shift_correction})...")

    MG_pro_bin_reg = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]))
    all_shifts_xy = np.zeros((I_shape[0], 2))
    
    # if median_filter_projections is False, no median-filtering is applied on the projections,
    # thus we need to do this here to improve the registration:
    if not median_filter_projections:
        print(f"  2Dreg: detected, that no median-filtering was applied on the projections")
        print(f"  2Dreg: median-filtering is applied to improve the registration (only for the registration)...")
        MG_pro_medianfiltered = median_filtering_on_projections(MG_pro, I_shape, 3, log)
    elif median_filter_projections=="circular" and median_filter_window_projections<1:
        print(f"  2Dreg: detected, that circular median-filtering was applied on the projections, but with a window < 1")
        print(f"  2Dreg: median-filtering is applied to improve the registration (only for the registration)...")
        MG_pro_medianfiltered = median_filtering_on_projections(MG_pro, I_shape, 3, log)
    elif median_filter_projections=="square" and median_filter_window_projections<=1:
        print(f"  2Dreg: detected, that squared median-filtering was applied on the projections, but with a window <0 1")
        print(f"  2Dreg: median-filtering is applied to improve the registration (only for the registration)...")
        MG_pro_medianfiltered = median_filtering_on_projections(MG_pro, I_shape, 3, log)
    else:
        MG_pro_medianfiltered = MG_pro.copy()
    
    if usepystackreg:
        sr = StackReg(StackReg.TRANSLATION)
        ref = MG_pro_medianfiltered[histogram_ref_stack]
    for stack in range(I_shape[0]):
        # stack=0
        if not usepystackreg:
            # use phase cross-correlation to find the shifts:
            shifts, _, _ = phase_cross_correlation(reference_image=MG_pro_medianfiltered[histogram_ref_stack],
                                            moving_image=MG_pro_medianfiltered[stack],
                                            upsample_factor=30)
            # check if the shifts are within the allowed range:
            if shifts[0] > max_xy_shift_correction:
                shifts[0] = max_xy_shift_correction
            elif shifts[0] < -max_xy_shift_correction:
                shifts[0] = -max_xy_shift_correction
            if shifts[1] > max_xy_shift_correction:
                shifts[1] = max_xy_shift_correction
            elif shifts[1] < -max_xy_shift_correction:
                shifts[1] = -max_xy_shift_correction
            all_shifts_xy[stack, :] = shifts
                    
            # apply the shift to the current slice:
            MG_pro_bin_reg[stack, :, :] = transform.warp(MG_pro_medianfiltered[stack],
                                                        transform.SimilarityTransform(translation=shifts),
                                                        preserve_range=True)
            
            log.log(f"   phase cross-correlation: registered stack {stack} with shifts {all_shifts_xy[stack, :]}")
        else:
            # use pystackreg to find the shifts (eg reg = StackReg(StackReg.TRANSLATION).register_transform(ref,mov)):
            mov = MG_pro_medianfiltered[stack]
            
            reg = sr.register(ref,mov)
            tmat = sr.get_matrix()
            all_shifts_xy[stack, :] = tmat[:2, 2]  # dx, dy
            reg = sr.transform(mov, tmat)
            reg = reg.clip(min=0)
            
            MG_pro_bin_reg[stack, :, :] = reg.clip(min=0) # store zero clipped registered 2D image
            
            log.log(f"   pystackreg: registered stack {stack} with shifts {all_shifts_xy[stack, :]}")

    # zero-edge-clipping:
    clip_r = np.ceil(all_shifts_xy[:,0].max()).astype("int")
    clip_l = np.floor(all_shifts_xy[:,0].min()).astype("int")
    clip_t = np.ceil(all_shifts_xy[:,1].max()).astype("int")
    clip_b = np.floor(all_shifts_xy[:,1].min()).astype("int")
    if clip_r<0: clip_r=0
    if clip_l>0: clip_l=0
    if clip_t<0: clip_t=0
    if clip_b>0: clip_b=0
    I_shape_create = (I_shape[0], 
                      int(I_shape[-2] - (np.abs(clip_r) + np.abs(clip_l))),
                      int(I_shape[-1] - (np.abs(clip_t) + np.abs(clip_b))))
    MG_pro_bin_reg_clipped = MG_pro_bin_reg[:, clip_r:I_shape[-2] + clip_l,
                                               clip_t:I_shape[-1] + clip_b].copy()
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="registration ")
    return MG_pro_bin_reg_clipped, I_shape_create

def binarize_2D_images(MG_pro, I_shape, log, plot_path, threshold_method="otsu",
                       compare_all_threshold_methods=True, gaussian_sigma_proj=1):
    """
    Binarizes 2D z-projection images using various thresholding methods.

    Parameters:
    -----------
    MG_pro : array-like
        The projected image stack.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        Path to save threshold comparison plots.
    threshold_method : str, optional
        The thresholding method to use. Options include:
        "isodata", "otsu", "li", "mean", "minimum", "triangle", "yen", or "auto" (default is "otsu").
    compare_all_threshold_methods : bool, optional
        If True, generates plots comparing all thresholding methods (default is True).
    gaussian_sigma_proj : float, optional
        Standard deviation for Gaussian blurring applied before thresholding (default is 1).

    Returns:
    --------
    MG_pro_bin : ndarray
        The binarized image stack.

    Notes:
    ------
    - Applies Gaussian blur before thresholding if `gaussian_sigma_proj` > 0.
    - Supports multiple thresholding methods and can auto-select the best based on Pearson correlation.
    - Saves comparison plots if `compare_all_threshold_methods` is enabled.
    - Logs execution time and selected thresholding method for each stack.
    """
    Process_t0 = time.time()
    log.log(f"binarizing z-projections...")
    log.log(f"  threshold method '{threshold_method}' chosen...")

    MG_pro_bin = np.zeros((I_shape[0], MG_pro[0].shape[0], MG_pro[0].shape[1]))

    # binarizing z-projections:
    for stack in range(I_shape[0]):
        MG_pro_curr = MG_pro[stack].copy()
        if gaussian_sigma_proj>0:
            MG_pro_curr = filter.gaussian(MG_pro_curr, sigma=gaussian_sigma_proj)
        if (compare_all_threshold_methods or threshold_method == "auto") or \
           (compare_all_threshold_methods and threshold_method == "auto"):
            thresh_li  = filter.threshold_li(MG_pro_curr)
            thresh_iso = filter.threshold_isodata(MG_pro_curr)
            thresh_otsu= filter.threshold_otsu(MG_pro_curr)
            thresh_mean= filter.threshold_mean(MG_pro_curr)
            try:
                thresh_min = filter.threshold_minimum(MG_pro_curr)
            except:
                thresh_min = np.array([0])
            thresh_tri = filter.threshold_triangle(MG_pro_curr)
            thresh_yen = filter.threshold_yen(MG_pro_curr)

            #if threshold_method == "auto":
            if thresh_li>0:
                thresh_li_R  = sp.stats.pearsonr((MG_pro_curr > thresh_li).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_li_R=np.array([0.0])[0]
            if thresh_iso>0:
                thresh_iso_R = sp.stats.pearsonr((MG_pro_curr > thresh_iso).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_iso_R=np.array([0.0])[0]
            if thresh_otsu>0:
                thresh_otsu_R= sp.stats.pearsonr((MG_pro_curr > thresh_otsu).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_otsu_R=np.array([0.0])[0]
            if thresh_mean>0:
                thresh_mean_R= sp.stats.pearsonr((MG_pro_curr > thresh_mean).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_mean_R=np.array([0.0])[0]
            if thresh_min>0:
                thresh_min_R = sp.stats.pearsonr((MG_pro_curr > thresh_min).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_min_R=np.array([0.0])[0]
            if thresh_tri>0:
                thresh_tri_R = sp.stats.pearsonr((MG_pro_curr > thresh_tri).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_tri_R=np.array([0.0])[0]
            if thresh_yen>0:
                thresh_yen_R = sp.stats.pearsonr((MG_pro_curr > thresh_yen).flatten(), MG_pro[stack].flatten())[0]
            else:
                thresh_yen_R=np.array([0.0])[0]

        if compare_all_threshold_methods:
            fig = plt.figure(3)
            plt.close()
            fig, ax = plt.subplots(4, 2, num=3, clear=True, figsize=(6, 9))

            ax[0,0].imshow(MG_pro[stack], cmap=plt.get_cmap('gist_gray'))
            ax[0,0].set_title("original")
            ax[0,0].xaxis.set_visible(False)
            ax[0,0].yaxis.set_visible(False)

            cmap_binary = plt.get_cmap('Greys') # bone Greys gist_gray

            ax[0,1].imshow(MG_pro_curr > thresh_li, cmap=cmap_binary)
            ax[0,1].set_title(f"li, $r$={thresh_li_R.round(2)}")
            ax[0,1].xaxis.set_visible(False)
            ax[0,1].yaxis.set_visible(False)

            ax[1,0].imshow(MG_pro_curr > thresh_otsu, cmap=cmap_binary)
            ax[1,0].set_title(f"otsu, $r$={thresh_otsu_R.round(2)}")
            ax[1,0].xaxis.set_visible(False)
            ax[1,0].yaxis.set_visible(False)

            ax[1,1].imshow(MG_pro_curr > thresh_iso, cmap=cmap_binary)
            ax[1,1].set_title(f"isodata, $r$={thresh_iso_R.round(2)}")
            ax[1,1].xaxis.set_visible(False)
            ax[1,1].yaxis.set_visible(False)

            ax[2,0].imshow(MG_pro_curr > thresh_mean, cmap=cmap_binary)
            ax[2,0].set_title(f"mean, $r$={thresh_mean_R.round(2)}")
            ax[2,0].xaxis.set_visible(False)
            ax[2,0].yaxis.set_visible(False)

            ax[2,1].imshow(MG_pro_curr > thresh_min, cmap=cmap_binary)
            ax[2,1].set_title(f"minimum, $r$={thresh_min_R.round(2)}")
            ax[2,1].xaxis.set_visible(False)
            ax[2,1].yaxis.set_visible(False)

            ax[3,0].imshow(MG_pro_curr > thresh_tri, cmap=cmap_binary)
            ax[3,0].set_title(f"triangle, $r$={thresh_tri_R.round(2)}")
            ax[3,0].xaxis.set_visible(False)
            ax[3,0].yaxis.set_visible(False)

            ax[3,1].imshow(MG_pro_curr > thresh_yen, cmap=cmap_binary)
            ax[3,1].set_title(f"yen, $r$={thresh_yen_R.round(2)}")
            ax[3,1].xaxis.set_visible(False)
            ax[3,1].yaxis.set_visible(False)

            plt.tight_layout()
            fig.savefig(os.path.join(plot_path, "All binarization try-outs, stack " + str(stack) + ".pdf"), dpi=300)
            plt.close(fig)
        
        if threshold_method == "auto":
            R_max = np.max([thresh_li_R, thresh_iso_R, thresh_otsu_R, thresh_mean_R, thresh_min_R, thresh_tri_R, thresh_yen_R])
            if thresh_li_R== R_max:
                threshold_method_choose = "li"
                thresh = thresh_li
            elif thresh_iso_R == R_max:
                threshold_method_choose = "isodata"
                thresh =  thresh_iso
            elif thresh_otsu_R == R_max:
                threshold_method_choose = "otsu"
                thresh = thresh_otsu
            elif thresh_mean_R == R_max:
                threshold_method_choose = "mean"
                thresh = thresh_mean
            elif thresh_min_R == R_max:
                threshold_method_choose = "minium"
                thresh = thresh_min
            elif thresh_tri_R == R_max:
                threshold_method_choose = "triangle"
                thresh = thresh_tri
            else:
                threshold_method_choose = "yen"
                thresh = thresh_yen
            log.log(f"     stack {stack}: auto-detected best thresholding method: {threshold_method_choose}, threshold={thresh}")
        else:
            threshold_method_choose = threshold_method.lower()
            if threshold_method.lower() == "li":
                thresh = filter.threshold_li(MG_pro_curr)
            elif threshold_method.lower() == "isodata" or threshold_method == "iso":
                threshold_method_choose = "isodata"
                thresh = filter.threshold_isodata(MG_pro[stack])
            elif threshold_method.lower() == "otsu":
                thresh = filter.threshold_otsu(MG_pro_curr)
            elif threshold_method.lower() == "mean":
                thresh = filter.threshold_mean(MG_pro_curr)
            elif threshold_method.lower() == "min" or threshold_method == "minimum":
                threshold_method_choose = "minium"
                thresh = filter.threshold_minimum(MG_pro[stack])
            elif threshold_method.lower() == "triangle":
                thresh = filter.threshold_triangle(MG_pro_curr)
            elif threshold_method.lower() == "yen":
                thresh = filter.threshold_yen(MG_pro_curr)
            log.log(f"     stack {stack}: {threshold_method_choose}-threshold={thresh}")
        MG_pro_bin[stack] = MG_pro_curr > thresh

        plot_2D_image(MG_pro_bin[stack], plot_path,
                      plot_title="Binarized projection, stack "+str(stack),
                      show_borders=True,
                      fignum=1, cmap=mcol.ListedColormap(['white', 'black']), cbar_label="binary mask",
                      cbar_ticks=[0.25, 0.75], cbar_ticks_labels=[0, 1],
                      title=f"Binarized projection ({threshold_method_choose}), stack {stack}")
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="binarization ")
    return MG_pro_bin

def remove_small_blobs(MG_pro, I_shape, log, plot_path, pixel_threshold=100, stats_plots=False):
    """
    Removes small microglial regions based on pixel connectivity and area threshold in segmented 2D images.

    Parameters:
    -----------
    MG_pro : array-like
        The binarized projected image stack.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        Path to save the plots and segmentation statistics.
    pixel_threshold : int, optional
        Minimum pixel area required to retain a connected region (default is 100).
    stats_plots : bool, optional
        Whether to generate and save additional statistics plots (default is False).

    Returns:
    --------
    MG_pro_bin_area_thresholded : ndarray
        The binarized image stack after removing small regions.
    MG_pro_bin_area_sum : ndarray
        The total number of pixels retained after thresholding.

    Notes:
    ------
    - Labels and counts connected regions using `skimage.measure.label`.
    - Segments regions that meet the pixel area threshold.
    - Generates and saves plots of connected component areas, histograms, and final segmentations.
    - Saves statistics on segmented pixel areas as an Excel file.
    - Logs the process and reports the number of retained segments.
    """
    Process_t0 = time.time()
    log.log(f"apply connectivity-measurements to exclude too small microglia parts...")

    MG_pro_bin_area_thresholded = np.zeros((I_shape[0], I_shape[-2], I_shape[-1]), dtype="uint16")
    MG_pro_bin_area_sum = np.zeros((I_shape[0]))

    for stack in range(I_shape[0]):

        all_labels, label_nums = measure.label(MG_pro[stack], background=0, connectivity=1,
                                               return_num=True)
        props = measure.regionprops(all_labels)

        props_areas = np.zeros(label_nums)
        for label in range(label_nums):
            props_areas[label] = props[label]["area"]

        # plot found pixel areas:
        if stats_plots:
            fig = plt.figure(27, figsize=(6, 6))
            plt.clf()
            plt.bar(np.arange(label_nums), props_areas)
            plt.hlines(pixel_threshold, 0, label_nums, ls='-', colors="r",
                    label=f"pixel threshold=>{str(pixel_threshold)} pixels")
            ax = plt.gca()
            ax.set_yscale('log')
            plt.xlim(-1, label_nums+1)
            plt.legend()
            plt.xlabel("found regions from the pixel connectivity analysis")
            plt.ylabel("pixels within the region (log-scale)")
            title = f"Binarized projection: regions of contiguous pixels, stack {stack}"
            plot_title = f"Stats Binarized projection, regions of contiguous pixels, stack {stack}"
            plt.title(title)
            plt.tight_layout()
            #plt.show()
            plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
            plt.close(fig)

            fig = plt.figure(28, figsize=(7, 5))
            plt.clf()
            hist_vals, _, _ = plt.hist(props_areas, bins=200)
            plt.vlines(pixel_threshold, 0, hist_vals.max(), ls='-', colors="r",
                    label=f"pixel threshold=>{str(pixel_threshold)} pixels")
            ax = plt.gca()
            ax.set_yscale('log')
            plt.legend()
            plt.xlabel("pixels within the found regions from the pixel connectivity analysis")
            plt.ylabel("number of regions (log-scale)")
            title = f"Binarized projection: regions of contiguous pixels, stack {stack}"
            plot_title = f"Stats Binarized projection, regions of contiguous pixels (histogram), stack {stack}"
            plt.title(title)
            plt.tight_layout()
            #plt.show()
            plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
            plt.close(fig)

        MG_pro_bin_area_thresholded_tmp = np.zeros((I_shape[-2], I_shape[-1]), dtype="uint16")
        new_label_start = 6 # this is just to increase the contrast in the later 2D color map segmentation image
        new_label = new_label_start
        reject_label = 1
        for label in range(label_nums):
            if props[label]["area"] >= pixel_threshold:
                # print(f'number of pixels in area with label {label} is above threshold {pixel_threshold}.')
                new_label += 1
                coords = np.nonzero(all_labels == label + 1)
                MG_pro_bin_area_thresholded_tmp[coords] = new_label
                len(MG_pro_bin_area_thresholded_tmp.flatten()>0)
            else:
                coords = np.nonzero(all_labels == label + 1)
                MG_pro_bin_area_thresholded_tmp[coords] = reject_label
        print(f"  stack {stack} - number of new labels: {new_label - (new_label_start + 1)}")

        if new_label/5.0==5.0:
            new_label_cbar = new_label+1
        else:
            new_label_cbar = new_label
        cbar_ticks_labels = np.append(np.array([0.5, 1.5]), np.arange(new_label_start, new_label_cbar, 5)).tolist()
        cbar_ticks=np.append(np.array([0.5, 1.5]), np.arange(new_label_start, new_label_cbar, 5))
        cbar_ticks_labels[0] = "bg"
        cbar_ticks_labels[1] = "reject"
        plot_2D_image(MG_pro_bin_area_thresholded_tmp, plot_path,
                  plot_title="Binarized segmented projection, labels, stack " + str(stack), fignum=1,
                  figsize=(6, 5), show_borders=True, cbar_show=True,
                  #cmap=plt.cm.get_cmap('nipy_spectral', new_label + 1), 
                  cmap = plt.get_cmap('nipy_spectral', lut=new_label + 1),
                  cbar_label="labels",
                  cbar_ticks=cbar_ticks,
                  cbar_ticks_labels=cbar_ticks_labels,
                  title=f"Binarized projection segmented, labels, stack {stack}")

        # re-binarize and plot the processed image:
        MG_pro_bin_area_thresholded[stack, ...] = MG_pro_bin_area_thresholded_tmp > reject_label
        plot_2D_image(MG_pro_bin_area_thresholded[stack], plot_path,
                      plot_title=f"Binarized final segmented projection, stack " + str(stack) + " mask",
                      fignum=1, show_borders=True,
                      cmap=mcol.ListedColormap(['white','black']), cbar_label="binary mask",
                      cbar_ticks=[0.25, 0.75], cbar_ticks_labels=[0, 1],
                      title=f"Binarized projection segmented, stack {stack}")

        # plot and save the segmented pixel areas above pixel_threshold:
        MG_pro_bin_area_sum[stack] = int(props_areas[props_areas > pixel_threshold].sum())
        if stats_plots:
            fig = plt.figure(29, figsize=(6, 4))
            plt.clf()
            final_labels = np.arange(props_areas[props_areas>pixel_threshold].shape[0])
            final_label_nums = len(final_labels)
            plt.bar(final_labels, props_areas[props_areas>pixel_threshold])
            ax = plt.gca()
            ax.set_yscale('log')
            try:
                annotation_y = props_areas[props_areas>pixel_threshold].max()
            except:
                annotation_y = 1
            plt.text(0, annotation_y,
                    f"segmented {int(props_areas[props_areas>pixel_threshold].sum())} pixels of total FOV "
                    f"{int(MG_pro_bin_area_thresholded[stack].shape[0]*MG_pro_bin_area_thresholded[stack].shape[1])} pixels"
                    f"={(100*props_areas[props_areas > pixel_threshold].sum()/(MG_pro_bin_area_thresholded[stack].shape[0]*MG_pro_bin_area_thresholded[stack].shape[1])).round(2)}%",
                    verticalalignment='top')
            plt.xlim(-1, final_label_nums + 1)
            plt.xlabel(f"found regions with pixel-area>{pixel_threshold}")
            plt.ylabel("pixels within the region (log-scale)")
            title = f"Binarized projection: pixels within thresholded regions, stack {stack}"
            plot_title = f"Stats Binarized segmented projection, pixels within thresholded regions, stack {stack}"
            plt.title(title)
            plt.tight_layout()
            plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
            plt.close(fig)
        
        # save thresholded pixel-areas:
        pixel_areas_df = pd.DataFrame(props_areas[props_areas > pixel_threshold], columns=["pixels per segment"])
        pixel_areas_df["sum of segmented pixels"] = pixel_areas_df["pixels per segment"].sum()
        pixel_areas_df["sum of all FOV pixels"] = MG_pro_bin_area_thresholded[stack].shape[0]*MG_pro_bin_area_thresholded[stack].shape[1]
        pixel_areas_df.to_excel(os.path.join(plot_path, f"pixel areas of segmented projection, stack {stack}.xlsx"))

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="connectivity measurement ")
    return MG_pro_bin_area_thresholded, MG_pro_bin_area_sum

def plot_pixel_areas(MG_areas, log, plot_path, I_shape):
    """
    Plots and saves the detected pixel areas per projected stack.

    Parameters:
    -----------
    MG_areas : array-like
        The total segmented pixel area per stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        Path where the plot and Excel file will be saved.
    I_shape : tuple
        Shape of the input image stack.

    Returns:
    --------
    None
        The function saves a bar plot and an Excel file with pixel area statistics.

    Notes:
    ------
    - Normalizes pixel areas relative to stack 0.
    - Saves a bar plot representing relative pixel areas per stack.
    - Outputs an Excel file with absolute and relative pixel areas, including total field-of-view (FOV) area.
    - Logs the process and computation time.
    """
    Process_t0 = time.time()
    log.log(f"plotting detected pixel areas per projected stack...")

    # plot normalized area rel. to stack 0:
    if MG_areas[0] != 0:
        plt.close(1)
        fig = plt.figure(2, figsize=(5, 3.5))
        plt.clf()
        plt.axhline(y=130, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=120, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=110, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=100, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=90, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=80, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=66, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=50, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=33, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.axhline(y=25, color="k", linestyle='--', lw=0.75, alpha=0.5)
        plt.bar(np.arange(I_shape[0]), 100 * MG_areas / MG_areas[0], zorder=3)
        # check if there are any values to calculate max for ylim:
        try:
            ylim_max = np.max([105, np.max(100 * MG_areas / MG_areas[0]) + 5]) 
        except ValueError:
            ylim_max = 100  # set a default value if the max calculation fails (e.g., NaN or Inf)
        # ensure ylim_max is finite (not NaN or Inf):
        if not np.isfinite(ylim_max):
            ylim_max = 100  # set a default value if ylim_max is NaN or Inf
        plt.ylim(0, ylim_max)
        plt.xlim(-0.5, I_shape[0]-0.5)
        #plt.xticks(np.arange(I_shape[0]))
        plt.xticks(np.arange(I_shape[0]), labels=[f"$t_{i}$" for i in range(I_shape[0])])
        plt.yticks(np.arange(0,101, 10))
        plt.xlabel("stack")
        plt.ylabel("relative total cell pixels [%]")
        title = f"Cell areas relative to $t_0$"
        plot_title = f"Normalized cell area rel. to t0"
        plt.title(title)
        # turn off right and top axis:
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['bottom'].set_visible(False)
        plt.gca().spines['left'].set_visible(False)
        # set fontsize to 14 for the current figure:
        plt.setp(plt.gca().get_xticklabels(), fontsize=14)
        plt.setp(plt.gca().get_yticklabels(), fontsize=14)
        plt.gca().title.set_fontsize(14)
        plt.gca().xaxis.label.set_fontsize(14)
        plt.gca().yaxis.label.set_fontsize(14)
        plt.tight_layout()
        plt.savefig(Path(plot_path, plot_title + ".pdf"), dpi=120)
        plt.close(fig)
    
        # save the data for later use:
        data_out = np.array([100 * MG_areas / MG_areas[0], MG_areas])
        df_out = pd.DataFrame(data=data_out.T,
                    columns=["cell area in pixel rel to stack 0", "cell area in pixel total"])
        df_out["total fov area in pixel"] = I_shape[-2]*I_shape[-1]
        df_out["t_i"] = np.arange(I_shape[0])
        # move ["t_i"] to the first column:
        cols = df_out.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df_out = df_out[cols]
        df_out.to_excel(os.path.join(plot_path,"pixel area sums.xlsx"))
        
    else:
        log.log("Warning: MG_areas[0] is zero, skipping relative area plot to avoid division by zero.")

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="pixel cell area plotting ")

def motility(MG_pro, I_shape, log, plot_path, ID="ID00000", group="blinded"):
    """
    Computes and visualizes microglial motility by analyzing changes in segmented pixel regions over time.
    
    Microglial fine processes are tracked by comparing segmented pixels between consecutive time points.
    The analysis includes stable, gain, and loss percentages of pixels between stacks.
    
    Microglial fine processes turn-over is calculated as the ratio of gained and lost pixels to the total 
    number of stable, gained, and lost pixels as it is common in the literature (e.g., Nebeling et al., 2023).

    Parameters:
    -----------
    MG_pro : array-like
        The binarized projected image stacks.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        Path where the plots and output data will be saved.
    ID : str, optional
        Identifier for the dataset (default is "ID00000").
    group : str, optional
        Experimental group (default is "blinded").

    Returns:
    --------
    MG_pro_delta_t : array-like
        The computed difference images representing changes between consecutive stacks.
    summary_df : pandas.DataFrame
        Dataframe summarizing motility metrics, including stable, gain, and loss percentages.

    Notes:
    ------
    - Computes changes in segmented pixels between consecutive time points.
    - Visualizes differences in motility with colormap images and histograms.
    - Saves computed motility differences as a multi-frame TIFF file.
    - Outputs an Excel file summarizing motility metrics.
    - Logs the process and computation time.
    """
    Process_t0 = time.time()
    log.log(f"motility analysis...")

    MG_pro_delta_t = np.zeros((I_shape[0] - 1, I_shape[-2], I_shape[-1]), dtype="int16")

    # prepare output-dataframe:
    summary_df = pd.DataFrame(index=range(0,I_shape[0] - 1),
                              columns=['delta t', 'ID', 'group',
                                       'Stable', 'Gain', 'Loss',
                                       'rel Stable', 'rel Gain', 'rel Loss'],
                              dtype='float')

    # calculate the delta t between the stacks:
    for stack in np.arange(1, I_shape[0]):
        MG_pro_delta_t[stack - 1] = MG_pro[stack - 1] * 2 - MG_pro[stack]

    # find the maximum hist value for the ylim:
    hist_0123_max = 0
    hist_023_max  = 0
    for stack in range(MG_pro_delta_t.shape[0]):
        hist, _ = np.histogram(MG_pro_delta_t[stack].flatten(), bins=4)
        hist_0123_max = np.max([hist_0123_max, hist[0], hist[1], hist[2], hist[3]])
        hist_023_max  = np.max([hist_023_max, hist[0], hist[2], hist[3]])
    hist_0123_max = hist_0123_max + 10
    hist_023_max  = hist_023_max + 10

    # plot the delta t images and histograms of stable, gain, and loss pixels:
    for stack in range(MG_pro_delta_t.shape[0]):
        hist, bins = np.histogram(MG_pro_delta_t[stack].flatten(), bins=4)
        summe = hist[0] + hist[2] + hist[3]

        plot_2D_image(MG_pro_delta_t[stack], plot_path, figsize=(6, 5),
                      plot_title=f"MG delta t_{stack} - t_{stack + 1}",
                      fignum=1, cbar_show=True, show_borders=True,
                      cmap=mcol.ListedColormap(['lime', 'white', 'blue', 'red']), cbar_label="",
                      cbar_ticks=[-0.5, 0.10, 0.85, 1.6],
                      cbar_ticks_labels=["-1 (G)", "0", "1 (S)", " 2 (L)"],
                      title=f"t_{stack} - t_{stack + 1}")


        fig = plt.figure(20, figsize=(3.5, 3.5))
        plt.clf()
        plt.bar(bins[0] + 0.75 / 2, hist[0], width=0.65, color="lime")
        plt.bar(bins[1] + 0.75 / 2, hist[1], width=0.65, color="black")
        plt.bar(bins[2] + 0.75 / 2, hist[2], width=0.65, color="blue")
        plt.bar(bins[3] + 0.75 / 2, hist[3], width=0.65, color="red")
        plt.xticks(bins[:-1] + 0.75 / 2, labels=["-1 (G)", "0", "1 (S)", "2 (L)"])
        plt.ylabel("absolute number of pixels w/ bg")
        title = f"$t_{stack}-t_{stack + 1}$"
        plot_title = f"pixel counts abs. w bg t_{stack}-t_{stack + 1}"
        plt.title(title)
        # turn-off right and top border (only for this plot):
        ax = plt.gca()
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        # set fontsize to 14 for the current figure:
        plt.setp(ax.get_xticklabels(), fontsize=14)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        ax.title.set_fontsize(14)
        ax.xaxis.label.set_fontsize(14)
        ax.yaxis.label.set_fontsize(14)
        plt.ylim(0, hist_0123_max)
        plt.tight_layout()
        plt.savefig(Path(plot_path, plot_title.replace("$", "").replace("_", "").replace(".", "") + ".pdf"))
        plt.close(fig)

        fig = plt.figure(22, figsize=(3.5, 3.5))
        plt.clf()
        plt.bar(bins[0] + 0.75 / 2, hist[0], width=0.65, color="lime")
        plt.bar(bins[1] + 0.75 / 2, hist[2], width=0.65, color="blue")
        plt.bar(bins[2] + 0.75 / 2, hist[3], width=0.65, color="red")
        plt.xticks(bins[:-2] + 0.75 / 2, labels=["-1 (G)", "1 (S)", "2 (L)"])
        plt.ylabel("absolute number of pixels")
        """ plt.text(bins[0] , np.max([hist[0], hist[2], hist[3]])-10, 
                 r"tor=$\frac{G+L}{S+G+L}=$"+str(round((hist[0]+hist[3])/(hist[0]+hist[2]+hist[3]),2)), 
                 ha="left", va="top", color="k") """
        title = f"$t_{stack}-t_{stack + 1}$"
        plot_title = f"pixel counts abs. t_{stack}-t_{stack + 1}"
        plt.title(title)
        # turn-off right and top border (only for this plot):
        ax = plt.gca()
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        # set fontsize to 14 for the current figure:
        plt.setp(ax.get_xticklabels(), fontsize=14)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        ax.title.set_fontsize(14)
        ax.xaxis.label.set_fontsize(14)
        ax.yaxis.label.set_fontsize(14)
        plt.ylim(0, hist_023_max)
        plt.tight_layout()
        plt.savefig(Path(plot_path, plot_title.replace("$", "").replace("_", "").replace(".", "") + ".pdf"))
        plt.close(fig)

        fig = plt.figure(23, figsize=(3.1, 3.5))
        plt.clf()
        plt.bar(bins[0] + 0.75 / 2, hist[0] / summe, width=0.65, color="lime")
        plt.bar(bins[1] + 0.75 / 2, hist[2] / summe, width=0.65, color="blue")
        plt.bar(bins[2] + 0.75 / 2, hist[3] / summe, width=0.65, color="red")
        plt.text(bins[1]+ 0.75 / 2 , 0.96, 
                 r"tor=$\frac{G+L}{S+G+L}=$"+str(round((hist[0]+hist[3])/(hist[0]+hist[2]+hist[3]),2)), 
                 ha="center", va="top", color="k")
        plt.xticks(bins[:-2] + 0.75 / 2, labels=["-1 (G)", "1 (S)", "2 (L)"])
        plt.ylabel("relative number of pixels")
        plt.ylim(0, 1.0)
        title = f"$t_{stack}-t_{stack + 1}$"
        plot_title = f"pixel counts relative t_{stack}-t_{stack + 1}"
        plt.title(title)
        # turn-off right and top border (only for this plot):
        ax = plt.gca()
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        # set fontsize to 14 for the current figure:
        plt.setp(ax.get_xticklabels(), fontsize=14)
        plt.setp(ax.get_yticklabels(), fontsize=14)
        ax.title.set_fontsize(14)
        ax.xaxis.label.set_fontsize(14)
        ax.yaxis.label.set_fontsize(14)
        plt.tight_layout()
        plt.savefig(Path(plot_path, plot_title.replace("$", "").replace("_", "") + ".pdf"))
        plt.close(fig)
        
        # before assigning values, explicitly cast the columns to string dtype to account pandas future behavior:
        summary_df['ID'] = summary_df['ID'].astype(str)
        summary_df['group'] = summary_df['group'].astype(str)
        summary_df['delta t'] = summary_df['delta t'].astype(str)

        summary_df.loc[stack, "ID"] = ID
        summary_df.loc[stack, "group"] = group
        summary_df.loc[stack, "Stable"] = hist[2]
        summary_df.loc[stack, "Gain"] = hist[0]
        summary_df.loc[stack, "Loss"] = hist[3]
        summary_df.loc[stack, "delta t"] = f"t_{stack}-t_{stack + 1}"
        summary_df.loc[stack, "rel Stable"] = hist[2]/summe
        summary_df.loc[stack, "rel Gain"] = hist[0]/summe
        summary_df.loc[stack, "rel Loss"] = hist[3]/summe
        summary_df.loc[stack, "tor"] = (hist[0]+hist[3])/(hist[0]+hist[3]+hist[2])

    TIFF_path = os.path.join(plot_path, f"MG delta t_i - t_i+1"+".tif")
    tifffile.imwrite(TIFF_path, MG_pro_delta_t, 
                        resolution=(MG_pro_delta_t[0].shape[-2], MG_pro_delta_t[0].shape[-1]),
                        metadata={'spacing': 1, 'unit': 'um', 'axes': 'ZYX'},
                        imagej=True, bigtiff=False)

    summary_df.to_excel(Path(plot_path,"motility_analysis.xlsx"))
    log.log(f"motility evaluation saved in {Path(plot_path,'motility_analysis.xlsx')}")

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="motility ")
    return MG_pro_delta_t, summary_df

# %% MAIN PIPELINE FUNCTIONS

def process_stack(fname, MG_channel, N_channel, two_channel, projection_center, projection_layers,
                  histogram_ref_stack, log, blob_pixel_threshold=100, 
                  regStack2d=True, regStack3d=False, template_mode="mean",
                  usepystackreg=False,
                  spectral_unmixing=True, hist_equalization=False, hist_match=True, 
                  hist_equalization_kernel_size=None, hist_equalization_clip_limit=0.05,
                  RESULTS_Path="motility_analysis",
                  ID="ID00000", group="blinded", max_xy_shift_correction=50,
                  threshold_method="li", compare_all_threshold_methods=True,
                  gaussian_sigma_proj=1, spectral_unmixing_amplifyer=1,
                  median_filter_slices = "square", median_filter_window_slices=3,
                  median_filter_projections = "square", median_filter_window_projections=3, 
                  clear_previous_results=False, spectral_unmixing_median_filter_window=3,
                  debug_output=False, stats_plots=False):
    """
    Processes a 4D/5D image stack to analyze microglial motility (MAIN MotiLA pipeline).

    Parameters:
    -----------
    fname : str or Path
        Path to the input TIFF file.
    MG_channel : int
        Index of the microglia fluorescence channel.
    N_channel : int
        Index of the neuron fluorescence channel.
    two_channel : bool
        Whether the dataset includes two channels.
    projection_center : int
        Center slice for z-projection.
    projection_layers : int
        Number of layers to include in the z-projection.
    histogram_ref_stack : int
        Stack index to use as reference for histogram matching.
    log : logger_object
        Logger for recording processing steps.
    blob_pixel_threshold : int
        Minimum pixel area for segmented objects.
    regStack2d : bool
        Whether to perform 2D registration on z-projections.
    regStack3d : bool
        Whether to perform 3D intra-stack registration.
    usepystackreg : bool, optional
        If True, use pystackreg (StackReg) for 2D registration instead of phase cross-correlation.
    template_mode : str
        Template calculation method for 3D registration.
    spectral_unmixing : bool
        Whether to perform spectral unmixing.
    hist_equalization : bool
        Whether to apply histogram equalization.
    hist_equalization_clip_limit : float
        Clip limit for histogram equalization.
    hist_equalization_kernel_size : None or tuple of int
        Kernel size for histogram equalization.
    hist_match : bool
        Whether to perform histogram matching across stacks.
    RESULTS_Path : str or Path
        Directory for saving results.
    ID : str
        Identifier for the dataset.
    group : str
        Experimental group label.
    max_xy_shift_correction : int
        Maximum allowed xy-shift in registration.
    threshold_method : str
        Method for binarization.
    compare_all_threshold_methods : bool
        Whether to compare multiple thresholding methods.
    gaussian_sigma_proj : float
        Sigma value for Gaussian filtering before binarization.
    spectral_unmixing_amplifyer : int
        Amplification factor for spectral unmixing.
    median_filter_slices : str
        Type of median filtering applied to individual slices ("square" or "circular").
    median_filter_window_slices : int
        Size of the median filter applied to individual slices.
    median_filter_projections : str
        Type of median filtering applied to z-projections ("square" or "circular").
    median_filter_window_projections : int
        Size of the median filter applied to z-projections.
    clear_previous_results : bool
        Whether to clear the results directory before processing.
    spectral_unmixing_median_filter_window : int
        Window size for median filtering in spectral unmixing.
    debug_output : bool
        Whether to enable debug output for memory usage and processing steps.
    stats_plots : bool
        Whether to generate additional statistics plots.

    Returns:
    --------
    None
        The function processes the image stack and saves various output files.

    Notes:
    ------
    - Loads and processes microglia fluorescence images for motility analysis.
    - Supports optional 3D and 2D registration.
    - 2D registration can use either phase cross-correlation or pystackreg (StackReg) if `usepystackreg` is True.
    - Includes histogram-based contrast adjustments and thresholding.
    - Computes motility metrics such as gain, loss, and stability.
    - Saves processed images, projections, and statistical results in a designated output directory.
    - Deletes intermediate large datasets to optimize memory usage.
    """
    Total_Process_t0 = time.time()
    log.log(f"Processing file {fname}...")
    if debug_output: print_ram_usage()
    
    plot_path = RESULTS_Path # Path(fname).parent.parent.joinpath(RESULTS_Path+"/")
    check_folder_exist_create(plot_path)
    # check whether folder is not empty; if not, delete all files in it:
    if len(os.listdir(plot_path)) != 0 and clear_previous_results:
        log.log(f"Info: Folder {plot_path} is not empty, deleting all files in it.")
        for file in os.listdir(plot_path):
            if file.startswith("._"):  # Skip macOS metadata files
                continue
            file_path = os.path.join(plot_path, file)
            try:
                os.remove(file_path)
            except FileNotFoundError:
                print(f"Warning: File {file_path} not found, skipping.")
            
            #os.remove(os.path.join(plot_path, file))
    
    # if fname is a zarr file, the I_shape is not known yet:
    if isinstance(fname, str):
        fname = Path(fname)  # convert string to Path if it's a string
    if fname.suffix == ".tif":
        I_shape = get_stack_dimensions(fname)
    else:
        log.log(f"Error: File {fname} is not a .tif file!")
        raise ValueError(f"Error: File {fname} is not a .tif file!")
 
    # calculate and verify projection layers:
    projection_range, projection_layers = calc_projection_range(projection_center, projection_layers, I_shape, log)
    # check whether we got a valid projection range returned:
    if projection_layers == 0:
        log.log(f"Projection center {projection_center} resulted in zero projection layers -> file {fname} will be skipped.")
        return  # skip processing this file

    # save all parameters used in this analysis into an excel file:
    excel_file_name = '_processing_parameters.xlsx'
    excel_file_path = os.path.join(plot_path, excel_file_name)
    processing_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    parameters = {
        "fname": fname,
        "processing date": processing_date,
        "ID": ID,
        "group": group,
        "shape": I_shape,
        "MG_channel": MG_channel,
        "N_channel": N_channel,
        "two_channel": two_channel,
        "spectral_unmixing": spectral_unmixing,
        "threshold_method": threshold_method,
        "projection_layers": projection_layers,
        "projection_range": projection_range,
        "median_filter_slices": median_filter_slices,
        "median_filter_window_slices": median_filter_window_slices,
        "median_filter_projections": median_filter_projections,
        "median_filter_window_projections": median_filter_window_projections,
        "gaussian_sigma_proj": gaussian_sigma_proj,
        "regStack2d": regStack2d,
        "regStack3d": regStack3d,
        "max_xy_shift_correction": max_xy_shift_correction,
        "histogram_equalization": hist_equalization,
        "hist_equalization_clip_limit": hist_equalization_clip_limit,
        "hist_equalization_kernel_size": hist_equalization_kernel_size,
        "hist_match": hist_match,
        "histogram_ref_stack": histogram_ref_stack,
        "spectral_unmixing_amplifyer": spectral_unmixing_amplifyer,
        "blob_pixel_threshold": blob_pixel_threshold,
        "stats_plots": stats_plots}
    parameters_list = [{"Parameter": key, "Value": value} for key, value in parameters.items()]
    processing_parameters_df = pd.DataFrame(data=parameters_list)
    processing_parameters_df.to_excel(excel_file_path, index=False)
        

    # extract sub-volume with optional intra-sub-stack registration:
    if regStack3d:
        if two_channel:
            MG_sub, N_sub, I_shape_new, Z = extract_and_register_subvolume(fname, I_shape, 
                                                       projection_layers, projection_range,
                                                       MG_channel=MG_channel, 
                                                       log=log, template_mode=template_mode,
                                                       two_channel=two_channel,
                                                       max_xy_shift_correction=max_xy_shift_correction,
                                                       debug_output=debug_output)
        else:
            MG_sub, I_shape_new, Z = extract_and_register_subvolume(fname, I_shape, 
                                                       projection_layers, projection_range,
                                                       MG_channel=MG_channel, 
                                                       log=log, template_mode=template_mode,
                                                       two_channel=two_channel,
                                                       max_xy_shift_correction=max_xy_shift_correction,
                                                       debug_output=debug_output)
    
        # correct I_shape for the new shape after registration (if any):
        I_shape[-2] = I_shape_new[-2]
        I_shape[-1] = I_shape_new[-1]
    else:
        if two_channel:
            MG_sub, N_sub, Z = extract_subvolume(fname, I_shape=I_shape, projection_layers=projection_layers,
                                       projection_range=projection_range, log=log, two_channel=two_channel,
                                       channel=MG_channel)
        else:
            MG_sub, Z = extract_subvolume(fname, I_shape=I_shape, projection_layers=projection_layers,
                                       projection_range=projection_range, log=log, two_channel=two_channel,
                                       channel=MG_channel)

    # spectral unmixing:        
    if spectral_unmixing:
        if np.array_equal(MG_sub[0], N_sub[0]): #or not np.all(((N_sub[0]) == 0))
            log.log(f"spectral_unmixing is set to {spectral_unmixing}, "
                    f"but the Neuron channel is the same as the Microglia channel --> skipped.")
            # create a dataset with the same shape as MG_sub and copy MG_sub into it:
            subvol_group = Z["subvolumes"]
            if zarr.__version__ >= "3.0.0":
                subvol_group.create_array("MG_sub_processed", shape=MG_sub.shape, dtype=MG_sub.dtype,
                                         chunks=MG_sub.chunks, overwrite=True)
                # ZARR>=3.0 + Jupyter notebook have a compatibility issue regarding async operations, thus
                # we need to use try-except to avoid errors when copying data:
                try:
                    subvol_group["MG_sub_processed"][:] = MG_sub  # copy data into the array
                except:
                    subvol_group["MG_sub_processed"][:] = np.array(MG_sub)
            else:
                subvol_group.create_dataset("MG_sub_processed", data=MG_sub)
            MG_sub_processed = subvol_group["MG_sub_processed"]
        elif np.all(((N_sub[0]) == 0)):
            log.log(f"spectral_unmixing is set to {spectral_unmixing}, "
                    f"but the Neuron channel is zero --> skipped.")
            MG_sub_processed = MG_sub.copy()
            # create a dataset with the same shape as MG_sub and copy MG_sub into it:
            subvol_group = Z["subvolumes"]
            if zarr.__version__ >= "3.0.0":
                subvol_group.create_array("MG_sub_processed", shape=MG_sub.shape, dtype=MG_sub.dtype,
                                         chunks=MG_sub.chunks, overwrite=True)
                # ZARR>=3.0 + Jupyter notebook have a compatibility issue regarding async operations, thus
                # we need to use try-except to avoid errors when copying data:
                try:
                    subvol_group["MG_sub_processed"][:] = MG_sub  # copy data into the array
                except:
                    subvol_group["MG_sub_processed"][:] = np.array(MG_sub)
            else:
                subvol_group.create_dataset("MG_sub_processed", data=MG_sub)
            MG_sub_processed = subvol_group["MG_sub_processed"]
        else:
            MG_sub_processed = spectral_unmix(MG_sub, N_sub, I_shape, Z, projection_layers, log,
                                              median_filter_window=spectral_unmixing_median_filter_window,
                                              amplifyer=spectral_unmixing_amplifyer)
    else:
        # create a dataset with the same shape as MG_sub and copy MG_sub into it:
        subvol_group = Z["subvolumes"]
        if zarr.__version__ >= "3.0":
            subvol_group.create_array("MG_sub_processed", shape=MG_sub.shape, dtype=MG_sub.dtype,
                                     chunks=MG_sub.chunks, overwrite=True)
            # ZARR>=3.0 + Jupyter notebook have a compatibility issue regarding async operations, thus
            # we need to use try-except to avoid errors when copying data:
            try:
                subvol_group["MG_sub_processed"][:] = MG_sub  # copy data into the array
            except:
                subvol_group["MG_sub_processed"][:] = np.array(MG_sub)
        else:
            subvol_group.create_dataset("MG_sub_processed", data=MG_sub, overwrite=True)
        MG_sub_processed = subvol_group["MG_sub_processed"]


    # save a raw version of the z-projected stack:
    MG_projection_raw = z_max_project(MG_sub, I_shape=I_shape, log=log)
    plot_projected_stack(MG_projection_raw, I_shape=I_shape, plot_path=plot_path, log=log, 
                         plottitle="MG projected, proc 0 raw")
    
    # median filter every single slice:
    if median_filter_slices == "circular":
        MG_sub_processed_medfiltered = single_slice_circular_median_filtering(MG_sub_processed, I_shape, Z,
                                            median_filter_window_slices, projection_layers, log)
    elif median_filter_slices == "square":
        MG_sub_processed_medfiltered = single_slice_median_filtering(MG_sub_processed, I_shape, Z,
                                            median_filter_window_slices, projection_layers, log)
    else:
        # create a dataset with the same shape as MG_sub and copy MG_sub into it:
        subvol_group = Z["subvolumes"]
        if zarr.__version__ >= "3.0":
            subvol_group.create_array("MG_sub_processed_medfiltered", 
                                      shape=MG_sub_processed.shape, dtype=MG_sub_processed.dtype,
                                      chunks=MG_sub_processed.chunks, overwrite=True)
            # ZARR>=3.0 + Jupyter notebook have a compatibility issue regarding async operations, thus
            # we need to use try-except to avoid errors when copying data:
            try:
                subvol_group["MG_sub_processed_medfiltered"][:] = MG_sub_processed  # copy data into the array
            except:
                subvol_group["MG_sub_processed_medfiltered"][:] = np.array(MG_sub_processed)
        else:
            subvol_group.create_dataset("MG_sub_processed_medfiltered", data=MG_sub_processed)
        MG_sub_processed_medfiltered = subvol_group["MG_sub_processed_medfiltered"]

    # project and copy so-far processed stacks into MG_projection_pre (for histogram evaluation) and plot current processed stack:
    MG_projection = z_max_project(MG_sub_processed_medfiltered, I_shape=I_shape, log=log)
    MG_projection_pre = MG_projection.copy()
    if median_filter_slices == "circular" or median_filter_slices == "square":
        plot_projected_stack(MG_projection, I_shape=I_shape, plot_path=plot_path, log=log,
                            plottitle="MG projected, proc 1 slicewise median filtered")

    """ 
    From here on, the MG_projection is the stack that will be further processed. Thus, the large MG_sub, 
    MG_sub_processed, and N_sub ZARR datasets are not needed anymore and can be deleted (i.e., the entire Z group).
    """
    print(f"ZARR storage will be deleted (not needed anymore) ...", end="")
    del MG_sub
    del MG_sub_processed
    if two_channel:
        del N_sub
    gc.collect()
    zarr_path = Z.attrs["ZARR file path"]
    if Path(zarr_path).exists():
        shutil.rmtree(zarr_path)
    gc.collect()
    if debug_output: print_ram_usage()
    
    # enhance the histograms WITHIN each projected stack:
    if hist_equalization:
        MG_projection = histogram_equalization_on_projections(MG_projection, I_shape,
                                                                   log, clip_limit=hist_equalization_clip_limit,
                                                                   kernel_size=hist_equalization_kernel_size)
        plot_projected_stack(MG_projection, I_shape=I_shape, plot_path=plot_path, log=log,
                         plottitle="MG projected, proc 2 histogram equalized")

    # match the histograms ACROSS the stacks:
    if hist_match:
        MG_projection = histogram_matching_on_projections(MG_projection, I_shape, histogram_ref_stack, log)
        plot_projected_stack(MG_projection, I_shape=I_shape, plot_path=plot_path, log=log,
                         plottitle="MG projected, proc 3 histogram matched")
        compare_histograms(MG_sub_pre=MG_projection_pre, MG_sub_post=MG_projection, log=log,
                        plot_path=plot_path, xlim=(0, 6000), I_shape=I_shape)
    
    # after all histogram enhancements, perform another median filtering (optional), this time 
    # on the projections (also to improve the later optional registration):
    if median_filter_projections == "circular":
        MG_projection_medianfiltered = circular_median_filtering_on_projections(MG_projection, I_shape, median_filter_window_projections, log)
        plot_projected_stack(MG_projection_medianfiltered, I_shape=I_shape, plot_path=plot_path, log=log,
                             plottitle="MG projected, proc 4 median filtered")
    elif median_filter_projections == "square":
        MG_projection_medianfiltered = median_filtering_on_projections(MG_projection, I_shape, median_filter_window_projections, log)
        plot_projected_stack(MG_projection_medianfiltered, I_shape=I_shape, plot_path=plot_path, log=log,
                             plottitle="MG projected, proc 4 median filtered")
    else:
        MG_projection_medianfiltered = MG_projection

    # register the projected stack on each other:
    if regStack2d:
        MG_projection_reg, I_shape_reg = reg_2D_images(MG_projection_medianfiltered, I_shape=I_shape, log=log,
                                                histogram_ref_stack=histogram_ref_stack, 
                                                max_xy_shift_correction=max_xy_shift_correction,
                                                median_filter_projections=median_filter_projections, 
                                                median_filter_window_projections=median_filter_window_projections,
                                                usepystackreg=usepystackreg)
        plot_projected_stack(MG_projection_reg, I_shape=I_shape, plot_path=plot_path, log=log,
                             plottitle="MG projected, proc 5 registered")
    else:
        MG_projection_reg = MG_projection_medianfiltered.copy()
        I_shape_reg = I_shape.copy()
    
    # calculate the mean intensity of each stack and plot it:
    intensity_means = plot_intensities(MG_projection_reg, log, plot_path, I_shape_reg)
    pd.DataFrame(data=100*intensity_means/intensity_means[0],
                 columns=["relative brightness drop"]).to_excel(os.path.join(plot_path,"relative brightness drops.xlsx"))
 
    # remove some further noise:
    if gaussian_sigma_proj>0:
        MG_projection_reg_gaussian_blurr  = gaussian_blurr_filtering_on_projections(MG_projection_reg, I_shape_reg,
                                                                    gaussian_blurr_sigma=gaussian_sigma_proj, 
                                                                    log=log)
        plot_projected_stack(MG_projection_reg_gaussian_blurr, I_shape=I_shape, plot_path=plot_path, log=log,
                             plottitle="MG projected, proc 6 gaussian blurr")
    else:
        MG_projection_reg_gaussian_blurr = MG_projection_reg.copy()

    if debug_output: print_ram_usage()

    MG_binarized_projection = binarize_2D_images(MG_projection_reg_gaussian_blurr, I_shape=I_shape_reg, log=log,
                                                 plot_path=plot_path,
                                                 threshold_method=threshold_method,
                                                 compare_all_threshold_methods=compare_all_threshold_methods,
                                                 gaussian_sigma_proj=gaussian_sigma_proj)

    if debug_output: print_ram_usage()

    MG_binarized_projection, MG_binarized_projection_areas = remove_small_blobs(MG_binarized_projection, 
                                                I_shape=I_shape_reg, log=log, plot_path=plot_path, 
                                                pixel_threshold=blob_pixel_threshold,
                                                stats_plots=stats_plots)
    plot_pixel_areas(MG_areas=MG_binarized_projection_areas, log=log, plot_path=plot_path, I_shape=I_shape_reg)

    if debug_output: print_ram_usage()

    _, _ = motility(MG_binarized_projection, I_shape=I_shape_reg, log=log, plot_path=plot_path, ID=ID, group=group)
    
    _ = log.logt(Total_Process_t0, verbose=True, spaces=2, unit="sec", process="total processing time")
    if debug_output: print_ram_usage()

def batch_process_stacks(PROJECT_Path, ID_list=[], project_tag="TP000", reg_tif_file_folder="registered", 
                  reg_tif_file_tag="reg", metadata_file="metadata.xls",
                  RESULTS_foldername="../motility_analysis/", group="blinded",
                  MG_channel=0, N_channel=1, two_channel=True, projection_center=50, projection_layers=20,
                  histogram_ref_stack=0, log="", blob_pixel_threshold=100, 
                  regStack2d=True, regStack3d=False, template_mode="mean",
                  usepystackreg=False,
                  spectral_unmixing=True, hist_equalization=False, hist_match=True, 
                  hist_equalization_kernel_size=None, hist_equalization_clip_limit=0.05,
                  max_xy_shift_correction=50,
                  threshold_method="li", compare_all_threshold_methods=True,
                  gaussian_sigma_proj=1, spectral_unmixing_amplifyer=1,
                  median_filter_slices = "square", median_filter_window_slices=3,
                  median_filter_projections = "square", median_filter_window_projections=3, 
                  clear_previous_results=False, spectral_unmixing_median_filter_window=3,
                  debug_output=False, stats_plots=False):
    """
    Processes multiple image stacks in a batch, extracting sub-volumes, registering them
    (optional), performing image processing, and analyzing microglial motility.

    Parameters:
    -----------
    PROJECT_Path : str or Path
        The base directory containing the image stacks.
    ID_list : list of str, optional
        List of sample or subject IDs to be processed (default is an empty list).
    project_tag : str, optional
        Tag used to identify project folders (default is "TP000").
    reg_tif_file_folder : str, optional
        Folder name containing registered TIFF files (default is "registered").
    reg_tif_file_tag : str, optional
        Tag used to filter for registered TIFF files (default is "reg").
    metadata_file : str, optional
        Name of the metadata file to retrieve processing parameters (default is "metadata.xls").
    RESULTS_Path : str or Path, optional
        Directory where results will be saved (default is "motility_analysis").
    group : str, optional
        Sample group label (default is "blinded").
    MG_channel : int, optional
        Channel index for microglial signal (default is 0).
    N_channel : int, optional
        Channel index for neuronal signal (default is 1).
    two_channel : bool, optional
        Indicates whether the data contains two channels (default is True).
    projection_center : int, optional
        Center plane for z-projections (default is 50).
    projection_layers : int, optional
        Number of layers used for projection (default is 20).
    histogram_ref_stack : int, optional
        Reference stack index for histogram matching (default is 0).
    log : object, optional
        Logging object for process tracking (default is an empty string).
    blob_pixel_threshold : int, optional
        Minimum size of segmented objects to retain (default is 100 pixels).
    regStack2d : bool, optional
        Whether to perform 2D registration (default is True).
    regStack3d : bool, optional
        Whether to perform 3D registration (default is False).
    template_mode : str, optional
        Mode used to generate a reference template for registration (default is "mean").
    spectral_unmixing : bool, optional
        Whether to perform spectral unmixing to separate signals (default is True).
    hist_equalization : bool, optional
        Whether to apply histogram equalization to enhance contrast (default is False).
    hist_equalization_clip_limit : float
        Clip limit for histogram equalization.
    hist_equalization_kernel_size : None or tuple of int
        Kernel size for histogram equalization.
    hist_match : bool, optional
        Whether to match histograms across image stacks (default is True).
    max_xy_shift_correction : int, optional
        Maximum allowed shift in pixels for image registration (default is 50).
    threshold_method : str, optional
        Method for binarization thresholding (default is "li").
    compare_all_threshold_methods : bool, optional
        Whether to compare multiple thresholding methods (default is True).
    gaussian_sigma_proj : int, optional
        Sigma value for Gaussian blur applied before binarization (default is 1).
    spectral_unmixing_amplifyer : int, optional
        Amplification factor for spectral unmixing (default is 1).
    median_filter_slices : str, optional
        Type of median filtering applied to individual slices ("square" or "circular") (default is "square").
    median_filter_window_slices : int, optional
        Window size for median filtering on slices (default is 3).
    median_filter_projections : str, optional
        Type of median filtering applied to projections ("square" or "circular") (default is "square").
    median_filter_window_projections : int, optional
        Window size for median filtering on projections (default is 3).
    clear_previous_results : bool, optional
        Whether to delete previous results before processing (default is False).
    spectral_unmixing_median_filter_window : int, optional
        Window size for median filtering applied before spectral unmixing (default is 3).
    debug_output : bool, optional
        Whether to print debug information, including RAM usage (default is False).
    stats_plots : bool, optional
        Whether to generate additional statistics plots (default is False).

    Returns:
    --------
    None
        The function processes each stack and saves the results in the specified output directory.

    Notes:
    ------
    - The function scans for project folders and extracts relevant image files.
    - Metadata files, if present, override certain function parameters.
    - Each stack is processed using the `process_stack` function.
    - Results are saved in subdirectories within `RESULTS_Path`, organized by projection center.
    """
    Total_batch_Process_t0 = time.time()
    log.log(f"Batch processing of stacks...")
    log.log("============================================================\n")
    if debug_output: print_ram_usage()
    
    for Current_ID in ID_list:
        # Current_ID = ID_list[0]
        Current_ID_Folder = os.path.join(PROJECT_Path + Current_ID + "/")
        _, TP_folderlist, _= filterfolder_by_string(Current_ID_Folder, project_tag)
        log.log(f"Mouse {Current_ID}\n")
        log.log(f" {project_tag}-tagged folders found: {TP_folderlist}" )

        for iTP in range(len(TP_folderlist)):
            """
            iTP=0
            """

            # Check for reg_tif_file_folder folders in each project_tag folder:
            Current_TP_Folder = os.path.join(Current_ID_Folder + TP_folderlist[iTP] + '/')
            _, reg_file_folder, _ = filterfolder_by_string(Current_TP_Folder, reg_tif_file_folder)
            # check for ambiguity (only one reg_tif_file_folder should be present):
            if len(reg_file_folder)>1:
                log.log(f"  WARNING: multiple '{reg_tif_file_folder}' folders found in {TP_folderlist[iTP]} -> skipping this folder.")
                continue
            elif len(reg_file_folder)==0:
                log.log(f"  WARNING: no '{reg_tif_file_folder}' folder found in {TP_folderlist[iTP]} -> skipping this folder.")
                continue
            else:
                log.log(f"  '{reg_tif_file_folder}' folder found in {TP_folderlist[iTP]}.")
                
            # check whether one ore more tif files including the reg_tif_file_tag are present in the reg_file_folder:
            reg_tif_file = glob.glob(Current_TP_Folder + reg_file_folder[0] + "/*" + reg_tif_file_tag + "*.tif")
            if len(reg_tif_file)==0:
                log.log(f"  WARNING: no tif file with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder -> skipping this folder.")
                continue
            elif len(reg_tif_file)>1:
                log.log(f"  AMBIGUITY WARNING: found more than 1 file with tag '{reg_tif_file_tag}' in '{reg_tif_file_folder}' folder -> skipping this folder.")
                for i in range(len(reg_tif_file)):
                    log.log(f"    {reg_tif_file[i]}")
                continue
            else:
                log.log(f"  {len(reg_tif_file)} tif file with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder in {TP_folderlist[iTP]} in {Current_ID}.")
                reg_tif_file = Path(reg_tif_file[0])
                
            
            # search for metadata file in the current TP_folder and extract the parameters from it (if any):
            _, metadata_files, _ = filterfiles_by_string(Current_TP_Folder, metadata_file)
            # remove dot-files from metadata_file list:
            metadata_files = [file for file in metadata_files if not file.startswith(".")]
            projection_centers_use = []
            if metadata_files:
                metadata = pd.read_excel(Current_TP_Folder + metadata_files[0])
                # overwrites processing variables from function input with metadata values:
                two_channel = metadata["Two Channel"][0]
                N_channel   = metadata["Neuron Channel"][0]
                MG_channel  = metadata["Microglia Channel"][0]
                spectral_unmixing = metadata["Spectral Unmixing"][0]
                
                # check, whether there is a column that contains the phrase "Projection Center":
                projection_centers_check = [col for col in metadata.columns if "Projection Center" in col]
                if projection_centers_check != []:
                    # run over all "projection center" columns and append the according numbers to the list projection_centers_use:
                    for col in projection_centers_check:
                        # check, whether the current column contains a number:
                        if not np.isnan(metadata[col][0]):
                            projection_centers_use.append(metadata[col][0])
                else:
                    projection_centers_use = [projection_center]
                if "N Projection Layers" in metadata.columns:
                    if metadata["N Projection Layers"][0]>1:
                        projection_layers = metadata["N Projection Layers"][0]
                    else:
                        projection_layers = projection_layers
                else:
                    projection_layers = projection_layers
                if "Spectral Unmixing Amplifyer" in metadata.columns:
                    spectral_unmixing_amplifyer = metadata["Spectral Unmixing Amplifyer"][0]
                else:
                    spectral_unmixing_amplifyer = spectral_unmixing_amplifyer
            else:
                projection_centers_use=[projection_center]

            # correct spectral_unmixing_amplifyer, if it is zero:
            if spectral_unmixing_amplifyer==0:
                spectral_unmixing_amplifyer=1

            # main batch loop iterating the tif file in the reg_file_folder over found projection centers:
            for curr_projection_center in projection_centers_use:
                # curr_projection_center = projection_centers_use[0]
                log.log(f"  processing projection center: {curr_projection_center}")
                RESULTS_Path = reg_tif_file.parent.joinpath(f"{RESULTS_foldername}")
                output_foldername = Path(RESULTS_Path).joinpath(f"projection_center_{curr_projection_center}")
                # check, whether the output folder already exists:
                if not os.path.exists(output_foldername):
                    os.makedirs(output_foldername)
                process_stack(fname=reg_tif_file, 
                              MG_channel=MG_channel, 
                              N_channel=N_channel, 
                              two_channel=two_channel,
                              projection_center=curr_projection_center, 
                              projection_layers=projection_layers,
                              histogram_ref_stack=histogram_ref_stack, 
                              log=log, 
                              blob_pixel_threshold=blob_pixel_threshold,
                              spectral_unmixing=spectral_unmixing, hist_equalization=hist_equalization,
                              hist_match=hist_match, 
                              hist_equalization_kernel_size=hist_equalization_kernel_size,
                              hist_equalization_clip_limit=hist_equalization_clip_limit,
                              RESULTS_Path=output_foldername, 
                              ID=Current_ID, 
                              group=group,
                              max_xy_shift_correction=max_xy_shift_correction, 
                              threshold_method=threshold_method,
                              compare_all_threshold_methods=compare_all_threshold_methods, 
                              gaussian_sigma_proj=gaussian_sigma_proj,
                              spectral_unmixing_amplifyer=spectral_unmixing_amplifyer,
                              spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                              median_filter_slices=median_filter_slices, 
                              median_filter_window_slices=median_filter_window_slices,
                              median_filter_projections=median_filter_projections, 
                              median_filter_window_projections=median_filter_window_projections,
                              clear_previous_results=clear_previous_results, 
                              regStack2d=regStack2d, 
                              regStack3d=regStack3d,
                              template_mode=template_mode,
                              usepystackreg=usepystackreg,
                              debug_output=debug_output,
                              stats_plots=stats_plots)
        log.log("\n============================================================\n")
            
    _ = log.logt(Total_batch_Process_t0, verbose=True, spaces=0, unit="sec", process="total batch ")
    if debug_output: print_ram_usage()

def batch_collect(PROJECT_Path, ID_list=[], project_tag="TP000", motility_folder="motility_analysis",
                  RESULTS_Path="batch_results", log=""):
    """
    Scans for processed results from multiple stacks and compiles data from 
    'motility_analysis.xlsx', 'Normalized average brightness of each stack.xlsx', 
    and 'pixel area sums.xlsx' into three consolidated DataFrames.

    Parameters:
    -----------
    PROJECT_Path : str or Path
        The base directory containing the image stacks.
    ID_list : list of str, optional
        List of sample or subject IDs to be processed (default is an empty list).
    project_tag : str, optional
        Tag used to identify project folders (default is "TP000").
    motility_folder : str, optional
        Folder name containing motility analysis results (default is "motility_analysis").
    RESULTS_Path : str or Path, optional
        Directory where the consolidated results will be saved (default is "batch_results").

    Returns:
    --------
    None
        Saves three DataFrames as Excel files in the `RESULTS_Path` directory.

    Notes:
    ------
    - This function assumes a folder structure like:
      `ID/project_tag*/motility_analysis/projection_center*/`
    - Extracts content from:
      - "motility_analysis.xlsx"
      - "Normalized average brightness of each stack.xlsx"
      - "pixel area sums.xlsx"
    - Saves three consolidated DataFrames in `RESULTS_Path`.
    - averages the motility data over all projection centers and t_i points.
    - excel files are saved as "all_motility.xlsx", "all_brightness.xlsx", "all_pixel_area.xlsx" and "average_motility.xlsx".
    """

    log.log(f"Collecting motility data from processed stacks...")
    
    PROJECT_Path = Path(PROJECT_Path)
    ID_list = ID_list if ID_list else [f.name for f in PROJECT_Path.iterdir() if f.is_dir()]
    RESULTS_Path = Path(RESULTS_Path)
    RESULTS_Path.mkdir(parents=True, exist_ok=True)

    motility_data = []
    brightness_data = []
    pixel_area_data = []

    for Current_ID in ID_list:
        # Current_ID = ID_list[0]
        Current_ID_Folder = PROJECT_Path / Current_ID
        TP_folderlist = sorted(glob.glob(str(Current_ID_Folder / f"{project_tag}*")))

        for TP_folder in TP_folderlist:
            # TP_folder = TP_folderlist[0]
            
            log.log(f"Processing ID {Current_ID}, project {Path(TP_folder).name}...")
            
            motility_folder_path = Path(TP_folder) / motility_folder
            if not motility_folder_path.exists():
                log.log(f"Warning: No motility folder found in {TP_folder}")
                continue

            projection_folders = sorted(glob.glob(str(motility_folder_path / "projection_center*")))

            for proj_folder in projection_folders:
                # proj_folder = projection_folders[0]
                log.log(f"  Processing projection center {Path(proj_folder).name}...")
                proj_folder = Path(proj_folder)
                motility_file = proj_folder / "motility_analysis.xlsx"
                brightness_file = proj_folder / "Normalized average brightness of each stack.xlsx"
                pixel_area_file = proj_folder / "pixel area sums.xlsx"

                # read motility analysis data:
                if motility_file.exists():
                    df_motility = pd.read_excel(motility_file)
                    df_motility["ID"] = Current_ID
                    df_motility["project tag"] = Path(TP_folder).name
                    df_motility["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_motility.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_motility = df_motility[cols]
                    df_motility.drop(columns="Unnamed: 0", inplace=True)
                    motility_data.append(df_motility)

                # read brightness data:
                if brightness_file.exists():
                    df_brightness = pd.read_excel(brightness_file)
                    df_brightness["ID"] = Current_ID
                    df_brightness["project tag"] = Path(TP_folder).name
                    df_brightness["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_brightness.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_brightness = df_brightness[cols]
                    df_brightness.drop(columns="Unnamed: 0", inplace=True)
                    brightness_data.append(df_brightness)

                # read pixel area data:
                if pixel_area_file.exists():
                    df_pixel_area = pd.read_excel(pixel_area_file)
                    df_pixel_area["ID"] = Current_ID
                    df_pixel_area["project tag"] = Path(TP_folder).name
                    df_pixel_area["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_pixel_area.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_pixel_area = df_pixel_area[cols]
                    df_pixel_area.drop(columns="Unnamed: 0", inplace=True)
                    pixel_area_data.append(df_pixel_area)

    # merge and save collected data:
    if motility_data:
        motility_df = pd.concat(motility_data, ignore_index=True)
        motility_df.to_excel(RESULTS_Path / "all_motility.xlsx", index=False)

    if brightness_data:
        brightness_df = pd.concat(brightness_data, ignore_index=True)
        brightness_df.to_excel(RESULTS_Path / "all_brightness.xlsx", index=False)

    if pixel_area_data:
        pixel_area_df = pd.concat(pixel_area_data, ignore_index=True)
        pixel_area_df.to_excel(RESULTS_Path / "all_pixel_areas.xlsx", index=False)
        
    # average Stable, Gain, Loss, rel Stable, rel Gain, rel Loss, and tor over delta_t 
    # for each projection center, project tag, and ID:
    motility_avrg_df = pd.DataFrame()
    for proj_center in motility_df["projection center"].unique():
        # proj_center = motility_df["projection center"].unique()[0]
        
        for proj_tag in motility_df["project tag"].unique():
            for ID in motility_df["ID"].unique():
                # ID = motility_df["ID"].unique()[1]
                current_df = motility_df[(motility_df["projection center"]==proj_center) &
                                         (motility_df["project tag"]==proj_tag) &
                                         (motility_df["ID"]==ID)]
                # check whether current_df is not empty:
                if current_df.empty:
                    continue

                current_avrg = pd.DataFrame(index=[0])
                current_avrg["ID"] = ID
                current_avrg["project tag"] = proj_tag
                current_avrg["projection center"] = proj_center
                # append the mean:
                current_avrg["avrg Stable"] = current_df["Stable"].mean()
                current_avrg["avrg Gain"] = current_df["Gain"].mean()
                current_avrg["avrg Loss"] = current_df["Loss"].mean()
                current_avrg["avrg rel Stable"] = current_df["rel Stable"].mean()
                current_avrg["avrg rel Gain"] = current_df["rel Gain"].mean()
                current_avrg["avrg rel Loss"] = current_df["rel Loss"].mean()
                current_avrg["avrg tor"] = current_df["tor"].mean()
                
                # append the std:
                current_avrg["Stable std"] = current_df["Stable"].std()
                current_avrg["Gain std"] = current_df["Gain"].std()
                current_avrg["Loss std"] = current_df["Loss"].std()
                current_avrg["rel Stable std"] = current_df["rel Stable"].std()
                current_avrg["rel Gain std"] = current_df["rel Gain"].std()
                current_avrg["rel Loss std"] = current_df["rel Loss"].std()
                current_avrg["tor std"] = current_df["tor"].std()
                
                # update the DataFrame:
                motility_avrg_df = pd.concat([motility_avrg_df, current_avrg], ignore_index=True)
                
    motility_avrg_df.to_excel(RESULTS_Path / "average_motility.xlsx")

    log.log(f"Collected data saved in {RESULTS_Path}")


# %% DEBUGGING/TESTING
if __name__ == '__main__':

    # EXAMPLE PARAMETERS FOR SINGLE FILE RUN:

    # define data input paths:
    Current_ID = "ID14201"
    group = "blinded"
    DATA_Path = "/Users/husker/Science/Python/Projekte/MotilA/example project/Data/ID240103_P17_1/TP000/registered/"
    IMG_File = "all stacks 4D reg.tif"
    fname = Path(DATA_Path).joinpath(IMG_File)
        
    # define projection settings:
    projection_layers_default = 44 # define how many z-layers you want to project for the motility analysis
    projection_center_default = 23 # define the center slice of the projection; a sub-stack of +/- projection_layers will be projected;
                                   # if metadata.xls is present, this value is ignored (in batch processing only)
    
    # define results output path:
    RESULTS_foldername = f"../motility_analysis_projcenter_{projection_center_default}/"
    RESULTS_Path = Path(DATA_Path).joinpath(RESULTS_foldername)
    check_folder_exist_create(RESULTS_Path)
    clear_previous_results = True # set to True if all files in RESULTS_Path folder should be deleted before processing
    

    # thresholding settings:
    threshold_method = "otsu"     # choose from: otsu, li, isodata, mean, triangle, yen, minimum
    blob_pixel_threshold = 100    # define the threshold for the minimal pixel area of a blob during the segmentation
    compare_all_threshold_methods = True # if True, all threshold methods will be compared and saved in the plot folder

    # image enhancement settings:
    hist_equalization = True             # enhance the histograms WITHIN EACH projected stack: True or False
    hist_equalization_clip_limit = 0.05  # clip limit for the histogram equalization (default is 0.05)
    hist_equalization_kernel_size = None # kernel size for the histogram equalization; 
                                         # None (default) for automatic, or use a tuple (x,y) for a fixed size;
                                         # when using a tuple, you can start increasing the values from multiples
                                         # of 8, e.g., (8,8), (16,16), (24,24), (32,32), ... (128,128), ...
    hist_match = True               # match the histograms   ACROSS the stacks          : True or False
    histogram_ref_stack = 0         # define the stack which should be used as reference for the histogram matching
    
    
    # filter settings:
    median_filter_slices             = 'circular' # median filter on SLICES BEFORE projecting
                                            # 'square', 'circular', or False
                                            # circular: floating point numbers allowed, not lower than 0.5 for circular
                                            # square: integer numbers (3, 5, 9)
    median_filter_window_slices      = 1.55 # median filter window size on SLICES BEFORE projecting
                                            # circular: only values >= 0.5 allowed/have an effect
                                            # square: integer numbers (3, 5, 9)
    
    median_filter_projections        = 'circular' # median filter on PROJECTIONS
                                            # square, circular, or False
    median_filter_window_projections = 1.55 # median filter window size on PROJECTIONS
                                            # circular: only values >= 0.5 allowed/have an effect
                                            # square: integer numbers (3, 5, 9)
    gaussian_sigma_proj = 1.00  # Standard deviation of Gaussian (blur) filter applied on the projected stack
                                # set to 0 for turning off

    # channel settings: 
    two_channel_default = True # define if the stack has two channels; if metadata.xls is present, this value is ignored
    MG_channel_default   = 0    # define the channel of the Microglia; if metadata.xls is present, this value is ignored
    N_channel_default    = 1    # define the channel of the Neurons/2nd channel; if metadata.xls is present, this value is ignored
    
    # registration settings:
    regStack3d = True          # register slices WITHIN each 3D time-stack; True or False
    regStack2d = False          # register projections on each other; True or False
    template_mode = "max"       # set the template mode for the 3D registration; defines for both 3D and 2D registration
                                # choose from: mean, median, max, std, var.
    max_xy_shift_correction = 100 # set the maximal shift in x/y direction for the 2D registration
    
    # spectral unmixing settings:
    spectral_unmixing = True                  # perform spectral unmixing; True or False
    spectral_unmixing_amplifyer_default    =1 # amplifies the MG channel (to save more from it)
    spectral_unmixing_median_filter_window =3 # must be integer; 1=off, 3=common, 5=strong, 7=very strong
    
    # debugging and stats settings:
    debug_output = False # set to True for debugging output
    stats_plots = False  # set to True for plotting additional statistics
    
    # init logger:
    log = logger_object()
    log.log("logger started for TEST/DEBUG RUN.")
    log.log("Test file: "+str(fname))
    log.log(f"Mouse ID: {Current_ID}")
    log.log(f"Group: {group}")

    process_stack(fname=fname,
                  MG_channel=MG_channel_default, 
                  N_channel=N_channel_default,
                  two_channel=two_channel_default,
                  projection_layers=projection_layers_default,
                  projection_center=projection_center_default,
                  histogram_ref_stack=histogram_ref_stack,
                  log=log,
                  blob_pixel_threshold=blob_pixel_threshold, 
                  regStack2d=regStack2d,
                  regStack3d=regStack3d,
                  template_mode=template_mode,
                  spectral_unmixing=spectral_unmixing,
                  hist_equalization=hist_equalization,
                  hist_equalization_clip_limit=hist_equalization_clip_limit,
                  hist_equalization_kernel_size=hist_equalization_kernel_size,
                  hist_match=hist_match,
                  RESULTS_Path=RESULTS_Path,
                  ID=Current_ID,
                  group=group,
                  threshold_method=threshold_method,
                  compare_all_threshold_methods=compare_all_threshold_methods,
                  gaussian_sigma_proj=gaussian_sigma_proj,
                  spectral_unmixing_amplifyer=spectral_unmixing_amplifyer_default,
                  median_filter_slices=median_filter_slices,
                  median_filter_window_slices=median_filter_window_slices,
                  median_filter_projections=median_filter_projections,
                  median_filter_window_projections=median_filter_window_projections,
                  clear_previous_results=clear_previous_results,
                  spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                  stats_plots=stats_plots)
    
    
    
    
    """ DEBUGGING CONVENIENCE for single file run:
    fname=fname
    MG_channel=MG_channel_default 
    N_channel=N_channel_default
    two_channel=two_channel_default
    projection_layers=projection_layers_default
    projection_center=projection_center_default
    histogram_ref_stack=histogram_ref_stack
    log=log
    blob_pixel_threshold=blob_pixel_threshold 
    regStack2d=regStack2d
    regStack3d=regStack3d
    template_mode=template_mode
    spectral_unmixing=spectral_unmixing
    hist_equalization=hist_equalization
    hist_equalization_clip_limit=hist_equalization_clip_limit,
    hist_equalization_kernel_size=hist_equalization_kernel_size,
    hist_match=hist_match
    RESULTS_Path=RESULTS_Path
    ID=Current_ID
    group=group
    threshold_method=threshold_method
    compare_all_threshold_methods=compare_all_threshold_methods
    gaussian_sigma_proj=gaussian_sigma_proj
    spectral_unmixing_amplifyer=spectral_unmixing_amplifyer_default
    median_filter_slices=median_filter_slices
    median_filter_window_slices=median_filter_window_slices
    median_filter_projections=median_filter_projections
    median_filter_window_projections=median_filter_window_projections
    clear_previous_results=clear_previous_results
    spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window
    debug_output=False
    """
    
    """ BATCH PROCESSING EXAMPLE:
    ID_list = ["ID240103_P17_1", "ID240321_P17_3"] # list of all IDs to be processed; must be exact the folder name of animals
    project_tag="TP000"      # all folders in the ID-folders containing this tag will be processed; can be just a part of the tag
    reg_tif_file_folder = "registered" # folder within the found project_tag-folder containing the registered tif files; must be exact
    reg_tif_file_tag = "reg" # a Tif file containing this tag will be processed within the reg_tif_file_folder; if multiple files containing this tag, folder will be skipped
    metadata_file="metadata.xls" # name of the metadata file in the project_tag-folder; must be exact
    PROJECT_Path = "/Users/husker/Science/Python/Projekte/MotilA/example project/Data/"
    RESULTS_foldername = f"../motility_analysis/" # define the folder where the results will be saved within each project_tag-folder
    
    # update some settings for faster example run:
    spectral_unmixing = False
    regStack2d = False
    regStack3d = False

    batch_process_stacks(PROJECT_Path=PROJECT_Path, 
                         ID_list=ID_list, 
                         project_tag=project_tag, 
                         reg_tif_file_folder=reg_tif_file_folder,
                         reg_tif_file_tag=reg_tif_file_tag,
                         metadata_file=metadata_file,
                         RESULTS_foldername=RESULTS_foldername,
                         group=group,
                         MG_channel=MG_channel_default, 
                         N_channel=N_channel_default, 
                         two_channel=two_channel_default,
                         projection_center=projection_center_default, 
                         projection_layers=projection_layers_default,
                         histogram_ref_stack=histogram_ref_stack, 
                         log=log, 
                         blob_pixel_threshold=blob_pixel_threshold,
                         regStack2d=regStack2d, 
                         regStack3d=regStack3d, 
                         template_mode=template_mode,
                         spectral_unmixing=spectral_unmixing, 
                         hist_equalization=hist_equalization, 
                         hist_equalization_clip_limit=hist_equalization_clip_limit,
                         hist_equalization_kernel_size=hist_equalization_kernel_size,
                         hist_match=hist_match,
                         max_xy_shift_correction=max_xy_shift_correction,
                         threshold_method=threshold_method, 
                         compare_all_threshold_methods=compare_all_threshold_methods,
                         gaussian_sigma_proj=gaussian_sigma_proj, 
                         spectral_unmixing_amplifyer=spectral_unmixing_amplifyer_default,
                         median_filter_slices=median_filter_slices, 
                         median_filter_window_slices=median_filter_window_slices,
                         median_filter_projections=median_filter_projections, 
                         median_filter_window_projections=median_filter_window_projections,
                         clear_previous_results=clear_previous_results, 
                         spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                         debug_output=False)
    """
    
    """ BATCH COLLECTING EXAMPLE:
    PROJECT_Path = "/Users/husker/Science/Python/Projekte/MotilA/example project/Data/"
    RESULTS_Path = "/Users/husker/Science/Python/Projekte/MotilA/example project/Analysis/"
    ID_list = ["ID240103_P17_1", "ID240321_P17_3"]
    project_tag = "TP000"
    motility_folder = "motility_analysis"
    
    batch_collect(PROJECT_Path=PROJECT_Path, 
                  ID_list=ID_list, 
                  project_tag=project_tag, 
                  motility_folder=motility_folder,
                  RESULTS_Path=RESULTS_Path,
                  log=log)
    """

# %% END
