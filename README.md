![GitHub Release](https://img.shields.io/github/v/release/FabrizioMusacchio/motila) [![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)](https://opensource.org/licenses/) ![Tests](https://github.com/FabrizioMusacchio/motila/actions/workflows/python-tests.yml/badge.svg) [![PyPI version](https://img.shields.io/pypi/v/motila.svg)](https://pypi.org/project/motila/)



# MotilA: A pipeline for microglial fine process motility analysis

*MotilA* is a Python-based image analysis pipeline designed to quantify microglial fine process motility from 4D and 5D time-lapse image stacks acquired through multi-photon in vivo imaging. While developed for microglial analysis, *MotilA* can be applied to other cell types and imaging studies as well. The pipeline supports both single-file and batch processing, making it adaptable for various experimental designs and high-throughput analyses. 

## What does MotilA do?
*MotilA* automates the processing and analysis of fluorescence microscopy data, particularly for microglial process dynamics. It performs:

- **Preprocessing**: Image registration, spectral unmixing, histogram equalization, bleach correction, and projection of z-layers to enhance signal quality.
- **Segmentation**: Adaptive thresholding and noise filtering to isolate microglial processes.
- **Motility quantification**: Frame-to-frame analysis of pixel changes in microglial structures.
- **Batch processing**: Automated handling of multiple datasets with standardized parameter settings.

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
If you prefer to install *MotilA* from source, you can clone or download the GitHub repository:

```bash
git clone https://github.com/fabriziomusacchio/MotilA.git
cd MotilA
```

We recommend setting up a dedicated conda environment for development and reproducibility:

```bash
conda create -n motila python=3.12 mamba -y
conda activate motila
mamba install -y numpy scipy matplotlib scikit-image scikit-learn pandas tifffile zarr numcodecs pystackreg openpyxl xlrd ipywidgets ipykernel ipympl
```

⚠️ **Avoid mixing install methods**:  
If you install *MotilA* via `pip`, make sure you do **not place a local folder named `motila/`** in the same directory where you run your scripts (e.g., a cloned or downloaded source folder). Python may try to import from the local folder instead of the installed package, leading to confusing errors.

### Compatibility
We have tested *MotilA* for Python 3.9 to 3.12 on Windows, macOS, and Linux systems. The pipeline should work on all these platforms without any issues. If you encounter any platform-specific issues, feel free to [open an issue](https://github.com/FabrizioMusacchio/MotilA/issues).

## Example data set and tutorials
To help you get started with *MotilA*, we provide an example dataset and tutorials to guide you through the pipeline steps. 

The example dataset includes a sample image stack and metadata file for testing the pipeline. Please download the example dataset from [Zenodo](https://zenodo.org/records/15061566) (Gockel &  Nieves-Rivera, 2025, doi: 10.5281/zenodo.15061566) and place it in the [`example project`](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20project) directory.

The tutorials cover the core pipeline steps, from loading and preprocessing image data to analyzing microglial motility and visualizing the results. A second tutorial demonstrates batch processing for analyzing multiple datasets in a structured project folder.

[Jupyter notebooks](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20notebooks):

* [single_file_run.ipynb](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/single_file_run.ipynb)
* [batch_run.ipynb](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/batch_run.ipynb)

[Python scripts](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20scripts):

* [single_file_run.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run.py)
* [batch_run.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/batch_run.py)


We used the following Python script to generate the figures presented in our submitted manuscript:

* [single_file_run_paper.py](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20scripts/single_file_run_paper.py)

This script includes all parameter settings used during analysis and can be employed to reproduce the figures. It was applied to a subset of the example dataset described above. This specific subset is available in the repository under [`example project/Data/ID240103_P17_1_cutout/`](https://github.com/FabrizioMusacchio/MotilA/tree/main/example%20project/Data/ID240103_P17_1_cutout/TP000).


## Data prerequisites  
Before using *MotilA*, ensure that your imaging data meets the following requirements:  

### 1. TIFF file format and image axis order  
*MotilA* expects input image stacks in TIFF format with axes structured as either **TZCYX** (for multi-channel data) or **TZYX** (for single-channel data). These axes correspond to:  

- **T**: Time (imaging frames over time)  
- **Z**: Depth (z-stack layers)  
- **C**: Channels (fluorescent signals from different markers, e.g., microglia and neurons)  
- **Y**: Height (spatial dimension)  
- **X**: Width (spatial dimension)  

This format follows the standard used in **ImageJ/Fiji**. If your dataset does not conform to this structure, *MotilA* provides the function **`tiff_axes_check_and_correct`**, which helps rearrange the axes into the required order. Here is an example of how to use this function:

```python
import sys
sys.path.append('motila/')
import motila as mt
from pathlib import Path

tif_file_path = Path("path/to/your/image_stack.tif")
corrected_tif_file_path = mt.tiff_axes_check_and_correct(tif_file)
```

The output `corrected_tif_file` is the path to the corrected TIFF file, which is automatically saved in the same directory as the original file.


### 2. Image registration  
For accurate motility analysis, the 3D stacks at each time point \( t_i \) must be **spatially registered** to ensure alignment across frames. This step minimizes drift and motion artifacts that could otherwise bias motility quantification.  

If your dataset requires registration, ensure it has been preprocessed accordingly before running MotilA.  


## Pipeline steps

### Core pipeline steps
*MotilA* follows a structured sequence of image processing and analysis steps to extract motility metrics from microscopy data:

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
11. **Analyze motility**: Tracks changes in segmented regions, classifying stable, gained, and lost pixels to compute motility metrics.

### Batch processing steps
For large-scale experiments, *MotilA* supports automated batch processing across multiple datasets:

1. **Define a project folder**: Organize multiple image stacks within a structured directory.
2. **Process each image stack**: Executes the core pipeline steps on all image stacks within the project folder.
3. **Save results**: Stores segmented images, histograms, and motility metrics for each image stack in its respective results directory.
4. **Batch-collect results**: Aggregates motility metrics from multiple datasets, facilitating cohort-level analysis and statistical comparisons.

*MotilA*'s batch processing capabilities streamline the analysis of large datasets, enabling efficient processing and comparison of motility metrics across experimental conditions. The batch process expects a specific project folder structure to automate the processing of multiple datasets. This folder structure includes subdirectories for each dataset, containing the necessary image stacks, metadata files, and results directories. See the [Parameters Overview](#batch_file_processing) for details on the required folder structure and input parameters for batch processing.


### Main functions
The three main processing functions in *MotilA* are:

* **`process_stack`**: Processes a single image stack, performing all core pipeline steps from image loading to motility analysis.
* **`batch_process_stacks`**: Automates the processing of multiple image stacks within a project folder, applying the core pipeline steps to each dataset.
* **`batch_collect`**: Collects motility metrics from multiple datasets, aggregating the results for cohort-level analysis and visualization.


## Parameters overview
The following sections provide an overview of the input/output parameters for single file processing, batch processing, and batch collection in *MotilA*. These parameters define the settings for image processing, analysis, and results output, allowing you to customize the pipeline for your specific experimental design and data requirements.

### Input/output parameters for single file processing 
#### Input paths
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `Current_ID`            | string | define the ID of the mouse/animal |
| `group`                 | string | define the group of the mouse/animal |
| `fname`                 | string | define the full image file path |


#### Results output settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `RESULTS_Path`          | string | define the path to the results folder; can be absolute or relative to the location of the currently executed script |
| `clear_previous_results`  | bool (`True` or `False`) | optional clear previous results in the results folder. |


<a name="batch_file_processing"></a>

### Input/output parameters for batch processing

| Parameter              | Values                          | Description |
|------------------------|---------------|-------------|
| `PROJECT_Path`         | string | define the path to the project folder; can be absolute or relative to the location of the currently executed script |
| `ID_list`              | list of strings | define the list of all IDs to be processed in `PROJECT_Path`; names must be exact names of the ID folders within the `PROJECT_Path` |
| `project_tag`          | string | define the tag of the project (folder) to be analyzed; all folders in the ID-folders containing this tag will be processed; can be just a part of the tag (will be searched for in the folder name) |
| `reg_tif_file_folder`  | string | name of the folder within the (found) `project_tag` folder containing the registered TIF files; must be exact. |
| `reg_tif_file_tag`     | string | a TIF file containing this tag will be processed within the `reg_tif_file_folder`; if multiple files contain this tag, the folder will be skipped |
| `RESULTS_foldername`   | string | define the folder name (not the full path!) where the results will be saved within each `project_tag` folder; can also be relative to the `project_tag` folder (e.g., `../motility_analysis/`); the default destination will be inside the `reg_tif_file_folder` |
| `metadata_file`        | string | name of the metadata file in the `project_tag` folder; must be exact; use the template provided in the MotilA repository to create the metadata file |


The batch process expects a project folder structure as follows:

```
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
```

The folder hierarchy follows a structured, [BIDS-inspired format](https://bids-specification.readthedocs.io), organized by subject ID and project-specific subfolders. While not fully BIDS-compliant, this layout supports consistent batch processing and metadata association.


By placing an Excel file (e.g., `metadata.xls`) in the `project_tag` folder for each animal ID folder (listed in `ID_list`), the following parameters set in the execution script/notebook will be overwritten by the parameters in the Excel file: 

* `two_channel_default`
* `MG_channel_default`
* `N_channel_default`
* `spectral_unmixing`
* `projection_center_default`

This allows for individual settings for each dataset. The table below shows an example of the content of the `metadata.xls` file:

| Two Channel | Registration Channel | Registration Co-Channel | Microglia Channel | Neuron Channel | Spectral Unmixing | Projection Center 1 |
| ----------- | -------------------- | ----------------------- | ----------------- | -------------- | ----------------- | ------------------- |
| True        | 1                    | 0                       | 0                 | 1              | False             | 28                  |

A template for this excel files is provided in the `[templates](templates/)` folder. In this template, ignore the columns `Registration Channel`  and `Registration Co-Channel` as they are not used in *MotilA*.

You can add several projection centers (`Projection Center 1`, `Projection Center 2`, etc.) to the excel file. The pipeline will then create a projection for each center along with the corresponding analysis results.



### General processing settings (single file and batch processing)

#### Projection settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `projection_layers_default` | integer   | define the number of z-layers to project for motility analysis. |
| `projection_center_default` | integer   | define the center slice of the projection |

In case of image volumes densely packed with microglia, we recommend to subdivided the volume into several subvolumes with different projection centers. This will help to avoid overlapping microglia in the projection and thus ensure a more accurate capturing of the microglial processes' motility.

Avoid including blood vessels in the projection center. Blood vessels can lead to false-positive motility results, as the pipeline cannot distinguish between microglial processes and blood vessels. 

*MotilA* performs a sanity check of the desired subvolume defined by the input parameters `projection_center_default` and `projection_layers_default`. If the subvolume exceeds the image dimensions, the pipeline will automatically adjust the subvolume to fit within the image dimensions. However, this may lead to a smaller subvolume than initially defined. To avoid this, ensure that the subvolume fits within the image dimensions. The final chosen parameters will be saved in a log Excel file into the results folder.

#### Thresholding settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `threshold_method`            | string | choose from: `otsu`, `li`, `isodata`, `mean`, `triangle`, `yen`, `minimum`. |
| `blob_pixel_threshold`        | integer | define the minimal pixel area of a blob during segmentation; 100 is a good starting value |
| `compare_all_threshold_methods` | bool (`True` or `False`) | optional comparison plot all threshold methods |


#### Image enhancement settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `hist_equalization`     | bool (`True` or `False`)  | enhance histograms WITHIN each 3D stack. |
| `hist_equalization_clip_limit` | float | clip limit for the histogram equalization (default is 0.05); the higher the value, the more intense the contrast enhancement, but also the more noise is amplified |
| `hist_equalization_kernel_size` | `None`/int tuple | kernel size for the histogram equalization; `None` (default) for automatic, or use a tuple (x,y) for a fixed size; when using a tuple, you can start increasing the values from multiples of 8, e.g., (8,8), (16,16), (24,24), (32,32), ... (128,128), ... |
| `hist_match`            | bool (`True` or `False`)  | match histograms across 3D stacks |
| `histogram_ref_stack`   | integer     | define the reference 3D stack for histogram matching. |

Histogram equalization enhances the contrast of the image by stretching the intensity range. This can be particularly useful for images with low contrast or uneven illumination. The `hist_equalization_clip_limit` parameter controls the intensity clipping limit for the histogram equalization. A higher value increases the intensity range but may also amplify noise. The `hist_equalization_kernel_size` parameter defines the kernel size for the histogram equalization. The default is `None` which let's the function choose the kernel size automatically. In cases of occurring block artifacts, you can set a fixed kernel size (e.g., (8,8), (16,16), (24,24), ...).

Histogram matching aligns the intensity distributions of different image stacks, ensuring consistent brightness and contrast across time points. The `histogram_ref_stack` parameter defines the reference stack for histogram matching. This reference stack serves as the basis for matching the intensity distributions of all other stacks. Both, the output plot `Normalized average brightness drop rel. to t0.pdf` and Excel file `Normalized average brightness of each stack.xlsx` show the average brightness of each stack relative to the reference stack. This can help to assess the quality of each time point stack and which time points might be excluded from further analysis.


#### Filter settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `median_filter_slices` | string/bool (`square`, `circular`, or `False`) | median filter on slices before projecting |
| `median_filter_window_slices`    | integer/float      | median filter window size on slices before projecting; for `square` median filter option, insert odd integer values, for `circular` floating point numbers |
| `median_filter_projections`      | string/bool (`square`, `circular`, or `False`) | median filter on projections |
| `median_filter_window_projections` | integer/float | median filter window size on projections; for `square` median filter option, insert odd integer values, for `circular` floating point numbers |
| `gaussian_sigma_proj` | integer | standard deviation of Gaussian blur filter applied on the projected stack, set to 0 to turn it off  |


Regarding median filtering, you have the option to filter on the single slices BEFORE the projection (**`median_filter_slices`**) and/or on the projected images (**`median_filter_projections`**). For both options, you can choose from:

* `False` (no filtering)
* `square` (square kernel): integer numbers (3, 5, 9)
* `circular` (disk-shaped kernel; analogous to the median filter in ImageJ/Fiji): only values >= 0.5 allowed/have an effect

When you apply median filtering, you need to additionally provide the kernel size (**`median_filter_window_slices`** for single slices and **`median_filter_window_projections`** for projections). Depending on the chosen filtering kernel method, you can choose a kernel size as listed above.

Gaussian smoothing further  enhances the contrast and reduces noise. Set

* `gaussian_smoothing` to 0: no smoothing, or
* `gaussian_smoothing` to a value > 0: the standard deviation of the Gaussian kernel.


#### Channel settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `two_channel_default`  | bool (`True` or `False`) | define if the stack has two channels. |
| `MG_channel_default`   | integer    | set the channel number of the Microglia. |
| `N_channel_default`    | integer    | set the channel number of the Neurons/2nd channel. |

If your stack contains only one channel, set `two_channel_default = False`; any value set in `N_channel_default` will be ignored.

If `metadata.xls` is present in `project_tag` folder, the above defined values (`two_channel_default`, `MG_channel_default`, `N_channel_default`) are ignored and values from the metadata.xls are used instead  (**in batch processing only!**)


#### Registration settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `regStack3d` | bool (`True` or `False`)     | perform optional registration of slices within each 3D time-stack. |
| `regStack2d` | bool (`True` or `False`)    | perform optional registration of projections on each other using phase cross-correlation. |
| `usepystackreg` | bool (`True` or `False`) | If `True`, use pystackreg (StackReg) for 2D registration instead of phase cross-correlation. |
| `template_mode` | string    | set the template mode for 3D registration (`mean`, `median`, `max`, `min`, `std`, and `var`).  |
| `max_xy_shift_correction` | integer     | Set the maximal shift in x/y direction for 2D registration. |


*MotilA* provides the option to register the image stacks. Two registration options are available:

* `regStack3d`: register slices WITHIN each 3D time-stack; `True` or `False`
* `regStack2d`: register projections on each other;  `True` or `False`

With `template_mode`you can define the template mode for the registration. Choose between `mean` (default), `median`, `max`, `min`, `std`, and `var`.

With `max_xy_shift_correction`, you can define the maximum allowed shift in x and y (and z) direction for the registration. This is useful to avoid overcorrection.


#### Spectral unmixing settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `spectral_unmixing` | bool (`True` or `False`) | perform optional spectral unmixing to correct for channel bleed-through. |
| `spectral_unmixing_amplifyer` | integer  | amplify the MG channel to preserve more signal from this channel; set to 1 for no amplification |
| `spectral_unmixing_median_filter_window` | integer | Must be an integer; `1=off`, `3=common`, `5=strong`, `7=very strong`.       |

*MotilA* provides the option to perform spectral unmixing on two-channel data. At the moment, only a simple method is implemented, which subtracts the N-channel from the MG-channel. Set `spectral_unmixing` to `True` to enable this feature. 

With `spectral_unmixing_amplifyer_default` you can define the amplification factor for the MG-channel before subtraction. This can be useful to preserve more information in the MG-channel.

`spectral_unmixing_median_filter_window` defines the kernel size for median filtering of N-channel before subtraction. This can be useful to reduce noise in the N-channel and, thus, achieve a better unmixing result. Allowed are odd integer numbers (3, 5, 9, ...).

#### Debug settings
| Parameter | Values | Description |
|------------|----------------------|----------------|
| `debug_output` | bool (`True` or `False`) | enable debug output for intermediate results; at the moment, only memory outputs are given.|
| `stats_plots` | bool (`True` or `False`) | enable additional statistics plots for the motility analysis (at the moment: histogram plots of the binarized pixels) |


### Input/output parameters for batch collection

| Parameter | Values | Description |
|-------------------|----------------------------------|-------------|
| `PROJECT_Path`    | string | define the path to the project folder; can be absolute or relative to the location of the currently executed script |
| `RESULTS_Path`    | string | define the path to the results folder; combined results of the cohort analysis will be saved here; can be absolute or relative to the location of the currently executed script |
| `ID_list`         | list of strings | define the list of all IDs to be processed in `PROJECT_Path`; names must be exact names of the ID folders |
| `project_tag`     | string | define the tag of the project (folder) to be analyzed; all folders in the ID-folders containing this tag will be processed |
| `motility_folder` | string | folder name (not the path!) containing motility analysis results in each ID folder/project_tag folder; must be exact; all projection center folders therein will be processed to collect the results. |

The batch collection process expects the same project folder structure as the batch processing (see above).

## Example usage

### Single file processing
Here is an example of how to use *MotilA* for single file processing. First, import the necessary modules:

```python
import sys
sys.path.append('../motila')
import motila as mt
from pathlib import Path
```

**Note**: `sys.path.append('../motila')` is used to add the *MotilA* directory to the system path – relative to the current working directory. If you execute this notebook from a different location, you may need to adjust the path accordingly.

You can verify the correct import by running the following cell:

```python
mt.hello_world()
```

Init the logger to get a log file for your current run:

```python
# init logger:
log = mt.logger_object()
```

Then, define the corresponding parameters as described above. When you have set the parameters, you can run the pipeline:

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


### Batch processing
The batch processing is similar to the single file processing. You need to define the parameters as described above and then run the batch processing function:

```python
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
```

After processing all datasets, you can collect the results and save them to a central output folder. This allows you to perform cohort-level analyses and visualize the results across all datasets. To collect the results, use the following function:

```python
mt.batch_collect(PROJECT_Path=PROJECT_Path, 
                 ID_list=ID_list, 
                 project_tag=project_tag, 
                 motility_folder=motility_folder,
                 RESULTS_Path=RESULTS_Path,
                 log=log)
```

## Assessing your results
### Single file processing
After running the pipeline, you can assess the results in the specified output folder. The results of each processing step described above are saved in separate tif and PDF files. By carefully investigating these results, you can evaluate the quality of the processing and adjust the parameters if necessary. An example assessment is given in the tutorial notebook [`single_file_run.ipynb`](https://github.com/FabrizioMusacchio/MotilA/blob/main/example%20notebooks/single_file_run.ipynb) including visualizations of the results.

Besides the intermediate results, the motility metrics are saved in an Excel file called `motility.xlsx` in the results folder. This file contains the 

* gained pixels (G),
* lost pixels (L),
* stable pixels (S), and
* the turnover rate (TOR) for each time point,

allowing you to analyze the motility dynamics of microglial processes over time.

Additionally, brightness metrics and pixel counts are saved in separate Excel files for further analysis. The average pixel brightness is an indicator of the overall intensity of the microglial cells in the image. A decreasing brightness over time could indicate bleaching or other issues. Note that the results show are those after applying the histogram matching (if chosen). Thus, if the average pixel brightness still drops even after histogram matching, the shown values may help to assess the quality each time point stack and which time points might be excluded from further analysis.

The cell pixel area is the number of segmented pixel of all (projected) MG cells per stack. Usually, this number should remain relatively stable over time as the cell motility does not imply a change in cell area/size. A decrease in cell pixel area could indicate a loss of cells over time, e.g., due to cell death or other issues. Bleaching or other issues could also lead to a decrease in cell pixel area. Thus, the same considerations as for the average pixel brightness apply here.

### Batch processing
The batch collection function aggregates the motility metrics from all datasets into a single Excel file, allowing you to compare the motility dynamics across different experimental conditions and animals. This cohort-level analysis provides a comprehensive overview of the motility metrics, enabling you to identify trends, differences, or similarities between groups. The following Excel files are generated:

* `all_motility.xlsx`: Contains the motility metrics (G, L, S, TOR) for each project tag and time point across all datasets.
* `all_brightness.xlsx`: Contains the average pixel brightness for each project tag and time point across all datasets.
* `all_cell_pixel_area.xlsx`: Contains the cell pixel area for each project tag and time point across all datasets.
* `average_motility.xlsx`: Contains the average motility metrics (G, L, S, TOR) for each project tag across all datasets (i.e., the motility dynamics averaged over all time points within each dataset/project tag).


## How to contribute
*MotilA* is an open-source software and improves because of contributions from users all over the world. If there is something about *Motila* that you would like to work on, then please reach out.

## License: GPL-3.0 License
This software is licensed under the GNU General Public License v3.0 (GPL-3.0). In summary, you are free to:

- **Use** this software for any purpose.
- **Modify** the source code and adapt it to your needs.
- **Distribute** copies of the original or modified software.

However, you must:
- **Share modifications under the same license** (copyleft).  
  If you distribute a modified version, you must also make the source code available under GPL-3.0.  
- **Include the original copyright notice and license** in any copies or substantial portions of the software.  

 You may **not**:
- Use this software in **proprietary** (closed-source) applications.  
- Distribute modified versions under a more restrictive license.  

This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the LICENSE file or <https://www.gnu.org/licenses/gpl-3.0.html> for full terms.

## Citation
If you use this software in your research, we kindly ask you to cite it using the following BibTeX entry:


```
@software{musacchio2025motila,
  author       = {Fabrizio Musacchio and Sophie Crux and Felix Nebeling and Nala Gockel and Falko Fuhrmann and Martin Fuhrmann},
  title        = {MotilA: A pipeline for microglial fine process motility analysis},
  year         = {2025},
  url          = {https://github.com/FabrizioMusacchio/motila},
  version      = {1.0.0},
  note         = {Accessed: YYYY-MM-DD},
}
```

**Note**: We are currently in the process of retrieving a DOI for this project. As soon as the DOI becomes available, we will update the citation reference accordingly.  *(Status: March 21, 2025)*

## Acknowledgments
We gratefully acknowledge the **Light Microscopy Facility (LMF)** and the **Animal Research Facility (ARF)** at the **German Center for Neurodegenerative Diseases (DZNE)** for their essential support in acquiring the in vivo imaging data upon which this pipeline is built.

We also thank [Gockel & Nieves-Rivera (2025)](https://zenodo.org/records/15061566) and colleagues for providing the example dataset used in this repository, which allows users to test and explore MotilA.


## Contact
For questions, suggestions, or feedback regarding *MotilA*, please contact:

Fabrizio Musacchio  
German Center for Neurodegenerative Diseases (DZNE)  
Email: [fabrizio.musacchio@dzne.de](mailto:fabrizio.musacchio@dzne.de)
GitHub: @[FabrizioMusacchio](https://github.com/FabrizioMusacchio)
