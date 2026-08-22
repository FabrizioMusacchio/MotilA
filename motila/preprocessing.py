"""
Preprocessing helpers for MotilA.

This module contains stack dimension inspection, subvolume extraction,
registration, spectral unmixing, contrast normalization, and filtering steps.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import gc
from pathlib import Path
import time

import numpy as np
from pystackreg import StackReg
import scipy as sp
from skimage import exposure, transform
import skimage.filters as filter
import skimage.morphology
from skimage.registration import phase_cross_correlation
import zarr

from motila.utils import print_ram_usage, print_ram_usage_in_loop
from .io import read_image_stack
# %% STACK INSPECTION AND SUBVOLUME EXTRACTION

def get_stack_dimensions(fname):
    """
    Retrieves the dimensions of an image stack after OMIO normalization.

    Parameters
    -----------
    fname : str or Path
        The path to the image file.

    Returns
    --------
    list
        A list representing the shape of the image stack, ordered as TZCYX.

    Raises:
    -------
    ValueError
        If the provided file format is not supported.

    Notes
    ------
    - OMIO normalizes TIFF, CZI, RAW and LSM inputs to TZCYX.
    - Some formats require reading the image data to determine the normalized shape.
    """
    image, _ = read_image_stack(fname)
    return list(image.shape)

def extract_subvolume(fname, I_shape, projection_layers, projection_range, log,
                      two_channel=False, channel=0, image_stack=None,
                      image_metadata=None):
    """
    Extracts sub-volumes from a multi-dimensional image stack and stores them in a Zarr format.

    Parameters
    -----------
    fname : str or Path
        Path to the image file.
    I_shape : tuple
        Shape of the input image stack in OMIO-normalized TZCYX order.
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

    Returns
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
        If the provided image file format is not supported.

    Notes
    ------
    - The function converts the OMIO-normalized image stack into a Zarr store for efficient memory access.
    - The extracted sub-volumes are saved in the Zarr format to reduce memory consumption.
    - The function supports both single-channel and two-channel extractions.
    """
    Process_t0 = time.time()
    log.log(f"extracting sub-volumes...")
    
    if image_stack is None:
        image_stack, image_metadata = read_image_stack(fname)
    I_shape = list(image_stack.shape)
    chunks = (1, 1, 1, I_shape[-2], I_shape[-1])
    zarr_path = Path(fname).parent.joinpath(Path(fname).stem + ".zarr")
    # info: we do not compress for speed reasons
    zarr_group = zarr.group(zarr_path, overwrite=True)
    if zarr.__version__ >= "3":
        chunks = tuple(int(x) for x in chunks)
        zarr_group.create_array("image", shape=image_stack.shape, chunks=chunks,
                                dtype=image_stack.dtype, overwrite=True)
    else:
        zarr_group.create_dataset("image", shape=image_stack.shape, chunks=chunks,
                                  dtype=image_stack.dtype)
    zarr_group["image"][:] = image_stack
    zarr_group.attrs["original_file"] = str(fname)
    zarr_group.attrs["ZARR file path"] = str(zarr_path)
    zarr_group.attrs["shape"] = image_stack.shape
    zarr_group.attrs["dtype"] = str(image_stack.dtype)
    zarr_group.attrs["axes"] = "TZCYX"

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
            MG_sub[stack] = I[stack, projection_range[0]:projection_range[1]+1, channel, :, :]
    
    del I
    gc.collect()
    
    _ = log.logt(Process_t0, verbose=True, spaces=2, unit="sec", process=f" sub-volume extracting ")
    
    if two_channel:
        return MG_sub, N_sub, zarr_group
    else:
        return MG_sub, zarr_group

def extract_and_register_subvolume(fname, I_shape, projection_layers, projection_range,
                                   MG_channel, log, two_channel, template_mode="mean",
                                   max_xy_shift_correction=5, debug_output=False,
                                   image_stack=None, image_metadata=None):
    """
    Extracts sub-volumes from a multi-dimensional TIFF image stack, registers them using 
    phase cross-correlation, and saves the results in a Zarr format.

    Parameters
    -----------
    fname : str or Path
        Path to the image file.
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

    Returns
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
        If the provided file is not a supported image file.

    Notes
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
                                                        two_channel=True, channel=MG_channel,
                                                        image_stack=image_stack,
                                                        image_metadata=image_metadata)
    else:
        MG_sub, zarr_group = extract_subvolume(fname, I_shape, projection_layers, projection_range, log,
                                               two_channel=False, channel=MG_channel,
                                               image_stack=image_stack,
                                               image_metadata=image_metadata)

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

