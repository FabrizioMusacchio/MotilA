Data prerequisites and project structure
========================================

MotilA operates on time-lapse multiphoton imaging data read through
`OMIO <https://omio.readthedocs.io>`_. This page summarizes the supported file
formats, the normalized axis order, the handling of metadata, and the
preprocessing considerations for accurate microglial motility analysis.

Image file formats and axis order
---------------------------------

MotilA accepts image formats supported by OMIO in the pipeline entry points,
including ``.tif``, ``.tiff``, ``.czi``, Thorlabs ``.raw`` and ``.lsm`` files.
OMIO reads these formats and normalizes the image data to the OME-compliant
**TZCYX** axis order before MotilA's processing steps begin. These axes
correspond to:

* **T**: time (imaging frames over time)  
* **Z**: depth (z-stack layers)  
* **C**: channels (fluorescent signals from different markers, for example
  microglia and neurons)  
* **Y**: height (spatial dimension)  
* **X**: width (spatial dimension)

For single-channel data, OMIO still provides a channel axis with ``C=1``. This
means MotilA's internal image shape after reading is always ``(T, Z, C, Y, X)``,
even if the source file did not explicitly store all dimensions.

Older TIFF-only workflows that already produce ImageJ/Fiji ``TZYX`` or
``TZCYX`` stacks remain supported. The legacy helper
:meth:`motila.utils.tiff_axes_check_and_correct` is still available for manual
TIFF axis correction, but most users no longer need to run it before
``process_stack`` because OMIO performs axis normalization during reading.

Example usage of axis correction function:

.. code-block:: python

   import motila as mt
   from pathlib import Path

   tif_file_path = Path("path/to/your/image_stack.tif")
   corrected_tif_file_path = mt.tiff_axes_check_and_correct(tif_file_path)

The output ``corrected_tif_file_path`` is the path to the corrected TIFF file,
which is automatically saved in the same directory as the original file.

Channel specification
---------------------

MotilA does **not** assume fixed channel identities for multi-channel data.
Instead, users must specify the channel indices explicitly through the
parameters of :func:`motila.motila.process_stack` and
:func:`motila.motila.batch_process_stacks`.

The key parameters are:

* ``two_channel`` – whether the stack contains two channels  
* ``MG_channel`` – channel index containing the microglia signal  
* ``N_channel`` – channel index containing the second signal  
  (e.g., neurons, reporter lines, THG, or other structures)

For **single-channel** datasets, set ``two_channel=False``. In that case,
``N_channel`` is ignored entirely.



Image registration pre-requirements
-----------------------------------

For accurate motility analysis, the 3D stacks at each time point must be
spatially registered to ensure alignment across frames. This step minimizes
drift and motion artefacts that could otherwise bias motility quantification.

If a dataset requires registration, it should be preprocessed accordingly before
running MotilA using external tools such as ImageJ/Fiji or other registration pipelines.

MotilA has built-in functions for image registration, but these operate best for
fine-tuning already roughly aligned stacks. Therefore, it is recommended not to
use MotilA's registration functions as the primary registration step for
datasets with significant drift or misalignment.

.. tip::
  
    For datasets with substantial drift, consider using dedicated registration
    software or plugins (for example in ImageJ/Fiji or
    `ZenReg <https://zenreg.readthedocs.io/en/latest/index.html>`_) before running 
    MotilA. This ensures that the stacks are well-aligned and suitable for accurate 
    motility analysis.


Project folder structure for batch processing
---------------------------------------------

MotilA v1.2.0 uses a flexible BIDS-like folder discovery for batch processing.
The project root should contain subject folders. Below each subject, users can
define one or more folder-tag levels that match their project structure.

.. code-block::

   project_root
   ├── ID000001
   │   ├── TP000
   │   │   ├── image_01.tif
   │   │   └── image_02.ome.tif
   │   ├── TP001
   │   │   └── registered
   │   │       └── image_03.czi
   │   └── DC000_FOV01
   │       └── TL_000
   │           └── image_04.raw
   └── ID000002
       └── TP000
           └── image_01.lsm

