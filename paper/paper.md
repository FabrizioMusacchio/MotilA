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


## Summary
*MotilA* is an open-source Python pipeline for quantifying microglial fine-process motility in 4D (TZYX) or 5D (TZCYX) time-lapse fluorescence microscopy data, supporting both single-channel and two-channel acquisition. It was developed for high-resolution *in vivo* multiphoton imaging and supports both single-stack and cohort-scale batch analyses. The workflow performs sub-volume extraction, optional registration and spectral unmixing, a maximum-intensity projection along the Z-axis, segmentation, and pixel-wise change detection to compute the turnover rate (TOR). *MotilA* specifically targets pixel-level process motility rather than object tracking or full morphometry.  The code is platform independent, documented with tutorials and example datasets, and released under GPL-3.0.


## Statement of need
Microglia are immune cells of the central nervous system and continuously remodel their processes to survey brain tissue and respond to pathology [@Nimmerjahn:2005; @Fuhrmann:2010; @Tremblay:2010; @Prinz:2019]. Quantifying this subcellular motility is important for studies of neuroinflammation, neurodegeneration, and synaptic plasticity. Current practice in many labs relies on manual or semi-manual measurements in general-purpose tools such as Fiji/ImageJ or proprietary software [@Schindelin:2012; @ZeissZEN:2025]. These procedures are time consuming, hard to reproduce, focus on single cells, and are sensitive to user bias [@Wall:2018; @Brown:2017]. There is no dedicated, open, and batch-capable solution tailored to this task.

*MotilA* fills this gap with an end-to-end, reproducible pipeline for 3D time-lapse two-channel imaging. It standardizes preprocessing, segmentation, and motility quantification and scales from individual stacks to large experimental cohorts. Unlike Fiji/ImageJ macros or proprietary packages, *MotilA* provides a fully automated non-interactive workflow in Python that applies identical parameters across datasets, logs all intermediate steps, and avoids user-dependent adjustments. This ensures reproducible, bias-minimized, and scalable processing of large 3D time-lapse datasets, including optional motion correction and spectral unmixing. Although optimized for microglia, the approach generalizes to other motile structures that can be reliably segmented across time.

To clarify *MotilA*'s novelty relative to existing analysis approaches, the following table summarizes key differences between *MotilA*, Fiji/ImageJ, and ZEISS ZEN:


**Table 1.** Comparison of MotilA with commonly used alternatives for microglial motility analysis.

| Feature | Fiji/ImageJ | ZEISS ZEN | MotilA |
|---------|--------------|-----------|--------|
| **Automation** | Limited. User-recorded macros; complex workflows often require manual steps and must be split across several macros. | None. Full user interaction required. | Full. End-to-end non-interactive workflow. |
| **Batch processing** | Limited. Macros can process several files in one folder, but they cannot navigate nested directory structures or manage multi-step 3D multi-channel time-series pipelines. | None. Each dataset processed manually. | Full. Metadata-driven cohort processing. |
| **Reproducibility** | Moderate. Requires complete manual logging; interactive tuning reduces reproducibility. | Low. Manual adjustments introduce strong user bias. | High. Full parameter logging and deterministic runs. |
| **Scalability** | Low. Full-stack RAM loading; no chunked I/O for large 3D data. | Low–medium. Efficient viewing but no automated processing for large time-lapse datasets. | High. Chunked I/O for multi-gigabyte 3D two-channel stacks. |
| **Open-source** | Yes (GPL-3.0). | No (proprietary). | Yes (GPL-3.0). |




## Implementation and core method
Input is a 5D stack in TZCYX or a 4D stack in TZYX order, where T is time, Z is depth, C is channel, and YX are spatial dimensions. *MotilA* does not assume a fixed channel order. Users specify which channel contains microglia and which, if present, provides a structural reference signal, such as a neuronal label. Although the reference channel does not enter the motility computation, it is commonly acquired in microglial imaging because it offers stable features that support robust pre-processing registration of the 3D stack before it is passed to *MotilA*. The additional channel may also be used for optional spectral unmixing in the presence of bleed-through.


For each time point, *MotilA* extracts a user-defined z-sub-volume, optionally performs 3D motion correction and spectral unmixing, and computes a 2D maximum-intensity projection along the Z-axis to enable interpretable segmentation. After thresholding, the binarized projection $B(t_i)$ is compared with $B(t_{i+1})$ to derive a change map

$$\Delta B(t_i)=2B(t_i)-B(t_{i+1}).$$

Pixels are classified as stable "S" ($\Delta B=1$), gained "G" ($\Delta B=-1$), or lost "L" ($\Delta B=2$). From these counts, the turnover rate is defined as

$$TOR=\frac{G+L}{S+G+L},$$

representing the fraction of pixels that changed between consecutive frames. This pixel-based strategy follows earlier microglial motility work [@Fuhrmann:2010; @Nebeling:2023] while providing a fully automated and batchable implementation with parameter logging and diagnostics.

