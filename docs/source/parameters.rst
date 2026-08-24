Parameters overview
===================

This page provides an overview of all parameters used in single-file
processing, batch processing and batch collection in MotilA. These
parameters control image preprocessing, segmentation, motility
quantification and output settings, and allow customization of the
pipeline for different imaging datasets and experimental designs.


Input/output parameters for single-file processing
--------------------------------------------------

Input paths
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``Current_ID``
     - string
     - Identifier of the mouse or animal
   * - ``group``
     - string
     - Experimental group of the animal
   * - ``fname``
     - string
     - Full file path to the image stack

Results output settings
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``RESULTS_Path``
     - string
     - Output directory for results; absolute or relative to the current script
   * - ``clear_previous_results``
     - bool
     - If ``True``, remove any existing results in the target folder before writing new output
   * - ``table_export_formats``
     - ``"excel"`` or list of ``"excel"``, ``"csv"``, ``"yaml"``
     - Table export formats. Defaults to ``"excel"`` for backward compatibility. Add ``"csv"`` and/or ``"yaml"`` to write plain-text sidecar files next to the default Excel files.


Input/output parameters for batch processing
--------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``project_root``
     - string or ``Path``
     - Root directory that contains all subject folders
   * - ``subject_ids``
     - list of strings or ``None``
     - Explicit subject folders to process. If ``None``, MotilA discovers folders whose names start with ``subject_prefix``.
   * - ``subject_prefix``
     - string
     - Prefix used for automatic subject discovery when ``subject_ids=None``
   * - ``tag_folder_levels``
     - list of tag tuples
     - Flexible folder-tag levels below each subject, for example ``[("TP",), ("registered",)]`` or ``[("DC000_FOV", "DA000_FOV"), ("TL_000",)]``
   * - ``image_patterns``
     - list of glob patterns or ``None``
     - File patterns to process. ``None`` uses MotilA defaults for TIFF/OME-TIFF, CZI, LSM and RAW files.
   * - ``exclude_name_contains``
     - tuple of strings
     - Exclude files or folders whose names contain one of these strings
   * - ``skip_processed``
     - bool
     - If ``True``, skip files whose expected MotilA output already exists and record them as already processed
   * - ``results_folder_name``
     - string
     - Name of the folder where MotilA writes per-image processing results
   * - ``processing_options``
     - dictionary
     - Options forwarded to ``process_stack`` such as channels, projection settings, filtering and segmentation parameters
   * - ``load_options``
     - dictionary
     - Optional preflight-load settings. Set ``{"preflight": True}`` to classify loading errors before running ``process_stack``.
   * - ``save_options``
     - dictionary
     - Optional output validation/report settings, for example ``{"validate_outputs": True}``
   * - ``metadata_file``
     - string or ``None``
     - Optional Excel metadata file in the output-scope folder that can override selected processing options
   * - ``table_export_formats``
     - ``"excel"`` or list of ``"excel"``, ``"csv"``, ``"yaml"``
     - Set inside ``processing_options``. Defaults to ``"excel"``; optional CSV/YAML exports are written as sidecars.

Expected project folder structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The v1.2.0 batch process expects a flexible BIDS-like project folder structure:

.. code-block::

   project_root
   ├── ID000001
   │   ├── TP000
   │   │   ├── image_01.ome.tif
   │   │   └── image_02.czi
   │   └── TP001
   │       └── registered
   │           └── image_03.raw
   └── ID000002
       └── DC000_FOV01
           └── TL_000
               └── image_01.tif

This hierarchy follows a `BIDS-inspired <https://bids-specification.readthedocs.io>`_ organization by subject ID and
project-specific subfolders. It is not fully BIDS-compliant, but it
supports automated batch processing and robust association of metadata.