Here:

* ``project_root``
  Base project folder.

* Subject folders
  Animal or sample identifiers. If ``subject_ids`` is provided, only those
  exact folders are processed. If ``subject_ids=None``, MotilA processes
  folders whose names start with ``subject_prefix``.

* ``tag_folder_levels``
  A list of folder-token levels below each subject. Each level may contain one
  or multiple strings that are matched by containment. For example,
  ``[("DC000_FOV", "DA000_FOV"), ("TL_000",)]`` matches either
  ``DC000_FOV*`` or ``DA000_FOV*`` folders, then ``TL_000*`` folders below
  them. Empty levels, ``None``, ``()`` and ``[]`` are skipped.

* ``image_patterns``
  Glob pattern(s) used in the final matched folder. ``None`` uses MotilA's
  default image patterns for TIFF/OME-TIFF, CZI, LSM and RAW files. Explicit
  patterns such as ``("*reg*.tif", "*reg*.ome.tif")`` restrict processing.

* ``exclude_name_contains``
  Excludes files and tag folders whose names contain one of the provided
  strings, for example previews or auxiliary microscope outputs.

* ``results_folder_name``
  Folder name where MotilA writes per-image processing results. With
  ``organize_by_image=True``, results are stored as
  ``<scope>/<results_folder_name>/<image_stem>/projection_center_<n>/``.

* ``metadata_file``  
  Optional Excel metadata file in the output-scope folder or image folder.
  It can override selected processing options such as channel indices,
  spectral unmixing and projection centers.

The folder hierarchy follows a structured, `BIDS-inspired format <https://bids-specification.readthedocs.io>`_.
It is not fully BIDS-compliant but provides a consistent organisation by
subject ID and project-specific subfolders, which facilitates batch processing
and metadata association.

The batch processor never treats an already processed file as a failure when
``skip_processed=True``. Instead, it records the file as already processed in
``motila_batch_run_report.txt``. Processing errors are captured per file and do
not stop the full batch unless ``continue_on_error=False`` is requested.


Metadata file (metadata.xls – for batch processing only)
--------------------------------------------------------------

For batch processing, MotilA can read an Excel file, typically named
``metadata.xls``, in each ``project_tag`` folder (see folder structure above). 
This file allows certain parameters that are set in the execution script or 
notebook to be overridden on a per-dataset basis. The parameters that can be 
overwritten via ``metadata.xls`` are:

* ``two_channel_default``
* ``MG_channel_default``
* ``N_channel_default``
* ``spectral_unmixing``
* ``projection_center_default``

This enables individual settings for each dataset while keeping a common script
for batch processing.

``metadata.xls`` must contain the following columns:

.. code-block:: text

   Two Channel | Registration Channel | Registration Co-Channel | Microglia Channel | Neuron Channel | Spectral Unmixing | Projection Center 1
   ----------- | -------------------- | ----------------------- | ----------------- | -------------- | ----------------- | -------------------
   True        | 1                    | 0                       | 0                 | 1              | False             | 28

A template for this Excel file is provided in the ``templates`` folder of the
repository. In this template, the columns *Registration Channel* and
*Registration Co-Channel* are not used by MotilA and can be ignored.

Multiple projection centres (for example *Projection Center 1*,
*Projection Center 2*, and so on) can be added to the Excel file. The pipeline
will then create projections for each specified centre and compute the
corresponding analysis results.




Summary
-------

In summary, MotilA expects:

* OMIO-supported image stacks that can be normalized to ``TZCYX``, and
* spatially registered 3D stacks for accurate motility analysis.

For batch processing, MotilA additionally requires:

* a structured project folder hierarchy, 
* correctly assigned channel indices via parameters, and
* optional per-dataset metadata Excel files to override selected parameters.
