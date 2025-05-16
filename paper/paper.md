---
title: 'MotilA – A Python pipeline for the analysis of microglial fine process motility in 3D time-lapse multiphoton microscopy data'
tags:
  - Python
  - neuroscience
  - image-processing
  - image-segmentation
  - microglia
  - motility
  - microglial-motility
  - motility-analysis
  - in-vivo-imaging
  - time-lapse-imaging
  - 3d-imaging
authors:
  - name: Fabrizio Musacchio
    orcid: 0000-0002-9043-3349
    corresponding: true
    affiliation: 1
  - name: Sophie Crux
    affiliation: 1
    corresponding: false
  - name: Felix Nebeling
    affiliation: 1
    corresponding: false
  - name: Nala Gockel
    affiliation: 1
    corresponding: false
  - name: Falko Fuhrmann
    corresponding: false
    affiliation: 1
  - name: Martin Fuhrmann
    orcid: 0000-0001-7672-2913
    corresponding: false
    affiliation: 1
affiliations:
 - name: German Center for Neurodegenerative Diseases (DZNE), Bonn, Germany
   index: 1
date: 25 March 2025
bibliography: paper.bib
---

# Summary
*MotilA* is a Python-based image analysis pipeline for quantifying fine process motility of microglia from 3D time-lapse two-channel fluorescence microscopy data. Developed for high-resolution multiphoton *in vivo* imaging datasets, *MotilA* enables both single-file and batch processing across multiple experimental conditions. It performs image preprocessing, segmentation, and motility quantification over time, using a pixel-based change detection strategy that yields biologically interpretable metrics such as the turnover rate (TOR) of microglial fine processes. While originally designed for microglial imaging, the pipeline can be extended to other cell types and imaging applications that require analysis of dynamic morphological changes. *MotilA* is openly available, platform-independent, and includes extensive documentation, tutorials, and example data to facilitate adoption by the broader scientific community. It is released under the GPL-3.0 open-source license.

# Statement of need
Microglia are innate immune cells of the central nervous system and exhibit highly dynamic, motile processes that continuously scan their environment [@Nimmerjahn:2005; @Fuhrmann:2010; @Tremblay:2010; @Prinz:2019; @Nebeling:2023]. Quantifying microglial motility at the level of fine processes is crucial for studying their function in health and disease, including neurodegeneration, inflammation, and synaptic remodeling. However, despite the biological importance of this analysis, there is currently no dedicated open-source tool tailored for this task.

To date, researchers typically quantify microglial motility manually (see., e.g., @Nebeling:2023) using general-purpose image processing software such as Fiji/ImageJ  [@Schindelin:2012] or ZEISS ZEN [@ZeissZEN:2025]. While these approaches are well established in the field, they are time-consuming, lack reproducibility, and are not well suited for batch processing or cohort-level comparisons. They often focus on individual microglia, whereas *MotilA* enables analysis of the full field of view, allowing for more comprehensive and scalable quantification. Manual workflows are also more susceptible to human bias, limiting their scalability and objectivity [@Lee:2024; @Wall:2018; @Misra:2015; @Brown:2017].

*MotilA* addresses these limitations by providing an end-to-end, user-friendly, and batch-capable pipeline specifically designed for 3D time-lapse two-channel microscopy data. It supports standardized workflows for single- and multi-channel datasets, integrates essential preprocessing steps (registration, spectral unmixing, histogram normalization), and derives biologically meaningful motility metrics from binarized pixel dynamics. The method builds on strategies used in prior studies but automates the workflow in a reproducible, scalable, and open-source manner. *MotilA* thus fills a critical gap in neuroimaging analysis pipelines and is particularly valuable for labs working with multiphoton *in vivo* imaging.


# What does *MotilA* do?
*MotilA* is a modular and customizable image analysis pipeline written in Python that quantifies microglial fine process motility from time-lapse fluorescence microscopy data, typically acquired with two-photon [@Denk:1990; @Helmchen:2001] or three-photon *in vivo* imaging [@Horton:2013; @FFuhrmann:2024]. Although it was originally developed for microglial analysis, the pipeline is adaptable to other cell types and imaging contexts involving dynamic morphological changes over time.

