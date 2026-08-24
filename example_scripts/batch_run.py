"""
MotilA example script for flexible BIDS-like batch processing.

This script demonstrates the MotilA v1.2.0 batch processor. It discovers image
files in a subject-based project tree, processes each image with MotilA's
existing process_stack workflow, skips already processed outputs if requested,
and writes persistent run/error reports in the project root.

Author: Fabrizio Musacchio, March 20, 2025
Updated for MotilA v1.2.0, August 2026
"""
# %% IMPORTS
from pathlib import Path

import motila as mt
# %% VERIFY IMPORT
mt.hello_world()
# %% SINGLE-FILE EXPLORATION
PROJECT_ROOT = Path("../example_project/Data/")

# Pick one representative file to inspect manually before launching a larger
# batch. Adjust this path to your own project.
single_file = PROJECT_ROOT / "ID240103_P17_1" / "TP000" / "registered" / "reg.tif"

if single_file.exists():
    image, metadata = mt.read_image_stack(single_file)
    print(f"Single-file check: shape={image.shape}, axes={metadata.get('axes', 'N/A')}")
else:
    print(f"Single-file check skipped; file not found: {single_file}")
# %% BATCH DISCOVERY SETTINGS
subject_ids = ["ID240103_P17_1", "ID240321_P17_3"]

# Set subject_ids=None to process all folders whose names start with
# subject_prefix.
subject_prefix = "ID"

# Flexible folder levels below each subject. Each tuple describes one level and
# can contain one or more name fragments. Empty levels and None are skipped.
tag_folder_levels = [
    ("TP000",),
    ("registered",)]

# Leave image_patterns as None to use MotilA defaults:
# ("*.ome.tif", "*.ome.tiff", "*.tif", "*.tiff", "*.czi", "*.lsm", "*.raw")
image_patterns = None

# Uncomment and adapt this if you only want specific image names/types:
# image_patterns = ("*reg*.ome.tif", "*reg*.tif")

exclude_name_contains = ("Preview",)
# %% MOTILA PROCESSING SETTINGS
processing_options = {
    "MG_channel": 0,
    "N_channel": 1,
    "two_channel": True,
    "projection_center": 23,
    "projection_layers": 44,
    "histogram_ref_stack": 0,
    "blob_pixel_threshold": 100,
    "regStack2d": False,
    "regStack3d": True,
    "template_mode": "max",
    "spectral_unmixing": True,
    "hist_equalization": True,
    "hist_equalization_clip_limit": 0.1,
    "hist_equalization_kernel_size": (128, 128),
    "hist_match": True,
    "max_xy_shift_correction": 100,
    "threshold_method": "otsu",
    "compare_all_threshold_methods": True,
    "gaussian_sigma_proj": 1.0,
    "spectral_unmixing_amplifyer": 1,
    "spectral_unmixing_median_filter_window": 3,
    "median_filter_slices": "circular",
    "median_filter_window_slices": 1.55,
    "median_filter_projections": "circular",
    "median_filter_window_projections": 1.55,
    "clear_previous_results": False,
    "debug_output": False,
    "stats_plots": False,
    "table_export_formats": ("excel",)}

load_options = {
    # Keep False for large projects if you do not want a preflight load before
    # process_stack. Set True if you want load failures classified explicitly.
    "preflight": False}

save_options = {
    # Validates that MotilA wrote the expected final result table.
    "validate_outputs": True}
# %% RUN MOTILA BATCH PROCESSING
log = mt.logger_object()
log.log("logger started for MotilA flexible batch run.")
log.log(f"Project root: {PROJECT_ROOT}")
log.log(f"Subject IDs: {subject_ids}")

result = mt.batch_process_stacks(
    project_root        = PROJECT_ROOT,
    subject_ids         = subject_ids,
    subject_prefix      = subject_prefix,
    tag_folder_levels   = tag_folder_levels,
    image_patterns      = image_patterns,
    exclude_name_contains= exclude_name_contains,
    skip_processed      = True,
    results_folder_name = "motility_analysis",
    organize_by_image   = True,
    metadata_file       = "metadata.xls",
    load_options        = load_options,
    processing_options  = {**processing_options, "log": log},
    save_options        = save_options,
    log                 = log,
    verbose             = True)

print(f"Processed: {len(result.processed)}")
print(f"Skipped:   {len(result.skipped)}")
print(f"Failed:    {len(result.failed)}")
print(f"Run report: {result.report_path}")
print(f"Error report: {result.error_report_path}")
# %% OPTIONAL BATCH COLLECTION OF RESULTS
RESULTS_PATH = Path("../example_project/Analysis/MG_motility/")

collection_result = mt.batch_collect(
    project_root            = PROJECT_ROOT,
    subject_ids             = subject_ids,
    subject_prefix          = subject_prefix,
    tag_folder_levels       = tag_folder_levels,
    image_patterns          = image_patterns,
    exclude_name_contains   = exclude_name_contains,
    results_folder_name     = "motility_analysis",
    organize_by_image       = True,
    RESULTS_Path            = RESULTS_PATH,
    table_export_formats    = ("excel",),
    log                     = log,
    verbose                 = True)

print(f"Collected result folders: {len(collection_result.collected)}")
print(f"Skipped during collection: {len(collection_result.skipped)}")
# %% END
