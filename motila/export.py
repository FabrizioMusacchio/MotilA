"""
Tabular export helpers for MotilA.

Excel remains MotilA's default table format for backward compatibility. CSV and
YAML can be requested as optional sidecar exports with matching base filenames.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# %% EXPORT CONSTANTS
DEFAULT_TABLE_EXPORT_FORMATS = ("excel",)

# %% TABLE EXPORT HELPERS

def _normalize_table_export_formats(table_export_formats):
    """Normalize table export format settings while keeping Excel as the default."""
    if table_export_formats is None:
        table_export_formats = DEFAULT_TABLE_EXPORT_FORMATS
    if isinstance(table_export_formats, str):
        table_export_formats = (table_export_formats,)

    aliases = {
        "xls": "excel",
        "xlsx": "excel",
        "excel": "excel",
        "csv": "csv",
        "yml": "yaml",
        "yaml": "yaml",
    }
    normalized = []
    for export_format in table_export_formats:
        key = str(export_format).lower()
        if key not in aliases:
            valid_formats = ", ".join(sorted(set(aliases.values())))
            raise ValueError(
                f"Unsupported table export format '{export_format}'. "
                f"Supported formats are: {valid_formats}."
            )
        mapped = aliases[key]
        if mapped not in normalized:
            normalized.append(mapped)
    return tuple(normalized)

def _normalize_table_export_value(value):
    """Convert NumPy, pandas, and Path values to YAML-safe Python values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_normalize_table_export_value(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_normalize_table_export_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize_table_export_value(val)
            for key, val in value.items()
        }
    if pd.isna(value):
        return None
    return value

def export_dataframe(df, excel_path, table_export_formats=None, index=True):
    """
    Export a DataFrame to Excel and optionally sidecar CSV/YAML files.

    Excel remains the default and the canonical path. Optional CSV and YAML
    exports use the same base filename with ``.csv`` and ``.yaml`` suffixes.
    """
    export_formats = _normalize_table_export_formats(table_export_formats)
    excel_path = Path(excel_path)
    written_paths = {}

    if "excel" in export_formats:
        df.to_excel(excel_path, index=index)
        written_paths["excel"] = excel_path
    if "csv" in export_formats:
        csv_path = excel_path.with_suffix(".csv")
        df.to_csv(csv_path, index=index)
        written_paths["csv"] = csv_path
    if "yaml" in export_formats:
        yaml_path = excel_path.with_suffix(".yaml")
        yaml_df = df.reset_index() if index else df
        yaml_records = [
            {
                str(key): _normalize_table_export_value(value)
                for key, value in row.items()
            }
            for row in yaml_df.to_dict(orient="records")
        ]
        with open(yaml_path, "w", encoding="utf-8") as yaml_file:
            yaml.safe_dump(
                yaml_records,
                yaml_file,
                sort_keys=False,
                allow_unicode=True,
            )
        written_paths["yaml"] = yaml_path

    return written_paths

# %% END