At its core, *MotilA* extracts sub-volumes from 3D time-stacks, performs 2D maximum intensity projections, and segments the resulting images to classify pixel-wise changes in microglial morphology. These changes are quantified frame-by-frame and used to calculate biologically interpretable metrics, including the turnover rate (TOR). The design is tailored to biological imaging data, with particular attention to typical issues such as z-axis projection loss, channel bleed-through, motion artifacts, photobleaching, and signal heterogeneity.

The pipeline supports both single-file processing and large-scale batch analysis. Parameters are highly customizable either programmatically or via metadata files, and all results are automatically logged, saved, and summarized for downstream statistical analysis. The outputs include segmented image series, intermediate diagnostics (e.g. histograms, projections, brightness traces), and Excel spreadsheets with motility metrics.

To accommodate large-scale, high-resolution imaging data, *MotilA* supports memory-efficient file handling via the Zarr format [@Miles:2025], enabling processing of large TIFF files using memory mapping to avoid RAM overload.

*MotilA* can be run via Python scripts or Jupyter notebooks, and it includes extensive documentation, examples, and a tutorial dataset to make onboarding straightforward.

We welcome community contributions and issue reports via the GitHub repository: [https://github.com/FabrizioMusacchio/motila](https://github.com/FabrizioMusacchio/motila).


## How is "motility" determined?
*MotilA* quantifies motility by analyzing pixel-wise changes in microglial fine processes’ morphology over time. The pipeline first extracts a sub-volume around a user-defined z-axis center from each 3D image stack and applies a 2D maximum intensity projection to reduce dimensionality. Although this sacrifices some z-axis information, it enables efficient segmentation and pixel-level tracking while maintaining biological interpretability.

At each time point $t_i$, the projected and binarized image $B(t_i)$ is compared to the next time point $B(t_{i+1})$. A temporal variation map $\Delta B(t_i)$ is computed as:

$$\Delta B(t_i) = 2 \times B(t_i) - B(t_{i+1})$$

Based on this difference image, each pixel is classified as:

* **Stable (S)** if $\Delta B = 1$
* **Gained (G)** if $\Delta B = -1$
* **Lost (L)** if $\Delta B = 2$

From these categories, *MotilA* calculates the microglial **fine process turnover rate (TOR)**, a central metric representing the fraction of pixels that changed:

$$TOR = \frac{G + L}{S + G + L}$$

This approach allows for a quantitative assessment of microglial process dynamics at each time point and across the full recording session. The same principle can be extended to other motile cell types or dynamic cellular structures where morphological changes manifest as gain or loss of segmented pixels over time.

The implementation is based on analytical strategies described in previous studies such as @Fuhrmann:2010 and @Nebeling:2023, with added flexibility for batch processing, filtering, and parameter tuning.


## Key features
*MotilA* offers a combination of modularity, reproducibility, and scalability specifically tailored to motility analysis in multiphoton *in vivo* imaging. Its key features include:

* **Automated preprocessing pipeline**  
  Includes optional steps for image registration (2D and 3D), spectral unmixing, histogram equalization for contrast enhancement within time points, and histogram matching for brightness normalization across time points (e.g. to correct for photobleaching), as well as noise reduction via median and Gaussian filtering.
* **Flexible segmentation and thresholding**  
  Supports multiple adaptive thresholding methods (e.g. Otsu, Li, Triangle) and customizable blob detection settings to isolate fine microglial processes or similar structures.
* **Pixel-based motility quantification**  
  Tracks pixel-wise changes between time points to classify stable, gained, and lost pixels, allowing biologically interpretable metrics like the turnover rate (TOR).
* **Batch processing capabilities**  
  Enables large-scale processing of multiple datasets with a standardized folder structure and parameter metadata sheets, suitable for cohort-level studies.
* **User-defined projection settings**  
  Allows flexible extraction of sub-volumes and z-projection around multiple centers to avoid overlapping cells and vascular artifacts.
* **Memory-efficient file handling**  
  Supports memory mapping of large TIFF files via the Zarr format, enabling efficient processing of high-resolution time-lapse datasets without exhausting system RAM.
* **Metadata integration and parameter logging**  
  Automatically reads per-dataset settings from metadata files (e.g. Excel sheets), and stores processing parameters and outputs in structured result folders.
* **Cross-platform compatibility**  
  Runs on Windows, macOS, and Linux, tested with Python ≥3.9 and compatible with common scientific computing environments via Conda.
* **Tutorials and example data included**  
  Comes with Jupyter notebooks, example datasets, and clear documentation to help new users get started quickly.


## Pipeline steps
The *MotilA* pipeline follows a modular sequence of image processing and analysis steps designed for robust and reproducible quantification of motility from multi-dimensional imaging data. It supports both single-file and batch workflows and includes options for fine-grained customization at each step.

### Core pipeline steps
For single datasets, *MotilA* executes the following sequence (\autoref{fig:figure1}a)):

