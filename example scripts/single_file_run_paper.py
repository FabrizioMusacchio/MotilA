""" MotilA example script for a single file run
===============================================

This script demonstrates how to use the **MotilA** pipeline for analyzing microglial fine process motility 
in 4D/5D image stacks.

## Overview
- Loads and processes a registered 4D TIFF image stack.
- Applies preprocessing steps such as projection, registration, and spectral unmixing.
- Performs image enhancements like histogram equalization and filtering.
- Segments microglia, applies thresholding, and quantifies motility.
- Saves the results, including segmented images, histograms, and motility metrics.

## Usage
1. **Set Parameters**  
   Modify the configuration parameters in the **"DEFINE MOTILA PARAMETERS"** section to fit your dataset.

2. **Run the Script**  
   Execute the script to process the image stack and generate results.

3. **Output**  
   Processed images, histograms, and analysis results are saved in the specified output folder.

## Dependencies
- Requires **MotilA** to be installed and accessible. (Download it from the GitHub repository.)

## Notes
- The `metadata.xls` file (if present) will override some user-defined parameters (e.g., projection settings) ONLY during batch processing.
- To clear existing results before running, set `clear_previous_results = True`.
- The pipeline supports both **single-channel** and **two-channel** data.

## Author
Fabrizio Musacchio,  March 20, 2025
"""
# %% IMPORTS
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from motila import motila as mt
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
# %% VERIFY IMPORT
mt.hello_world()
# %% DEFINE MOTILA PARAMETERS

# define data input paths:
Current_ID = "ID240103_P17_1_cutout"           # define the ID of the mouse/animal
group      = "blinded"                  # define the group of the mouse/animal
#DATA_Path  = "/Users/husker/Science/Python/Projekte/MotilA/example project/Data/ID240103_P17_1_cutout/TP000/registered/"
DATA_Path  = "../example project/Data/ID240103_P17_1_cutout/TP000/registered/"
                                        # define the path to the data folder; can be absolute or relative to the
                                        # location of this script
IMG_File   = "all stacks 4D reg.tif"    # define the image file name
fname      = Path(DATA_Path).joinpath(IMG_File)
    
# define projection settings:
projection_layers_default = 44 # define number of z-layers to project for motility analysis
projection_center_default = 23 # define the center slice of the projection; a sub-stack of +/- projection_layers will be projected;
                               # if metadata.xls is present in project_tag folder, this value is ignored and
                               # the value from the metadata.xls is used instead (in batch processing only!)

# define results output path:
RESULTS_foldername = f"../motility_analysis/projection_center_{projection_center_default}/"
                                        # define the folder name (not the full path) for the results;
                                        # by default, a folder with this name is generated within the DATA_Path, 
                                        # but you can also define a relative path to this.
RESULTS_Path = Path(DATA_Path).joinpath(RESULTS_foldername)
mt.check_folder_exist_create(RESULTS_Path)

# previous results settings:
clear_previous_results = True # set to True if all files in RESULTS_Path folder should be deleted before processing

# thresholding settings:
threshold_method = "otsu"     # choose from: otsu, li, isodata, mean, triangle, yen, minimum
blob_pixel_threshold = 100    # define the threshold for the minimal pixel area of a blob during the segmentation
compare_all_threshold_methods = True # if True, all threshold methods will be compared and saved in the plot folder

# image enhancement settings:
hist_equalization = True              # enhance the histograms WITHIN EACH projected stack: True or False
hist_equalization_clip_limit = 0.1    # clip limit for the histogram equalization (default is 0.05);
                                      # the higher the value, the more intense the contrast enhancement, 
                                      # but also the more noise is amplified  
hist_equalization_kernel_size = (128,128)  # kernel size for the histogram equalization; 
                                      # None (default) for automatic, or use a tuple (x,y) for a fixed size;
                                      # when using a tuple, you can start increasing the values from multiples
                                      # of 8, e.g., (8,8), (16,16), (24,24), (32,32), ... (128,128), ...
                                      # start increasing the values if the images start to included block artifacts
hist_match = True               # match the histograms   ACROSS the stacks          : True or False
histogram_ref_stack = 0         # define the stack which should be used as reference for the histogram matching

