Overview
========

MotilA is a Python-based image analysis pipeline designed to quantify microglial
fine process motility from 4D and 5D time-lapse stacks acquired with in vivo
multiphoton imaging. While developed for microglia, the pipeline can in principle
be applied to other cell types and imaging paradigms that share similar data
characteristics.

MotilA supports both single-file and batch processing, making it suitable for
small experiments and high-throughput analyses. The main entry points are

* :func:`motila.motila.process_stack` for single-stack analysis,
* :func:`motila.motila.batch_process_stacks` for batch processing of project
  folders, and
* :func:`motila.motila.batch_collect` for aggregation of results across datasets.


What does MotilA do?
--------------------

MotilA automates the processing and analysis of fluorescence microscopy data
with a focus on microglial process dynamics. The pipeline performs:

* **Preprocessing**: image registration, spectral unmixing, histogram
  equalization, bleach correction and z-projection of subvolumes.
* **Segmentation**: adaptive thresholding and noise filtering to isolate
  microglial fine processes.
* **Motility quantification**: frame-to-frame analysis of pixel changes in
  segmented microglial structures.
* **Batch processing**: automated handling of multiple datasets with
  standardized parameter settings.

The individual processing steps and parameter choices are documented in more
detail in the sections on data prerequisites, pipeline steps and parameter
overview.


How is motility determined?
---------------------------

MotilA quantifies motility by extracting, for each time point :math:`t_i`, a
3D subvolume around a defined projection center and performing a maximum
intensity z-projection. This sacrifices z-axis information but allows efficient
segmentation and frame-to-frame comparison in 2D, which is particularly useful
for batch processing. This approach is consistent with earlier work on
microglial motility (for example Nebeling et al. 2023; Fuhrmann et al. 2010).

Let :math:`B(t_i)` denote the binarized projection at time :math:`t_i`. MotilA
computes a temporal difference

.. math::

   \Delta B(t_i) = 2 \times B(t_i) - B(t_{i+1}) .

Based on the value of :math:`\Delta B(t_i)` at each pixel, three classes are
defined:

* **Stable pixels** :math:`S` with :math:`\Delta B = 1`,
* **Gained pixels** :math:`G` with :math:`\Delta B = -1`,
* **Lost pixels** :math:`L` with :math:`\Delta B = 2`.

From these counts MotilA derives the turnover rate (TOR) as a central motility
metric,

.. math::

   TOR = \frac{G + L}{S + G + L} ,

which represents the fraction of pixels that change between two consecutive
time points. Higher TOR values correspond to stronger fine process motility.


Pipeline overview
-----------------

.. figure:: _static/figures/motila_figure_2.png
   :alt: MotilA pipeline overview
   :align: center
   :figwidth: 100%

   **Step-by-step illustration of the MotilA pipeline using the included test 
   dataset**. **a)** Overview of the image processing pipeline, showing core and 
   optional steps. **b)** Example projections of a cropped microglial cell at time 
   points $t_0$ and $t_1$, including raw, histogram-equalized, filtered 
   (median and Gaussian), and binarized versions.  **c)** Binarized pixel-wise 
   comparison between $t_0$ and $t_1$, with classification into stable (S, blue), 
   gained (G, green), lost (L, red), and background (BG, white) pixels, along with 
   the corresponding pixel statistics.  **d)** Normalized cell brightness over time, 
   relative to $t_0$, used to assess bleaching and signal stability. **e)** Turnover 
   rate (TOR) plotted across all time points for the same cell, representing 
   process-level motility dynamics. All microglial image panels in b and c are 
   shown at the same scale. Scale bar in the top-left image of panel b represents 10 μm.



Core pipeline steps
~~~~~~~~~~~~~~~~~~~

MotilA follows a structured sequence of image processing and analysis steps to extract motility metrics from microscopy data:

1. **Load image data**: Supports TIFF in TZCYX and TZYX formats.
2. **Extract sub-volumes**: Extracts a sub-volume from each 3D stack at every time point to ensure consistent analysis across time frames.
3. **(Optional) Register sub-volumes**: Performs motion correction by aligning sub-volumes across time points, improving tracking accuracy.
4. **(Optional) Perform spectral unmixing**: Reduces channel bleed-through, particularly for two-channel imaging setups.
5. **Z-projection**: Converts the extracted 3D sub-volume into a 2D projection, enabling computationally efficient segmentation and tracking.
6. **(Optional) Register projections**: Aligns projections across time points to further correct for motion artifacts.
7. **(Optional) Apply histogram equalization**: Enhances contrast using contrast-limited adaptive histogram equalization (CLAHE), improving feature visibility.
8. **(Optional) Apply histogram matching**: Aligns image intensities across time points to correct for bleaching artifacts, ensuring consistent brightness.
9. **(Optional) Apply filtering**: Median filtering and Gaussian smoothing reduce noise while preserving relevant microglial structures.
10. **Segment microglial processes**: Identifies microglial structures using adaptive thresholding and blob detection to extract relevant morphological features.
11. **Analyze motility**: Tracks changes in segmented regions, classifying stable, gained and lost pixels to compute motility metrics.

Batch processing steps
~~~~~~~~~~~~~~~~~~~~~~

For large-scale experiments, MotilA supports automated batch processing across multiple datasets:

1. **Define a project folder**: Organize multiple image stacks within a structured directory.
2. **Process each image stack**: Executes the core pipeline steps on all image stacks within the project folder.
3. **Save results**: Stores segmented images, histograms and motility metrics for each image stack in its respective results directory.
4. **Batch-collect results**: Aggregates motility metrics from multiple datasets, facilitating cohort-level analysis and statistical comparisons.

MotilA’s batch processing capabilities streamline the analysis of large datasets, enabling efficient processing and comparison of motility metrics across experimental conditions. The batch process expects a specific project folder structure to automate the processing of multiple datasets. This folder structure includes subdirectories for each dataset, containing the necessary image stacks, metadata files and results directories. See the :doc:`parameters` page for details on the required folder structure and input parameters for batch processing.

Main functions
~~~~~~~~~~~~~~

The three main processing functions in MotilA are:

* ``process_stack``: Processes a single image stack, performing all core pipeline steps from image loading to motility analysis.
* ``batch_process_stacks``: Automates the processing of multiple image stacks within a project folder, applying the core pipeline steps to each dataset.
* ``batch_collect``: Collects motility metrics from multiple datasets, aggregating the results for cohort-level analysis and visualization.


Installation
------------

MotilA targets Python 3.9–3.12 and builds on the standard scientific Python
stack (NumPy, SciPy, scikit-image, scikit-learn, pandas, tifffile, zarr and
related packages). The recommended way to install MotilA for end users is via
PyPI:

.. code-block:: bash

   conda create -n motila python=3.12 -y
   conda activate motila
   pip install motila

For development or reproducible analysis pipelines, it is often convenient to
install MotilA from source:

.. code-block:: bash

   git clone https://github.com/FabrizioMusacchio/MotilA.git
   cd MotilA
   pip install .

Alternatively, MotilA can be installed directly from GitHub without cloning:

.. code-block:: bash

   pip install git+https://github.com/FabrizioMusacchio/MotilA.git

If you plan to modify the code, use editable installation:

.. code-block:: bash

   pip install -e .

Avoid mixing local source folders and installed packages with the same name in
the same working directory, as this can lead to confusing import behaviour.


Example dataset and tutorials
-----------------------------

To facilitate onboarding, MotilA is accompanied by an example dataset hosted on
Zenodo and several example notebooks and scripts in the repository.

The :doc:`example dataset <tutorials>` contains a subset of in vivo multiphoton imaging data used
in the associated manuscript and can be downloaded from Zenodo. Placing the
data into the provided example project folder allows users to run the pipeline
end-to-end using the supplied notebooks and scripts.