1. **Load image data**  
   Supports TIFF files [@Gohlke:2025] in TZCYX (multi-channel) or TZYX (single-channel) format, following ImageJ/Fiji conventions (T: time, Z: z-axis, C: channel, Y: height, X: width).
2. **Extract sub-volumes**  
   Selects a z-stack around a projection center for each time point, allowing focused analysis and optional multiple projections per stack.
3. **(Optional) Register sub-volumes**  
   Applies 3D motion correction [@GuizarSicairos:2008; @Anuta:1970; @Kuglin:1975] to each time series stack using user-defined template strategies (e.g. mean, median).
4. **(Optional) Perform spectral unmixing**  
   Removes signal bleed-through between channels, especially relevant for two-channel imaging setups.
5. **Z-projection**  
   Projects each 3D sub-volume into a 2D image via maximum intensity projection to simplify segmentation and speed up processing.
6. **(Optional) Register projections**  
   Aligns the 2D projections across time to correct for lateral motion artifacts.
7. **(Optional) Apply histogram equalization**  
   Enhances local contrast within each projection using contrast-limited adaptive histogram equalization (CLAHE) [@Pizer:1987; @Walt:2014].
8. **(Optional) Apply histogram matching**  
   Normalizes brightness across time points to mitigate bleaching effects or intensity drift [@Walt:2014].
9. **(Optional) Apply filtering**  
   Reduces noise with optional median filtering (square or circular kernel) and/or Gaussian smoothing [@Virtanen:2020; @Harris:2020].
10. **Segment microglial processes**  
    Applies adaptive thresholding [@Ridler:1978; @Otsu:1979; @Li:1998; @Glasbey:1993; @Prewitt:1966; @Zack:1977; @Yen:1995] and blob filtering [@Fiorio:1996; @Wu:2005; @Walt:2014] to identify and isolate morphologically relevant structures.
11. **Analyze motility**  
    Quantifies pixel-level changes over time to classify stable, gained, and lost regions, from which motility metrics are derived.

All intermediate outputs and metrics are saved for validation and further analysis.

### Batch processing steps
*MotilA* supports fully automated batch processing using a standardized folder structure and Excel-based metadata configuration. This enables reproducible cohort-level analysis across many animals or experimental conditions.

1. **Define a project folder**  
   Each dataset is placed in an ID-specific subdirectory, containing imaging files, metadata, and optional result directories.
2. **Run the batch process**  
   The core pipeline is executed for each dataset using shared or per-dataset parameters defined in `metadata.xls`.
3. **Save results**  
   Segmentation outputs, projections, and motility metrics are stored in structured result folders for each dataset.
4. **Batch-collect metrics**  
   Aggregates metrics across datasets into cohort-level Excel files for downstream statistical analysis.

This design enables large-scale, reproducible quantification of microglial motility with minimal manual intervention.

### Assessing results and analyzing outputs
*MotilA* provides rich output in the form of diagnostic plots, intermediate image files, and structured Excel tables to support both per-dataset assessment and cohort-level statistical analysis.

#### Per-dataset assessment
For each processed image stack, *MotilA* generates:

* **Segmented images and overlays** showing gained, lost, and stable regions across time points.
* **Histogram plots** for brightness, pixel area, and thresholding diagnostics.
* **Motility metrics table (`motility.xlsx`)** containing:
  - Gained pixels (G)
  - Lost pixels (L)
  - Stable pixels (S)
  - turnover rate (TOR) per time point
* **Brightness metrics** (`brightness.xlsx`) tracking average pixel intensity over time.
* **Cell area metrics** (`cell_pixel_area.xlsx`) reporting the segmented microglial pixel area per time point.

These outputs help assess segmentation quality, evaluate photobleaching or signal loss, and refine preprocessing parameters as needed.

#### Cohort-level batch analysis
During batch processing, *MotilA* can aggregate key metrics from all datasets into shared summary files, including:

* `all_motility.xlsx` — All G/L/S/TOR metrics across datasets.
* `all_brightness.xlsx` — Mean brightness per dataset and time point.
* `all_cell_pixel_area.xlsx` — Segmented area per dataset and time point.
* `average_motility.xlsx` — Dataset-wise average motility metrics across the full recording.