# filter settings:
median_filter_slices             = 'circular' # median filter on SLICES BEFORE projecting
                                        # 'square', 'circular', or False
                                        # circular: floating point numbers allowed, not lower than 0.5 for circular
                                        # square: integer numbers (3, 5, 9)
median_filter_window_slices      = 2.00 # median filter window size on SLICES BEFORE projecting
                                        # circular: only values >= 0.5 allowed/have an effect
                                        # square: integer numbers (3, 5, 9)

median_filter_projections        = 'circular' # median filter on PROJECTIONS
                                        # square, circular, or False
median_filter_window_projections = 1.55 # median filter window size on PROJECTIONS
                                        # circular: only values >= 0.5 allowed/have an effect
                                        # square: integer numbers (3, 5, 9)
gaussian_sigma_proj = 1.00  # standard deviation of Gaussian (blur) filter applied on the projected stack
                            # set to 0 for turning off

# channel settings: 
two_channel_default = True # define if the stack has two channels; if metadata.xls is present, this value is ignored
MG_channel_default  = 0    # define the channel of the Microglia; if metadata.xls is present, this value is ignored
N_channel_default   = 1    # define the channel of the Neurons/2nd channel; if metadata.xls is present, this value is ignored
# if metadata.xls is present in project_tag folder, these values (two_channel_default, MG_channel_default, 
# N_channel_default) are ignored and values from the metadata.xls are used instead  (in batch processing only!)

# registration settings:
regStack3d = True          # register slices WITHIN each 3D time-stack; True or False
regStack2d = False          # register projections on each other; True or False
template_mode = "max"       # set the template mode for the 3D registration; defines for both 3D and 2D registration
                            # choose from: mean, median, max, std, var.
max_xy_shift_correction = 100 # set the maximal shift in x/y direction for the 2D registration

# spectral unmixing settings:
spectral_unmixing = True                  # perform spectral unmixing; True or False
                                          # if metadata.xls is present in project_tag folder, this value is 
                                          # ignored and the value from the metadata.xls is used instead 
                                          # (in batch processing only!)
spectral_unmixing_amplifyer_default    =1 # amplifies the MG channel (to save more from it)
spectral_unmixing_median_filter_window =3 # must be integer; 1=off, 3=common, 5=strong, 7=very strong

# init logger:
log = mt.logger_object()
log.log("logger started for TEST/DEBUG RUN.")
log.log("Test file: "+str(fname))
log.log(f"Mouse ID: {Current_ID}")
log.log(f"Group: {group}")
# %% RUN MOTILA
mt.process_stack(fname=fname,
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
                spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window)
# %% SOME EXTRA PLOTS

# load and plot the motility data over time:
motility_file = os.path.join(RESULTS_Path, "motility_analysis.xlsx")
motility_data_df = pd.read_excel(motility_file)

N_vals = motility_data_df["tor"].shape[0]

fig = plt.figure(2, figsize=(5, 3.5))
plt.clf()
plt.plot(motility_data_df["tor"], 'o-')
plt.ylim(0, 1.05)
plt.xlim(-0.5, N_vals-0.5)
plt.xticks(np.arange(N_vals), labels=[f"$t_{i}$-$t_{i+1}$" for i in range(N_vals)])
plt.yticks(np.arange(0,1.05, 0.10))
plt.xlabel("stack")
plt.ylabel("turnover rate")
title = f"Microglia turnover rate per time point"
plot_title = title
plt.title(title)
# turn off right and top axis:
plt.gca().spines['right'].set_visible(False)
plt.gca().spines['top'].set_visible(False)
# plt.gca().spines['bottom'].set_visible(False)
# plt.gca().spines['left'].set_visible(False)
# set fontsize to 14 for the current figure:
plt.setp(plt.gca().get_xticklabels(), fontsize=14)
plt.setp(plt.gca().get_yticklabels(), fontsize=14)
plt.gca().title.set_fontsize(14)
plt.gca().xaxis.label.set_fontsize(14)
plt.gca().yaxis.label.set_fontsize(14)
plt.tight_layout()
plt.savefig(Path(RESULTS_Path, plot_title + ".pdf"), dpi=120)
plt.close(fig)


# %% END