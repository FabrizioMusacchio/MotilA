"""
Motility metric computation for MotilA.

This module contains the core frame-to-frame motility analysis and the
associated motility image/table outputs.

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

from .export import DEFAULT_TABLE_EXPORT_FORMATS, export_dataframe
from .io import write_image_stack
from .projection import plot_2D_image
# %% MOTILITY ANALYSIS

def motility(MG_pro, I_shape, log, plot_path, ID="ID00000", group="blinded",
             table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Computes and visualizes microglial motility by analyzing changes in segmented pixel regions over time.
    
    Microglial fine processes are tracked by comparing segmented pixels between consecutive time points.
    The analysis includes stable, gain, and loss percentages of pixels between stacks.
    
    Microglial fine processes turn-over is calculated as the ratio of gained and lost pixels to the total 
    number of stable, gained, and lost pixels as it is common in the literature (e.g., Nebeling et al., 2023).

    Parameters
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

    Returns
    --------
    MG_pro_delta_t : array-like
        The computed difference images representing changes between consecutive stacks.
    summary_df : pandas.DataFrame
        Dataframe summarizing motility metrics, including stable, gain, and loss percentages.

    Notes
    ------
    - Computes changes in segmented pixels between consecutive time points.
    - Visualizes differences in motility with colormap images and histograms.
    - Saves computed motility differences as a multi-frame image file.
    - Outputs table file(s) summarizing motility metrics.
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
    write_image_stack(TIFF_path, MG_pro_delta_t)

    export_dataframe(
        summary_df,
        Path(plot_path, "motility_analysis.xlsx"),
        table_export_formats=table_export_formats,
    )
    log.log(f"motility evaluation saved in {Path(plot_path,'motility_analysis.xlsx')}")

    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process="motility ")
    return MG_pro_delta_t, summary_df

# %% END
