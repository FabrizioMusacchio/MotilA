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
*MotilA* is an open-source Python pipeline for quantifying motility of microglial fine processes in 3D time-lapse two-channel fluorescence microscopy. It was developed for high-resolution *in vivo* multiphoton imaging and supports both single-stack and batch analyses. The workflow performs sub-volume extraction, optional registration and spectral unmixing, 2D z-projection, adaptive segmentation, and pixel-wise change detection across time to compute biologically interpretable metrics such as the fine-process turnover rate (TOR). The code is platform independent, documented with tutorials and an example dataset, and released under GPL-3.0.

## Statement of need
Microglia are innate immune cells of the central nervous system and continuously remodel highly branched processes to survey brain tissue and to respond to pathology [@Nimmerjahn:2005; @Fuhrmann:2010; @Tremblay:2010; @Prinz:2019]. Quantifying this subcellular motility is important for studies of neuroinflammation, neurodegeneration, and synaptic plasticity. Current practice in many labs relies on manual or semi-manual measurements in general-purpose tools such as Fiji/ImageJ or proprietary software [@Schindelin:2012; @ZeissZEN:2025]. These procedures are time consuming, hard to reproduce, and poorly suited for cohort-level comparisons; they often analyze single cells rather than fields of view, and they are sensitive to user bias [@Wall:2018; @Brown:2017]. There is no dedicated, open, and batch-capable solution tailored to this task.

*MotilA* fills this gap with an end-to-end, reproducible pipeline for 3D time-lapse two-channel imaging. It standardizes preprocessing, segmentation, and motility quantification and scales from individual stacks to large experimental cohorts. Although optimized for microglia, the approach generalizes to other motile structures that can be reliably segmented over time.

## Implementation and core method
Input is a 5D stack in TZCYX or TZYX order, where T is time, Z is depth, C is channel, and YX are spatial dimensions. For each time point, *MotilA* extracts a user-defined z-sub-volume, optionally performs 3D motion correction and spectral unmixing, and computes a 2D maximum-intensity projection to enable fast and interpretable segmentation. After adaptive thresholding, the binarized projection at time $t_i$, denoted $B(t_i)$, is compared with $B(t_{i+1})$ to derive a temporal change map

$$\Delta B(t_i)=2B(t_i)-B(t_{i+1}).$$

Pixels are classified as stable "S" ($\Delta B=1$), gained "G" ($\Delta B=-1$), or lost "L" ($\Delta B=2$). From these counts, the turnover rate is defined as

$$TOR=\frac{G+L}{S+G+L},$$

representing the fraction of pixels that changed between consecutive frames. This pixel-based strategy follows earlier microglial motility work [@Fuhrmann:2010; @Nebeling:2023] while providing a fully automated and batchable implementation with parameter logging and diagnostics.

The pipeline exposes options for 3D or 2D registration, contrast-limited adaptive histogram equalization, histogram matching across time to mitigate bleaching, and median or Gaussian filtering [@Pizer:1987; @Walt:2014; @Virtanen:2020]. Results include segmented images and overlays, per-time-point G, L, S, and TOR values, brightness and area traces, and summary spreadsheets for downstream statistics. Memory-efficient reading and chunked processing of large TIFFs are supported via Zarr [@Miles:2025].

![Example analysis with MotilA. **a)** z-projected microglial images at two consecutive time points ($t_0$, $t_1$), shown as raw, processed, and binarized data. **b)** pixel-wise classification of gained (G), stable (S), and lost (L) pixels used to compute the turnover rate (TOR). **c)** TOR values across time points from the same dataset, illustrating dynamic remodeling of microglial fine processes. Scale bar represents 10 μm.](figures/motila_figure.pdf)


## Usage
*MotilA* can be called from Python scripts or Jupyter notebooks. Three entry points cover common scenarios: `process_stack` for a single stack, `batch_process_stacks` for a project folder organized by dataset identifiers with a shared metadata sheet, and `batch_collect` to aggregate metrics across datasets. All steps write intermediate outputs and logs to facilitate validation and reproducibility. *MotilA*'s GitHub repository provides tutorials and an example dataset to shorten onboarding.

## Applications and scope
*MotilA* has been applied to quantify microglial process dynamics in several *in vivo* imaging studies and preprints [@FFuhrmann:2024; @Crux:2024; @Gockel:2025]. Typical use cases include baseline surveillance behavior, responses to neuroinflammation or genetic perturbations, and deep three-photon imaging where manual analysis is impractical. The binarize-and-compare principle can in principle be adapted to other structures such as dendrites or axons when segmentation across time is robust.

## Limitations
Using 2D projections simplifies processing but sacrifices axial specificity and can merge overlapping structures. Segmentation quality determines accuracy and can be affected by vessels, low signal-to-noise ratios, or strong intensity drift. The current spectral unmixing implementation is a simple subtraction, and more advanced approaches may be needed for some fluorophore combinations. *MotilA* targets pixel-level process motility rather than object-level tracking or full morphometry.

## Example dataset
The repository includes two *in vivo* two-photon time-lapse stacks from mouse frontal cortex formatted for direct use with *MotilA* [@Gockel:2025]. Each stack contains eight time points at five-minute intervals, two channels for microglia and neurons, and approximately sixty z-planes at one micrometer steps in a field of view of about 125 by 125 micrometers. The example reproduces the full analysis, including projections, segmentation, change maps, brightness traces, and TOR over time, and serves as a template for cohort-level workflows.

## Availability
Source code, documentation, tutorials, and issue tracking are hosted at: [https://github.com/FabrizioMusacchio/motila](https://github.com/FabrizioMusacchio/motila). The software runs on Windows, macOS, and Linux with Python 3.9 or newer and standard scientific Python stacks. It is released under GPL-3.0, and contributions via pull requests or issues are welcome.

## Acknowledgements
We thank the Light Microscopy Facility and Animal Research Facility at the DZNE, Bonn, for essential support. This work was supported by the DZNE and grants to MF from the ERC (MicroSynCom 865618) and the DFG (SFB1089 C01, B06; SPP2395). MF is a member of the DFG Excellence Cluster ImmunoSensation2. Additional support came from the iBehave network and the CANTAR network funded by the Ministry of Culture and Science of North Rhine-Westphalia, and from the Mildred-Scheel School of Oncology Cologne-Bonn. Animal procedures for the example dataset followed institutional and national regulations, with efforts to reduce animal numbers and refine procedures.

## References