Jupyter notebooks :doc:`demonstrate <tutorials>`:

* single-stack processing for one dataset,
* batch processing of multiple datasets in a structured project folder,
* reproduction of the figures used in the manuscript from the example subset.

Example Python scripts mirror these workflows for use outside of notebooks.


Running the example scripts and notebooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The example scripts in ``example scripts`` and ``example notebooks`` expect a relative path 
layout and therefore must be executed from within that directory. For example:

.. code-block:: bash

   cd example_scripts
   python single_file_run_paper.py


Alternatively, users may modify the ``DATA_Path`` variable inside the script to point 
to the absolute location of the example project. 


.. _license:

License
-------

MotilA is distributed under the terms of the `GNU General Public License v3.0 (GPL-3.0) <https://github.com/FabrizioMusacchio/MotilA?tab=GPL-3.0-1-ov-file>`_.

In summary, users are permitted to

* **use** the software for any purpose  
* **modify** the source code and adapt it to their needs
* **redistribute** the original or modified code

Under the following conditions:

* **Copyleft** applies. Modifications must be released under the same GPL-3.0 license.  
* The **original copyright notice and license** must be preserved.

Not permitted:

* Use of MotilA in **proprietary or closed-source** applications  
* Redistribution of modified versions under more restrictive terms  

MotilA is provided **without any warranty**, including implied warranties of merchantability
or fitness for a particular purpose.

For full license terms, see the ``LICENSE`` file in the `repository <https://github.com/FabrizioMusacchio/MotilA?tab=GPL-3.0-1-ov-file>`_ or  
`https://www.gnu.org/licenses/gpl-3.0.html <https://www.gnu.org/licenses/gpl-3.0.html>`_.


Citation
--------

If you use MotilA in your research, please cite the associated preprint:

Musacchio, F., Crux, S., Nebeling, F., Gockel, N., Fuhrmann, F., & Fuhrmann, M. (2025).  
*MotilA – A Python pipeline for the analysis of microglial fine process motility in 3D time-lapse multiphoton microscopy data*.  
bioRxiv. https://doi.org/10.1101/2025.08.04.668426

BibTeX:

.. code-block:: bibtex

    @article{musacchio2025motila,
      author  = {Fabrizio Musacchio and Sophie Crux and Felix Nebeling and
                  Nala Gockel and Falko Fuhrmann and Martin Fuhrmann},
      title   = {MotilA – A Python pipeline for the analysis of microglial fine
                 process motility in 3D time-lapse multiphoton microscopy data},
      journal = {bioRxiv},
      year    = {2025},
      doi     = {10.1101/2025.08.04.668426},
      url     = {https://www.biorxiv.org/content/10.1101/2025.08.04.668426v1}
    }

The citation metadata (authors, ORCID identifiers, release date, keywords and
software version) are also provided in the repository via the ``CITATION.cff``
`file <https://github.com/FabrizioMusacchio/MotilA/blob/main/CITATION.cff>`_. This ensures compatibility with GitHub, Zenodo and other indexing tools.
The entry will be updated if the associated manuscript is accepted by the
Journal of Open Source Software (JOSS).


Acknowledgments and contact
---------------------------

MotilA was developed in the context of in vivo multiphoton imaging of microglia
at the German Center for Neurodegenerative Diseases (DZNE), with support from
the Light Microscopy Facility, the Animal Research Facility and several
collaborators.

For questions, suggestions or bug reports, please refer to the
`GitHub issue tracker <https://github.com/FabrizioMusacchio/MotilA/issues>`_ of 
the `MotilA repository <https://github.com/FabrizioMusacchio/MotilA>`_ or contact the maintainer 
directly:

| **Fabrizio Musacchio**: `Email <mailto:fabrizio.musacchio@dzne.de>`_ | `GitHub <https://github.com/FabrizioMusacchio>`_ | `Website <https://www.fabriziomusacchio.com>`_