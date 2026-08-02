from __future__ import annotations

import os
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
sys.path.insert(0, str(PROJECT_ROOT / "04_code" / "vendor"))

import numpy as np
import pandas as pd


GRID_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1" / "mimic_analysis_grid_v1_1.csv.gz"
INTERVAL_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1" / "mimic_analysis_intervals_v1_1.csv.gz"
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "mimic"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def add_check(rows: list[dict], check: str, observed: object, expected: object, passed: bool) -> None:
    rows.append(
        {
            "section": "integrity_check",
            "item": check,
            "observed": observed,
            "expected": expected,
            "status": "PASS" if passed else "FAIL",
        }
    )


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(GRID_PATH, low_memory=False)
    intervals = pd.read_csv(INTERVAL_PATH, low_memory=False)
    rows: list[dict] = []

    add_check(rows, "grid_rows", len(grid), 9830, len(grid) == 9830)
    add_check(rows, "interval_rows", len(intervals), len(grid) * 4, len(intervals) == len(grid) * 4)
    duplicate_grids = int(grid.duplicated(["stay_id", "grid_hour"]).sum())
    add_check(rows, "duplicate_grid_keys", duplicate_grids, 0, duplicate_grids == 0)
    interval_counts = intervals.groupby(["stay_id", "grid_hour"], observed=True)["interval_index"].nunique()
    bad_interval_counts = int(interval_counts.ne(4).sum())
    add_check(rows, "grids_without_four_intervals", bad_interval_counts, 0, bad_interval_counts == 0)
    duplicate_intervals = int(intervals.duplicated(["stay_id", "grid_hour", "interval_index"]).sum())
    add_check(rows, "duplicate_interval_keys", duplicate_intervals, 0, duplicate_intervals == 0)

    criteria = {
        "map_median_below_65": pd.to_numeric(grid["map_median_2h"], errors="coerce").lt(65),
        "map_min_below_60": pd.to_numeric(grid["map_min_2h"], errors="coerce").lt(60),
        "fio2_above_0_60": pd.to_numeric(grid["fio2"], errors="coerce").gt(0.60),
        "peep_above_10": pd.to_numeric(grid["peep"], errors="coerce").gt(10),
        "no_neurologic_measure": pd.to_numeric(grid["neuro_measure_count"], errors="coerce").fillna(0).le(0),
        "recent_nmba": pd.to_numeric(grid["nmba_recent2h"], errors="coerce").fillna(0).ne(0),
        "recent_barbiturate": pd.to_numeric(grid["barbiturate_recent6h"], errors="coerce").fillna(0).ne(0),
        "recent_hyperosmolar": pd.to_numeric(grid["hyperosmolar_recent6h"], errors="coerce").fillna(0).ne(0),
        "successful_sbt_before_timezero": pd.to_numeric(grid["successful_sbt_prior6h"], errors="coerce").fillna(0).ne(0),
        "tracheostomy_before_timezero": pd.to_numeric(grid["trach_before_timezero"], errors="coerce").fillna(0).ne(0),
    }
    icp_latest = pd.to_numeric(grid["icp_latest"], errors="coerce")
    icp_max = pd.to_numeric(grid["icp_max_2h"], errors="coerce").fillna(icp_latest)
    criteria["icp_above_22"] = icp_latest.gt(22) | icp_max.gt(22)
    for name, violation in criteria.items():
        count = int(violation.fillna(False).sum())
        add_check(rows, name, count, 0, count == 0)

    grid_hour = pd.to_numeric(grid["grid_hour"], errors="coerce")
    invalid_grid_hour = int((grid_hour.lt(12) | grid_hour.gt(96) | grid_hour.mod(6).ne(0)).sum())
    add_check(rows, "invalid_grid_hour", invalid_grid_hour, 0, invalid_grid_hour == 0)
    invalid_outcome = int((~pd.to_numeric(grid["alive_success_extub_day7"], errors="coerce").isin([0, 1])).sum())
    add_check(rows, "nonbinary_primary_outcome", invalid_outcome, 0, invalid_outcome == 0)

    for column in ["grid_time", "first_qualifying_action_time", "first_successful_sbt_time", "extubation_time"]:
        grid[column] = pd.to_datetime(grid[column], errors="coerce")
    early = grid["early_temporal_valid"].fillna(0).astype(int).eq(1)
    missing_early_action = int((early & grid["first_qualifying_action_time"].isna()).sum())
    add_check(rows, "valid_early_without_action_time", missing_early_action, 0, missing_early_action == 0)
    action_after_sbt = int(
        (
            early
            & grid["first_successful_sbt_time"].notna()
            & grid["first_qualifying_action_time"].ge(grid["first_successful_sbt_time"])
        ).sum()
    )
    add_check(rows, "valid_early_not_before_successful_sbt", action_after_sbt, 0, action_after_sbt == 0)
    action_lead_violation = int(
        (
            early
            & grid["extubation_time"].notna()
            & grid["first_qualifying_action_time"].gt(grid["extubation_time"] - pd.Timedelta(minutes=60))
        ).sum()
    )
    add_check(rows, "valid_early_extubation_lead_under_60_min", action_lead_violation, 0, action_lead_violation == 0)

    analysis_columns = [
        "age",
        "grid_hour",
        "comorbidity_count",
        "map_median_2h_1",
        "map_min_2h_1",
        "heart_rate_1",
        "fio2_1",
        "peep_1",
        "rass_1",
        "gcs_motor_1",
        "gcs_eye_1",
        "gcs_verbal_1",
        "icp_latest_1",
        "temperature_c_1",
        "lactate_1",
        "creatinine_1",
        "bilirubin_1",
        "paco2_1",
        "pao2_fio2_1",
    ]
    for column in analysis_columns:
        missing_pct = float(100 * intervals[column].isna().mean())
        rows.append(
            {
                "section": "missingness",
                "item": column,
                "observed": round(missing_pct, 4),
                "expected": "descriptive_only",
                "status": "INFO",
            }
        )

    rows.extend(
        [
            {
                "section": "file_integrity",
                "item": "mimic_analysis_grid_v1_1.csv.gz",
                "observed": sha256(GRID_PATH),
                "expected": "recorded",
                "status": "PASS",
            },
            {
                "section": "file_integrity",
                "item": "mimic_analysis_intervals_v1_1.csv.gz",
                "observed": sha256(INTERVAL_PATH),
                "expected": "recorded",
                "status": "PASS",
            },
        ]
    )

    qa = pd.DataFrame(rows)
    csv_path = RESULT_DIR / "mimic_analysis_ready_qa_v1_1.csv"
    qa.to_csv(csv_path, index=False, encoding="utf-8-sig")
    failures = qa[(qa["section"].eq("integrity_check")) & (qa["status"].eq("FAIL"))]
    summary = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "grid_rows": int(len(grid)),
        "interval_rows": int(len(intervals)),
        "unique_stays": int(grid["stay_id"].nunique()),
        "integrity_failures": int(len(failures)),
        "status": "PASS" if failures.empty else "FAIL",
        "grid_sha256": sha256(GRID_PATH),
        "interval_sha256": sha256(INTERVAL_PATH),
        "patient_level_rows_exported": False,
    }
    json_path = RESULT_DIR / "mimic_analysis_ready_qa_v1_1.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not failures.empty:
        raise RuntimeError(f"Analysis-ready QA failed: {len(failures)} checks")


if __name__ == "__main__":
    main()