These results allow for statistical comparison of motility dynamics across experimental conditions and facilitate downstream visualization and modeling in tools like Python, R, or Excel.

This multi-level output strategy ensures both technical validation and biological insight, making *MotilA* suitable for both exploratory and hypothesis-driven studies.

### Main functions
The three main entry points for the pipeline are:

* `process_stack` — Processes a single image stack, performing the full pipeline.
* `batch_process_stacks` — Executes the pipeline across multiple datasets in a project folder.
* `batch_collect` — Gathers motility metrics from all datasets for cohort-level analysis.

Each function supports extensive parameterization via arguments or metadata files.

A complete overview of configurable parameters for single-file processing, batch workflows, and image enhancement is provided in the [MotilA README](https://github.com/FabrizioMusacchio/motila#parameters-overview).


### Useful helper functions
Several additional functions assist with data preparation and quality control, including:

* `tiff_axes_check_and_correct` — Automatically adjusts TIFF axis order to TZCYX/ TZYX if needed.
* `hello_world` — Verifies a successful import of the *MotilA* module.
* `logger_object` — Initializes logging for the current analysis session.


## Applications and limitations
*MotilA* was designed with a primary focus on the analysis of microglial fine process motility *in vivo*, using high-resolution 3D time-lapse two-channel fluorescence microscopy data. Its modular design and general image processing framework, however, make it applicable to a broader range of dynamic imaging contexts.

### Applications
* **Microglial dynamics**  
  Quantification of process turnover during surveillance, neuroinflammation, or disease models such as neurodegeneration and injury.
* **Neuronal structural plasticity**  
  While *MotilA* is optimized for microglial processes, its pixel-based change detection framework can in principle be adapted to analyze dynamic changes in dendrites or axons — such as growth, retraction, or remodeling — provided the structures can be reliably segmented across time.
* **Two-channel *in vivo* imaging**  
  Effective for experiments involving simultaneous imaging of microglia and neurons (e.g., Cx3Cr1-GFP with Thy1-YFP), with spectral unmixing to reduce bleed-through from overlapping channels or fluorophores.
* **Cohort-level studies**  
  Designed to analyze and compare motility metrics across large experimental groups, enabling high-throughput, statistically robust results.
* **Teaching and prototyping**  
  The example datasets and tutorials make *MotilA* a useful tool for training purposes or prototyping new analysis approaches.

### Limitations
* **Loss of z-resolution**  
  The use of 2D maximum intensity projections simplifies processing but sacrifices z-axis information. This may lead to overlapping structures and limits spatial specificity.
* **Segmentation-dependent**  
  Accuracy depends on appropriate thresholding and image quality. Overlapping processes, blood vessels, or low signal-to-noise ratios can reduce segmentation performance.
* **Limited spectral unmixing**  
  The current unmixing approach is a simple channel subtraction. More advanced unmixing strategies may be required for some experimental setups.
* **Not a general-purpose tracking tool**  
  *MotilA* is optimized for pixel-level process motility, not for full cell tracking or object-based morphological quantification over time.
* **Assumes TIFF input with standardized axis order**  
  Input images must conform to TZCYX or TZYX structure; other formats require conversion.

Despite these limitations, *MotilA* provides a powerful, reproducible framework for analyzing microglial motility and similar biological processes, especially in experimental setups where manual analysis would be impractical.

# Real-world example
To demonstrate its practical utility, *MotilA* includes a fully compatible example dataset of *in vivo* two-photon time-lapse imaging stacks from the mouse frontal cortex [@Gockel:2025]. These data were acquired to assess microglial fine process motility under control conditions and during complement C4 overexpression, a genetic risk factor for schizophrenia.

The dataset contains two 5D TIFF stacks with the following structure:

* **T**: 8 time points (5-minute intervals over 35 minutes)
* **C**: 2 imaging channels (Cx3cr1-GFP for microglia, tdTomato for neurons)
* **Z**: ~60 optical sections (1 μm step size)
* **Y, X**: ~1200 × 1200 px (~125 × 125 μm^2^ field of view)

The files are formatted for direct use with *MotilA*, requiring no manual reorganization or preprocessing.

\autoref{fig:figure1} summarizes the full *MotilA* workflow as applied to the example dataset. For visualization purposes, the original full-field dataset was cropped around a single microglial cell to reduce background clutter and allow detailed inspection of each processing step. **Panel a)** outlines the core and optional steps in the processing pipeline. **Panel b)** shows z-projections of the microglial cell at time points $t_0$ and $t_1$, including raw data, contrast enhancement, and filtering prior to segmentation. **Panel c)** displays the delta image used for motility quantification and the corresponding pixel-wise classification into stable (S, blue), gained (G, green), and lost (L, red) pixels. **Panel d)** tracks the average brightness of the segmented cell relative to the first time point, which helps assess signal stability and potential bleaching. **Panel e)** presents the turnover rate (TOR) across all time points, capturing the dynamics of microglial process remodeling.

