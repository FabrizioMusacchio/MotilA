## MotilA Changelog

See here for a detailed list of changes made in each release of MotilA.
Please, also refer to the Repository [Releases page](https://github.com/FabrizioMusacchio/motila/releases).

Each release is also archived on Zenodo for long-term preservation and citation purposes:

[![Zenodo Archive](https://img.shields.io/badge/Zenodo%20Archive-10.5281%2Fzenodo.15175053-blue)](https://doi.org/10.5281/zenodo.15175053)


--- 

### 🔜 MotilA v1.1.1 - UNRELEASED

#### Flexible image I/O via OMIO

MotilA now uses **OMIO** for image reading and stack-style TIFF output writing. Input stacks are normalized to OME-compliant ``TZCYX`` order before MotilA's core processing begins, which relaxes the previous requirement that TIFF files already arrive in MotilA's expected axis order.

Supported pipeline input formats now include:

* ``.tif`` / ``.tiff`` / OME-TIFF
* ``.czi``
* Thorlabs ``.raw``
* ``.lsm``

The core motility-processing logic remains unchanged: MotilA still extracts subvolumes, uses its existing Zarr-backed intermediate storage, performs the same registration/filtering/segmentation steps, and computes the same motility metrics. A future OMIO-Zarr migration remains a separate follow-up.

#### API and batch processing updates

* Added OMIO-backed ``read_image_stack`` and ``write_image_stack`` helpers.
* ``process_stack`` now reads supported image files via OMIO and logs the normalized input shape and axes.
* ``get_stack_dimensions`` now reports the OMIO-normalized ``TZCYX`` shape. For single-channel data this includes ``C=1``.
* ``extract_subvolume`` and ``extract_and_register_subvolume`` now operate on OMIO-normalized ``TZCYX`` input while preserving the 4D subvolume arrays used by downstream MotilA processing.
* ``batch_process_stacks`` now searches the registered-image folder for all supported OMIO image extensions instead of only ``.tif`` files.

#### Repository path cleanup

The example and internal script folders were renamed to remove whitespace:

* ``example scripts`` → ``example_scripts``
* ``example project`` → ``example_project``
* ``example notebooks`` → ``example_notebooks``
* ``user scripts`` → ``user_scripts``

All affected scripts, notebooks, README links, and Read the Docs pages were updated accordingly.

#### Tests and documentation

* Added tests for OMIO-based axis normalization from ``TZYX`` to ``TZCYX``.
* Updated tests for the new normalized shape semantics.
* Updated the RTD data requirements, tutorials, overview, and API reference for OMIO-supported formats.
* Disabled GUI-related pytest plugin autoloading for Napari/NPE plugins in the project test configuration, avoiding terminal/CI cache issues introduced by OMIO's optional Napari dependencies.
* Removed coverage options from default pytest arguments so ``pytest`` works in a minimal test environment; coverage can still be requested explicitly in CI or development runs.

---

### 🚀 MotilA v1.1.0 Release Notes

#### 🚀 Major improvements: installation, API structure, CI, code coverage, documentation, and roadmap
This release introduces several substantial improvements that modernize the installation workflow, strengthen the package structure, add full Read the Docs documentation, ensure consistent behavior across environments, notebooks, and CI testing, and formally introduce a project-level roadmap for future development.  In addition, citation metadata has been consolidated. The previously included `.zenodo.json` file has been removed to avoid duplication and version mismatches. MotilA now uses `CITATION.cff` as the single authoritative source of citation information.

Many of these enhancements were developed in direct response to the constructive feedback provided during the JOSS review process, which greatly strengthened the overall robustness of the software and significantly improved its readiness for sustainable open-source development.

#### 📚 **Full Read the Docs documentation**

MotilA now includes a complete, structured documentation site:

**🔗 https://motila.readthedocs.io**

The new documentation provides:

* A full Sphinx-based site with:
  * automated API reference (autodoc, autosummary, napoleon, typehints)
  * detailed descriptions of preprocessing steps  
    (3D and 2D registration, spectral unmixing, histogram equalization and matching, filtering)
  * input format expectations (TZCYX and TZYX)
  * an expanded pipeline overview with figures
  * structured tutorials and example datasets
  * clear parameter explanations
  * API references for all main and utility functions
* A dedicated **Contributing** section
* Cross-referenced pages and improved navigation

These changes make MotilA's documentation maintainable and easy to extend.


#### 🔧 **API improvements**
##### ✔️ Clean top-level API
MotilA now exposes its main functions directly at package level:

```python
import motila as mt
mt.process_stack(...)
````

The top-level namespace includes:

* `process_stack`
* `batch_process_stacks`
* `batch_collect`
* `hello_world`
* `tiff_axes_check_and_correct`

##### ✔️ Backward compatibility preserved

The older import style remains functional:

```python
from motila import motila as mt
```

#### 🧹 **Internal code cleanup**

* Removed all debugging code under `if __name__ == '__main__':` in production modules
* Removed all `sys.path.append(...)` development helpers
* Cleaned unused imports throughout scripts and notebooks
* Unified import patterns to:

  ```python
  import motila as mt
  ```

* Updated in-code comments for clarity
* Updated example_notebooks and scripts

#### 🏷️ Citation metadata cleanup

MotilA now standardizes its citation metadata by removing the obsolete `.zenodo.json` file. This file originated from an older DOI workflow and is no longer required. Maintaining two parallel metadata sources introduced the possibility of version inconsistencies. With this change, `CITATION.cff` is the sole source of truth for citation information, ensuring clarity and long-term maintainability.

#### 📦 **Installation & environment handling**

##### ✔️ Modernized installation instructions

The README now uses current best practices:

```bash
pip install motila
pip install .
pip install -e .
pip install git+https://github.com/FabrizioMusacchio/MotilA.git
```

Additions include:

* clearer environment recommendations
* explicit warnings about mixing install methods
* notes on correct kernel selection for notebooks
* simplified dependency setup

##### ✔️ Example scripts updated

* All development-only `sys.path.append` statements commented out with explanation
* Scripts now run out-of-the-box after a standard installation

#### 📂 Example dataset externalization
The example dataset previously included inside the repository has been removed and is now hosted on Zenodo as a citable research object. Both the full dataset and a curated subset ("cutout") are available for independent download:

* Full dataset: **Musacchio et al., 2025**, DOI: [10.5281/zenodo.15061566](https://zenodo.org/records/15061566)  
* Subset ("cutout"): **Musacchio, 2025**, DOI: [10.5281/zenodo.17803977](https://zenodo.org/records/17803977)

Externalizing the data avoids accidental overwriting of example_projects inside the repository, enables clean and reproducible workflows, and significantly reduces the size of the main MotilA installation.

#### 🧪 **CI workflow modernization**
The GitHub Actions workflow (`python-tests.yml`) has been updated to match real-world user workflows:

* creates a clean conda environment
* installs MotilA via `pip install .`
* installs pytest and coverage tools
* runs the test suite and uploads coverage

This ensures consistent behavior across systems.

#### 📊 **Test coverage integration**
MotilA now includes full test coverage reporting integrated directly into the development workflow.

* The test suite is executed with `pytest-cov`, generating standardized coverage reports.
* GitHub Actions automatically upload coverage reports to Codecov on every push and pull request.
* A Codecov badge in the README provides immediate visibility into current test coverage.
* Coverage includes core functionality such as subvolume extraction, optional registration, spectral unmixing, segmentation, change detection, and Zarr-based chunked processing.

This integration enhances transparency, supports reproducibility, and improves long-term maintainability of the pipeline.

#### 🧭 **Contribution and community guidelines**
MotilA now includes:

* **CONTRIBUTING.md**, covering:
  * environment setup
  * branching and workflow
  * pull request guidelines
  * commit conventions
  * issue reporting
* **CODE_OF_CONDUCT.md**, based on the Contributor Covenant
* Both documents integrated into the Read the Docs site

These additions support healthy, sustainable project development.

#### 🗺️ **Roadmap implementation**
MotilA now includes a project-level roadmap (`ROADMAP.md`) that outlines planned future enhancements and long-term development priorities. The roadmap documents upcoming changes such as dedicated TYX support, transition of tabular outputs from `.xls` to `.csv` or `.yml`, standardization of naming conventions for cross-platform compatibility, restructuring of example_scripts, and further expansions to the documentation. This file provides a transparent reference for users and contributors and supports structured, forward-looking development.

#### 🧹 **Additional documentation refinements**

* Expanded "Example Usage" with parameter explanations
* Added example parameter blocks from tutorial scripts
* Added screenshot of Zenodo dataset structure
* Ensured consistent and accessible reStructuredText formatting
* Improved cross-referencing throughout the documentation

#### Summary
**MotilA v1.1.0** focuses on strengthening:

* installation consistency
* API clarity
* documentation quality
* development workflow
* CI reliability
* code cleanliness
* forward-oriented planning through an explicitly documented roadmap

The release also consolidates citation metadata by removing the outdated `.zenodo.json` file and designating `CITATION.cff` as the central and only citation reference.

The integration of automated test coverage and public reporting additionally reinforces MotilA's robustness by making testing completeness visible and traceable to users and contributors.

These improvements significantly enhance the usability, maintainability, and long-term stability of MotilA.

If you encounter any issues or have suggestions, please open an issue on GitHub.

We thank the JOSS reviewers for their constructive feedback, which helped guide several of the improvements included in this release.  

Thank you for using MotilA!


---

### 🚀 MotilA v1.0.7 Release Notes

#### 🐞 Critical bugfix: PyStackReg support in batch processing
This release fixes a critical issue that prevented PyStackReg from being used in batch processing, along with a minor metadata filtering correction.

##### 🚨 Critical bug fixed

- **Missing `usepystackreg` parameter in `batch_process_stacks`**: The `usepystackreg` parameter was not being passed through to the `process_stack` function during batch processing. This meant that even when `usepystackreg=True` was set, the batch processor would always use phase cross-correlation instead of PyStackReg for 2D registration. This has been fixed and PyStackReg now works correctly in batch mode.

##### 🐞 Minor bug fixed

- **Metadata file filtering**: Fixed hardcoded "metadata.xls" string in the batch processor's metadata file search. The function now correctly uses the `metadata_file` parameter, allowing for flexible metadata file naming (e.g., "metadata.xlsx", "parameters.xls", etc.).

##### Technical details

- The `usepystackreg` parameter is now properly passed from `batch_process_stacks` to `process_stack`.
- Metadata file filtering now uses the configurable `metadata_file` parameter instead of a hardcoded string.
- Both single-file and batch processing now consistently support PyStackReg registration.

**Critical upgrade recommended for all users who rely on PyStackReg for 2D registration in batch processing.**

Thank you for using MotilA! If you encounter any issues, please open

---

### 🚀 MotilA v1.0.6 Release Notes

#### 🐞 Bugfix: skip processing for invalid projection ranges

This release adds an important safety check to prevent processing of files with invalid projection parameters.

##### Bug fixed

- **Added file skipping for invalid projection ranges**: The main processing pipeline now properly checks if `calc_projection_range` returns zero projection layers and skips processing the current file instead of continuing with invalid parameters. This prevents errors and wasted processing time when projection parameters are incompatible with the image stack dimensions.

##### Technical details

- When `projection_center` is out of bounds or results in an invalid projection range, `calc_projection_range` returns `projection_layers = 0`.
- The main processing function now detects this condition and logs a warning message before safely skipping the file.
- This ensures robust handling of edge cases where projection parameters don't match the available z-dimension of image stacks.

**Upgrade recommended for all users to ensure robust file processing.**

Thank you for using MotilA! If you encounter any issues, please open an issue

---

### 🚀 MotilA v1.0.5 Release Notes

#### 🐞 Bugfix: projection range and layer count consistency

This release fixes an important consistency issue in the projection range calculation logic.

##### Bug fixed

- **Corrected `calc_projection_range` output consistency**: Fixed an issue where the `projection_layers` count could become inconsistent with the actual `projection_range` when the requested range exceeded the image stack's z-dimension boundaries. The function now properly updates and returns the corrected `projection_layers` count to match the adjusted projection range, ensuring accurate layer counting for downstream processing steps.

##### Technical details

- When a projection range exceeds the available z-layers in an image stack, MotilA now correctly adjusts both the range boundaries AND the layer count to maintain consistency.
- This prevents potential errors or unexpected behavior in subsequent processing steps that rely on accurate layer counts.


**Upgrade recommended for all users to ensure consistent projection handling.**

Thank you for using MotilA! If you encounter any issues, please open

---

### 🚀 MotilA v1.0.4 Release Notes

#### 🐞 Bugfix & 🚀 New feature: registration improvements

This release includes a critical bugfix for subvolume extraction and registration, along with an exciting new registration option for enhanced flexibility.

##### 🐞 Bug fixes
- **Fixed Shift Application in Subvolume Extraction**
  - Corrected shift application logic in `extract_and_register_subvolume` function to ensure proper alignment of extracted subvolumes.
  - Updated dataset creation for full Zarr 3.0+ compatibility within the same function, resolving potential data handling issues.

##### 🚀 New features
- **PyStackReg Support for 2D Registration**
  - Added support for **PyStackReg** (StackReg) as an alternative method for 2D image registration of projected stacks.
  - Enhanced `reg_2D_images` and `process_stack` functions with new parameter `usepystackreg`.
  - Users can now choose between phase cross-correlation (default) and PyStackReg for 2D registration:
    - Set `usepystackreg=False` for phase cross-correlation (default behavior)
    - Set `usepystackreg=True` to use PyStackReg registration
  - PyStackReg may provide more robust registration in certain imaging conditions, particularly for images with low contrast or minimal features.

#### Parameter updates
The following new parameter is available in both single-file and batch processing:

| Parameter | Values | Description |
|-----------|---------|-------------|
| `usepystackreg` | `bool` (`True` or `False`) | If `True`, use PyStackReg (StackReg) for 2D registration instead of phase cross-correlation. |



---

### 🚀 MotilA v1.0.3 Release Notes

#### 🐞 Bugfix: Zarr v3+ compatibility

This release brings important fixes to ensure MotilA works seamlessly with Zarr version 3 and higher.

##### Highlights

- **Zarr v3+ Support:**  
  - Fixed all known compatibility issues with Zarr v3 and above.
  - Ensured correct handling of shape and chunk arguments (now always plain Python `int`).
  - Updated all Zarr array and group creation/access patterns to match the new Zarr v3 API.
  - Improved detection and handling of Zarr store attributes (`.url` for v3, `.path` for v2).
  - Fixed assignment and reading issues that could cause sync errors in async environments (e.g., Jupyter, pytest).
  - Tests and code now use `zarr.Array` for type checks, compatible with both v2 and v3.

- **General Robustness:**  
  - The codebase is now more robust to future Zarr changes and works with both Zarr v2 and v3.


Thank you to all users who reported Zarr v3 issues and helped test the fixes!  
If you encounter any further problems, please open an issue on GitHub.

**Upgrade recommended for all users, especially those using Zarr v3 or newer.**

---

### 🚀 MotilA v1.0.2 Release Notes

#### 🐞 Bugfix & improvement: projection range calculation

This release focuses on a critical bugfix and improvements to the projection range logic in MotilA's core image processing pipeline.

##### Highlights

- **Projection Range Calculation Overhaul**
  - Removed the unnecessary `projection_layers_correction` variable.
  - Simplified and clarified the logic to ensure the projection range always includes exactly the requested number of layers (`projection_layers`), even when the projection center is near the image boundaries.
  - The projection range is now symmetrically expanded around the center when possible, and boundaries are correctly handled if the range would exceed the image stack's z-dimension.
  - Improved the robustness and readability of the `calc_projection_range` function for more accurate and predictable behavior.

##### Bug fixed

- Fixed an issue where the projection range could be off by one or not include the correct number of layers, especially when the projection center was close to the start or end of the z-stack.

##### Other

- Test folders generated during automated testing are now deleted after tests complete, keeping your workspace clean.


Thank you to all users who reported issues and contributed feedback!  
If you encounter any further problems, please open an issue on GitHub.

**Upgrade recommended for all users.**

---

### 🚀 MotilA v1.0.1 - Dummy release

* dummy release for Zenodo

---

### 🚀 MotilA v1.0.0 – Initial public release

We are pleased to release **MotilA v1.0.0**, the first versioned and archived release of the MotilA analysis pipeline.

MotilA is designed for automated and scalable analysis of **4D and 5D multi-photon time-lapse imaging data**, with a particular focus on quantifying **microglial motility**. This release introduces a stable and tested version of the core pipeline, including:

#### ✨ Features

* Support for **single-stack and batch analysis** of 4D and 5D imaging data
* Automated extraction and quantification of **motility** from segmented stacks
* Full integration with the **Napari viewer**
* Included **example dataset** (via Zenodo) for testing and teaching
* **Jupyter-based tutorials** for easy onboarding and reproducibility
* Modular pipeline structure for future extensions

#### 📦 Dataset and tutorials

You can find the example dataset accompanying this release here:  
👉 [https://zenodo.org/records/15061566](https://zenodo.org/records/15061566)  

A hands-on tutorial notebook is included in the `tutorials/` folder of this repository.
