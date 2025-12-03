# MotilA Roadmap 🛣️

This roadmap summarizes planned improvements and future extensions derived from user feedback, JOSS reviewer suggestions, and long term development goals. Items listed here are not part of the current release but are planned for future versions.


## Support for additional input formats and axis configurations
* Implementing dedicated support for **TYX time-lapse stacks**. <br> The core algorithm is already compatible, but explicit input handling and metadata inference still need to be added.


## Data formats and metadata handling
* Transition all tabular outputs from **.xls** to **.csv** for long term sustainability and interoperability.
* Transition `_processing_parameters.xlsx` to **.yml** format to improve open access, better human readability and easier parsing.
* Migrating metadata files (currently .xls) to **.yml**  format to improve open access, better human readability and easier parsing. Migration must preserve backward compatibility.
* Standardizing all folder and file names to **avoid whitespace** and to use underscores for cross-platform stability (e.g., `example dataset` ⟶ `example_dataset`).


## Repository organization and auxiliary datasets
* ✅ **[addressed in release v1.1.0]** Providing the **cutout dataset** as a separate Zenodo record linked to the main example datasets. This avoids overwriting example projects and allows independent downloads. Also, it reduced the size of the main repository.


## Including JOSS review changes
* ✅ **[release v1.1.0 is done]** Push a new release to **v1.1.0** on GitHub and PyPI to include all changes made during the JOSS review process.