from .motila import (
    hello_world,
    read_image_stack,
    write_image_stack,
    process_stack,
    batch_process_stacks,
    batch_process_stacks_old,
    batch_collect,
    batch_collect_old,
    discover_bids_like_batch_images,
    batch_create_thorlabs_raw_yaml_templates,
)
from .utils import (
    tiff_axes_check_and_correct,
    check_folder_exist_create,
    filterfolder_by_string,
    filterfiles_by_string,
    logger_object
)

__all__ = [
    "hello_world",
    "read_image_stack",
    "write_image_stack",
    "process_stack",
    "batch_process_stacks",
    "batch_process_stacks_old",
    "batch_collect",
    "batch_collect_old",
    "discover_bids_like_batch_images",
    "batch_create_thorlabs_raw_yaml_templates",
    "tiff_axes_check_and_correct",
    "check_folder_exist_create",
    "filterfolder_by_string",
    "filterfiles_by_string",
    "logger_object",
]

# expose the motila submodule for backward compatibility
from . import motila as motila