![Step-by-step illustration of the *MotilA* pipeline using the included test dataset. **a)** Overview of the image processing pipeline, showing core and optional steps. **b)** Example projections of a cropped microglial cell at time points $t_0$ and $t_1$, including raw, histogram-equalized, filtered (median and Gaussian), and binarized versions.  **c)** Binarized pixel-wise comparison between $t_0$ and $t_1$, with classification into stable (S, blue), gained (G, green), lost (L, red), and background (BG, white) pixels, along with the corresponding pixel statistics.  **d)** Normalized cell brightness over time, relative to $t_0$, used to assess bleaching and signal stability. **e)** Turnover rate (TOR) plotted across all time points for the same cell, representing process-level motility dynamics. All microglial image panels in b and c are shown at the same scale. Scale bar in the top-left image of panel b represents 10 μm. \label{fig:figure1}](figures/motila_figure.pdf)


# Past and ongoing projects
*MotilA* has already been successfully applied in multiple neuroscience studies involving *in vivo* imaging of microglia and neurons in the mouse brain.

The following published and preprint works used *MotilA* to analyze fine process motility in physiological and pathological contexts:

- **@Crux:2024**  
  Investigated the role of actin depolymerizing factors ADF/Cofilin1 in microglial motility and memory formation. *MotilA* was used to quantify reduced motility in knockout mice.  
  → [https://doi.org/10.1101/2024.09.27.615114](https://doi.org/10.1101/2024.09.27.615114)
- **@FFuhrmann:2024**  
  Employed deep three-photon imaging of microglia in the medial prefrontal cortex to measure sub-cellular process dynamics in awake mice. *MotilA* was used to quantify microglial turnover at depths beyond 1 mm.  
  → [https://doi.org/10.1101/2024.08.28.610026](https://doi.org/10.1101/2024.08.28.610026)
- **@Gockel:2025**  
  Generated and published the example dataset accompanying this pipeline, which was used to demonstrate microglial motility changes in response to complement C4 overexpression.  
  → [https://doi.org/10.5281/zenodo.15061566](https://doi.org/10.5281/zenodo.15061566)

These studies showcase the pipeline’s suitability for both targeted microglial investigations and large-scale, high-resolution imaging projects. Ongoing work continues to extend *MotilA*’s application to additional brain regions, genetic perturbations, and imaging modalities, including multi-channel and high-speed two-photon datasets.


# Acknowledgements
We gratefully acknowledge the **Light Microscopy Facility (LMF)** and **Animal Research Facility (ARF)** at the German Center for Neurodegenerative Diseases (DZNE), Bonn, for their essential support in data acquisition and technical infrastructure.

This work was supported by the DZNE and by grants to MF from the European Union ERC-CoG (MicroSynCom 865618) and the German Research Foundation DFG (SFB1089 C01, B06; SPP2395). MF is a member of the DFG Excellence Cluster ImmunoSensation2. This work was also supported by the iBehave network to MF and the CANTAR (CANcerTARgeting) network to FN, both funded by the Ministry of Culture and Science of the State of North Rhine-Westphalia. The funders had no role in study design, data collection and interpretation, or the decision to submit the work for publication. FN received additional funding from the Mildred-Scheel School of Oncology Cologne-Bonn.

All animal procedures related to the example dataset were conducted in compliance with institutional, national, and international regulations. Experiments were approved by the relevant animal care and use committees at DZNE (Germany), following guidelines equivalent to the ARRIVE 2.0 framework. All efforts were made to reduce the number of animals used and to refine experimental conditions in accordance with the 3Rs (Replacement, Reduction, and Refinement) principles.

We also acknowledge the open-source community whose tools and contributions made the development of *MotilA* possible.

# References

