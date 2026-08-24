"""
Batch processing and result collection for MotilA.

This module contains the current batch-processing wrapper and cohort-level
result aggregation. It is intentionally separated to make room for a future,
more extensive batch processor.

author: Fabrizio Musacchio  
date: September 2023
ported to modular MotilA: August 2026
"""
# %% IMPORTS
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from motila.utils import filterfiles_by_string, filterfolder_by_string, print_ram_usage
from .export import DEFAULT_TABLE_EXPORT_FORMATS, export_dataframe
from .io import SUPPORTED_IMAGE_EXTENSIONS, read_image_stack
from .pipeline import process_stack
# %% CONSTANTS
DEFAULT_IMAGE_PATTERNS = (
    "*.ome.tif",
    "*.ome.tiff",
    "*.tif",
    "*.tiff",
    "*.czi",
    "*.lsm",
    "*.raw")

DEFAULT_TAG_FOLDER_LEVELS = (("TP",),)

DEFAULT_RAW_TEMPLATE_METADATA = {
    "T": 1,
    "Z": 1,
    "C": 1,
    "Y": 1,
    "X": 1,
    "bits": 16,
    "pixelunit": "micron",
    "physicalsize_xyz": (0.5, 0.5, 1.0),
    "time_increment": 1.0,
    "time_increment_unit": "seconds"}
# %% DATA CLASSES
@dataclass(frozen=True)
class BatchImageRecord:
    """One image discovered in a BIDS-like MotilA batch project."""

    subject_id: str
    tag_folders: tuple[str, ...]
    image_path: Path
    output_scope_dir: Path

    @property
    def experiment_tag(self) -> str:
        """Backward-compatible first tag folder label."""

        return self.tag_folders[0] if self.tag_folders else ""


@dataclass(frozen=True)
class BatchProcessedRecord:
    """One successfully processed image/projection-center pair."""

    input_path: Path
    output_dir: Path
    subject_id: str
    tag_folders: tuple[str, ...]
    projection_center: int | float | str


@dataclass(frozen=True)
class BatchSkippedRecord:
    """One image/projection-center pair skipped without being treated as failed."""

    input_path: Path
    reason: str
    subject_id: str
    tag_folders: tuple[str, ...] = ()
    stage: str = "unknown"
    output_dir: Path | None = None
    projection_center: int | float | str | None = None


@dataclass(frozen=True)
class BatchErrorRecord:
    """Structured per-file MotilA batch error record."""

    timestamp: str
    input_path: Path
    relative_path: str
    stage: str
    exception_type: str
    message: str
    subject_id: str
    tag_folders: tuple[str, ...] = ()
    output_dir: Path | None = None
    projection_center: int | float | str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchProcessingResult:
    """Summary returned by :func:`batch_process_stacks`."""

    processed: tuple[BatchProcessedRecord, ...] = ()
    skipped: tuple[BatchSkippedRecord, ...] = ()
    failed: tuple[BatchErrorRecord, ...] = ()
    discovered: tuple[BatchImageRecord, ...] = ()
    report_path: Path | None = None
    run_report_yaml_path: Path | None = None
    error_report_path: Path | None = None
    file_error_report_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class BatchRawYamlTemplateRecord:
    """One RAW file considered for OMIO YAML template creation."""

    raw_path: Path
    yaml_path: Path | None
    template_metadata: dict[str, Any]
    status: str
    reason: str = ""


@dataclass(frozen=True)
class BatchRawYamlTemplateResult:
    """Summary returned by :func:`batch_create_thorlabs_raw_yaml_templates`."""

    report_path: Path | None
    records: tuple[BatchRawYamlTemplateRecord, ...] = ()

    @property
    def created(self) -> tuple[BatchRawYamlTemplateRecord, ...]:
        """RAW files for which YAML template creation was attempted."""

        return tuple(record for record in self.records if record.status == "created")

    @property
    def skipped(self) -> tuple[BatchRawYamlTemplateRecord, ...]:
        """RAW files skipped during YAML template creation."""

        return tuple(record for record in self.records if record.status != "created")


@dataclass(frozen=True)
class BatchCollectionRecord:
    """One collected MotilA result folder."""

    input_path: Path
    output_dir: Path
    subject_id: str
    tag_folders: tuple[str, ...]
    projection_center: str


@dataclass(frozen=True)
class BatchCollectionResult:
    """Summary returned by :func:`batch_collect`."""

    collected: tuple[BatchCollectionRecord, ...] = ()
    skipped: tuple[BatchSkippedRecord, ...] = ()
    discovered: tuple[BatchImageRecord, ...] = ()
    results_path: Path | None = None


class _BatchConsoleLogger:
    """Small fallback logger used when no MotilA logger object is provided."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.messages: list[str] = []

    def log(self, msg: str):
        self.messages.append(msg)
        if self.verbose:
            print(msg)

    def logt(self, t0, verbose=True, spaces=0, unit="sec", process=""):
        dt = time.time() - t0
        self.log(" " * spaces + f"{process} done")
        return dt
# %% DISCOVERY HELPERS
def _timestamp() -> str:
    """Return a report-safe timestamp string."""

    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _normalize_subject_ids(subject_ids: Iterable[str | Path] | None) -> tuple[str, ...] | None:
    """Normalize optional requested subject names."""

    if subject_ids is None:
        return None
    return tuple(str(Path(subject_id).name) for subject_id in subject_ids if str(subject_id))


def _normalize_tag_folder_levels(
    tag_folder_levels: Sequence[Iterable[str | Path] | str | Path | None] | None
) -> tuple[tuple[str, ...], ...]:
    """Normalize folder-tag levels and skip empty levels."""

    if tag_folder_levels is None:
        tag_folder_levels = DEFAULT_TAG_FOLDER_LEVELS
    normalized: list[tuple[str, ...]] = []
    for level in tag_folder_levels:
        if level is None:
            continue
        if isinstance(level, (str, Path)):
            tokens = (str(Path(level).name if isinstance(level, Path) else level),)
        else:
            tokens = tuple(str(Path(token).name if isinstance(token, Path) else token)
                           for token in level if str(token))
        if tokens:
            normalized.append(tokens)
    return tuple(normalized)


def _normalize_image_patterns(image_patterns: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalize image glob patterns and use MotilA defaults when omitted."""

    if image_patterns is None:
        return DEFAULT_IMAGE_PATTERNS
    if isinstance(image_patterns, str):
        return (image_patterns,)
    return tuple(str(pattern) for pattern in image_patterns if str(pattern))


def _name_is_excluded(name: str, exclude_name_contains: Sequence[str]) -> bool:
    """Return True when any exclude token occurs in ``name``."""

    return any(str(token) in name for token in exclude_name_contains)


def _select_matching_child_dirs(
    parent: Path,
    tags: Sequence[str],
    *,
    exclude_name_contains: Sequence[str]
) -> list[Path]:
    """Return child folders whose names contain one of ``tags``."""

    return sorted(
        path
        for path in parent.iterdir()
        if path.is_dir()
        and not _name_is_excluded(path.name, exclude_name_contains)
        and any(tag in path.name for tag in tags))


def _iter_tag_folder_chains(
    root_dir: Path,
    tag_folder_levels: Sequence[Sequence[str]],
    *,
    exclude_name_contains: Sequence[str]
) -> list[tuple[Path, ...]]:
    """Return matched folder chains for an arbitrary number of tag levels."""

    if not tag_folder_levels:
        return [()]

    current_level = tag_folder_levels[0]
    remaining_levels = tag_folder_levels[1:]
    chains: list[tuple[Path, ...]] = []
    for child_dir in _select_matching_child_dirs(
        root_dir,
        current_level,
        exclude_name_contains=exclude_name_contains):
        for tail_chain in _iter_tag_folder_chains(
            child_dir,
            remaining_levels,
            exclude_name_contains=exclude_name_contains):
            chains.append((child_dir, *tail_chain))
    return chains


def _collect_image_paths(
    scan_dir: Path,
    image_patterns: str | Sequence[str],
    *,
    exclude_name_contains: Sequence[str] = ()
) -> list[Path]:
    """Collect image files from one folder using one or multiple glob patterns."""

    patterns = (image_patterns,) if isinstance(image_patterns, str) else tuple(image_patterns)
    matched_paths: dict[Path, None] = {}
    for pattern in patterns:
        for path in scan_dir.glob(str(pattern)):
            if path.is_file() and not _name_is_excluded(path.name, exclude_name_contains):
                matched_paths[path] = None
    return sorted(matched_paths)


def _output_scope_for_chain(subject_dir: Path, tag_folder_chain: Sequence[Path]) -> Path:
    """Choose the folder that receives MotilA batch output."""

    return tag_folder_chain[0] if tag_folder_chain else subject_dir


