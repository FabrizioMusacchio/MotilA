"""
Public compatibility layer for the MotilA pipeline.

The implementation is split across focused modules, while this module preserves
MotilA's historical public import path. Existing scripts can continue importing
functions from ``motila.motila``.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import warnings

from .batch import (
    BatchErrorRecord,
    BatchImageRecord,
    BatchProcessedRecord,
    BatchProcessingResult,
    BatchRawYamlTemplateRecord,
    BatchRawYamlTemplateResult,
    BatchSkippedRecord,
    batch_collect,
    batch_collect_old,
    batch_create_thorlabs_raw_yaml_templates,
    batch_process_stacks,
    batch_process_stacks_old,
    discover_bids_like_batch_images)
from .core import hello_world
from .export import (
    DEFAULT_TABLE_EXPORT_FORMATS,
    _normalize_table_export_formats,
    _normalize_table_export_value,
    export_dataframe)
from .io import (
    SUPPORTED_IMAGE_EXTENSIONS,
    _as_tzcyx,
    _import_omio,
    _is_supported_image_file,
    _prepare_omio_import_environment,
    _purge_partial_imports,
    read_image_stack,
    write_image_stack)
from .motility import motility
from .pipeline import process_stack
from .preprocessing import (
    circular_median_filtering_on_projections,
    extract_and_register_subvolume,
    extract_subvolume,
    gaussian_blurr_filtering_on_projections,
    get_stack_dimensions,
    histogram_equalization,
    histogram_equalization_on_projections,
    histogram_matching,
    histogram_matching_on_projections,
    median_filtering_on_projections,
    reg_2D_images,
    single_slice_circular_median_filtering,
    single_slice_gaussian_blurr_filtering,
    single_slice_median_filtering,
    spectral_unmix)
from .projection import (
    calc_projection_range,
    compare_histograms,
    plot_2D_image,
    plot_2D_image_as_tif,
    plot_histogram,
    plot_histogram_of_projections,
    plot_intensities,
    plot_projected_stack,
    plot_projected_stack_as_tif,
    z_max_project)
from .segmentation import binarize_2D_images, plot_pixel_areas, remove_small_blobs

# turn off warnings:
warnings.filterwarnings("ignore")
# %% PUBLIC API
__all__ = [
    "DEFAULT_TABLE_EXPORT_FORMATS",
    "SUPPORTED_IMAGE_EXTENSIONS",
    "BatchErrorRecord",
    "BatchImageRecord",
    "BatchProcessedRecord",
    "BatchProcessingResult",
    "BatchRawYamlTemplateRecord",
    "BatchRawYamlTemplateResult",
    "BatchSkippedRecord",
    "_as_tzcyx",
    "_import_omio",
    "_is_supported_image_file",
    "_normalize_table_export_formats",
    "_normalize_table_export_value",
    "_prepare_omio_import_environment",
    "_purge_partial_imports",
    "batch_collect",
    "batch_collect_old",
    "batch_create_thorlabs_raw_yaml_templates",
    "batch_process_stacks",
    "batch_process_stacks_old",
    "binarize_2D_images",
    "calc_projection_range",
    "circular_median_filtering_on_projections",
    "compare_histograms",
    "discover_bids_like_batch_images",
    "export_dataframe",
    "extract_and_register_subvolume",
    "extract_subvolume",
    "gaussian_blurr_filtering_on_projections",
    "get_stack_dimensions",
    "hello_world",
    "histogram_equalization",
    "histogram_equalization_on_projections",
    "histogram_matching",
    "histogram_matching_on_projections",
    "median_filtering_on_projections",
    "motility",
    "plot_2D_image",
    "plot_2D_image_as_tif",
    "plot_histogram",
    "plot_histogram_of_projections",
    "plot_intensities",
    "plot_pixel_areas",
    "plot_projected_stack",
    "plot_projected_stack_as_tif",
    "process_stack",
    "read_image_stack",
    "reg_2D_images",
    "remove_small_blobs",
    "single_slice_circular_median_filtering",
    "single_slice_gaussian_blurr_filtering",
    "single_slice_median_filtering",
    "spectral_unmix",
    "write_image_stack",
    "z_max_project"]

# %% DEBUGGING/TESTING
if __name__ == "__main__":
    # For local testing and usage examples, see:
    # - example_scripts in `example_scripts/`
    # - tutorial notebooks in `example_notebooks/`
    pass

# %% END