The pipeline exposes options for 3D or 2D registration, contrast-limited adaptive histogram equalization, histogram matching across time to mitigate bleaching, and median or Gaussian filtering [@Pizer:1987; @Walt:2014; @Virtanen:2020]. Results include segmented images, G/L/S/TOR values, brightness and area traces, and spreadsheets for downstream statistics. Memory-efficient reading and chunked processing of large TIFFs are supported via Zarr [@Miles:2025].

![Example analysis with MotilA. **a)** z-projected microglial images at two consecutive time points ($t_0$, $t_1$), shown as raw, processed, and binarized data. **b)** pixel-wise classification of gained (G), stable (S), and lost (L) pixels used to compute the turnover rate (TOR). **c)** TOR values across time points from the same dataset, illustrating dynamic remodeling of microglial fine processes.](figures/motila_figure.pdf)


## Usage
*MotilA* can be called from Python scripts or Jupyter notebooks. Three entry points cover common scenarios: `process_stack` for a single stack, `batch_process_stacks` for a project folder organized by dataset identifiers with a shared metadata sheet, and `batch_collect` to aggregate metrics across datasets. All steps write intermediate outputs and logs to facilitate validation and reproducibility. *MotilA*'s GitHub repository provides tutorials and an example dataset to shorten onboarding.

## Applications and scope
*MotilA* has been applied to quantify microglial process dynamics in several *in vivo* imaging studies and preprints [@FFuhrmann:2024; @Crux:2024; @Gockel:2025]. Typical use cases include baseline surveillance behavior, responses to neuroinflammation or genetic perturbations, and deep three-photon imaging where manual analysis is impractical. The binarize-and-compare principle can in principle be adapted to other structures such as dendrites or axons when segmentation across time is robust.

## Limitations
Using 2D projections simplifies processing but sacrifices axial specificity and can merge overlapping structures. Segmentation quality determines accuracy and can be affected by vessels, low signal-to-noise ratios, or strong intensity drift. The current spectral unmixing is a simple subtraction; advanced approaches may be needed for some fluorophores. *MotilA* targets pixel-level process motility rather than object-level tracking or full morphometry.

Using 2D Z-projections confines motility quantification to the XY plane, but this reflects practical constraints of two-photon microglial imaging. Axial resolution degrades with imaging depth, yielding elongated point-spread functions and reduced contrast along Z, which makes voxel-wise 3D segmentation of thin microglial processes unreliable. Maximum-intensity projection increases effective signal per pixel and follows established practice in earlier microglial motility work (see, e.g., @Fuhrmann:2010; @Nebeling:2023). This approach necessarily sacrifices axial specificity and can merge structures that overlap in Z, particularly in densely populated regions, which are best avoided by selecting a sub-volume with minimal axial overlap. Fully 3D motility analysis would require volumetric segmentation, morphological reconstruction, and substantially higher memory and computational resources and is therefore out of scope for the current version of *MotilA*.

Beyond the inherent limitations of Z-projection, segmentation quality critically affects accuracy and can be influenced by blood vessels, low signal-to-noise ratios, and strong intensity drift across time. The current spectral unmixing is implemented as a simple subtraction and may be insufficient for fluorophores with complex spectral overlap. *MotilA* targets pixel-level process motility rather than object-level tracking or full morphometry, and its interpretability depends on reliable and consistent segmentation across frames.


## Example dataset
The repository includes two *in vivo* two-photon stacks from mouse frontal cortex formatted for use with *MotilA* [@Gockel:2025]. Each stack contains eight time points at five-minute intervals, two channels for microglia and neurons, and approximately sixty z-planes at one micrometer steps in a field of view of about 125 by 125 micrometers. The example reproduces the full analysis, including projections, segmentation, change maps, brightness traces, and TOR over time, and serves as a template for cohort-level workflows.

## Availability
Source code, documentation, tutorials, and issue tracking are hosted at: [https://github.com/FabrizioMusacchio/motila](https://github.com/FabrizioMusacchio/motila). The software runs on Windows, macOS, and Linux with Python 3.9 or newer and standard scientific Python stacks. It is released under GPL-3.0, and contributions via pull requests or issues are welcome.

## Acknowledgements
We thank the Light Microscopy Facility and Animal Research Facility at the DZNE, Bonn, for essential support. This work was supported by the DZNE and grants to MF from the ERC (MicroSynCom 865618) and the DFG (SFB1089 C01, B06; SPP2395). MF is a member of the DFG Excellence Cluster ImmunoSensation2. Additional support came from the iBehave network and the CANTAR network funded by the Ministry of Culture and Science of North Rhine-Westphalia, and from the Mildred-Scheel School of Oncology Cologne-Bonn. Animal procedures followed institutional and national regulations, with efforts to reduce numbers and refine conditions.

## References
