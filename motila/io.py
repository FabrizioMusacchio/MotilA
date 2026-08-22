"""
Image I/O helpers for MotilA.

This module keeps OMIO-based image reading and writing isolated from the core
motility workflow. All image stacks entering MotilA are normalized to TZCYX by
OMIO before downstream processing uses them.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
# %% IMAGE I/O CONSTANTS
SUPPORTED_IMAGE_EXTENSIONS = (".tif", ".tiff", ".czi", ".raw", ".lsm")

# %% IMAGE I/O HELPERS

def _is_supported_image_file(fname):
    """Return True if OMIO can handle the image file extension."""
    return Path(fname).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS

def _prepare_omio_import_environment():
    """Prepare writable cache locations for OMIO's optional Napari dependencies."""
    cache_dir = Path(tempfile.gettempdir()).joinpath("motila_numba_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(cache_dir))

def _purge_partial_imports(module_prefixes):
    """Remove partially imported modules after a failed lazy import."""
    for module_name in list(sys.modules):
        if any(module_name == prefix or module_name.startswith(prefix + ".")
               for prefix in module_prefixes):
            sys.modules.pop(module_name, None)

def _import_omio():
    """
    Import OMIO lazily and keep terminal/CI runs robust against Napari cache setup.

    OMIO itself is used only for image I/O here, but its optional Napari support
    can initialize cache files during import. If the user's home cache is not
    writable, retry with a temporary home directory.
    """
    _prepare_omio_import_environment()
    try:
        import omio as om
        return om
    except (RuntimeError, PermissionError, FileNotFoundError):
        _purge_partial_imports(("omio", "napari", "numba"))
        fallback_home = Path(tempfile.gettempdir()).joinpath("motila_omio_home")
        fallback_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(fallback_home)
        _prepare_omio_import_environment()
        import omio as om
        return om

# %% IMAGE STACK READING AND WRITING

def read_image_stack(fname):
    """
    Read an image stack with OMIO and return an OME-style ``TZCYX`` image.

    Supported input formats are TIFF/OME-TIFF, CZI, Thorlabs RAW and LSM.
    OMIO normalizes all supported inputs to ``TZCYX`` before MotilA receives
    the array, so downstream processing can use one consistent axis order.
    """
    if not _is_supported_image_file(fname):
        supported = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
        raise ValueError(f"Unsupported image file '{fname}'. Supported extensions: {supported}.")

    om = _import_omio()
    image, metadata = om.imread(fname, verbose=False)
    if isinstance(image, list):
        if len(image) != 1:
            raise ValueError(
                f"OMIO returned {len(image)} image stacks for '{fname}'. "
                "MotilA currently expects one stack per process_stack call."
            )
        image = image[0]
        metadata = metadata[0]

    axes = metadata.get("axes", "")
    if axes == "TZYX" and len(image.shape) == 4:
        image = image[:, :, np.newaxis, :, :]
        metadata = om.update_metadata_from_image(metadata, image, verbose=False)
    elif axes != "TZCYX" or len(image.shape) != 5:
        raise ValueError(
            f"OMIO returned unsupported axes '{axes}' and shape {image.shape} "
            f"for '{fname}'. MotilA expects TZCYX after reading."
        )

    return image, metadata

def _as_tzcyx(image):
    """Convert MotilA output arrays to TZCYX for OMIO writing."""
    image = np.asarray(image)
    if image.ndim == 2:
        return image[np.newaxis, np.newaxis, np.newaxis, :, :]
    if image.ndim == 3:
        return image[:, np.newaxis, np.newaxis, :, :]
    if image.ndim == 4:
        return image[:, :, np.newaxis, :, :]
    if image.ndim == 5:
        return image
    raise ValueError(f"Cannot write image with unsupported shape {image.shape}.")

def write_image_stack(fname, image, metadata=None):
    """
    Write an image with OMIO while preserving MotilA's historical file names.

    OMIO writes OME-TIFF stacks with an ``.ome.tif`` suffix. If callers request
    a plain ``.tif`` name, the OME-TIFF file is moved back to that requested
    path so existing scripts and notebooks keep working.
    """
    om = _import_omio()
    fname = Path(fname)
    image_tzcyx = _as_tzcyx(image)
    if metadata is None:
        metadata = om.create_empty_metadata(shape=image_tzcyx.shape, verbose=False)
    metadata = om.update_metadata_from_image(metadata, image_tzcyx, verbose=False)
    written = om.imwrite(
        str(fname),
        image_tzcyx,
        metadata,
        overwrite=True,
        return_fnames=True,
        verbose=False,
    )
    written_path = Path(written[0])
    if written_path != fname:
        if fname.exists():
            fname.unlink()
        written_path.replace(fname)
    return fname

# %% END
