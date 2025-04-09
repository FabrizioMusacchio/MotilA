""" MotilA Utilities Module
=======================

This module contains utility functions and helper classes used throughout the MotilA pipeline
for analyzing microglial fine process motility in 4D/5D image stacks.

Contents:
---------
• Folder operations (creation, filtering by name)
• Process timing and logging utilities
• RAM usage monitoring
• TIFF file axis verification and correction
• General system introspection tools

Functions:
----------
- check_folder_exist_create(path, verbose)
- getfile()
- filterfolder_by_string(path_to_folder, search_string)
- filterfiles_by_string(path_to_folder, search_string)
- calc_process_time_logger(t0, ...)
- print_ram_usage()
- print_ram_usage_in_loop()
- tiff_axes_check_and_correct(fname)

Classes:
--------
- logger_object: flexible file-based logger with timestamped entries

Note:
-----
This module is designed to be imported into the main MotilA scripts and can also be reused 
independently for other image processing tasks.

Author: Fabrizio Musacchio  
Date: September 2023
License: GPL-3.0
"""
# %% IMPORTS
import os
import sys
import time
import logging
import psutil
from datetime import datetime
import tifffile
import numpy as np
from pathlib import Path
# %% HELLO WORLD FUNCTION
def hello_world_utils():
    """
    Prints a friendly message to the user.
    """
    print("Hello, World! Welcome to MotilA (from utils.py)!")
# %% FOLDER OPERATION FUNCTIONS