``tag_folder_levels`` tells MotilA how to walk the folder tree below each
subject. For example, ``[("DC000_FOV", "DA000_FOV"), ("TL_000",)]`` first
matches ``DC000_FOV*`` or ``DA000_FOV*`` folders and then searches for
``TL_000*`` folders below them. Empty levels, ``None``, ``()`` and ``[]`` are
ignored.

The batch processor writes persistent reports in ``project_root``:

* ``motila_batch_run_report.txt`` records the discovered files, current status,
  output folders and run history.
* ``motila_batch_run_report.yaml`` stores the same history in a machine-readable
  format so later runs can append to it.
* ``motila_batch_error_report_<timestamp>.txt`` is written only when failures
  occur. Per-file error reports are also written next to affected image files.


Metadata override file (metadata.xls)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If an Excel metadata file (for example ``metadata.xls``) is present in
each project_tag folder, selected parameters from the execution script
or notebook are overridden on a per-dataset basis.

The following parameters can be set via metadata:

* ``two_channel_default``
* ``MG_channel_default``
* ``N_channel_default``
* ``spectral_unmixing``
* ``projection_center_default``

This allows for individual settings for each dataset. 

Example table structure for ``metadata.xls``:

.. list-table:: Example metadata.xls structure
   :header-rows: 1
   :widths: 15 20 25 20 20 20 20

   * - Two Channel
     - Registration Channel
     - Registration Co-Channel
     - Microglia Channel
     - Neuron Channel
     - Spectral Unmixing
     - Projection Center 1
   * - True
     - 1
     - 0
     - 0
     - 1
     - False
     - 28

Columns *Registration Channel* and *Registration Co-Channel* are
currently not used by MotilA and can be ignored.

Additional projection centers (for example *Projection Center 2*) can be
added as extra columns. MotilA will then generate projections and
motility analyses for each defined center.

A template for this excel file is provided in the ``templates`` folder of the
repository.

General processing settings
---------------------------

Projection settings
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``projection_layers_default``
     - integer
     - Number of z-layers included in the projection subvolume
   * - ``projection_center_default``
     - integer
     - Central z-slice around which the projection subvolume is defined

In case of image volumes densely packed with microglia, we recommend to 
subdivide the volume into several subvolumes with different projection 
centers. This will help to avoid overlapping microglia in the projection 
and thus ensure a more accurate capturing of the microglial processes' motility.

Avoid including blood vessels in the projection center. Blood vessels can 
lead to false-positive motility results, as the pipeline cannot distinguish 
between microglial processes and blood vessels.

MotilA performs a sanity check of the desired subvolume defined by the 
input parameters ``projection_center_default`` and ``projection_layers_default``. 
If the subvolume exceeds the image dimensions, the pipeline will automatically 
adjust the subvolume to fit within the image dimensions. However, this may 
lead to a smaller subvolume than initially defined. To avoid this, ensure 
that the subvolume fits within the image dimensions. The final chosen parameters will be saved in a log Excel file into the results folder.

Thresholding settings
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``threshold_method``
     - string
     - Thresholding method; one of ``otsu``, ``li``, ``isodata``, ``mean``, ``triangle``, ``yen``, ``minimum``
   * - ``blob_pixel_threshold``
     - integer
     - Minimum area (in pixels) for segmented objects; a value of 100 is a reasonable starting point
   * - ``compare_all_threshold_methods``
     - bool
     - If ``True``, generate a comparison plot for all available threshold methods

Image enhancement settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Values
     - Description
   * - ``hist_equalization``
     - bool
     - Apply contrast-limited adaptive histogram equalization (CLAHE) within each 3D stack
   * - ``hist_equalization_clip_limit``
     - float
     - Clip limit for CLAHE (for example 0.05); higher values increase contrast but may amplify noise
   * - ``hist_equalization_kernel_size``
     - None or tuple
     - Kernel size for CLAHE; ``None`` lets the function choose automatically, or specify a tuple such as ``(16, 16)``
   * - ``hist_match``
     - bool
     - Match histograms across stacks to compensate for bleaching and intensity drift
   * - ``histogram_ref_stack``
     - integer
     - Index of the reference stack used for histogram matching

