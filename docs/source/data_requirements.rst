Data Prerequisites and Project Structure
========================================

MotilA operates on time-lapse multiphoton imaging data stored in TIFF format.
This page summarizes the required file structure, the expected axis order, the
handling of metadata, and the preprocessing considerations for accurate
microglial motility analysis.

TIFF file format and image axis order
-------------------------------------

MotilA expects input image stacks in TIFF format with axes structured as either
**TZCYX** (for multi-channel data) or **TZYX** (for single-channel data). These
axes correspond to:

* **T**: time (imaging frames over time)  
* **Z**: depth (z-stack layers)  
* **C**: channels (fluorescent signals from different markers, for example
  microglia and neurons)  
* **Y**: height (spatial dimension)  
* **X**: width (spatial dimension)

This format follows the standard used in ImageJ/Fiji. 

If an input file uses a different axis order, MotilA provides the function
:meth:`motila.utils.tiff_axes_check_and_correct`, which reads the axis labels
from the ImageJ metadata and writes a corrected TIFF file with properly ordered
dimensions.

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


Project folder structure for batch processing
---------------------------------------------

The batch processing functions of MotilA expect a structured project folder
layout as follows:

.. code-block::

   PROJECT_Path
   │
   └───ID1
   │   └───project_tag
   │       └───reg_tif_file_folder
   │           └───reg_tif_file_tag
   │       └───RESULTS_foldername
   │       └───metadata_file
   │
   └───ID2
   │   └───project_tag
   │       └───reg_tif_file_folder
   │           └───reg_tif_file_tag
   │       └───RESULTS_foldername
   │       └───metadata_file
   │
   └───ID3
   │   └───project_tag ...

Here:

* ``PROJECT_Path``  
  Base project folder.

* ``ID1``, ``ID2``, …  
  Animal or sample identifiers.

* ``project_tag``  
  Project-specific subfolder (for example imaging session, condition or
  time point). All folders in an ID folder whose name contains this tag
  can be processed.

* ``reg_tif_file_folder``  
  Folder within the ``project_tag`` directory that contains the registered
  TIFF files.

* ``reg_tif_file_tag``  
  Substring used to identify the TIFF file(s) to process within
  ``reg_tif_file_folder``; if multiple files contain this tag, the folder
  is skipped.

* ``RESULTS_foldername``  
  Folder name where MotilA will save the results for each project. It can
  be placed inside or relative to the ``project_tag`` folder (for example
  ``../motility_analysis/``).

* ``metadata_file``  
  Name of the Excel metadata file (for example ``metadata.xls``) in the
  ``project_tag`` folder.

The folder hierarchy follows a structured, `BIDS-inspired format <https://bids-specification.readthedocs.io>`_.
It is not fully BIDS-compliant but provides a consistent organisation by
subject ID and project-specific subfolders, which facilitates batch processing
and metadata association.


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

* TIFF image stacks with axes ordered as ``TZCYX`` (multi-channel) or
  ``TZYX`` (single-channel), and
* spatially registered 3D stacks for accurate motility analysis.

For batch processing, MotilA additionally requires:

* a structured project folder hierarchy, 
* correctly assigned channel indices via parameters, and
* optional per-dataset metadata Excel files to override selected parameters.