def check_folder_exist_create(path, verbose=True):
    """
    Check whether a folder exists at the specified path, and create it if it does not.

    Parameters:
    -----------
    path : str or Path
        The directory path to check or create.
    verbose : bool, optional (default=True)
        If True, prints a message indicating whether the folder was created or already exists.

    Returns:
    --------
    None

    Notes:
    ------
    - Ensures the specified folder is available before performing file operations.
    - Useful for logging, output saving, or checkpointing during pipeline execution.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        if verbose:
            print(f"    created folder: {path}.")
    else:
        if verbose:
            print(f"    folder already exists: {path} ")

def getfile():
    """
    Retrieve the name of the currently executing script or fallback to "console" if run interactively.

    This function returns the filename of the main Python script. If executed in an interactive
    environment (e.g., IPython or Jupyter Notebook), it returns the string "console".

    Returns:
    --------
    str
        The filename of the main executing script or "console" if run interactively.

    Notes:
    ------
    - Useful for dynamically naming log files or output paths based on the script being executed.
    - Handles edge cases where the script is executed from a shell, notebook, or other environments.
    """
    try:
        sys.modules['__main__'].__file__
        if sys.modules['__main__'].__file__ == "<input>":
            file_name = "console"
        else:
            file_name = os.path.basename(os.path.abspath(sys.modules['__main__'].__file__))
    except:
        file_name = "console"

    return file_name

def filterfolder_by_string(path_to_folder, search_string):
    """
    Scans for folders in a specified directory and returns those that match a given search string.

    Parameters:
    -----------
    path_to_folder : str or Path
        The directory path where folders should be searched.
    search_string : str
        The substring to look for in folder names.

    Returns:
    --------
    MatchingFolders_Indices : list of int
        Indices of matching folders in the sorted directory listing.
    folderlist_matching : list of str
        List of folder names that match the search string.
    folderlist : list of str
        Full list of folder names in the directory.

    Notes:
    ------
    - Only directories (not files) are considered.
    - The function sorts the folder list before filtering.
    - Matching is case-sensitive.
    """
    folderlist = sorted(os.listdir(path_to_folder))
    entry = 0
    MatchingFolders_Indices = []
    folderlist_matching = []
    for folder in folderlist:
        if search_string in folder and os.path.isdir((path_to_folder + folder)):
            MatchingFolders_Indices.append(entry)
            folderlist_matching.append(folder)
        entry += 1
    return (MatchingFolders_Indices, folderlist_matching, folderlist)

def filterfiles_by_string(path_to_folder, search_string):
    """
    Scans for files in a specified directory and returns those that match a given search string.

    Parameters:
    -----------
    path_to_folder : str or Path
        The directory path where files should be searched.
    search_string : str
        The substring to look for in file names.

    Returns:
    --------
    MatchingFiles_Indices : list of int
        Indices of matching files in the sorted directory listing.
    filelist_matching : list of str
        List of file names that match the search string.
    filelist : list of str
        Full list of file names in the directory.

    Notes:
    ------
    - Only files (not directories) are considered.
    - The function sorts the file list before filtering.
    - Matching is case-sensitive.
    """
    folderlist = sorted(os.listdir(path_to_folder))
    entry = 0
    MatchingFolders_Indices = []
    folderlist_matching = []
    for folder in folderlist:
        if search_string in folder and os.path.isfile((path_to_folder + folder)):
            MatchingFolders_Indices.append(entry)
            folderlist_matching.append(folder)
            # print(entry, folder)
        entry += 1
    return (MatchingFolders_Indices, folderlist_matching, folderlist)

# %% PROCESSING TIME FUNCTIONS
def calc_process_time_logger(t0, verbose=False, leadspaces="",  unit="min", process=""):
    """
        Calculates the processing time/time difference for a given input time and the current time

    Usage:
        Process_t0 = time.time()
        #your process
        calc_process_time(Process_t0, verbose=True, leadspaces="  ")

        :param t0:              starting time stamp
        :param verbose:         verbose? True or False
        :param leadspaces:      pre-fix, e.g., some space in front of any verbose output
        :param output:          provide an output (s. below)? True or False
        :return: dt (optional)  the calculated processing time
    :rtype:
    """
    dt = time.time() - t0
    if verbose:
        if unit=="min":
            print(leadspaces + process + f'process time: {round(dt / 60, 2)} min')
        elif unit=="sec":
            print(leadspaces + process + f'process time: {round(dt , 10)} sec')
    if unit=="min":
        out_str = leadspaces + process + f'process time: {round(dt / 60, 2)} min'
    elif unit=="sec":
        out_str = leadspaces + process + f'process time: {round(dt , 10)} sec'
    return dt, out_str


# %% LOGGING FUNCTIONS
class logger_object:
    """ Class, that creates a logger object with some base functions:

        __init__            initializes the logger object
        type                tells user type of this class object
        log(input, space)   logs input with optional preceding spaces
        logc(input)         logs input with chapter-separator
        stop                stops the logger object and the logging
        __del__             stops the logger object and the logging before deleting the object
    """

    def __init__(self, logger_path=""):
        print(f"creating logger object...", end="")
        if logger_path == "":
            self.logfile_path = "logs/"
        else:
            self.logfile_path = logger_path+"/logs/"
        check_folder_exist_create(self.logfile_path, verbose=False)
        # self.logfile_name = os.path.basename(__file__) + " " + datetime.now().strftime(
        #         "%Y-%m-%d (%Hh%Mm%Ss)") + ".log"
        self.logfile_name = getfile() + " " + datetime.now().strftime("%Y-%m-%d (%Hh%Mm%Ss)") + ".log"
        self.logfile_fullpath = os.path.join(self.logfile_path, self.logfile_name)

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.file_handler = logging.FileHandler(self.logfile_fullpath)
        self.file_handler.setLevel(logging.DEBUG)
        # formatter = logging.Formatter("%(asctime)s %(filename)s, L%(lineno)04d, %(funcName)s: %(message)s")
        #self.formatter = logging.Formatter("%(asctime)s %(filename)s (L%(lineno)04d): %(message)s")
        self.formatter = logging.Formatter(f"%(asctime)s {getfile()} (L%(lineno)04d): %(message)s")
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)
        # self.logger = logger
        print(f"done.")

    def type(self):
        print("I'm a logger object")

    def log(self, input, spaces=0, printconsole=True):
        self.logger.info(" " * spaces + input)
        if printconsole:
            print(" " * spaces + input)

    def logc(self, input, printconsole=True):
        self.logger.info("===================================================================")
        self.logger.info(input)
        if printconsole:
            print("===================================================================")
            print(input)
            
    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        dt, dt_string = calc_process_time_logger(t0, verbose=verbose, leadspaces=" "*spaces, unit=unit,
                                                 process=process)
        self.log(dt_string, printconsole=False)
        return dt

    def stop(self, printconsole=True):
        self.log("logging stopped.", printconsole=printconsole)
        #self.logger.handlers[0].stream.close()
        #self.logger.removeHandler(self.logger.handlers[0])
        if hasattr(self.file_handler, "stream"):
            self.file_handler.stream.close()
        self.logger.removeHandler(self.file_handler)

# %% RAM USAGE FUNCTIONS
def print_ram_usage_in_loop(indent=0):
    """
    Print the current RAM usage continuously in a loop-friendly format.

    This function is designed to be called repeatedly within a loop to monitor
    real-time memory usage. It updates the same console line without adding newlines,
    making it suitable for progress monitoring in iterative processes.

    Parameters:
    -----------
    indent : int, optional (default=0)
        Number of spaces to prepend to the output for indentation.

    Returns:
    --------
    None
        The function outputs the current RAM usage to the console and does not return any value.

    Notes:
    ------
    - RAM usage is measured for the current process.
    - Output is formatted in megabytes (MB) with two decimal places.
    """
    process = psutil.Process(os.getpid())
    ram_usage_MB = process.memory_info().rss / 1024 ** 2
    sys.stdout.write(f"\r{' ' * indent}Current RAM usage: {ram_usage_MB:.2f} MB")
    sys.stdout.flush()  # Ensures the line is updated without newlines

def print_ram_usage(indent=0):
    """
    Print the current RAM usage of the process.

    This function prints the resident memory usage (RAM) of the current Python process,
    formatted in megabytes (MB). It is useful for tracking memory consumption at 
    specific checkpoints in a script.

    Parameters:
    -----------
    indent : int, optional (default=0)
        Number of spaces to prepend to the output line for indentation.

    Returns:
    --------
    None
        The function prints the RAM usage to the console and does not return any value.

    Notes:
    ------
    - RAM usage is measured using the `psutil` library.
    - Output is displayed in MB with two decimal places.
    """
    process = psutil.Process(os.getpid())
    ram_usage_MB = process.memory_info().rss / 1024 ** 2
    print(f"{' ' * indent}Current RAM usage: {ram_usage_MB:.2f} MB")

# %% TIFF FILE FUNCTIONS
def tiff_axes_check_and_correct(fname):
    """
    Check and correct the axis order of a TIFF file to match TZCYX or TZYX.

    This function loads a TIFF file, checks its axis labels (as recorded in ImageJ metadata),
    and reorders the array to conform to standard axis conventions (TZCYX for 5D, TZYX for 4D).
    If the axes are already correct, the original file path is returned. If correction is needed,
    a new TIFF file is saved with the corrected axis order and updated metadata.

    Parameters:
    -----------
    fname : str or Path
        Path to the input TIFF file.

    Returns:
    --------
    Path
        Path to the corrected TIFF file (or the original if no correction was necessary).

    Raises:
    -------
    ValueError
        If the TIFF file does not contain the required axes (T, Z, Y, X).

    Notes:
    ------
    - Expected axis order is either TZYX (for single-channel) or TZCYX (for multi-channel).
    - The corrected TIFF is saved in the same folder as the original, prefixed with "axes_corrected_".
    - ImageJ metadata and spatial resolution information are preserved in the output file.
    - This is especially useful when handling TIFFs generated by software that may reorder axes.
    """
    with tifffile.TiffFile(fname) as tif:
        volume = tif.asarray()
        axes = tif.series[0].axes  # Get axis order as a string
        metadata = {
            "imagej_metadata": tif.imagej_metadata,
            "x_resolution": tif.pages[0].tags['XResolution'].value,
            "y_resolution": tif.pages[0].tags['YResolution'].value,
            "resolution_unit": tif.pages[0].tags['ResolutionUnit'].value}
        if metadata["imagej_metadata"] is None:
            metadata["imagej_metadata"] = {}
    
    # ensure required axes are present:
    required_axes = set("TZYX")
    missing_axes = required_axes - set(axes)
    if missing_axes:
        raise ValueError(f"Missing required axes: {missing_axes} in {axes}")

    # define/ the correct order:
    expected_order = "TZCYX" if "C" in axes else "TZYX"
    
    # if the axes are already correct, return the original file:
    if axes == expected_order:
        print(f"No correction needed. Axes are already {axes}.")
        return fname

    # determine the mapping of current axes to expected order:
    axis_map = {axis: i for i, axis in enumerate(axes)}
    new_order = [axis_map[axis] for axis in expected_order if axis in axis_map]

    # rearrange the array:
    volume = np.transpose(volume, new_order)
    corrected_axes = "".join(expected_order[i] for i in range(len(new_order)))
    
    print(f"Found axes: {axes}, rearranged to: {corrected_axes}")
    
    # update the imagej_metadata:
    metadata['imagej_metadata']['axes'] = corrected_axes
    
    # save the corrected volume:
    IMG_File = Path(fname).name
    DATA_Path = Path(fname).parent
    corrected_fname = Path(DATA_Path).joinpath("axes_corrected_" + IMG_File)
    tifffile.imwrite(corrected_fname, volume, 
                    metadata=metadata['imagej_metadata'],
                    resolution=(metadata['x_resolution'][0] / metadata['x_resolution'][1],
                                metadata['y_resolution'][0] / metadata['y_resolution'][1]),
                    compression='zlib',
                    compressionargs={'level': 9},
                    photometric='minisblack',
                    bigtiff=False, imagej=True)
    print(f"Corrected axes saved to: {corrected_fname}")
    return corrected_fname
# %% END