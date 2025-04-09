""" MotilA example script for batch-processing
===============================================

This script demonstrates how to use the **MotilA** pipeline for batch-processing multiple 
4D/5D image stacks of microglia motility across multiple experimental conditions.

## Overview
- Scans and processes multiple registered 4D TIFF image stacks from multiple experimental folders.
- Applies preprocessing steps such as projection, registration, and spectral unmixing.
- Performs image enhancements like histogram equalization and filtering.
- Segments microglia, applies thresholding, and quantifies motility.
- Collects results from all processed stacks into summary tables for cohort analysis.

## Workflow
1. **Batch Processing**
   - Iterates over multiple subject folders (`ID_list`) and searches for experiment folders (`project_tag`).
   - Processes microglial motility for each dataset according to predefined settings.
   - Saves analysis results per subject in a structured output folder.

2. **Batch Collection**
   - Gathers and combines results across all processed datasets.
   - Saves consolidated results into a cohort-level output directory.

## Usage
- **Modify Parameters:** Adjust paths, projection settings, thresholding methods, and filter settings.
- **Run the Script:** Execute the script to batch process and collect results.
- **Check Outputs:** Processed images, histograms, and motility metrics are saved in structured folders.

## Dependencies
- Requires **MotilA** to be installed and accessible (available in the GitHub repository).

## Notes
- The `metadata.xls` file (if present) overrides user-defined parameters during batch processing.
- To clear existing results before running, set `clear_previous_results = True`.
- The pipeline supports **single-channel** and **two-channel** data.
- Ensure `motility_folder` is correctly set for batch result collection.

## Author
Fabrizio Musacchio,  March 20, 2025
"""
# %% IMPORTS
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from motila import motila as mt
# %% VERIFY IMPORT
mt.hello_world()
# %% DEFINE MOTILA PARAMETERS

# define data input paths:
#PROJECT_Path = "/Volumes/Media/Workspace/MotilA example files/single_file/"
PROJECT_Path = "../example project/Data/"
                                          # define the path to the project folder; can be absolute or relative to the
                                          # location of this script
ID_list = ["ID240103_P17_1", "ID240321_P17_3"]
                                          # define the list of all IDs to be processed in PROJECT_Path; 
                                          # names must be exact names of the ID folders
project_tag = "TP000"                     # define the tag of the project (folder) to be analyzed;
                                          # all folders in the ID-folders containing this tag will be processed; 
                                          # can be just a part of the tag (will be searched for in the folder name)
reg_tif_file_folder = "registered"        # name of folder within the (found) project_tag-folder containing the 
                                          # registered tif files; must be exact
reg_tif_file_tag = "reg"                  # a Tif file containing this tag will be processed within the reg_tif_file_folder;
                                          # if multiple files containing this tag, folder will be skipped (!)
RESULTS_foldername = f"../motility_analysis/" 
                                          # define the folder name (not the full path!) where the results will be saved
                                          # within each project_tag-folder; can also be relative to the project_tag-folder
                                          # (e.g. "../motility_analysis/"); default destination will be inside the
                                          # reg_tif_file_folder folder
metadata_file = "metadata.xls"            # name of the metadata file in the project_tag-folder; must be exact
                                          # use template provided in the MotilA repository to create the metadata file
                                              
# define projection settings:
projection_layers_default = 44 # define number of z-layers to project for motility analysis
projection_center_default = 23 # define the center slice of the projection; a sub-stack of +/- projection_layers will be projected;
                               # if metadata.xls is present in project_tag folder, this value is ignored and
                               # the value from the metadata.xls is used instead (in batch processing only!)

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
median_filter_window_slices      = 1.55 # median filter window size on SLICES BEFORE projecting
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
log.log("logger started for TEST/DEBUG RUN: BATCH RUN.")
log.log("Test project: "+str(PROJECT_Path))
log.log(f"Mouse IDs: {ID_list}")
log.log(f"Group: {project_tag}")
# %% RUN MOTILA
mt.batch_process_stacks(PROJECT_Path=PROJECT_Path, 
                        ID_list=ID_list, 
                        project_tag=project_tag, 
                        reg_tif_file_folder=reg_tif_file_folder,
                        reg_tif_file_tag=reg_tif_file_tag,
                        metadata_file=metadata_file,
                        RESULTS_foldername=RESULTS_foldername,
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

# %% BATCH COLLECTION OF RESULTS

#PROJECT_Path = "/Volumes/Media/Workspace/MotilA example files/single_file/"
PROJECT_Path = "../example project/Data/"
                                          # define the path to the project folder; is the same as in the batch
                                          # processing step and can be omitted if already defined
#RESULTS_Path = "/Volumes/Media/Workspace/MotilA example files/single_file/Analysis/MG_motility/"
RESULTS_Path = "../example project/Analysis/MG_motility/"
                                          # define the path to the results folder; in here, the combined results
                                          # of the cohort analysis will be saved; can be absolute or relative to the
                                          # location of this script
ID_list = ["ID240103_P17_1", "ID240321_P17_3"]
                                          # define the list of all IDs to be processed in PROJECT_Path; 
                                          # names must be exact names of the ID folders; is the same as in the batch
                                          # processing step and can be omitted if already defined
project_tag = "TP000"                     # define the tag of the project (folder) to be analyzed;
                                          # all folders in the ID-folders containing this tag will be processed;
                                          # is the same as in the batch processing step and can be omitted if already defined
motility_folder = "motility_analysis"     # folder name containing motility analysis results in each ID folder/project_tag folder;
                                          # must be exact; wherein, all projection center folders therein will be
                                          #  processed to collect the results

# don't forget to init the logger (if not already done)
log = mt.logger_object()
log.log("logger started for TEST/DEBUG RUN: COLLECTING RESULTS.")
log.log("Test project: "+str(PROJECT_Path))
log.log(f"Mouse IDs: {ID_list}")
log.log(f"Group: {project_tag}")

mt.batch_collect(PROJECT_Path=PROJECT_Path, 
                 ID_list=ID_list, 
                 project_tag=project_tag, 
                 motility_folder=motility_folder,
                 RESULTS_Path=RESULTS_Path,
                 log=log)


# %% END