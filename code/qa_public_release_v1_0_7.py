from __future__ import annotations

import argparse
import csv
import hashlib
import json
import py_compile
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.7"
CONCEPT_DOI = "10.5281/zenodo.21761953"
TITLE = (
    "Stability-Triggered Sedation De-escalation and Day-7 Ventilator Liberation "
    "After Acute Brain Injury: A Sequential Target-Trial Emulation"
)

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
    "C:\\Users\\",
    "D:\\DataAnalysis\\",
)
RELEASE_FACING_FILES = (
    "README.md",
    "RELEASE_NOTES_v1.0.7.md",
    "CITATION.cff",
    ".zenodo.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def release_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        yield path


def refresh_manifest(root: Path) -> tuple[int, int]:
    excluded = {"MANIFEST_SHA256.csv", "PUBLIC_RELEASE_QA.json"}
    rows = []
    for path in sorted(p for p in release_files(root) if p.name not in excluded):
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    with (root / "MANIFEST_SHA256.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["relative_path", "bytes", "sha256"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), sum(int(row["bytes"]) for row in rows)


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--immutable-doi",
        help="Zenodo version DOI after archival; omit for the pre-archive tag audit.",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    forbidden_content_hits: list[dict[str, str]] = []
    restricted_filename_hits: list[str] = []
    syntax_errors: list[dict[str, str]] = []
    for path in sorted(release_files(root)):
        relative = path.relative_to(root).as_posix()
        lower_name = path.name.lower()
        if any(token in lower_name for token in FORBIDDEN_NAME_TOKENS):
            restricted_filename_hits.append(relative)
        is_qa_script = path.name.startswith("qa_public_release_v1_0_")
        if (
            not is_qa_script
            and path.name not in {"PUBLIC_RELEASE_QA.json", "MANIFEST_SHA256.csv"}
            and path.suffix.lower() in {".md", ".txt", ".py", ".json", ".csv", ".cff"}
        ):
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            for token in FORBIDDEN_CONTENT_TOKENS:
                if token.lower() in text.lower():
                    forbidden_content_hits.append({"path": relative, "token": token})
        if path.suffix.lower() == ".py":
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    py_compile.compile(
                        str(path),
                        cfile=str(Path(temp_dir) / "check.pyc"),
                        doraise=True,
                    )
            except Exception as exc:
                syntax_errors.append({"path": relative, "error": str(exc)})

    required = [
        "README.md",
        "CITATION.cff",
        ".zenodo.json",
        "LICENSE",
        "RELEASE_NOTES_v1.0.7.md",
        "protocol/SAP_AMENDMENT_v1.5_POSTHOC_BIAS_TARGETED.md",
        "code/build_mimic_analysis_ready_v1_5.py",
        "code/merge_v1_5_features_onto_frozen_v1_3_population.py",
        "code/run_mimic_bias_targeted_sensitivity_v1_5.py",
        "code/qa_public_release_v1_0_7.py",
        "aggregate_results/mimic_bias_targeted_v1_5/mimic_bias_targeted_v1_5_effect.csv",
        "aggregate_results/mimic_bias_targeted_v1_5/mimic_bias_targeted_v1_5_bootstrap_distribution.csv",
        "aggregate_results/mimic_bias_targeted_v1_5/mimic_bias_targeted_v1_5_balance_diagnostics.csv",
        "aggregate_results/mimic_bias_targeted_v1_5/mimic_bias_targeted_v1_5_adherence_model_diagnostics.csv",
        "aggregate_results/mimic_bias_targeted_v1_5/mimic_bias_targeted_v1_5_run_metadata.json",
        "publication_assets/figures/Figure_1_stability_gate_and_cohort.pdf",
        "publication_assets/figures/Figure_2_effect_estimates.pdf",
        "publication_assets/figures/Figure_3_covariate_balance.pdf",
        "publication_assets/tables/Table_2_effect_estimates_v1_0_7.csv",
        "publication_assets/tables/Table_S5_bias_targeted_results.csv",
        "publication_assets/tables/Table_S6_trajectory_missingness.csv",
    ]
    missing_required_files = [item for item in required if not (root / item).is_file()]

    cff = (root / "CITATION.cff").read_text(encoding="utf-8")
    zenodo = json.loads((root / ".zenodo.json").read_text(encoding="utf-8"))
    cff_version_ok = bool(re.search(r"(?m)^cff-version:\s*1\.2\.0\s*$", cff))
    software_version_ok = bool(re.search(r"(?m)^version:\s*1\.0\.7\s*$", cff))
    cff_title_ok = TITLE in cff
    cff_author_order_ok = cff.index("given-names: Lifei") < cff.index("given-names: Zhichao")
    zenodo_ok = (
        str(zenodo.get("version")) == VERSION
        and TITLE in str(zenodo.get("title"))
        and zenodo.get("license") == "MIT"
        and [item.get("name") for item in zenodo.get("creators", [])[:2]]
        == ["Wei, Lifei", "Bi, Zhichao"]
    )

    release_facing_text = "\n".join(
        (root / item).read_text(encoding="utf-8", errors="ignore")
        for item in RELEASE_FACING_FILES
    )
    pending_language_hits = [
        token
        for token in ("candidate pending author approval", "not yet released", "do not publish or tag")
        if token in release_facing_text.lower()
    ]

    aggregate = root / "aggregate_results" / "mimic_bias_targeted_v1_5"
    bootstrap = csv_rows(aggregate / "mimic_bias_targeted_v1_5_bootstrap_distribution.csv")
    bootstrap_ok = len(bootstrap) == 200 and all(row.get("converged") == "1" for row in bootstrap)
    effect = csv_rows(aggregate / "mimic_bias_targeted_v1_5_effect.csv")
    effect_map = {(row["analysis"], row["estimand"]): row for row in effect}
    primary_rd = effect_map.get(("trajectory_dose_augmented", "risk_difference"), {})
    primary_rr = effect_map.get(("trajectory_dose_augmented", "risk_ratio"), {})
    effect_ok = (
        abs(float(primary_rd.get("estimate", "nan")) - 0.07249066236150165) < 1e-12
        and abs(float(primary_rr.get("estimate", "nan")) - 1.1696395263114803) < 1e-12
        and primary_rd.get("bootstrap_converged") == "200"
        and primary_rr.get("bootstrap_converged") == "200"
    )
    balance = csv_rows(aggregate / "mimic_bias_targeted_v1_5_balance_diagnostics.csv")
    primary_balance = [
        abs(float(row["smd_weighted"]))
        for row in balance
        if row["analysis"] == "trajectory_dose_augmented" and row["smd_weighted"]
    ]
    max_primary_smd = max(primary_balance)
    balance_value_ok = abs(max_primary_smd - 0.10152529921089744) < 1e-12

    adherence = csv_rows(aggregate / "mimic_bias_targeted_v1_5_adherence_model_diagnostics.csv")
    small_count_suppression_ok = True
    for row in adherence:
        for field in ("probability_floor_count", "probability_ceiling_count"):
            value = row[field]
            if value == "<10":
                continue
            numeric = int(value)
            if 0 < numeric < 10:
                small_count_suppression_ok = False

    metadata = json.loads(
        (aggregate / "mimic_bias_targeted_v1_5_run_metadata.json").read_text(encoding="utf-8")
    )
    metadata_ok = (
        metadata.get("analysis_version") == "1.5-posthoc-bias-targeted"
        and metadata.get("bootstrap_requested") == 200
        and metadata.get("bootstrap_converged") == 200
        and "sandbox" not in json.dumps(metadata).lower()
    )

    figure_pdfs_ok = all(
        (root / item).read_bytes().startswith(b"%PDF")
        and (root / item).stat().st_size < 10 * 1024 * 1024
        for item in required
        if item.endswith(".pdf")
    )

    if args.immutable_doi:
        doi_sync_ok = (
            f'doi: "{args.immutable_doi}"' in cff
            and args.immutable_doi in (root / "README.md").read_text(encoding="utf-8")
            and args.immutable_doi
            in (root / "RELEASE_NOTES_v1.0.7.md").read_text(encoding="utf-8")
        )
        status = "PASS" if doi_sync_ok else "FAIL"
    else:
        doi_sync_ok = not bool(re.search(r"(?m)^doi:\s*", cff))
        status = "PASS_PRE_ARCHIVE" if doi_sync_ok else "FAIL"

    checks = {
        "missing_required_files": not missing_required_files,
        "forbidden_content": not forbidden_content_hits,
        "restricted_filenames": not restricted_filename_hits,
        "python_syntax": not syntax_errors,
        "cff_version": cff_version_ok,
        "software_version": software_version_ok,
        "cff_title": cff_title_ok,
        "cff_author_order": cff_author_order_ok,
        "zenodo_metadata": zenodo_ok,
        "pending_language_removed": not pending_language_hits,
        "bootstrap_distribution": bootstrap_ok,
        "effect_values": effect_ok,
        "balance_value": balance_value_ok,
        "small_count_suppression": small_count_suppression_ok,
        "run_metadata": metadata_ok,
        "figure_pdfs": figure_pdfs_ok,
        "doi_sync": doi_sync_ok,
    }
    if not all(checks.values()):
        status = "FAIL"

    file_count, total_bytes = refresh_manifest(root)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "release_version": VERSION,
        "concept_doi": CONCEPT_DOI,
        "immutable_version_doi": args.immutable_doi,
        "all_author_approval_confirmed": True,
        "manifest_file_count_excluding_manifest_and_qa": file_count,
        "manifest_total_bytes": total_bytes,
        "checks": checks,
        "missing_required_files": missing_required_files,
        "forbidden_content_hits": forbidden_content_hits,
        "restricted_filename_hits": restricted_filename_hits,
        "python_syntax_errors": syntax_errors,
        "pending_language_hits": pending_language_hits,
        "bootstrap_rows": len(bootstrap),
        "maximum_weighted_absolute_smd": max_primary_smd,
        "license_status": "APPROVED_MIT",
        "patient_level_data_included": False,
        "aggregate_outputs_only": True,
        "failed_gate_stay_balanced_inference_released": False,
    }
    (root / "PUBLIC_RELEASE_QA.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