Histogram equalization enhances the contrast of the image by stretching the 
intensity range. This can be particularly useful for images with low contrast 
or uneven illumination. The ``hist_equalization_clip_limit`` parameter controls 
the intensity clipping limit for the histogram equalization. A higher value 
increases the intensity range but may also amplify noise. 
The ``hist_equalization_kernel_size`` parameter defines the kernel size for the 
histogram equalization. The default is ``None`` which lets the function choose 
the kernel size automatically. In cases of occurring block artifacts, you can set 
a fixed kernel size (e.g., (8,8), (16,16), (24,24), ...).

Histogram matching aligns the intensity distributions of different 
image stacks, ensuring consistent brightness and contrast across time 
points. The ``histogram_ref_stack`` parameter defines the reference stack for 
histogram matching. This reference stack serves as the basis for matching the 
intensity distributions of all other stacks. Both, the output plot Normalized 
average brightness drop rel. to t0.pdf and Excel file Normalized average 
brightness of each stack.xlsx show the average brightness of each stack relative 
to the reference stack. This can help to assess the quality of each time point 
stack and which time points might be excluded from further analysis.


Filter settings
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Values
     - Description
   * - ``median_filter_slices``
     - string or bool
     - Median filter on individual z-slices before projection; ``square``, ``circular`` or ``False``
   * - ``median_filter_window_slices``
     - int or float
     - Kernel size for slice-wise filtering; integers for square kernels, floating point radii for circular kernels
   * - ``median_filter_projections``
     - string or bool
     - Median filter on projected images; ``square``, ``circular`` or ``False``
   * - ``median_filter_window_projections``
     - int or float
     - Kernel size for filtering of projections
   * - ``gaussian_sigma_proj``
     - int
     - Standard deviation of the Gaussian blur applied to projections; 0 disables Gaussian filtering


Regarding median filtering, you have the option to filter on the single slices 
BEFORE the projection (``median_filter_slices``) and/or on the projected images 
(``median_filter_projections``). For both options, you can choose from:

* ``False`` (no filtering)
* ``square`` (square kernel): integer numbers (3, 5, 9)
* ``circular`` (disk-shaped kernel; analogous to the median filter in ImageJ/Fiji): only values >= 0.5 allowed/have an effect

When you apply median filtering, you need to additionally provide the kernel size 
(``median_filter_window_slices`` for single slices and ``median_filter_window_projections`` 
for projections). Depending on the chosen filtering kernel method, you can choose 
a kernel size as listed above.

Gaussian smoothing further enhances the contrast and reduces noise. Set

* ``gaussian_sigma_proj`` to 0: no smoothing, or
*  ``gaussian_sigma_proj`` to a value > 0: the standard deviation of the Gaussian kernel.

Channel settings
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Values
     - Description
   * - ``two_channel_default``
     - bool
     - Indicates whether the input stack contains two channels
   * - ``MG_channel_default``
     - integer
     - Channel index that contains the microglia signal
   * - ``N_channel_default``
     - integer
     - Channel index that contains the second signal (for example neurons or THG)

If your stack contains only one channel, set ``two_channel_default = False``; 
any value set in N_channel_default will be ignored.

If metadata.xls is present in project_tag folder, the above defined values 
(``two_channel_default``, ``MG_channel_default``, ``N_channel_default``) are 
ignored and values from the ``metadata.xls`` are used instead (in batch processing only!)

Registration settings
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Values
     - Description
   * - ``regStack3d``
     - bool
     - Register slices within each 3D stack across time
   * - ``regStack2d``
     - bool
     - Register 2D projections across time
   * - ``usepystackreg``
     - bool
     - If ``True``, use pystackreg (StackReg) for 2D registration instead of phase cross-correlation
   * - ``template_mode``
     - string
     - Template mode for 3D registration; one of ``mean``, ``median``, ``max``, ``min``, ``std``, ``var``
   * - ``max_xy_shift_correction``
     - integer
     - Maximum allowed shift in x and y direction during registration

