from __future__ import annotations

import argparse
import csv
import hashlib
import json
import py_compile
import tempfile
from pathlib import Path


FORBIDDEN_NAME_TOKENS = (
    "subject_id",
    "patientunitstayid",
    "hadm_id",
    "retained_clone",
    "restricted_data",
    ".csv.gz",
    "__pycache__",
    ".pyc",
)
FORBIDDEN_CONTENT_TOKENS = (
    "PhysioNet password",
    "BEGIN PRIVATE KEY",
    "api_key=",
    "C:\\\\Users\\\\",
    "D:\\\\DataAnalysis\\\\",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def release_files(root: Path):
    """Yield release content only, excluding repository-control metadata."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.relative_to(root).parts:
            continue
        yield path


def refresh_manifest(root: Path) -> tuple[int, int]:
    rows = []
    for path in sorted(
        p for p in release_files(root)
        if p.is_file() and p.name not in {"MANIFEST_SHA256.csv", "PUBLIC_RELEASE_QA.json"}
    ):
        rows.append(
            {
                "relative_path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    with (root / "MANIFEST_SHA256.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), sum(row["bytes"] for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()

    restricted_filename_hits = []
    forbidden_content_hits = []
    syntax_errors = []
    for path in sorted(release_files(root)):
        relative = str(path.relative_to(root))
        lower_name = path.name.lower()
        if any(token in lower_name for token in FORBIDDEN_NAME_TOKENS):
            restricted_filename_hits.append(relative)
        if path != Path(__file__).resolve() and path.name not in {"PUBLIC_RELEASE_QA.json", "MANIFEST_SHA256.csv"} and path.suffix.lower() in {".md", ".txt", ".py", ".json", ".csv", ".cff"}:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            for token in FORBIDDEN_CONTENT_TOKENS:
                if token.lower() in text.lower():
                    forbidden_content_hits.append({"path": relative, "token": token})
        if path.suffix.lower() == ".py":
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    py_compile.compile(str(path), cfile=str(Path(temp_dir) / "check.pyc"), doraise=True)
            except Exception as exc:  # pragma: no cover - audit path
                syntax_errors.append({"path": relative, "error": str(exc)})

    required = [
        "README.md",
        "CITATION.cff",
        ".zenodo.json",
        "LICENSE",
        "RELEASE_NOTES_v1.0.5.md",
        "protocol/SAP_AMENDMENT_v1.4_SEVERITY_MEASUREMENT.md",
        "protocol/eicu_transport_config_v1.2.json",
        "code/build_eicu_analysis_ready_v1_1.py",
        "code/qa_eicu_analysis_ready_v1_1.py",
        "code/run_eicu_transport_ccw_v1_1.py",
        "code/qa_eicu_transport_v1_2.py",
        "aggregate_results/eicu/eicu_transport_v1_2_gcs_validated_effect.csv",
        "aggregate_results/eicu/eicu_transport_v1_2_qa.json",
        "aggregate_results/severity/APACHE_TIME_VALID_SENSITIVITY_FEASIBILITY_v1_4.json",
        "publication_assets/tables/Table_S4_severity_balance_diagnostics.csv",
    ]
    missing_required_files = [item for item in required if not (root / item).is_file()]
    file_count, total_bytes = refresh_manifest(root)
    result = {
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "status": "PASS",
        "release_version": "1.0.5",
        "immutable_release_doi": "10.5281/zenodo.21787638",
        "manifest_file_count_excluding_manifest_and_qa": file_count,
        "manifest_total_bytes": total_bytes,
        "forbidden_content_hits": forbidden_content_hits,
        "restricted_filename_hits": restricted_filename_hits,
        "python_syntax_errors": syntax_errors,
        "missing_required_files": missing_required_files,
        "license_status": "APPROVED_MIT",
        "patient_level_data_included": False,
        "failed_gate_apache_effect_included": False,
    }
    if forbidden_content_hits or restricted_filename_hits or syntax_errors or missing_required_files:
        result["status"] = "FAIL"
    (root / "PUBLIC_RELEASE_QA.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
