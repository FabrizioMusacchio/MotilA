# MotilA: A pipeline for microglial fine process motility analysis

![GitHub Release](https://img.shields.io/github/v/release/FabrizioMusacchio/motila) [![PyPI version](https://img.shields.io/pypi/v/motila.svg)](https://pypi.org/project/motila/) [![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-green.svg)](https://motila.readthedocs.io/en/latest/overview.html#license) ![Tests](https://github.com/FabrizioMusacchio/motila/actions/workflows/python-tests.yml/badge.svg) [![GitHub last commit](https://img.shields.io/github/last-commit/FabrizioMusacchio/MotilA)](https://github.com/FabrizioMusacchio/MotilA/commits/main/)  [![codecov](https://img.shields.io/codecov/c/github/FabrizioMusacchio/Motila?logo=codecov)](https://codecov.io/gh/fabriziomusacchio/motila)  [![GitHub Issues Open](https://img.shields.io/github/issues/FabrizioMusacchio/MotilA)](https://github.com/FabrizioMusacchio/MotilA/issues) [![GitHub Issues Closed](https://img.shields.io/github/issues-closed/FabrizioMusacchio/MotilA?color=53c92e)](https://github.com/FabrizioMusacchio/MotilA/issues?q=is%3Aissue%20state%3Aclosed) [![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-pr/FabrizioMusacchio/MotilA)](https://github.com/FabrizioMusacchio/MotilA/pulls)  [![Documentation Status](https://readthedocs.org/projects/motila/badge/?version=latest)](https://motila.readthedocs.io/en/latest/?badge=latest) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/fabriziomusacchio/motila) [![PyPI - Downloads](https://img.shields.io/pypi/dm/MotilA?logo=pypy&label=PiPY%20downloads&color=blue)](https://pypistats.org/packages/motila)


*MotilA* is a Python-based image analysis pipeline designed to quantify microglial fine process motility from 4D and 5D time-lapse image stacks acquired through multi-photon in vivo imaging. While developed for microglial analysis, *MotilA* can be applied to other cell types and imaging studies as well. The pipeline supports both single-file and batch processing, making it adaptable for various experimental designs and high-throughput analyses. 


## What does MotilA do?
*MotilA* automates the processing and analysis of fluorescence microscopy data, particularly for microglial process dynamics. It performs:

- **Preprocessing**: Image registration, spectral unmixing, histogram equalization, bleach correction, and projection of z-layers to enhance signal quality.
- **Segmentation**: Adaptive thresholding and noise filtering to isolate microglial processes.
- **Motility quantification**: Frame-to-frame analysis of pixel changes in microglial structures.
- **Batch processing**: Automated handling of multiple datasets with standardized parameter settings.

A high-level description of all processing steps and parameters is given in the [online documentation](https://motila.readthedocs.io/en/latest/parameters.html).


## How is "motility" determined?
*MotilA* quantifies motility by first extracting a sub-volume from the 3D stack at each imaging time point $t_i$ and performing a maximum intensity z-projection. This sacrifices the z-axis information but enables segmentation and quantification of stable, lost, and gained pixels in a computationally efficient manner, facilitating batch processing with standard image analysis techniques. This approach aligns with methodologies used in prior studies, such as [Nebeling et al. (2023)](https://pubmed.ncbi.nlm.nih.gov/36749020/) or [Fuhrmann et al. (2010)](https://pubmed.ncbi.nlm.nih.gov/20305648/). The temporal variation $\Delta B(t_i)$ is then computed as:

$$\Delta B(t_i) = 2 \times B(t_i) - B(t_{i+1})$$

where $B(t)$ represents the binarized image at time point $t$. From this, *MotilA* categorizes pixels as follows:

- **Stable pixels (S)**: Pixels that remain unchanged $\Delta B = 1$.
- **Gained pixels (G)**: Newly appearing microglial pixels $\Delta B = -1$.
- **Lost pixels (L)**: Pixels that disappear $\Delta B = 2$.

From these, MotilA derives the **turnover rate (TOR)**, a key metric for motility:

$$
TOR = \frac{G + L}{S + G + L}
$$

This turnover rate represents the fraction of pixels undergoing change, providing a quantitative measure of microglial fine process motility.


![MotilA pipeline overview](figures/motila_figure_1_demo.png)
**Core pipeline steps of *MotilA* illustrated using a representative microglial cell from the included example dataset**. **a)** The pipeline begins with loading and z-projecting 3D image stacks, followed by optional preprocessing steps such as spectral unmixing, registration, and histogram equalization (upper panel). The resulting projections are filtered and binarized for segmentation of microglial fine processes (lower panel). **b)** Motility analysis compares consecutive time points by classifying stable (S), gained (G), and lost (L) pixels, from which the turnover rate (TOR) is computed. **c)** The TOR is plotted across time points, quantifying microglial fine process motility over time.


