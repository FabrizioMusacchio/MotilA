Tutorials and Example Datasets
==============================

MotilA provides Jupyter notebooks and Python scripts that
demonstrate the complete analysis workflow. Also, an example dataset is
publicly available on Zenodo. These resources enable users to
validate their installation, understand the processing steps and reproduce the
results shown in the associated manuscript.

Example dataset (Zenodo)
------------------------

A curated example dataset is available on Zenodo and contains:

* a representative 4D or 5D time-lapse image stack,
* a corresponding ``metadata.xls`` file with projection center settings, and
* a ready-to-use project folder structure compatible with MotilA.

The dataset can be downloaded from:

* Gockel & Nieves-Rivera (2025), doi: 10.5281/zenodo.15061566  
  `Zenodo record <https://zenodo.org/records/15061566>`_

After downloading, place the dataset into the ``example project`` directory of
MotilA:

* `example project folder <https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20project>`_

Running MotilA directly on this dataset allows users to verify that the pipeline
is functioning correctly and produces meaningful motility metrics.

Tutorial notebooks
------------------

MotilA includes Jupyter notebooks that illustrate the core processing steps on
the example data:

* `single_file_run.ipynb <https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/single_file_run.ipynb>`_  
  Demonstrates the complete workflow for processing a single image stack.

* `batch_run.ipynb <https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/batch_run.ipynb>`_  
  Shows how to process multiple datasets stored in a structured project folder.

These notebooks guide users through image loading, optional preprocessing,
motility computation and inspection of intermediate and final results. They
serve as the most accessible introduction to the pipeline.

Example Python scripts
----------------------

Equivalent Python scripts are provided for users who prefer script-based
workflows or who want to integrate MotilA into automated analysis pipelines:

* `single_file_run.py <https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run.py>`_
* `batch_run.py <https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/batch_run.py>`_

These scripts mirror the behavior of the tutorial notebooks and can be adapted
for larger projects or command-line environments.

Reproducing manuscript figures
------------------------------

The figures shown in the associated manuscript were generated using a dedicated
script that applies MotilA to a specific subset of the example dataset:

* `single_file_run_paper.py <https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run_paper.py>`_

The subset used for figure generation is located at:

* ``example project/Data/ID240103_P17_1_cutout/TP000``

The script contains all parameter settings used during analysis and can be used
to reproduce the manuscript figures exactly.

Additional example datasets
---------------------------

The repository may include additional reduced datasets, project templates or
folder structures intended to help users set up their own analyses. These
resources are located in the ``example project`` directory and follow the same
format expected by the batch processing routines of MotilA. They can be used as
templates for structuring new experimental datasets.



Example usage
-------------

The following code examples illustrate how to use MotilA in practice.

Single-file processing
~~~~~~~~~~~~~~~~~~~~~~

Import MotilA and initialize logging:

.. code-block:: python

   import sys
   sys.path.append('../motila')
   import motila as mt
   from pathlib import Path

   # verify installation
   mt.hello_world()

   # initialize logger
   log = mt.logger_object()

Then, define the corresponding parameters. A set of example values can be 
found in the `tutorial notebooks <https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20notebooks>`_ and `scripts <https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20scripts>`_ provided in the repository. 

After defining the necessary parameters, run the pipeline:

.. code-block:: python

   mt.process_stack(fname=fname,
                    MG_channel=MG_channel,
                    N_channel=N_channel,
                    two_channel=two_channel,
                    projection_layers=projection_layers,
                    projection_center=projection_center,
                    histogram_ref_stack=histogram_ref_stack,
                    log=log,
                    blob_pixel_threshold=blob_pixel_threshold,
                    regStack2d=regStack2d,
                    regStack3d=regStack3d,
                    template_mode=template_mode,
                    spectral_unmixing=spectral_unmixing,
                    hist_equalization=hist_equalization,
                    hist_equalization_clip_limit=hist_equalization_clip_limit,
                    hist_equalization_kernel_size=hist_equalization_kernel_size,
                    hist_match=hist_match,
                    RESULTS_Path=RESULTS_Path,
                    ID=Current_ID,
                    group=group,
                    threshold_method=threshold_method,
                    compare_all_threshold_methods=compare_all_threshold_methods,
                    gaussian_sigma_proj=gaussian_sigma_proj,
                    spectral_unmixing_amplifyer=spectral_unmixing_amplifyer,
                    median_filter_slices=median_filter_slices,
                    median_filter_window_slices=median_filter_window_slices,
                    median_filter_projections=median_filter_projections,
                    median_filter_window_projections=median_filter_window_projections,
                    clear_previous_results=clear_previous_results,
                    spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                    debug_output=debug_output,
                    stats_plots=stats_plots)

Batch processing
~~~~~~~~~~~~~~~~

Batch processing uses the same parameters but operates on multiple datasets:

.. code-block:: python

   mt.batch_process_stacks(PROJECT_Path=PROJECT_Path,
                           ID_list=ID_list,
                           project_tag=project_tag,
                           reg_tif_file_folder=reg_tif_file_folder,
                           reg_tif_file_tag=reg_tif_file_tag,
                           metadata_file=metadata_file,
                           RESULTS_foldername=RESULTS_foldername,
                           MG_channel=MG_channel,
                           N_channel=N_channel,
                           two_channel=two_channel,
                           projection_center=projection_center,
                           projection_layers=projection_layers,
                           histogram_ref_stack=histogram_ref_stack,
                           log=log,
                           blob_pixel_threshold=blob_pixel_threshold,
                           regStack2d=regStack2d,
                           regStack3d=regStack3d,
                           template_mode=template_mode,
                           spectral_unmixing=spectral_unmixing,
                           hist_equalization=hist_equalization,
                           hist_equalization_clip_limit=hist_equalization_clip_limit,
                           hist_equalization_kernel_size=hist_equalization_kernel_size,
                           hist_match=hist_match,
                           max_xy_shift_correction=max_xy_shift_correction,
                           threshold_method=threshold_method,
                           compare_all_threshold_methods=compare_all_threshold_methods,
                           gaussian_sigma_proj=gaussian_sigma_proj,
                           spectral_unmixing_amplifyer=spectral_unmixing_amplifyer,
                           median_filter_slices=median_filter_slices,
                           median_filter_window_slices=median_filter_window_slices,
                           median_filter_projections=median_filter_projections,
                           median_filter_window_projections=median_filter_window_projections,
                           clear_previous_results=clear_previous_results,
                           spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                           debug_output=debug_output,
                           stats_plots=stats_plots)

Batch collection
~~~~~~~~~~~~~~~~

Aggregate results across multiple datasets:

.. code-block:: python

   mt.batch_collect(PROJECT_Path=PROJECT_Path,
                    ID_list=ID_list,
                    project_tag=project_tag,
                    motility_folder=motility_folder,
                    RESULTS_Path=RESULTS_Path,
                    log=log)

Assessing your results
----------------------

Single-file results include TIFF and PDF files for each processing step as well
as an Excel file ``motility.xlsx`` containing:

* gained pixels (G),
* lost pixels (L),
* stable pixels (S),
* turnover rate (TOR).

Additional Excel files summarize brightness metrics and cell pixel areas.

Batch processing generates cohort-level summary files:

* ``all_motility.xlsx``  
* ``all_brightness.xlsx``  
* ``all_cell_pixel_area.xlsx``  
* ``average_motility.xlsx``



Summary
-------

MotilA provides a complete set of resources for learning and validating the
pipeline:

* a publicly available Zenodo dataset,
* Jupyter notebooks for interactive exploration,
* Python scripts for automated workflows, and
* a dedicated dataset and script for reproducing manuscript figures.

Together, these materials offer a reproducible and practical starting point for
using MotilA on real multiphoton imaging data.