# %% SPECTRAL UNMIXING

def spectral_unmix(MG_sub, N_sub, I_shape, zarr_group, projection_layers, log, 
                   median_filter_window=3, amplifyer=2):
    """
    Performs spectral unmixing to reduce channel bleed-through in microglial image stacks.
    It requires a microglial and a neuronal channel and spectral unmixing is performed by 
    simple subtraction of the neuronal signal from the microglial signal.

    Parameters
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

    Returns
    --------
    MG_sub_processed : Zarr dataset
        The spectrally unmixed microglial sub-volume.

    Notes
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

# %% CONTRAST NORMALIZATION

def histogram_equalization(MG_sub, I_shape, projection_layers, log, clip_limit=0.02):
    """
    Applies adaptive histogram equalization to enhance contrast in microglial image stacks.

    Parameters
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

    Returns
    --------
    MG_sub_histeq : ndarray
        The histogram-equalized microglial sub-volume.

    Notes
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

    Parameters
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

    Returns
    --------
    MG_sub_histeq : ndarray
        The histogram-equalized projected microglial sub-volume.

    Notes
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

    Parameters
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

    Returns
    --------
    MG_sub_histeq : ndarray
        The histogram-matched microglial sub-volume.

    Notes
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

    Parameters
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    histogram_ref_stack : int
        Index of the reference stack to which all other stacks' histograms will be matched.
    log : logger_object
        Logging object for recording the process.

    Returns
    --------
    MG_sub_histeq : ndarray
        The histogram-matched projected image stacks.

    Notes
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

# %% FILTERING HELPERS

def median_filtering_on_projections(MG_sub, I_shape, median_filter_window,  log):
    """
    Applies a median filter to each projected stack to reduce noise, using a square kernel.
    
    Parameters
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    median_filter_window : int
        Size of the window for median filtering. If ≤1, filtering is skipped.
    log : logger_object
        Logging object for recording the process.

    Returns
    --------
    MG_sub_median : ndarray
        The median-filtered projected image stacks.

    Notes
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

    Parameters
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    median_filter_window : int
        Radius of the circular structuring element for median filtering. If <1, filtering is skipped.
    log : logger_object
        Logging object for recording the process.

    Returns
    --------
    MG_sub_median : ndarray
        The median-filtered projected image stacks.

    Notes
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

    Parameters
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

    Returns
    --------
    MG_sub_median : zarr dataset
        The median-filtered image stacks stored in Zarr.

    Notes
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

    Parameters
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

    Returns
    --------
    MG_sub_median : zarr dataset
        The median-filtered image stacks stored in Zarr.

    Notes
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

    Parameters
    -----------
    MG_sub : array-like
        The input microglial projections containing image stacks.
    I_shape : tuple
        Shape of the input image stack.
    gaussian_blurr_sigma : float
        Standard deviation for the Gaussian kernel.
    log : logger_object
        Logging object for recording the process.

    Returns
    --------
    MG_sub_gaussian : ndarray
        The Gaussian-blurred image stacks.

    Notes
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

    Parameters
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

    Returns
    --------
    MG_sub_gaussian : ndarray
        The Gaussian-blurred image stack.

    Notes
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

# %% REGISTRATION HELPERS

def reg_2D_images(MG_pro, I_shape, log, histogram_ref_stack, max_xy_shift_correction=50,
                  median_filter_projections=None, median_filter_window_projections=3,
                  usepystackreg=False):
    """
    Registers 2D z-projection images using phase cross-correlation or pystackreg.

    Parameters
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

    Returns
    --------
    MG_pro_bin_reg_clipped : ndarray
        The registered and cropped image stack.
    I_shape_create : tuple
        New shape of the registered stack after cropping.

    Notes
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

# %% END