## Installation
### Installation via PyPI
The easiest way to install *MotilA* is via [PyPI](https://pypi.org/project/motila):

```bash
conda create -n motila python=3.12 -y
conda activate motila
pip install motila
```

### Installation from source
We recommend using a dedicated virtual environment for development and reproducibility.

Below is an example using conda:

```bash
conda create -n motila python=3.12 -y
conda activate motila
```

Clone the GitHub repository and install the package from its root directory:

```bash
git clone https://github.com/FabrizioMusacchio/MotilA.git
cd MotilA
pip install .
```

Alternatively, install directly from GitHub without cloning:

```bash
pip install git+https://github.com/FabrizioMusacchio/MotilA.git
```

**Note:** If you are contributing or making code changes, install in editable mode so updates are immediately reflected:

```bash
pip install -e .
```

⚠️ **Avoid mixing install methods**:  
If you install *MotilA* via `pip`, make sure you do **not place a local folder named `motila/`** in the same directory where you run your scripts (e.g., a cloned or downloaded source folder). Python may try to import from the local folder instead of the installed package, leading to confusing errors.

### Compatibility
We have tested *MotilA* for Python 3.9 to 3.12 on Windows, macOS, and Linux systems. The pipeline should work on all these platforms without any issues. If you encounter any platform-specific issues, feel free to [open an issue](https://github.com/FabrizioMusacchio/MotilA/issues).

## Example data set and tutorials
To help you get started with *MotilA*, we provide an example dataset and tutorials to guide you through the pipeline steps. 

The example dataset includes sample image stacks and metadata files for testing the pipeline. You can download the 

* **full example dataset** from [Zenodo](https://zenodo.org/records/15061566) (Musacchio et al., 2025, doi: 10.5281/zenodo.15061566; data based on Gockel & Nieves-Rivera et al., currently under revision), or a
* **subset ("cutout") of the example dataset**, also from [Zenodo](https://zenodo.org/records/17803978) (Musacchio, 2025, doi: 10.5281/zenodo.17803977)

After downloading and extracting, place it in the [`example project`](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20project) directory. If you use one of the provided datasets for any purpose beyond the example tutorials, please cite both the dataset record (Musacchio et al., 2025, doi: 10.5281/zenodo.15061566 / Musacchio, 2025, doi: 10.5281/zenodo.17803977) and Gockel & Nieves-Rivera et al., currently under revision (we will update the citation once available).

The tutorials cover the core pipeline steps, from loading and preprocessing image data to analyzing microglial motility and visualizing the results. A second tutorial demonstrates batch processing for analyzing multiple datasets in a structured project folder.

[Jupyter notebooks](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20notebooks):

* [single_file_run.ipynb](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/single_file_run.ipynb)
* [batch_run.ipynb](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/batch_run.ipynb)

[Python scripts](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20scripts):

* [single_file_run.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run.py)
* [batch_run.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/batch_run.py)


We used the following Python script to generate the figures presented in our submitted manuscript:

* [single_file_run_paper.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run_paper.py)

This script includes all parameter settings used during analysis and can be employed to reproduce the figures. It was applied to the subset of the example dataset described above.

### Running the example scripts and notebooks
The example scripts in `example scripts` and `example notebooks` expect a relative path layout and therefore must be executed from within that directory. For example:

```bash
cd example_scripts
python single_file_run_paper.py
```

Alternatively, users may modify the `DATA_Path` variable inside the script to point to the absolute location of your `example project` folder. 


## Quick start

### Single file processing
Here is an example of how to use *MotilA* for single file processing. First, import the necessary modules:

```python
import motila as mt
from pathlib import Path
```

You can verify the correct import by running the following cell:

```python
mt.hello_world()
```

Init the logger to get a log file for your current run:

```python
# init logger:
log = mt.logger_object()
```

Then, define the corresponding parameters. A set of example values can be found in the [tutorial notebooks](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20notebooks) and [scripts](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20scripts) provided in the repository. 

When you have set the parameters, run the pipeline via:

```python
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
```


More complete examples, including batch processing and collection of cohort-level metrics, are explained in [online documentation](https://motila.readthedocs.io/en/latest/tutorials.html#example-usage).


## Future developments
Please refer to the [ROADMAP.md](ROADMAP.md) file for an overview of planned improvements and future extensions of *MotilA*.


## How to contribute
*MotilA* is an open-source software and improves because of contributions from users all over the world. If there is something about *Motila* that you would like to work on, then please reach out: 

* open an [issue](https://github.com/FabrizioMusacchio/MotilA/issues), or
* submit a pull request against the `main` branch.

Please find more information on how to contribute in the [CONTRIBUTING.md](CONTRIBUTING.md) file.


## Citation
If you use this software in your research, please cite the following preprint:

Musacchio, F., Crux, S., Nebeling, F., Gockel, N., Fuhrmann, F., & Fuhrmann, M. (2025).  
*MotilA – A Python pipeline for the analysis of microglial fine process motility in 3D time-lapse multiphoton microscopy data*.  
bioRxiv. https://doi.org/10.1101/2025.08.04.668426

BibTeX:

```
@article{musacchio2025motila,
author = {Fabrizio Musacchio and Sophie Crux and Felix Nebeling and Nala Gockel and Falko Fuhrmann and Martin Fuhrmann},
title = {MotilA – A Python pipeline for the analysis of microglial fine process motility in 3D time-lapse multiphoton microscopy data},
journal = {bioRxiv},
year = {2025},
doi = {10.1101/2025.08.04.668426},
url = {https://www.biorxiv.org/content/10.1101/2025.08.04.668426v1}
}
```

**Note**: This manuscript has also been submitted to the Journal of Open Source Software (JOSS) and is currently under review. Once peer-reviewed and accepted, the citation will be updated accordingly.

## Acknowledgments
We gratefully acknowledge the **Light Microscopy Facility (LMF)** and the **Animal Research Facility (ARF)** at the **German Center for Neurodegenerative Diseases (DZNE)** for their essential support in acquiring the in vivo imaging data upon which this pipeline is built.

We also thank Gockel & Nieves-Rivera  and colleagues (currently under revision) for providing the [example dataset](https://zenodo.org/records/15061566) used in this repository, which allows users to test and explore MotilA.


## Contact
For questions, suggestions, or feedback regarding *MotilA*, please contact:

Fabrizio Musacchio  
German Center for Neurodegenerative Diseases (DZNE)  
Email: [fabrizio.musacchio@dzne.de](mailto:fabrizio.musacchio@dzne.de) \| GitHub: @[FabrizioMusacchio](https://github.com/FabrizioMusacchio) \| Website: [fabriziomusacchio.com](https://www.fabriziomusacchio.com)
