"""
Single-stack MotilA processing pipeline.

This module keeps the high-level single-stack workflow separate from the public
``motila.motila`` compatibility layer.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
from datetime import datetime
import gc
import os
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd
import zarr

from motila.utils import check_folder_exist_create, print_ram_usage
from .export import DEFAULT_TABLE_EXPORT_FORMATS, _normalize_table_export_formats, export_dataframe
from .io import SUPPORTED_IMAGE_EXTENSIONS, _is_supported_image_file, read_image_stack
from .motility import motility
from .preprocessing import (
    extract_and_register_subvolume,
    extract_subvolume,
    gaussian_blurr_filtering_on_projections,
    histogram_equalization,
    histogram_equalization_on_projections,
    histogram_matching,
    histogram_matching_on_projections,
    median_filtering_on_projections,
    circular_median_filtering_on_projections,
    reg_2D_images,
    single_slice_circular_median_filtering,
    single_slice_gaussian_blurr_filtering,
    single_slice_median_filtering,
    spectral_unmix)
from .projection import (
    calc_projection_range,
    compare_histograms,
    plot_histogram_of_projections,
    plot_intensities,
    plot_projected_stack,
    z_max_project)
from .segmentation import binarize_2D_images, plot_pixel_areas, remove_small_blobs
# %% SINGLE-STACK PIPELINE

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
                  debug_output=False, stats_plots=False,
                  table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    Process a single 4D or 5D multiphoton imaging stack and extract microglial
    motility metrics. This is the main entry point of the MotilA pipeline.

    The function loads an OMIO-supported image stack, optionally performs 2D or 3D registration,
    applies spectral unmixing and contrast corrections, generates z-projections,
    segments microglial structures, and computes motility metrics such as gain,
    loss and stability. Outputs are written to a structured results directory.

    Parameters
    -----------
    fname : str or Path
        Path to the input image file. Supported formats are TIFF/OME-TIFF,
        CZI, Thorlabs RAW and LSM.
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
    table_export_formats : str or iterable of str, optional
        Table export formats. Defaults to ``("excel",)`` for backward
        compatibility. Add ``"csv"`` and/or ``"yaml"`` to write sidecar
        plain-text exports next to the default Excel files.

    Returns
    -------
    None
        The function writes processed images, projections, segmentation masks,
        motility metrics and auxiliary outputs to ``RESULTS_Path``.

    Notes
    ------
    * Loads and processes microglia fluorescence images for motility analysis.
    * Supports optional 3D and 2D registration.
    * 2D registration can use either phase cross-correlation or pystackreg (StackReg) if ``usepystackreg`` is True.
    * Includes histogram-based contrast adjustments and thresholding.
    * Computes motility metrics such as gain, loss, and stability.
    * Saves processed images, projections, and statistical results in a designated output directory.
    * Deletes intermediate large datasets to optimize memory usage.
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
    
    if isinstance(fname, str):
        fname = Path(fname)  # convert string to Path if it's a string
    if _is_supported_image_file(fname):
        image_stack, image_metadata = read_image_stack(fname)
        I_shape = list(image_stack.shape)
        log.log(f"Loaded image via OMIO with shape {I_shape} and axes {image_metadata.get('axes', 'N/A')}.")
    else:
        supported = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
        log.log(f"Error: File {fname} is not a supported image file ({supported})!")
        raise ValueError(f"Error: File {fname} is not a supported image file ({supported})!")
 
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
        "stats_plots": stats_plots,
        "table_export_formats": _normalize_table_export_formats(table_export_formats)}
    parameters_list = [{"Parameter": key, "Value": value} for key, value in parameters.items()]
    processing_parameters_df = pd.DataFrame(data=parameters_list)
    export_dataframe(
        processing_parameters_df,
        excel_file_path,
        table_export_formats=table_export_formats,
        index=False,
    )
        

    # extract sub-volume with optional intra-sub-stack registration:
    if regStack3d:
        if two_channel:
            MG_sub, N_sub, I_shape_new, Z = extract_and_register_subvolume(fname, I_shape, 
                                                       projection_layers, projection_range,
                                                       MG_channel=MG_channel, 
                                                       log=log, template_mode=template_mode,
                                                       two_channel=two_channel,
                                                       max_xy_shift_correction=max_xy_shift_correction,
                                                       debug_output=debug_output,
                                                       image_stack=image_stack,
                                                       image_metadata=image_metadata)
        else:
            MG_sub, I_shape_new, Z = extract_and_register_subvolume(fname, I_shape, 
                                                       projection_layers, projection_range,
                                                       MG_channel=MG_channel, 
                                                       log=log, template_mode=template_mode,
                                                       two_channel=two_channel,
                                                       max_xy_shift_correction=max_xy_shift_correction,
                                                       debug_output=debug_output,
                                                       image_stack=image_stack,
                                                       image_metadata=image_metadata)
    
        # correct I_shape for the new shape after registration (if any):
        I_shape[-2] = I_shape_new[-2]
        I_shape[-1] = I_shape_new[-1]
    else:
        if two_channel:
            MG_sub, N_sub, Z = extract_subvolume(fname, I_shape=I_shape, projection_layers=projection_layers,
                                       projection_range=projection_range, log=log, two_channel=two_channel,
                                       channel=MG_channel, image_stack=image_stack,
                                       image_metadata=image_metadata)
        else:
            MG_sub, Z = extract_subvolume(fname, I_shape=I_shape, projection_layers=projection_layers,
                                       projection_range=projection_range, log=log, two_channel=two_channel,
                                       channel=MG_channel, image_stack=image_stack,
                                       image_metadata=image_metadata)

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
    intensity_means = plot_intensities(
        MG_projection_reg,
        log,
        plot_path,
        I_shape_reg,
        table_export_formats=table_export_formats,
    )
    export_dataframe(
        pd.DataFrame(data=100*intensity_means/intensity_means[0],
                     columns=["relative brightness drop"]),
        os.path.join(plot_path, "relative brightness drops.xlsx"),
        table_export_formats=table_export_formats,
    )
 
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
                                                stats_plots=stats_plots,
                                                table_export_formats=table_export_formats)
    plot_pixel_areas(
        MG_areas=MG_binarized_projection_areas,
        log=log,
        plot_path=plot_path,
        I_shape=I_shape_reg,
        table_export_formats=table_export_formats,
    )

    if debug_output: print_ram_usage()

    _, _ = motility(
        MG_binarized_projection,
        I_shape=I_shape_reg,
        log=log,
        plot_path=plot_path,
        ID=ID,
        group=group,
        table_export_formats=table_export_formats,
    )
    
    _ = log.logt(Total_Process_t0, verbose=True, spaces=2, unit="sec", process="total processing time")
    if debug_output: print_ram_usage()

# %% END