MotilA provides the option to register the image stacks. Two registration 
options are available:

* ``regStack3d``: register slices WITHIN each 3D time-stack; True or False
* ``regStack2d``: register projections on each other;  True or False

With ``template_mode`` you can define the template mode for the registration. 
Choose between ``mean`` (default), ``median``, ``max``, ``min``, ``std``, and ``var``.

With ``max_xy_shift_correction``, you can define the maximum allowed shift in x and y 
(and z) direction for the registration. This is useful to avoid overcorrection.



Spectral unmixing settings
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Parameter
     - Values
     - Description
   * - ``spectral_unmixing``
     - bool
     - Enable simple spectral unmixing by subtracting the non-microglia channel from the microglia channel
   * - ``spectral_unmixing_amplifyer``
     - integer
     - Amplification factor for the microglia channel before subtraction; 1 disables amplification
   * - ``spectral_unmixing_median_filter_window``
     - integer
     - Median filter kernel for the second channel before subtraction; typical values are 1 (off), 3, 5, 7

MotilA provides the option to perform spectral unmixing on two-channel data. 
At the moment, only a simple method is implemented, which subtracts the N-channel 
from the MG-channel. Set ``spectral_unmixing`` to ``True`` to enable this feature.

With ``spectral_unmixing_amplifyer`` you can define the amplification 
factor for the MG-channel before subtraction. This can be useful to preserve 
more information in the MG-channel.

``spectral_unmixing_median_filter_window`` defines the kernel size for 
median filtering of N-channel before subtraction. This can be useful to 
reduce noise in the N-channel and, thus, achieve a better unmixing result. 
Allowed are odd integer numbers (3, 5, 9, ...).

Debug settings
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Values
     - Description
   * - ``debug_output``
     - bool
     - Enable additional debug output (for example memory usage and processing stages)
   * - ``stats_plots``
     - bool
     - Generate additional statistics plots for the motility analysis (for example histograms of binarized pixels)


Input/output parameters for batch collection
--------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Values
     - Description
   * - ``project_root``
     - string or ``Path``
     - Root directory that contains all subject folders
   * - ``RESULTS_Path``
     - string
     - Path to the folder where aggregated batch-collection results are saved
   * - ``subject_ids``
     - list of strings or ``None``
     - Explicit subject folders to collect. If ``None``, MotilA discovers folders whose names start with ``subject_prefix``.
   * - ``subject_prefix``
     - string
     - Prefix used for automatic subject discovery when ``subject_ids=None``
   * - ``tag_folder_levels``
     - list of tag tuples
     - Same folder-tag levels used for ``batch_process_stacks``
   * - ``image_patterns``
     - list of glob patterns or ``None``
     - Same image filters used for ``batch_process_stacks``
   * - ``exclude_name_contains``
     - tuple of strings
     - Exclude files or folders whose names contain one of these strings
   * - ``results_folder_name``
     - string
     - Name of the MotilA results folder to collect from
   * - ``organize_by_image``
     - bool
     - Must match the setting used during ``batch_process_stacks``
   * - ``table_export_formats``
     - ``"excel"`` or list of ``"excel"``, ``"csv"``, ``"yaml"``
     - Export formats for aggregated result tables. Defaults to ``"excel"`` and can optionally add CSV/YAML sidecars.

The batch collection function now uses the same discovery settings as
``batch_process_stacks``. It derives MotilA output folders from the discovered
input files and aggregates per-dataset results into cohort-level Excel files.
If ``table_export_formats`` includes ``"csv"`` or ``"yaml"``, matching
plain-text sidecar files are written with the same base names.