def discover_bids_like_batch_images(
    project_root: str | Path,
    *,
    subject_ids: Iterable[str | Path] | None = None,
    subject_prefix: str = "ID",
    tag_folder_levels: Sequence[Iterable[str | Path] | str | Path | None] | None = None,
    image_patterns: str | Sequence[str] | None = None,
    exclude_name_contains: Sequence[str] = ("Preview",)
) -> list[BatchImageRecord]:
    """
    Discover microscopy image files in a flexible BIDS-like MotilA project tree.

    Parameters
    ----------
    project_root : str or pathlib.Path
        Root folder containing subject folders.
    subject_ids : iterable of str or None, optional
        Explicit subject folders to process. If None, all child folders whose
        names start with ``subject_prefix`` are used.
    subject_prefix : str, optional
        Prefix used for automatic subject discovery.
    tag_folder_levels : sequence, optional
        Folder-token levels below each subject. Empty levels, ``None``, ``()``
        and ``[]`` are skipped. Each non-empty level can contain one or more
        tokens matched by containment.
    image_patterns : str or sequence[str] or None, optional
        Glob pattern(s) used to find images in the final matched folder.
        ``None`` uses MotilA's supported default patterns.
    exclude_name_contains : sequence[str], optional
        Tokens that exclude files and matched tag folders by name.

    Returns
    -------
    list[BatchImageRecord]
        Sorted image records with subject ID, tag-folder chain, image path and
        output scope folder.
    """

    root = Path(project_root)
    if not root.exists():
        raise FileNotFoundError(f"project_root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"project_root is not a directory: {root}")

    requested_subjects = _normalize_subject_ids(subject_ids)
    if requested_subjects is None:
        subject_dirs = sorted(
            path for path in root.iterdir()
            if path.is_dir()
            and path.name.startswith(subject_prefix)
            and not _name_is_excluded(path.name, exclude_name_contains))
    else:
        subject_dirs = [root / subject_id for subject_id in requested_subjects]

    levels = _normalize_tag_folder_levels(tag_folder_levels)
    patterns = _normalize_image_patterns(image_patterns)
    records: list[BatchImageRecord] = []
    for subject_dir in subject_dirs:
        if not subject_dir.is_dir() or _name_is_excluded(subject_dir.name, exclude_name_contains):
            continue
        folder_chains = _iter_tag_folder_chains(
            subject_dir,
            levels,
            exclude_name_contains=exclude_name_contains)
        for folder_chain in folder_chains:
            scan_dir = folder_chain[-1] if folder_chain else subject_dir
            image_paths = _collect_image_paths(
                scan_dir,
                patterns,
                exclude_name_contains=exclude_name_contains)
            output_scope_dir = _output_scope_for_chain(subject_dir, folder_chain)
            tag_folders = tuple(path.name for path in folder_chain)
            for image_path in image_paths:
                records.append(
                    BatchImageRecord(
                        subject_id=subject_dir.name,
                        tag_folders=tag_folders,
                        image_path=image_path,
                        output_scope_dir=output_scope_dir))
    return records
# %% REPORT HELPERS
def _image_stem(image_path: Path) -> str:
    """Return a clean image stem while keeping OME-TIFF names compact."""

    name_lower = image_path.name.lower()
    if name_lower.endswith(".ome.tiff"):
        return image_path.name[:-9]
    if name_lower.endswith(".ome.tif"):
        return image_path.name[:-8]
    return image_path.stem


def _sanitize_name(value: Any) -> str:
    """Return a filesystem-friendly name fragment."""

    return (
        str(value)
        .replace("\\", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .replace(":", "_"))


def _relative_report_path(path: Path, root: Path) -> str:
    """Return a stable POSIX-style path relative to ``root`` when possible."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _output_dir_for_record(
    record: BatchImageRecord,
    *,
    results_folder_name: str,
    projection_center: int | float | str,
    organize_by_image: bool
) -> Path:
    """Return the MotilA output directory for one discovered image."""

    output_root = record.output_scope_dir / results_folder_name
    if organize_by_image:
        output_root = output_root / _sanitize_name(_image_stem(record.image_path))
    return output_root / f"projection_center_{projection_center}"


def _expected_outputs_exist(output_dir: Path, expected_output_names: Sequence[str]) -> bool:
    """Return True if the output folder contains the expected MotilA output."""

    return output_dir.exists() and any((output_dir / name).exists() for name in expected_output_names)


def _run_report_paths(project_root: Path, run_report_name: str) -> tuple[Path, Path]:
    """Return YAML and text report paths for one MotilA batch project."""

    report_base = project_root / run_report_name
    return report_base.with_suffix(".yaml"), report_base.with_suffix(".txt")


def _empty_run_report_payload(project_root: Path) -> dict[str, Any]:
    """Return a new run report payload."""

    return {
        "motila_batch_run_report_version": 1,
        "project_root": str(project_root),
        "last_updated": None,
        "files": {}}


def _load_run_report(path: Path, project_root: Path) -> dict[str, Any]:
    """Load an existing machine-readable run report or return an empty payload."""

    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return _empty_run_report_payload(project_root)
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        loaded = yaml.safe_load(text)
    except Exception:
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Run report is not a mapping: {path}")
    loaded.setdefault("motila_batch_run_report_version", 1)
    loaded.setdefault("project_root", str(project_root))
    loaded.setdefault("last_updated", None)
    loaded.setdefault("files", {})
    if not isinstance(loaded["files"], dict):
        raise ValueError(f"Run report 'files' entry is not a mapping: {path}")
    return loaded


def _write_run_report_yaml(path: Path, payload: dict[str, Any]) -> None:
    """Write the machine-readable run report."""

    try:
        import yaml

        text = yaml.safe_dump(
            payload,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False)
    except Exception:
        text = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")


def _run_status_label(run: dict[str, Any]) -> str:
    """Return one compact run-history line."""

    status = str(run.get("status", "unknown"))
    timestamp = str(run.get("timestamp", "unknown"))
    if status == "already_processed":
        return f"{timestamp} | skipped/already processed"
    if status == "processed":
        method_name = run.get("method_name", "MotilA process_stack")
        channel = run.get("microglia_channel")
        channel_text = f" | c={channel}" if channel is not None else ""
        return f"{timestamp} | processed | {method_name}{channel_text}"
    if status == "failed":
        stage = run.get("stage", "unknown")
        exception_type = run.get("exception_type", "Exception")
        message = run.get("message", "")
        return f"{timestamp} | failed | {stage} | {exception_type}: {message}"
    reason = run.get("reason")
    return f"{timestamp} | {status}" + (f" | {reason}" if reason else "")


def _add_tree_path(tree: dict[str, Any], parts: Sequence[str], file_key: str) -> None:
    """Add one file key to a nested folder tree."""

    node = tree
    for part in parts:
        node = node.setdefault(part, {})
    node.setdefault("__files__", []).append(file_key)


def _status_marker(file_entry: dict[str, Any]) -> str:
    """Return the visible status marker for one file in the text report."""

    status = str(file_entry.get("latest_status", "unknown"))
    if status in {"processed", "already_processed"}:
        return "PROCESSED"
    if status == "failed":
        return "FAILED"
    return status.upper()


def _render_tree_node(
    lines: list[str],
    tree: dict[str, Any],
    files: dict[str, Any],
    *,
    indent: str = ""
) -> None:
    """Render one nested folder node into ``lines``."""

    folder_names = sorted(key for key in tree if key != "__files__")
    file_keys = sorted(tree.get("__files__", []))
    entries = [(name, "folder") for name in folder_names] + [(key, "file") for key in file_keys]
    for index, (name, entry_type) in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "└─ " if is_last else "├─ "
        child_indent = indent + ("   " if is_last else "│  ")
        if entry_type == "folder":
            lines.append(f"{indent}{branch}{name}/")
            _render_tree_node(lines, tree[name], files, indent=child_indent)
            continue
        file_entry = files[name]
        lines.append(f"{indent}{branch}{Path(name).name} [{_status_marker(file_entry)}]")
        output_dir = file_entry.get("latest_output_dir")
        if output_dir:
            lines.append(f"{child_indent}output: {output_dir}")
        runs = list(file_entry.get("runs", []))
        if runs:
            lines.append(f"{child_indent}runs:")
            for run in runs:
                lines.append(f"{child_indent}  - {_run_status_label(run)}")


def _render_run_report_text(payload: dict[str, Any], path: Path) -> None:
    """Write the human-readable text run report."""

    files = payload.get("files", {})
    tree: dict[str, Any] = {}
    for file_key in files:
        parts = Path(file_key).parts
        if parts:
            _add_tree_path(tree, parts[:-1], file_key)

    lines = [
        "MotilA batch run report",
        f"Project root: {payload.get('project_root', '')}",
        f"Last updated: {payload.get('last_updated', '')}",
        ""]
    if files:
        _render_tree_node(lines, tree, files)
    else:
        lines.append("No batch image files have been recorded yet.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _append_run_report_entry(
    payload: dict[str, Any],
    record: BatchImageRecord,
    *,
    project_root: Path,
    timestamp: str,
    status: str,
    output_dir: Path | None = None,
    projection_center: int | float | str | None = None,
    method_name: str = "MotilA process_stack",
    microglia_channel: int | None = None,
    stage: str | None = None,
    exception_type: str | None = None,
    message: str | None = None,
    reason: str | None = None
) -> None:
    """Append one run-history entry for a discovered image."""

    file_key = _relative_report_path(record.image_path, project_root)
    files = payload.setdefault("files", {})
    file_entry = files.setdefault(
        file_key,
        {
            "subject_id": record.subject_id,
            "tag_folders": list(record.tag_folders),
            "input_path": file_key,
            "runs": []})
    file_entry["subject_id"] = record.subject_id
    file_entry["tag_folders"] = list(record.tag_folders)
    file_entry["input_path"] = file_key
    run_entry: dict[str, Any] = {
        "timestamp": timestamp,
        "status": status}
    if output_dir is not None:
        relative_output_dir = _relative_report_path(output_dir, project_root)
        run_entry["output_dir"] = relative_output_dir
        file_entry["latest_output_dir"] = relative_output_dir
    if projection_center is not None:
        run_entry["projection_center"] = projection_center
    if status == "processed":
        run_entry["method_name"] = method_name
        if microglia_channel is not None:
            run_entry["microglia_channel"] = microglia_channel
    if status == "failed":
        run_entry["stage"] = stage
        run_entry["exception_type"] = exception_type
        run_entry["message"] = message
    if reason:
        run_entry["reason"] = reason
    file_entry.setdefault("runs", []).append(run_entry)
    file_entry["latest_status"] = status


def _write_template_metadata_block(handle, metadata: dict[str, Any]) -> None:
    """Write one formatted ``template_metadata`` block."""

    handle.write("        'template_metadata': {\n")
    for key, value in metadata.items():
        handle.write(f"            {key!r}: {value!r},\n")
    handle.write("        },\n")


def _write_file_error_report(
    error_record: BatchErrorRecord,
    *,
    raw_template_metadata: dict[str, Any]
) -> Path:
    """Write a short per-file MotilA batch error report."""

    report_path = error_record.input_path.parent / f"motila_batch_error_report_{error_record.timestamp}.txt"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(f"MotilA batch error report: {error_record.timestamp}\n")
        handle.write(f"Input file: {error_record.input_path}\n")
        handle.write(f"Relative path: {error_record.relative_path}\n")
        handle.write(f"Stage: {error_record.stage}\n")
        handle.write(f"Exception: {error_record.exception_type}: {error_record.message}\n")
        if error_record.output_dir is not None:
            handle.write(f"Output directory: {error_record.output_dir}\n")
        if error_record.input_path.suffix.lower() == ".raw":
            handle.write(f"RAW template metadata defaults: {raw_template_metadata!r}\n")
        handle.write("\n")
    return report_path


def _write_root_error_report(
    project_root: Path,
    *,
    timestamp: str,
    failed_records: Sequence[BatchErrorRecord],
    raw_template_metadata: dict[str, Any]
) -> Path | None:
    """Write a structured root-level MotilA batch error report."""

    if not failed_records:
        return None
    report_path = project_root / f"motila_batch_error_report_{timestamp}.txt"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# MotilA batch error report: {timestamp}\n")
        handle.write("# Edit RAW 'template_metadata' blocks here before creating OMIO YAML templates.\n\n")
        handle.write("MOTILA_BATCH_ERRORS = [\n")
        for record in failed_records:
            handle.write("    {\n")
            handle.write(f"        'timestamp': {record.timestamp!r},\n")
            handle.write(f"        'input_path': {str(record.input_path)!r},\n")
            handle.write(f"        'relative_path': {record.relative_path!r},\n")
            handle.write(f"        'stage': {record.stage!r},\n")
            handle.write(f"        'exception_type': {record.exception_type!r},\n")
            handle.write(f"        'message': {record.message!r},\n")
            handle.write(f"        'subject_id': {record.subject_id!r},\n")
            handle.write(f"        'tag_folders': {record.tag_folders!r},\n")
            handle.write(f"        'output_dir': {str(record.output_dir) if record.output_dir else None!r},\n")
            handle.write(f"        'projection_center': {record.projection_center!r},\n")
            handle.write(f"        'extra': {record.extra!r},\n")
            handle.write("    },\n")
        handle.write("]\n\n")
        handle.write("MOTILA_BATCH_SKIPPED_RAW_FILES = {\n")
        for record in failed_records:
            if record.input_path.suffix.lower() != ".raw":
                continue
            handle.write(f"    {str(record.input_path)!r}: {{\n")
            handle.write(f"        'reason': {record.message!r},\n")
            handle.write(f"        'stage': {record.stage!r},\n")
            handle.write(f"        'subject_id': {record.subject_id!r},\n")
            handle.write(f"        'tag_folders': {record.tag_folders!r},\n")
            handle.write(f"        'reported_at': {timestamp!r},\n")
            _write_template_metadata_block(handle, raw_template_metadata)
            handle.write("    },\n")
        handle.write("}\n")
    return report_path
# %% RAW YAML TEMPLATE HELPERS
def _import_omio():
    """Import OMIO lazily for optional RAW YAML helper functionality."""

    try:
        import omio as om
    except ImportError as exc:
        raise ImportError(
            "Creating Thorlabs RAW YAML templates requires OMIO. Install "
            "'omio-microscopy' or use an environment that provides `import omio`."
        ) from exc
    return om


def _extract_raw_dict(report_text: str) -> dict[str, Any]:
    """Extract ``MOTILA_BATCH_SKIPPED_RAW_FILES`` from a root error report."""

    variable_name = "MOTILA_BATCH_SKIPPED_RAW_FILES"
    assignment_index = report_text.find(variable_name)
    if assignment_index < 0:
        return {}
    brace_start = report_text.find("{", assignment_index)
    if brace_start < 0:
        return {}

    depth = 0
    for index in range(brace_start, len(report_text)):
        character = report_text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                parsed = ast.literal_eval(report_text[brace_start:index + 1])
                if not isinstance(parsed, dict):
                    raise ValueError("MOTILA_BATCH_SKIPPED_RAW_FILES is not a dictionary.")
                return parsed
    raise ValueError("Could not find the end of MOTILA_BATCH_SKIPPED_RAW_FILES.")


def _extract_raw_paths_from_report_text(report_text: str) -> list[Path]:
    """Fallback parser for legacy plain-text reports containing RAW paths."""

    raw_path_pattern = re.compile(r"([A-Za-z]:\\[^\n\r'\"]+?\.raw|/[^\n\r'\"]+?\.raw)")
    return [Path(match.group(1).strip()) for match in raw_path_pattern.finditer(report_text)]


def _load_raw_entries_from_report(
    report_path: Path,
    *,
    raw_template_metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    """Load skipped RAW paths and template metadata from one MotilA report."""

    report_text = report_path.read_text(encoding="utf-8")
    raw_dict = _extract_raw_dict(report_text)
    if raw_dict:
        entries = []
        for raw_path, details in raw_dict.items():
            details = details if isinstance(details, dict) else {}
            entries.append(
                {
                    "path": Path(raw_path),
                    "template_metadata": dict(details.get("template_metadata", raw_template_metadata))})
        return entries
    return [
        {
            "path": raw_path,
            "template_metadata": dict(raw_template_metadata)}
        for raw_path in _extract_raw_paths_from_report_text(report_text)]


def _expected_raw_yaml_paths(raw_path: Path) -> tuple[Path, ...]:
    """Return likely OMIO Thorlabs RAW YAML sidecar paths."""

    return (
        raw_path.with_suffix(".yaml"),
        raw_path.with_suffix(".yml"),
        raw_path.with_name(raw_path.name + ".yaml"),
        raw_path.with_name(raw_path.name + ".yml"))


def _find_latest_batch_error_report(project_root: Path) -> Path | None:
    """Return the latest root-level MotilA batch error report if present."""

    reports = sorted(project_root.glob("motila_batch_error_report_*.txt"))
    return reports[-1] if reports else None
# %% NEW BIDS-LIKE BATCH PROCESSOR
def _metadata_options_for_record(
    record: BatchImageRecord,
    *,
    metadata_file: str | None,
    base_processing_options: dict[str, Any]
) -> tuple[dict[str, Any], list[int | float | str]]:
    """Return processing options and projection centers for one record."""

    options = dict(base_processing_options)
    projection_center = options.get("projection_center", 50)
    projection_centers = (
        list(projection_center)
        if isinstance(projection_center, (list, tuple, np.ndarray))
        else [projection_center])
    if not metadata_file:
        return options, projection_centers

    metadata_candidates = [
        record.output_scope_dir / metadata_file,
        record.image_path.parent / metadata_file]
    metadata_path = next((path for path in metadata_candidates if path.exists()), None)
    if metadata_path is None:
        return options, projection_centers

    metadata = pd.read_excel(metadata_path)
    if "Two Channel" in metadata.columns:
        options["two_channel"] = metadata["Two Channel"][0]
    if "Neuron Channel" in metadata.columns:
        options["N_channel"] = metadata["Neuron Channel"][0]
    if "Microglia Channel" in metadata.columns:
        options["MG_channel"] = metadata["Microglia Channel"][0]
    if "Spectral Unmixing" in metadata.columns:
        options["spectral_unmixing"] = metadata["Spectral Unmixing"][0]
    projection_columns = [col for col in metadata.columns if "Projection Center" in col]
    metadata_projection_centers = []
    for col in projection_columns:
        value = metadata[col][0]
        if not pd.isna(value):
            metadata_projection_centers.append(value)
    if metadata_projection_centers:
        projection_centers = metadata_projection_centers
    if "N Projection Layers" in metadata.columns and metadata["N Projection Layers"][0] > 1:
        options["projection_layers"] = metadata["N Projection Layers"][0]
    if "Spectral Unmixing Amplifyer" in metadata.columns:
        options["spectral_unmixing_amplifyer"] = metadata["Spectral Unmixing Amplifyer"][0]
    if options.get("spectral_unmixing_amplifyer") == 0:
        options["spectral_unmixing_amplifyer"] = 1
    return options, projection_centers


def _base_processing_options(processing_options: dict[str, Any] | None, log: Any) -> dict[str, Any]:
    """Return MotilA processing options with conservative defaults."""

    options = {
        "MG_channel": 0,
        "N_channel": 1,
        "two_channel": True,
        "projection_center": 50,
        "projection_layers": 20,
        "histogram_ref_stack": 0,
        "log": log,
        "blob_pixel_threshold": 100,
        "regStack2d": True,
        "regStack3d": False,
        "template_mode": "mean",
        "usepystackreg": False,
        "spectral_unmixing": True,
        "hist_equalization": False,
        "hist_match": True,
        "hist_equalization_kernel_size": None,
        "hist_equalization_clip_limit": 0.05,
        "group": "blinded",
        "max_xy_shift_correction": 50,
        "threshold_method": "li",
        "compare_all_threshold_methods": True,
        "gaussian_sigma_proj": 1,
        "spectral_unmixing_amplifyer": 1,
        "median_filter_slices": "square",
        "median_filter_window_slices": 3,
        "median_filter_projections": "square",
        "median_filter_window_projections": 3,
        "clear_previous_results": False,
        "spectral_unmixing_median_filter_window": 3,
        "debug_output": False,
        "stats_plots": False,
        "table_export_formats": DEFAULT_TABLE_EXPORT_FORMATS}
    options.update(dict(processing_options or {}))
    options["log"] = options.get("log") or log
    return options


def _preflight_load_image(
    record: BatchImageRecord,
    *,
    reader: Callable[..., Any],
    reader_kwargs: dict[str, Any]
) -> None:
    """Optionally load one image before processing to classify load failures."""

    loaded = reader(record.image_path, **reader_kwargs)
    if loaded is None:
        raise ValueError("Image reader returned None.")
    if isinstance(loaded, tuple) and any(item is None for item in loaded[:2]):
        raise ValueError("Image reader returned an empty image/metadata tuple.")


def batch_process_stacks(
    project_root: str | Path | None = None,
    *,
    subject_ids: Iterable[str | Path] | None = None,
    subject_prefix: str = "ID",
    tag_folder_levels: Sequence[Iterable[str | Path] | str | Path | None] | None = None,
    image_patterns: str | Sequence[str] | None = None,
    exclude_name_contains: Sequence[str] = ("Preview",),
    skip_processed: bool = True,
    skip_registered: bool | None = None,
    results_folder_name: str = "motility_analysis",
    organize_by_image: bool = True,
    expected_output_names: Sequence[str] = ("motility_analysis.xlsx",),
    metadata_file: str | None = "metadata.xls",
    load_options: dict[str, Any] | None = None,
    processing_options: dict[str, Any] | None = None,
    save_options: dict[str, Any] | None = None,
    process_function: Callable[..., Any] | None = None,
    raw_template_metadata: dict[str, Any] | None = None,
    write_error_reports: bool = True,
    write_run_report: bool = True,
    run_report_name: str = "motila_batch_run_report",
    continue_on_error: bool = True,
    log: Any | None = None,
    verbose: bool = True,
    PROJECT_Path: str | Path | None = None
) -> BatchProcessingResult:
    """
    Process a flexible BIDS-like MotilA project tree.

    This is the v1.2.0 batch processor. It discovers supported microscopy
    image files below subject folders, applies MotilA's existing
    :func:`process_stack` workflow to each discovered image/projection-center
    pair, skips already processed outputs when requested, and writes persistent
    run/error reports in ``project_root``.

    ``batch_process_stacks_old`` keeps the pre-v1.2.0 batch implementation for
    migration workflows.
    """

    if project_root is None:
        project_root = PROJECT_Path
    if project_root is None:
        raise TypeError("batch_process_stacks requires 'project_root'.")
    if skip_registered is not None:
        skip_processed = skip_registered

    root = Path(project_root)
    run_timestamp = _timestamp()
    batch_log = log or _BatchConsoleLogger(verbose=verbose)
    process_function = process_function or process_stack
    base_raw_template_metadata = dict(raw_template_metadata or DEFAULT_RAW_TEMPLATE_METADATA)
    base_load_options = dict(load_options or {})
    base_save_options = dict(save_options or {})
    preflight_load = bool(base_load_options.pop("preflight", False))
    image_reader = base_load_options.pop("reader", read_image_stack)
    validate_outputs = bool(base_save_options.pop("validate_outputs", True))
    method_name = str(base_save_options.pop("method_name", "MotilA process_stack"))

    records = discover_bids_like_batch_images(
        root,
        subject_ids=subject_ids,
        subject_prefix=subject_prefix,
        tag_folder_levels=tag_folder_levels,
        image_patterns=image_patterns,
        exclude_name_contains=exclude_name_contains)

    processed: list[BatchProcessedRecord] = []
    skipped: list[BatchSkippedRecord] = []
    failed: list[BatchErrorRecord] = []
    file_error_report_paths: set[Path] = set()
    run_report_events: list[dict[str, Any]] = []

    if verbose:
        print(f"MotilA batch discovered {len(records)} image file(s).")

    base_options = _base_processing_options(processing_options, batch_log)
    for record in records:
        record_options, projection_centers = _metadata_options_for_record(
            record,
            metadata_file=metadata_file,
            base_processing_options=base_options)
        for projection_center in projection_centers:
            output_dir = _output_dir_for_record(
                record,
                results_folder_name=results_folder_name,
                projection_center=projection_center,
                organize_by_image=organize_by_image)
            output_dir.mkdir(parents=True, exist_ok=True)

            if skip_processed and _expected_outputs_exist(output_dir, expected_output_names):
                reason = f"MotilA output already exists: {output_dir}"
                skipped_record = BatchSkippedRecord(
                    input_path=record.image_path,
                    reason=reason,
                    subject_id=record.subject_id,
                    tag_folders=record.tag_folders,
                    stage="already_processed",
                    output_dir=output_dir,
                    projection_center=projection_center)
                skipped.append(skipped_record)
                run_report_events.append(
                    {
                        "record": record,
                        "status": "already_processed",
                        "output_dir": output_dir,
                        "projection_center": projection_center,
                        "reason": reason})
                if verbose:
                    print(f"Skipping already processed file: {record.image_path}")
                continue

            if verbose:
                print(f"Processing: {record.image_path}")

            stage_context = "process"
            try:
                if preflight_load:
                    stage_context = "load"
                    _preflight_load_image(
                        record,
                        reader=image_reader,
                        reader_kwargs=base_load_options)
                stage_context = "process"
                call_options = dict(record_options)
                call_options.update(
                    {
                        "fname": record.image_path,
                        "projection_center": projection_center,
                        "RESULTS_Path": output_dir,
                        "ID": record.subject_id})
                process_function(**call_options)
                stage_context = "save"
                if validate_outputs and not _expected_outputs_exist(output_dir, expected_output_names):
                    raise FileNotFoundError(
                        "MotilA processing finished but no expected output file "
                        f"was found in {output_dir}. Expected one of: {expected_output_names}.")
            except Exception as exc:
                stage = stage_context
                if not continue_on_error:
                    raise
                error_record = BatchErrorRecord(
                    timestamp=run_timestamp,
                    input_path=record.image_path,
                    relative_path=_relative_report_path(record.image_path, root),
                    stage=stage,
                    exception_type=type(exc).__name__,
                    message=str(exc),
                    subject_id=record.subject_id,
                    tag_folders=record.tag_folders,
                    output_dir=output_dir,
                    projection_center=projection_center)
                failed.append(error_record)
                if write_error_reports:
                    file_error_report_paths.add(
                        _write_file_error_report(
                            error_record,
                            raw_template_metadata=base_raw_template_metadata))
                run_report_events.append(
                    {
                        "record": record,
                        "status": "failed",
                        "output_dir": output_dir,
                        "projection_center": projection_center,
                        "stage": stage,
                        "exception_type": type(exc).__name__,
                        "message": str(exc)})
                if verbose:
                    print(f"  failed [{stage}]: {type(exc).__name__}: {exc}")
                continue

            processed_record = BatchProcessedRecord(
                input_path=record.image_path,
                output_dir=output_dir,
                subject_id=record.subject_id,
                tag_folders=record.tag_folders,
                projection_center=projection_center)
            processed.append(processed_record)
            run_report_events.append(
                {
                    "record": record,
                    "status": "processed",
                    "output_dir": output_dir,
                    "projection_center": projection_center,
                    "method_name": method_name,
                    "microglia_channel": call_options.get("MG_channel")})
            if verbose:
                print(f"  processed: {output_dir}")

    error_report_path = (
        _write_root_error_report(
            root,
            timestamp=run_timestamp,
            failed_records=failed,
            raw_template_metadata=base_raw_template_metadata)
        if write_error_reports
        else None)

    run_report_yaml_path = None
    run_report_txt_path = None
    if write_run_report:
        run_report_yaml_path, run_report_txt_path = _run_report_paths(root, run_report_name)
        payload = _load_run_report(run_report_yaml_path, root)
        payload["project_root"] = str(root)
        payload["last_updated"] = run_timestamp
        for event in run_report_events:
            _append_run_report_entry(
                payload,
                event["record"],
                project_root=root,
                timestamp=run_timestamp,
                status=event["status"],
                output_dir=event.get("output_dir"),
                projection_center=event.get("projection_center"),
                method_name=event.get("method_name", method_name),
                microglia_channel=event.get("microglia_channel"),
                stage=event.get("stage"),
                exception_type=event.get("exception_type"),
                message=event.get("message"),
                reason=event.get("reason"))
        _write_run_report_yaml(run_report_yaml_path, payload)
        _render_run_report_text(payload, run_report_txt_path)

    if verbose:
        print(
            f"MotilA batch finished: {len(processed)} processed, "
            f"{len(skipped)} skipped, {len(failed)} failed.")
        if skipped:
            print("Skipped files:")
            for record in skipped:
                print(str(record.input_path))
        if failed:
            print("Failed files:")
            for record in failed:
                print(str(record.input_path))
            if error_report_path is not None:
                print(f"MotilA batch error report written to: {error_report_path}")

    return BatchProcessingResult(
        processed=tuple(processed),
        skipped=tuple(skipped),
        failed=tuple(failed),
        discovered=tuple(records),
        report_path=run_report_txt_path,
        run_report_yaml_path=run_report_yaml_path,
        error_report_path=error_report_path,
        file_error_report_paths=tuple(sorted(file_error_report_paths)))


def batch_create_thorlabs_raw_yaml_templates(
    project_root: str | Path,
    *,
    report_name: str | Path | None = None,
    raw_template_metadata: dict[str, Any] | None = None,
    overwrite_existing: bool = False,
    verbose: bool = True
) -> BatchRawYamlTemplateResult:
    """
    Create OMIO Thorlabs RAW YAML templates from a MotilA batch error report.

    Users can edit the ``template_metadata`` blocks in a root-level
    ``motila_batch_error_report_*.txt`` file and then call this helper to
    distribute those metadata values into per-RAW YAML sidecars.
    """

    root = Path(project_root)
    if report_name is None:
        report_path = _find_latest_batch_error_report(root)
        if report_path is None:
            raise FileNotFoundError(f"No motila_batch_error_report_*.txt found in {root!s}.")
    else:
        report_path = Path(report_name)
        if not report_path.is_absolute():
            report_path = root / report_path
    if not report_path.exists():
        raise FileNotFoundError(f"MotilA batch error report not found: {report_path}")

    fallback_metadata = dict(raw_template_metadata or DEFAULT_RAW_TEMPLATE_METADATA)
    entries = _load_raw_entries_from_report(
        report_path,
        raw_template_metadata=fallback_metadata)

    om = _import_omio()
    records: list[BatchRawYamlTemplateRecord] = []
    for entry in entries:
        raw_path = Path(entry["path"])
        template_metadata = dict(entry.get("template_metadata", fallback_metadata))
        yaml_paths = _expected_raw_yaml_paths(raw_path)
        existing_yaml_paths = [path for path in yaml_paths if path.exists()]

        if not raw_path.exists():
            reason = "RAW file does not exist."
            records.append(
                BatchRawYamlTemplateRecord(
                    raw_path=raw_path,
                    yaml_path=None,
                    template_metadata=template_metadata,
                    status="missing",
                    reason=reason))
            if verbose:
                print(f"Skipping missing RAW file: {raw_path}")
            continue

        if existing_yaml_paths and not overwrite_existing:
            reason = "YAML/YML sidecar already exists."
            records.append(
                BatchRawYamlTemplateRecord(
                    raw_path=raw_path,
                    yaml_path=existing_yaml_paths[0],
                    template_metadata=template_metadata,
                    status="exists",
                    reason=reason))
            if verbose:
                existing_names = ", ".join(str(path) for path in existing_yaml_paths)
                print(f"Skipping existing YAML for {raw_path}: {existing_names}")
            continue

        if verbose:
            print(f"Creating OMIO YAML template for: {raw_path}")
        om.create_thorlabs_raw_yaml(raw_path, **template_metadata)
        created_yaml = next((path for path in yaml_paths if path.exists()), yaml_paths[0])
        records.append(
            BatchRawYamlTemplateRecord(
                raw_path=raw_path,
                yaml_path=created_yaml,
                template_metadata=template_metadata,
                status="created",
                reason=""))

    if verbose:
        created_count = sum(record.status == "created" for record in records)
        skipped_count = len(records) - created_count
        print(f"MotilA RAW YAML template creation finished: {created_count} created, {skipped_count} skipped.")

    return BatchRawYamlTemplateResult(report_path=report_path, records=tuple(records))
# %% BATCH COLLECTION HELPERS
def _find_projection_result_dirs(
    record: BatchImageRecord,
    *,
    results_folder_name: str,
    organize_by_image: bool
) -> list[Path]:
    """Return projection-center result folders for one discovered image."""

    output_root = record.output_scope_dir / results_folder_name
    if organize_by_image:
        output_root = output_root / _sanitize_name(_image_stem(record.image_path))
    if not output_root.exists():
        return []
    return sorted(path for path in output_root.glob("projection_center*") if path.is_dir())


def _drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop pandas Excel index columns from imported MotilA result tables."""

    return df.loc[:, [col for col in df.columns if not str(col).startswith("Unnamed:")]]


def _annotate_collected_dataframe(
    df: pd.DataFrame,
    record: BatchImageRecord,
    projection_dir: Path,
    project_root: Path
) -> pd.DataFrame:
    """Add batch context columns to one collected result DataFrame."""

    df = _drop_unnamed_columns(df).copy()
    df["ID"] = record.subject_id
    df["project tag"] = record.tag_folders[0] if record.tag_folders else ""
    df["tag folders"] = "/".join(record.tag_folders)
    df["projection center"] = projection_dir.name
    df["source image"] = _relative_report_path(record.image_path, project_root)
    front_cols = ["ID", "project tag", "tag folders", "projection center", "source image"]
    remaining_cols = [col for col in df.columns if col not in front_cols]
    return df[front_cols + remaining_cols]


def _append_average_motility_rows(motility_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate average motility rows for each collected grouping."""

    motility_avrg_df = pd.DataFrame()
    group_columns = ["ID", "project tag", "tag folders", "projection center", "source image"]
    existing_group_columns = [col for col in group_columns if col in motility_df.columns]
    value_columns = [
        "Stable",
        "Gain",
        "Loss",
        "rel Stable",
        "rel Gain",
        "rel Loss",
        "tor"]
    existing_value_columns = [col for col in value_columns if col in motility_df.columns]
    if not existing_value_columns:
        return motility_avrg_df

    for group_values, current_df in motility_df.groupby(existing_group_columns, dropna=False):
        if not isinstance(group_values, tuple):
            group_values = (group_values,)
        current_avrg = pd.DataFrame(index=[0])
        for column, value in zip(existing_group_columns, group_values):
            current_avrg[column] = value
        for column in existing_value_columns:
            current_avrg[f"avrg {column}"] = current_df[column].mean()
            current_avrg[f"{column} std"] = current_df[column].std()
        motility_avrg_df = pd.concat([motility_avrg_df, current_avrg], ignore_index=True)
    return motility_avrg_df


def batch_collect(
    project_root: str | Path | None = None,
    *,
    subject_ids: Iterable[str | Path] | None = None,
    subject_prefix: str = "ID",
    tag_folder_levels: Sequence[Iterable[str | Path] | str | Path | None] | None = None,
    image_patterns: str | Sequence[str] | None = None,
    exclude_name_contains: Sequence[str] = ("Preview",),
    results_folder_name: str = "motility_analysis",
    organize_by_image: bool = True,
    RESULTS_Path: str | Path = "batch_results",
    table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS,
    log: Any | None = None,
    verbose: bool = True,
    PROJECT_Path: str | Path | None = None
) -> BatchCollectionResult:
    """
    Collect MotilA outputs using the same BIDS-like discovery as batch processing.

    The v1.2.0 collector mirrors :func:`batch_process_stacks`: it discovers the
    same input files, derives the expected MotilA result folders and aggregates
    ``motility_analysis.xlsx``, ``Normalized average brightness of each
    stack.xlsx`` and ``pixel area sums.xlsx`` when present.

    ``batch_collect_old`` keeps the pre-v1.2.0 collection implementation for
    migration workflows.
    """

    if project_root is None:
        project_root = PROJECT_Path
    if project_root is None:
        raise TypeError("batch_collect requires 'project_root'.")

    root = Path(project_root)
    results_path = Path(RESULTS_Path)
    results_path.mkdir(parents=True, exist_ok=True)
    collection_log = log or _BatchConsoleLogger(verbose=verbose)

    records = discover_bids_like_batch_images(
        root,
        subject_ids=subject_ids,
        subject_prefix=subject_prefix,
        tag_folder_levels=tag_folder_levels,
        image_patterns=image_patterns,
        exclude_name_contains=exclude_name_contains)

    motility_data: list[pd.DataFrame] = []
    brightness_data: list[pd.DataFrame] = []
    pixel_area_data: list[pd.DataFrame] = []
    collected: list[BatchCollectionRecord] = []
    skipped: list[BatchSkippedRecord] = []

    collection_log.log(f"Collecting MotilA batch data from {root}...")
    if verbose:
        print(f"MotilA collection discovered {len(records)} source image file(s).")

    for record in records:
        projection_dirs = _find_projection_result_dirs(
            record,
            results_folder_name=results_folder_name,
            organize_by_image=organize_by_image)
        if not projection_dirs:
            skipped.append(
                BatchSkippedRecord(
                    input_path=record.image_path,
                    reason="No MotilA projection result folders found.",
                    subject_id=record.subject_id,
                    tag_folders=record.tag_folders,
                    stage="missing_results"))
            continue

        for projection_dir in projection_dirs:
            motility_file = projection_dir / "motility_analysis.xlsx"
            brightness_file = projection_dir / "Normalized average brightness of each stack.xlsx"
            pixel_area_file = projection_dir / "pixel area sums.xlsx"
            any_file_collected = False

            if motility_file.exists():
                motility_data.append(
                    _annotate_collected_dataframe(
                        pd.read_excel(motility_file),
                        record,
                        projection_dir,
                        root))
                any_file_collected = True
            if brightness_file.exists():
                brightness_data.append(
                    _annotate_collected_dataframe(
                        pd.read_excel(brightness_file),
                        record,
                        projection_dir,
                        root))
                any_file_collected = True
            if pixel_area_file.exists():
                pixel_area_data.append(
                    _annotate_collected_dataframe(
                        pd.read_excel(pixel_area_file),
                        record,
                        projection_dir,
                        root))
                any_file_collected = True

            if any_file_collected:
                collected.append(
                    BatchCollectionRecord(
                        input_path=record.image_path,
                        output_dir=projection_dir,
                        subject_id=record.subject_id,
                        tag_folders=record.tag_folders,
                        projection_center=projection_dir.name))
            else:
                skipped.append(
                    BatchSkippedRecord(
                        input_path=record.image_path,
                        reason=f"No expected MotilA result tables found in {projection_dir}.",
                        subject_id=record.subject_id,
                        tag_folders=record.tag_folders,
                        stage="missing_tables",
                        output_dir=projection_dir,
                        projection_center=projection_dir.name))

    if motility_data:
        motility_df = pd.concat(motility_data, ignore_index=True)
        export_dataframe(
            motility_df,
            results_path / "all_motility.xlsx",
            table_export_formats=table_export_formats,
            index=False)
        motility_avrg_df = _append_average_motility_rows(motility_df)
        export_dataframe(
            motility_avrg_df,
            results_path / "average_motility.xlsx",
            table_export_formats=table_export_formats,
            index=False)

    if brightness_data:
        brightness_df = pd.concat(brightness_data, ignore_index=True)
        export_dataframe(
            brightness_df,
            results_path / "all_brightness.xlsx",
            table_export_formats=table_export_formats,
            index=False)

    if pixel_area_data:
        pixel_area_df = pd.concat(pixel_area_data, ignore_index=True)
        export_dataframe(
            pixel_area_df,
            results_path / "all_pixel_areas.xlsx",
            table_export_formats=table_export_formats,
            index=False)

    collection_log.log(f"Collected data saved in {results_path}")
    if verbose:
        print(
            f"MotilA collection finished: {len(collected)} collected, "
            f"{len(skipped)} skipped.")

    return BatchCollectionResult(
        collected=tuple(collected),
        skipped=tuple(skipped),
        discovered=tuple(records),
        results_path=results_path)
# %% BATCH PROCESSING

def batch_process_stacks_old(PROJECT_Path, ID_list=[], project_tag="TP000", reg_tif_file_folder="registered",
                  reg_tif_file_tag="reg", metadata_file="metadata.xls",
                  RESULTS_foldername="../motility_analysis/", group="blinded",
                  MG_channel=0, N_channel=1, two_channel=True, projection_center=50, projection_layers=20,
                  histogram_ref_stack=0, log="", blob_pixel_threshold=100, 
                  regStack2d=True, regStack3d=False, template_mode="mean",
                  usepystackreg=False,
                  spectral_unmixing=True, hist_equalization=False, hist_match=True, 
                  hist_equalization_kernel_size=None, hist_equalization_clip_limit=0.05,
                  max_xy_shift_correction=50,
                  threshold_method="li", compare_all_threshold_methods=True,
                  gaussian_sigma_proj=1, spectral_unmixing_amplifyer=1,
                  median_filter_slices = "square", median_filter_window_slices=3,
                  median_filter_projections = "square", median_filter_window_projections=3, 
                  clear_previous_results=False, spectral_unmixing_median_filter_window=3,
                  debug_output=False, stats_plots=False,
                  table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    DEPRECATED since version v1.2.0.

    Use :func:`batch_process_stacks` for new MotilA batch processing. This
    function keeps the pre-v1.2.0 folder assumptions and is provided only for
    migration and reproducibility of existing internal workflows.

    Batch-processing wrapper that applies the MotilA pipeline to multiple 4D/5D
    multiphoton imaging stacks.

    This function detects all project folders matching a given tag, loads the
    associated registered stacks, and processes each dataset using
    :func:`process_stack`. The function handles metadata loading, optional
    registration, spectral unmixing, contrast adjustments, thresholding, and
    motility extraction. Results for each dataset are written into structured
    output directories.

    Parameters
    -----------
    PROJECT_Path : str or Path
        The base directory containing the image stacks.
    ID_list : list of str, optional
        List of sample or subject IDs to be processed (default is an empty list).
    project_tag : str, optional
        Tag used to identify project folders (default is "TP000").
    reg_tif_file_folder : str, optional
        Folder name containing registered image files (default is "registered").
    reg_tif_file_tag : str, optional
        Tag used to filter for registered image files (default is "reg").
    metadata_file : str, optional
        Name of the metadata file to retrieve processing parameters (default is "metadata.xls").
    RESULTS_Path : str or Path, optional
        Directory where results will be saved (default is "motility_analysis").
    group : str, optional
        Sample group label (default is "blinded").
    MG_channel : int, optional
        Channel index for microglial signal (default is 0).
    N_channel : int, optional
        Channel index for neuronal signal (default is 1).
    two_channel : bool, optional
        Indicates whether the data contains two channels (default is True).
    projection_center : int, optional
        Center plane for z-projections (default is 50).
    projection_layers : int, optional
        Number of layers used for projection (default is 20).
    histogram_ref_stack : int, optional
        Reference stack index for histogram matching (default is 0).
    log : object, optional
        Logging object for process tracking (default is an empty string).
    blob_pixel_threshold : int, optional
        Minimum size of segmented objects to retain (default is 100 pixels).
    regStack2d : bool, optional
        Whether to perform 2D registration (default is True).
    regStack3d : bool, optional
        Whether to perform 3D registration (default is False).
    template_mode : str, optional
        Mode used to generate a reference template for registration (default is "mean").
    spectral_unmixing : bool, optional
        Whether to perform spectral unmixing to separate signals (default is True).
    hist_equalization : bool, optional
        Whether to apply histogram equalization to enhance contrast (default is False).
    hist_equalization_clip_limit : float
        Clip limit for histogram equalization.
    hist_equalization_kernel_size : None or tuple of int
        Kernel size for histogram equalization.
    hist_match : bool, optional
        Whether to match histograms across image stacks (default is True).
    max_xy_shift_correction : int, optional
        Maximum allowed shift in pixels for image registration (default is 50).
    threshold_method : str, optional
        Method for binarization thresholding (default is "li").
    compare_all_threshold_methods : bool, optional
        Whether to compare multiple thresholding methods (default is True).
    gaussian_sigma_proj : int, optional
        Sigma value for Gaussian blur applied before binarization (default is 1).
    spectral_unmixing_amplifyer : int, optional
        Amplification factor for spectral unmixing (default is 1).
    median_filter_slices : str, optional
        Type of median filtering applied to individual slices ("square" or "circular") (default is "square").
    median_filter_window_slices : int, optional
        Window size for median filtering on slices (default is 3).
    median_filter_projections : str, optional
        Type of median filtering applied to projections ("square" or "circular") (default is "square").
    median_filter_window_projections : int, optional
        Window size for median filtering on projections (default is 3).
    clear_previous_results : bool, optional
        Whether to delete previous results before processing (default is False).
    spectral_unmixing_median_filter_window : int, optional
        Window size for median filtering applied before spectral unmixing (default is 3).
    debug_output : bool, optional
        Whether to print debug information, including RAM usage (default is False).
    stats_plots : bool, optional
        Whether to generate additional statistics plots (default is False).
    table_export_formats : str or iterable of str, optional
        Table export formats passed to :func:`process_stack`. Defaults to
        ``("excel",)``. Add ``"csv"`` and/or ``"yaml"`` for sidecar plain-text
        exports next to the default Excel files.

    Returns
    --------
    None
        The function processes each stack and saves the results in the specified output directory.

    Notes
    ------
    * The function scans for project folders and extracts relevant image files.
    * Metadata files, if present, override certain function parameters.
    * Each stack is processed using :func:`process_stack`.
    * Results are saved in subdirectories within `RESULTS_Path`, organized by projection center.
    """
    Total_batch_Process_t0 = time.time()
    log.log(f"Batch processing of stacks...")
    log.log("============================================================\n")
    if debug_output: print_ram_usage()
    
    for Current_ID in ID_list:
        # Current_ID = ID_list[0]
        Current_ID_Folder = os.path.join(PROJECT_Path + Current_ID + "/")
        _, TP_folderlist, _= filterfolder_by_string(Current_ID_Folder, project_tag)
        log.log(f"Mouse {Current_ID}\n")
        log.log(f" {project_tag}-tagged folders found: {TP_folderlist}" )

        for iTP in range(len(TP_folderlist)):
            """
            iTP=0
            """

            # Check for reg_tif_file_folder folders in each project_tag folder:
            Current_TP_Folder = os.path.join(Current_ID_Folder + TP_folderlist[iTP] + '/')
            _, reg_file_folder, _ = filterfolder_by_string(Current_TP_Folder, reg_tif_file_folder)
            # check for ambiguity (only one reg_tif_file_folder should be present):
            if len(reg_file_folder)>1:
                log.log(f"  WARNING: multiple '{reg_tif_file_folder}' folders found in {TP_folderlist[iTP]} -> skipping this folder.")
                continue
            elif len(reg_file_folder)==0:
                log.log(f"  WARNING: no '{reg_tif_file_folder}' folder found in {TP_folderlist[iTP]} -> skipping this folder.")
                continue
            else:
                log.log(f"  '{reg_tif_file_folder}' folder found in {TP_folderlist[iTP]}.")
                
            # check whether one or more supported image files including the reg_tif_file_tag are present:
            reg_tif_file = []
            for extension in SUPPORTED_IMAGE_EXTENSIONS:
                reg_tif_file.extend(
                    glob.glob(Current_TP_Folder + reg_file_folder[0] + "/*" + reg_tif_file_tag + "*" + extension)
                )
            if len(reg_tif_file)==0:
                supported = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
                log.log(f"  WARNING: no supported image file ({supported}) with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder -> skipping this folder.")
                continue
            elif len(reg_tif_file)>1:
                log.log(f"  AMBIGUITY WARNING: found more than 1 supported image file with tag '{reg_tif_file_tag}' in '{reg_tif_file_folder}' folder -> skipping this folder.")
                for i in range(len(reg_tif_file)):
                    log.log(f"    {reg_tif_file[i]}")
                continue
            else:
                log.log(f"  {len(reg_tif_file)} image file with tag '{reg_tif_file_tag}' found in '{reg_tif_file_folder}' folder in {TP_folderlist[iTP]} in {Current_ID}.")
                reg_tif_file = Path(reg_tif_file[0])
                
            
            # search for metadata file in the current TP_folder and extract the parameters from it (if any):
            _, metadata_files, _ = filterfiles_by_string(Current_TP_Folder, metadata_file)
            # remove dot-files from metadata_file list:
            metadata_files = [file for file in metadata_files if not file.startswith(".")]
            projection_centers_use = []
            if metadata_files:
                metadata = pd.read_excel(Current_TP_Folder + metadata_files[0])
                # overwrites processing variables from function input with metadata values:
                two_channel = metadata["Two Channel"][0]
                N_channel   = metadata["Neuron Channel"][0]
                MG_channel  = metadata["Microglia Channel"][0]
                spectral_unmixing = metadata["Spectral Unmixing"][0]
                
                # check, whether there is a column that contains the phrase "Projection Center":
                projection_centers_check = [col for col in metadata.columns if "Projection Center" in col]
                if projection_centers_check != []:
                    # run over all "projection center" columns and append the according numbers to the list projection_centers_use:
                    for col in projection_centers_check:
                        # check, whether the current column contains a number:
                        if not np.isnan(metadata[col][0]):
                            projection_centers_use.append(metadata[col][0])
                else:
                    projection_centers_use = [projection_center]
                if "N Projection Layers" in metadata.columns:
                    if metadata["N Projection Layers"][0]>1:
                        projection_layers = metadata["N Projection Layers"][0]
                    else:
                        projection_layers = projection_layers
                else:
                    projection_layers = projection_layers
                if "Spectral Unmixing Amplifyer" in metadata.columns:
                    spectral_unmixing_amplifyer = metadata["Spectral Unmixing Amplifyer"][0]
                else:
                    spectral_unmixing_amplifyer = spectral_unmixing_amplifyer
            else:
                projection_centers_use=[projection_center]

            # correct spectral_unmixing_amplifyer, if it is zero:
            if spectral_unmixing_amplifyer==0:
                spectral_unmixing_amplifyer=1

            # main batch loop iterating the image file in the reg_file_folder over found projection centers:
            for curr_projection_center in projection_centers_use:
                # curr_projection_center = projection_centers_use[0]
                log.log(f"  processing projection center: {curr_projection_center}")
                RESULTS_Path = reg_tif_file.parent.joinpath(f"{RESULTS_foldername}")
                output_foldername = Path(RESULTS_Path).joinpath(f"projection_center_{curr_projection_center}")
                # check, whether the output folder already exists:
                if not os.path.exists(output_foldername):
                    os.makedirs(output_foldername)
                process_stack(fname=reg_tif_file, 
                              MG_channel=MG_channel, 
                              N_channel=N_channel, 
                              two_channel=two_channel,
                              projection_center=curr_projection_center, 
                              projection_layers=projection_layers,
                              histogram_ref_stack=histogram_ref_stack, 
                              log=log, 
                              blob_pixel_threshold=blob_pixel_threshold,
                              spectral_unmixing=spectral_unmixing, hist_equalization=hist_equalization,
                              hist_match=hist_match, 
                              hist_equalization_kernel_size=hist_equalization_kernel_size,
                              hist_equalization_clip_limit=hist_equalization_clip_limit,
                              RESULTS_Path=output_foldername, 
                              ID=Current_ID, 
                              group=group,
                              max_xy_shift_correction=max_xy_shift_correction, 
                              threshold_method=threshold_method,
                              compare_all_threshold_methods=compare_all_threshold_methods, 
                              gaussian_sigma_proj=gaussian_sigma_proj,
                              spectral_unmixing_amplifyer=spectral_unmixing_amplifyer,
                              spectral_unmixing_median_filter_window=spectral_unmixing_median_filter_window,
                              median_filter_slices=median_filter_slices, 
                              median_filter_window_slices=median_filter_window_slices,
                              median_filter_projections=median_filter_projections, 
                              median_filter_window_projections=median_filter_window_projections,
                              clear_previous_results=clear_previous_results, 
                              regStack2d=regStack2d, 
                              regStack3d=regStack3d,
                              template_mode=template_mode,
                              usepystackreg=usepystackreg,
                              debug_output=debug_output,
                              stats_plots=stats_plots,
                              table_export_formats=table_export_formats)
        log.log("\n============================================================\n")
            
    _ = log.logt(Total_batch_Process_t0, verbose=True, spaces=0, unit="sec", process="total batch ")
    if debug_output: print_ram_usage()

# %% BATCH COLLECTION

def batch_collect_old(PROJECT_Path, ID_list=[], project_tag="TP000", motility_folder="motility_analysis",
                      RESULTS_Path="batch_results", log="",
                      table_export_formats=DEFAULT_TABLE_EXPORT_FORMATS):
    """
    DEPRECATED since version v1.2.0.

    Use :func:`batch_collect` for new MotilA batch collection. This function
    keeps the pre-v1.2.0 folder assumptions and is provided only for migration
    and reproducibility of existing internal workflows.

    Collect motility outputs from multiple processed stacks and consolidate them
    into combined tables.

    This function scans all project subfolders, loads the output files generated
    by the MotilA pipeline (motility metrics, brightness tables, and pixel area
    summaries), merges them across stacks or animals, and saves the resulting
    DataFrames into a summary directory.

    Parameters
    -----------
    PROJECT_Path : str or Path
        The base directory containing the image stacks.
    ID_list : list of str, optional
        List of sample or subject IDs to be processed (default is an empty list).
    project_tag : str, optional
        Tag used to identify project folders (default is "TP000").
    motility_folder : str, optional
        Folder name containing motility analysis results (default is "motility_analysis").
    RESULTS_Path : str or Path, optional
        Directory where the consolidated results will be saved (default is "batch_results").
    table_export_formats : str or iterable of str, optional
        Table export formats. Defaults to ``("excel",)`` for backward
        compatibility. Add ``"csv"`` and/or ``"yaml"`` to write sidecar
        plain-text exports next to the default Excel files.

    Returns
    --------
    None
        Saves consolidated DataFrames as Excel files and optional CSV/YAML
        sidecar files in the `RESULTS_Path` directory.

    Notes
    ------
    Expected folder structure::

        ID/
            project_tag*/motility_analysis/projection_center*/

    Extracted files include:

    * ``motility_analysis.xlsx``
    * ``Normalized average brightness of each stack.xlsx``
    * ``pixel area sums.xlsx``
    
    The function saves three consolidated DataFrames in `RESULTS_Path`.   
    
    Motility metrics are averaged across projection centers and across time
    points before export.
    
    Additional excel files are saved as:
    
    * ``all_motility.xlsx``
    * ``all_brightness.xlsx``
    * ``all_pixel_area.xlsx``
    * ``average_motility.xlsx``.
    """

    log.log(f"Collecting motility data from processed stacks...")
    
    PROJECT_Path = Path(PROJECT_Path)
    ID_list = ID_list if ID_list else [f.name for f in PROJECT_Path.iterdir() if f.is_dir()]
    RESULTS_Path = Path(RESULTS_Path)
    RESULTS_Path.mkdir(parents=True, exist_ok=True)

    motility_data = []
    brightness_data = []
    pixel_area_data = []

    for Current_ID in ID_list:
        # Current_ID = ID_list[0]
        Current_ID_Folder = PROJECT_Path / Current_ID
        TP_folderlist = sorted(glob.glob(str(Current_ID_Folder / f"{project_tag}*")))

        for TP_folder in TP_folderlist:
            # TP_folder = TP_folderlist[0]
            
            log.log(f"Processing ID {Current_ID}, project {Path(TP_folder).name}...")
            
            motility_folder_path = Path(TP_folder) / motility_folder
            if not motility_folder_path.exists():
                log.log(f"Warning: No motility folder found in {TP_folder}")
                continue

            projection_folders = sorted(glob.glob(str(motility_folder_path / "projection_center*")))

            for proj_folder in projection_folders:
                # proj_folder = projection_folders[0]
                log.log(f"  Processing projection center {Path(proj_folder).name}...")
                proj_folder = Path(proj_folder)
                motility_file = proj_folder / "motility_analysis.xlsx"
                brightness_file = proj_folder / "Normalized average brightness of each stack.xlsx"
                pixel_area_file = proj_folder / "pixel area sums.xlsx"

                # read motility analysis data:
                if motility_file.exists():
                    df_motility = pd.read_excel(motility_file)
                    df_motility["ID"] = Current_ID
                    df_motility["project tag"] = Path(TP_folder).name
                    df_motility["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_motility.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_motility = df_motility[cols]
                    df_motility.drop(columns="Unnamed: 0", inplace=True)
                    motility_data.append(df_motility)

                # read brightness data:
                if brightness_file.exists():
                    df_brightness = pd.read_excel(brightness_file)
                    df_brightness["ID"] = Current_ID
                    df_brightness["project tag"] = Path(TP_folder).name
                    df_brightness["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_brightness.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_brightness = df_brightness[cols]
                    df_brightness.drop(columns="Unnamed: 0", inplace=True)
                    brightness_data.append(df_brightness)

                # read pixel area data:
                if pixel_area_file.exists():
                    df_pixel_area = pd.read_excel(pixel_area_file)
                    df_pixel_area["ID"] = Current_ID
                    df_pixel_area["project tag"] = Path(TP_folder).name
                    df_pixel_area["projection center"] = proj_folder.name
                    # move ["ID"], ["project tag"] and ["projection center"] columns to the front,
                    # in that order, and drop the columns called "Unnamed: 0":
                    cols = df_pixel_area.columns.tolist()
                    # find indices of ["ID"], ["project tag"] and ["projection center"] in col:
                    idx_ID = cols.index("ID")
                    idx_project_tag = cols.index("project tag")
                    idx_projection_center = cols.index("projection center")
                    # move them to the front:
                    cols = cols[idx_ID:idx_ID+1] + cols[idx_project_tag:idx_project_tag+1] + cols[idx_projection_center:idx_projection_center+1] + cols[:idx_ID] + cols[idx_ID+1:-2]
                    df_pixel_area = df_pixel_area[cols]
                    df_pixel_area.drop(columns="Unnamed: 0", inplace=True)
                    pixel_area_data.append(df_pixel_area)

    # merge and save collected data:
    if motility_data:
        motility_df = pd.concat(motility_data, ignore_index=True)
        export_dataframe(
            motility_df,
            RESULTS_Path / "all_motility.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )

    if brightness_data:
        brightness_df = pd.concat(brightness_data, ignore_index=True)
        export_dataframe(
            brightness_df,
            RESULTS_Path / "all_brightness.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )

    if pixel_area_data:
        pixel_area_df = pd.concat(pixel_area_data, ignore_index=True)
        export_dataframe(
            pixel_area_df,
            RESULTS_Path / "all_pixel_areas.xlsx",
            table_export_formats=table_export_formats,
            index=False,
        )
        
    # average Stable, Gain, Loss, rel Stable, rel Gain, rel Loss, and tor over delta_t 
    # for each projection center, project tag, and ID:
    motility_avrg_df = pd.DataFrame()
    for proj_center in motility_df["projection center"].unique():
        # proj_center = motility_df["projection center"].unique()[0]
        
        for proj_tag in motility_df["project tag"].unique():
            for ID in motility_df["ID"].unique():
                # ID = motility_df["ID"].unique()[1]
                current_df = motility_df[(motility_df["projection center"]==proj_center) &
                                         (motility_df["project tag"]==proj_tag) &
                                         (motility_df["ID"]==ID)]
                # check whether current_df is not empty:
                if current_df.empty:
                    continue

                current_avrg = pd.DataFrame(index=[0])
                current_avrg["ID"] = ID
                current_avrg["project tag"] = proj_tag
                current_avrg["projection center"] = proj_center
                # append the mean:
                current_avrg["avrg Stable"] = current_df["Stable"].mean()
                current_avrg["avrg Gain"] = current_df["Gain"].mean()
                current_avrg["avrg Loss"] = current_df["Loss"].mean()
                current_avrg["avrg rel Stable"] = current_df["rel Stable"].mean()
                current_avrg["avrg rel Gain"] = current_df["rel Gain"].mean()
                current_avrg["avrg rel Loss"] = current_df["rel Loss"].mean()
                current_avrg["avrg tor"] = current_df["tor"].mean()
                
                # append the std:
                current_avrg["Stable std"] = current_df["Stable"].std()
                current_avrg["Gain std"] = current_df["Gain"].std()
                current_avrg["Loss std"] = current_df["Loss"].std()
                current_avrg["rel Stable std"] = current_df["rel Stable"].std()
                current_avrg["rel Gain std"] = current_df["rel Gain"].std()
                current_avrg["rel Loss std"] = current_df["rel Loss"].std()
                current_avrg["tor std"] = current_df["tor"].std()
                
                # update the DataFrame:
                motility_avrg_df = pd.concat([motility_avrg_df, current_avrg], ignore_index=True)
                
    export_dataframe(
        motility_avrg_df,
        RESULTS_Path / "average_motility.xlsx",
        table_export_formats=table_export_formats,
    )

    log.log(f"Collected data saved in {RESULTS_Path}")

# %% END
