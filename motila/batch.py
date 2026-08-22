"""
Batch processing and result collection for MotilA.

This module contains the current batch-processing wrapper and cohort-level
result aggregation. It is intentionally separated to make room for a future,
more extensive batch processor.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import glob
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

from motila.utils import filterfiles_by_string, filterfolder_by_string, print_ram_usage
from .export import DEFAULT_TABLE_EXPORT_FORMATS, export_dataframe
from .io import SUPPORTED_IMAGE_EXTENSIONS
from .pipeline import process_stack
# %% BATCH PROCESSING

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
                  debug_output=False, stats_plots=False,
                  table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Batch-processing wrapper that applies the MotilA pipeline to multiple 4D/5D
    multiphoton imaging stacks.

    This function detects all project folders matching a given tag, loads the
    associated registered stacks, and processes each dataset using
    :func:`process_stack`. The function handles metadata loading, optional
    registration, spectral unmixing, contrast adjustments, thresholding, and
    motility extraction. Results for each dataset are written into structured
    output directories.

    Parameters
    -----------
    PROJECT_Path : str or Path
        The base directory containing the image stacks.
    ID_list : list of str, optional
        List of sample or subject IDs to be processed (default is an empty list).
    project_tag : str, optional
        Tag used to identify project folders (default is "TP000").
    reg_tif_file_folder : str, optional
        Folder name containing registered image files (default is "registered").
    reg_tif_file_tag : str, optional
        Tag used to filter for registered image files (default is "reg").
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
    table_export_formats : str or iterable of str, optional
        Table export formats passed to :func:`process_stack`. Defaults to
        ``("excel",)``. Add ``"csv"`` and/or ``"yaml"`` for sidecar plain-text
        exports next to the default Excel files.

    Returns
    --------
    None
        The function processes each stack and saves the results in the specified output directory.

    Notes
    ------
    * The function scans for project folders and extracts relevant image files.
    * Metadata files, if present, override certain function parameters.
    * Each stack is processed using :func:`process_stack`.
    * Results are saved in subdirectories within `RESULTS_Path`, organized by projection center.
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
                
            # check whether one or more supported image files including the reg_tif_file_tag are present:
            reg_tif_file = []
            for extension in SUPPORTED_IMAGE_EXTENSIONS:
                reg_tif_file.extend(
                    glob.glob(Current_TP_Folder + reg_file_folder[0] + "/*" + reg_tif_file_tag + "*" + extension)
                )
            if len(reg_tif_file)==0:
                supported = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
                log.log(f"  WARNING: no supported image file ({supported}) with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder -> skipping this folder.")
                continue
            elif len(reg_tif_file)>1:
                log.log(f"  AMBIGUITY WARNING: found more than 1 supported image file with tag '{reg_tif_file_tag}' in '{reg_tif_file_folder}' folder -> skipping this folder.")
                for i in range(len(reg_tif_file)):
                    log.log(f"    {reg_tif_file[i]}")
                continue
            else:
                log.log(f"  {len(reg_tif_file)} image file with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder in {TP_folderlist[iTP]} in {Current_ID}.")
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

            # main batch loop iterating the image file in the reg_file_folder over found projection centers:
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
                              stats_plots=stats_plots,
                              table_export_formats=table_export_formats)
        log.log("\n============================================================\n")
            
    _ = log.logt(Total_batch_Process_t0, verbose=True, spaces=0, unit="sec", process="total batch ")
    if debug_output: print_ram_usage()

# %% BATCH COLLECTION

def batch_collect(PROJECT_Path, ID_list=[], project_tag="TP000", motility_folder="motility_analysis",
                  RESULTS_Path="batch_results", log="",
                  table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Collect motility outputs from multiple processed stacks and consolidate them
    into combined tables.

    This function scans all project subfolders, loads the output files generated
    by the MotilA pipeline (motility metrics, brightness tables, and pixel area
    summaries), merges them across stacks or animals, and saves the resulting
    DataFrames into a summary directory.

    Parameters
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
    table_export_formats : str or iterable of str, optional
        Table export formats. Defaults to ``("excel",)`` for backward
        compatibility. Add ``"csv"`` and/or ``"yaml"`` to write sidecar
        plain-text exports next to the default Excel files.

    Returns
    --------
    None
        Saves consolidated DataFrames as Excel files and optional CSV/YAML
        sidecar files in the `RESULTS_Path` directory.

    Notes
    ------
    Expected folder structure::

        ID/
            project_tag*/motility_analysis/projection_center*/

    Extracted files include:

    * ``motility_analysis.xlsx``
    * ``Normalized average brightness of each stack.xlsx``
    * ``pixel area sums.xlsx``
    
    The function saves three consolidated DataFrames in `RESULTS_Path`.   
    
    Motility metrics are averaged across projection centers and across time
    points before export.
    
    Additional excel files are saved as:
    
    * ``all_motility.xlsx``
    * ``all_brightness.xlsx``
    * ``all_pixel_area.xlsx``
    * ``average_motility.xlsx``.
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
        export_dataframe(
            motility_df,
            RESULTS_Path / "all_motility.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )

    if brightness_data:
        brightness_df = pd.concat(brightness_data, ignore_index=True)
        export_dataframe(
            brightness_df,
            RESULTS_Path / "all_brightness.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )

    if pixel_area_data:
        pixel_area_df = pd.concat(pixel_area_data, ignore_index=True)
        export_dataframe(
            pixel_area_df,
            RESULTS_Path / "all_pixel_areas.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )
        
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
                
    export_dataframe(
        motility_avrg_df,
        RESULTS_Path / "average_motility.xlsx",
        table_export_formats=table_export_formats,
    )

    log.log(f"Collected data saved in {RESULTS_Path}")

# %% END
