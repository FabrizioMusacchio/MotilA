"""
Projection and plotting helpers for MotilA.

This module contains z-projection utilities and plot/table outputs that describe
projection intensity, histograms, and projected image stacks.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import os
from pathlib import Path
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from skimage import exposure

from .export import DEFAULT_TABLE_EXPORT_FORMATS, export_dataframe
from .io import write_image_stack
# %% PROJECTION RANGE HELPERS

def calc_projection_range(projection_center, projection_layers, I_shape, log):
    """
    Calculate a z-projection range for a given center plane and number of layers,
    ensuring that the range stays within stack boundaries.

    Parameters
    ----------
    projection_center : int
        Index of the central z-plane around which the projection is computed.
    projection_layers : int
        Total number of layers to include in the projection (symmetric around
        ``projection_center``).
    I_shape : tuple
        Shape of the input image stack. The second entry must represent the z-dimension.
    log : object
        Logging object with a ``log`` method for recording warnings and information.

    Returns
    -------
    tuple
        A tuple ``(projection_range, projection_layers)`` where:

        * **projection_range** : list of int  
          Two-element list ``[start, end]`` defining the z-range after boundary
          correction.

        * **projection_layers** : int  
          Actual number of layers used in the projection after adjusting for
          stack limits.

    Notes
    -----
    The projection range is clipped automatically if ``projection_center ± layers/2``
    extends beyond stack boundaries. Any correction is reported via ``log.log()``.
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
    
    log.log(f"Projection center: {projection_center}, Projection range: {projection_range}")

    # update projection_layers if it was adjusted to the actual number of layers:
    projection_layers = projection_range[1] - projection_range[0] + 1

    return projection_range, projection_layers

# %% GENERAL PLOTTING HELPERS

def plot_2D_image(image, plot_path, plot_title, fignum=1, figsize=(5,5.15),
                  show_ticks=False, show_borders=False, cbar_show=False,
                  cmap=plt.get_cmap('viridis'), cbar_label="",
                  cbar_ticks=[], cbar_ticks_labels="", title=""):
    """
    Plots a 2D image and saves it as a PDF file.

    Parameters
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

    Returns
    --------
    None
        This function saves the plot as a PDF file and does not return a value.

    Notes
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
    Saves a 2D image as an OME-TIFF file.

    Parameters
    -----------
    image : array-like
        The 2D array representing the image to be saved.
    plot_path : str or Path
        The directory where the image file will be saved.
    plot_title : str
        The filename for the saved image file (without extension).

    Returns
    --------
    None
        This function saves the image as an image file and does not return a value.

    Notes
    ------
    - The file is saved as `<plot_title>.tif` in the specified directory.
    - The image is written through OMIO while preserving the historical `.tif` filename.
    """
    TIFF_path = os.path.join(plot_path, plot_title+".tif")
    write_image_stack(TIFF_path, image)

def plot_histogram(image, plot_path, plot_title, fignum=1, title="histogram"):
    """
    Plots the histogram and cumulative distribution function (CDF) of an image and saves it as a PDF file.

    Parameters
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

    Returns
    --------
    None
        The function saves the histogram plot as a PDF file and does not return a value.

    Notes
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

    Parameters
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

    Returns
    --------
    None
        The function saves histogram plots for each projected stack as PDF files.

    Notes
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

# %% PROJECTION PLOTTING HELPERS

def plot_projected_stack(image_stack, I_shape, plot_path, log, plottitle="MG projected"):
    """
    Plots and saves z-projected image stacks as grayscale images and an OME-TIFF file.

    Parameters
    -----------
    image_stack : array-like
        The stack of 2D projected images to be plotted and saved.
    I_shape : tuple
        The shape of the image stack, used to determine the number of stacks.
    plot_path : str or Path
        The directory where the plots and image file will be saved.
    log : logger_object
        A logging object to record processing steps and execution time.
    plottitle : str, optional
        The base title for the saved plots and image file (default is "MG projected").

    Returns
    --------
    None
        The function saves each projected stack as a grayscale plot and the full stack as an image file.

    Notes
    ------
    - Individual stacks are plotted as grayscale images and saved as PDFs.
    - The full image stack is saved as an image file with metadata.
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
    write_image_stack(TIFF_path, image_stack.astype("float32"))

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="z-projection plotting ")

def plot_projected_stack_as_tif(image_stack, I_shape, plot_path, log, plottitle="MG projected"):
    """
    Saves z-projected image stacks as OME-TIFF files.

    Parameters
    -----------
    image_stack : array-like
        The stack of 2D projected images to be saved as image files.
    I_shape : tuple
        The shape of the image stack, used to determine the number of stacks.
    plot_path : str or Path
        The directory where the image files will be saved.
    log : logger_object
        A logging object to record processing steps and execution time.
    plottitle : str, optional
        The base title for the saved image files (default is "MG projected").

    Returns
    --------
    None
        The function saves each projected stack as an individual image file.

    Notes
    ------
    - Each stack is saved as a separate image file with a unique filename.
    - The function logs the saving process and execution time.
    """
    Process_t0 = time.time()

    log.log(f"saving z-projections as image files...")
    for stack in range(I_shape[0]):
        plot_2D_image_as_tif(image=image_stack[stack], plot_path=plot_path,
                             plot_title=plottitle+", stack " + str(stack))

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="z-projection tif saving ")

def z_max_project(MG_sub, I_shape, log):
    """
    Computes the maximum intensity Z-projection of an image stack.

    Parameters
    -----------
    MG_sub : array-like
        The input microglial image stack.
    I_shape : tuple
        Shape of the input image stack.
    log : logger_object
        Logging object for recording the process.

    Returns
    --------
    MG_pro : ndarray
        The Z-projected image stack using maximum intensity projection.

    Notes
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

    Parameters
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

    Returns
    --------
    None
        The function saves the histogram plots as PDF files.

    Notes
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

def plot_intensities(MG_pro, log, plot_path, I_shape,
                     table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Plots and saves the normalized average brightness per projected stack.

    Parameters
    -----------
    MG_pro : array-like
        The projected image stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        The directory path where the plot and data file will be saved.
    I_shape : tuple
        Shape of the input image stack.

    Returns
    --------
    intensity_means : ndarray
        Array containing the mean intensity values for each stack.

    Notes
    ------
    - The function calculates the average intensity for each projected stack.
    - Normalizes intensity values relative to the first stack.
    - Saves a bar plot and table file(s) with the normalized brightness values.
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
    export_dataframe(
        df_out,
        os.path.join(plot_path, "Normalized average brightness of each stack.xlsx"),
        table_export_formats=table_export_formats,
    )

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="brightness comparison ")
    return intensity_means

# %% END
