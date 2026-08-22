"""
Segmentation helpers for MotilA.

This module contains projection binarization, connected-component filtering, and
pixel-area result exports.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import os
from pathlib import Path
import time

import matplotlib.pyplot as plt
from matplotlib import colors as mcol
import numpy as np
import pandas as pd
import scipy as sp
import skimage.filters as filter
import skimage.measure as measure

from .export import DEFAULT_TABLE_EXPORT_FORMATS, export_dataframe
from .projection import plot_2D_image
# %% BINARIZATION

def binarize_2D_images(MG_pro, I_shape, log, plot_path, threshold_method="otsu",
                       compare_all_threshold_methods=True, gaussian_sigma_proj=1):
    """
    Binarizes 2D z-projection images using various thresholding methods.

    Parameters
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

    Returns
    --------
    MG_pro_bin : ndarray
        The binarized image stack.

    Notes
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

# %% CONNECTED-COMPONENT FILTERING

def remove_small_blobs(MG_pro, I_shape, log, plot_path, pixel_threshold=100,
                       stats_plots=False,
                       table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Removes small microglial regions based on pixel connectivity and area threshold in segmented 2D images.

    Parameters
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

    Returns
    --------
    MG_pro_bin_area_thresholded : ndarray
        The binarized image stack after removing small regions.
    MG_pro_bin_area_sum : ndarray
        The total number of pixels retained after thresholding.

    Notes
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
        export_dataframe(
            pixel_areas_df,
            os.path.join(plot_path, f"pixel areas of segmented projection, stack {stack}.xlsx"),
            table_export_formats=table_export_formats,
        )

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="connectivity measurement ")
    return MG_pro_bin_area_thresholded, MG_pro_bin_area_sum

# %% PIXEL-AREA OUTPUTS

def plot_pixel_areas(MG_areas, log, plot_path, I_shape,
                     table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Plots and saves the detected pixel areas per projected stack.

    Parameters
    -----------
    MG_areas : array-like
        The total segmented pixel area per stack.
    log : logger_object
        Logging object for recording the process.
    plot_path : str or Path
        Path where the plot and Excel file will be saved.
    I_shape : tuple
        Shape of the input image stack.

    Returns
    --------
    None
        The function saves a bar plot and an Excel file with pixel area statistics.

    Notes
    ------
    - Normalizes pixel areas relative to stack 0.
    - Saves a bar plot representing relative pixel areas per stack.
    - Outputs table file(s) with absolute and relative pixel areas, including total field-of-view (FOV) area.
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
        export_dataframe(
            df_out,
            os.path.join(plot_path, "pixel area sums.xlsx"),
            table_export_formats=table_export_formats,
        )
        
    else:
        log.log("Warning: MG_areas[0] is zero, skipping relative area plot to avoid division by zero.")

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="pixel cell area plotting ")

# %% END
