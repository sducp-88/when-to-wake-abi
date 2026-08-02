from __future__ import annotations

import os
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
sys.path.insert(0, str(PROJECT_ROOT / "04_code" / "vendor"))

import pandas as pd


GRID_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0" / "eicu_analysis_grid_transport_v1_0.csv.gz"
INTERVAL_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0" / "eicu_analysis_intervals_transport_v1_0.csv.gz"
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "eicu"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(GRID_PATH, low_memory=False)
    intervals = pd.read_csv(INTERVAL_PATH, low_memory=False)
    checks = []

    def check(item: str, observed: int, expected: int) -> None:
        checks.append(
            {
                "section": "integrity_check",
                "item": item,
                "observed": observed,
                "expected": expected,
                "status": "PASS" if observed == expected else "FAIL",
            }
        )

    check("grid_rows", len(grid), 2964)
    check("interval_rows", len(intervals), len(grid) * 4)
    check("duplicate_grid_keys", int(grid.duplicated(["patientunitstayid", "grid_hour"]).sum()), 0)
    check(
        "duplicate_interval_keys",
        int(intervals.duplicated(["patientunitstayid", "grid_hour", "interval_index"]).sum()),
        0,
    )
    interval_counts = intervals.groupby(["patientunitstayid", "grid_hour"], observed=True)["interval_index"].nunique()
    check("grids_without_four_intervals", int(interval_counts.ne(4).sum()), 0)

    violations = {
        "map_median_below_65": pd.to_numeric(grid["map_median_2h"], errors="coerce").lt(65),
        "map_min_below_60": pd.to_numeric(grid["map_min_2h"], errors="coerce").lt(60),
        "fio2_above_0_60": pd.to_numeric(grid["fio2"], errors="coerce").gt(0.60),
        "peep_above_10": pd.to_numeric(grid["peep"], errors="coerce").gt(10),
        "no_neurologic_measure": pd.to_numeric(grid["neuro_measure_count"], errors="coerce").fillna(0).le(0),
        "recent_nmba_observed": pd.to_numeric(grid["nmba_recent2h"], errors="coerce").fillna(0).ne(0),
        "recent_barbiturate_observed": pd.to_numeric(grid["barbiturate_recent6h"], errors="coerce").fillna(0).ne(0),
        "recent_hyperosmolar_observed": pd.to_numeric(grid["hyperosmolar_recent6h"], errors="coerce").fillna(0).ne(0),
    }
    icp_latest = pd.to_numeric(grid["icp_latest"], errors="coerce")
    icp_max = pd.to_numeric(grid["icp_max_2h"], errors="coerce").fillna(icp_latest)
    violations["icp_above_22"] = icp_latest.gt(22) | icp_max.gt(22)
    for item, mask in violations.items():
        check(item, int(mask.fillna(False).sum()), 0)

    check(
        "nonbinary_transport_outcome",
        int((~pd.to_numeric(grid["alive_vent_end_day7"], errors="coerce").isin([0, 1])).sum()),
        0,
    )
    check(
        "valid_early_without_action_offset",
        int(
            (
                grid["early_temporal_valid"].fillna(0).astype(int).eq(1)
                & grid["first_qualifying_action_offset"].isna()
            ).sum()
        ),
        0,
    )
    check(
        "valid_early_ventilation_end_lead_under_60_min",
        int(
            (
                grid["early_temporal_valid"].fillna(0).astype(int).eq(1)
                & grid["ventilation_end_offset"].notna()
                & pd.to_numeric(grid["first_qualifying_action_offset"], errors="coerce").gt(
                    pd.to_numeric(grid["ventilation_end_offset"], errors="coerce") - 60
                )
            ).sum()
        ),
        0,
    )

    for column in [
        "map_median_2h_1",
        "map_min_2h_1",
        "heart_rate_1",
        "temperature_c_1",
        "icp_latest_1",
        "fio2_1",
        "peep_1",
        "rass_1",
        "gcs_value_1",
        "lactate_1",
        "creatinine_1",
        "bilirubin_1",
        "paco2_1",
        "pao2_fio2_1",
    ]:
        checks.append(
            {
                "section": "missingness",
                "item": column,
                "observed": round(float(100 * intervals[column].isna().mean()), 4),
                "expected": "descriptive_only",
                "status": "INFO",
            }
        )

    for path in (GRID_PATH, INTERVAL_PATH):
        checks.append(
            {
                "section": "file_integrity",
                "item": path.name,
                "observed": sha256(path),
                "expected": "recorded",
                "status": "PASS",
            }
        )

    qa = pd.DataFrame(checks)
    qa_path = RESULT_DIR / "eicu_analysis_ready_qa_v1_0.csv"
    qa.to_csv(qa_path, index=False, encoding="utf-8-sig")
    failures = qa[(qa["section"].eq("integrity_check")) & qa["status"].eq("FAIL")]
    summary = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "database": "eICU-CRD-2.0",
        "analysis_role": "measurement-aware transport",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "grid_rows": int(len(grid)),
        "interval_rows": int(len(intervals)),
        "unique_stays": int(grid["patientunitstayid"].nunique()),
        "integrity_failures": int(len(failures)),
        "status": "PASS" if failures.empty else "FAIL",
        "grid_sha256": sha256(GRID_PATH),
        "interval_sha256": sha256(INTERVAL_PATH),
        "patient_level_rows_exported": False,
        "explicit_extubation_claim_permitted": False,
    }
    metadata_path = RESULT_DIR / "eicu_analysis_ready_qa_v1_0.json"
    metadata_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not failures.empty:
        raise RuntimeError(f"eICU analysis-ready QA failed: {len(failures)} checks")


if __name__ == "__main__":
    main()
