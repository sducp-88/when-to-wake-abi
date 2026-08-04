from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
EICU = ROOT / "aggregate_results" / "eicu"
SEVERITY = ROOT / "aggregate_results" / "severity"
GRID = ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_1" / "eicu_analysis_grid_transport_v1_1.csv.gz"


def main() -> None:
    effect = pd.read_csv(EICU / "eicu_transport_v1_2_gcs_validated_effect.csv").set_index("estimand")
    weights = pd.read_csv(EICU / "eicu_transport_v1_2_gcs_validated_weight_diagnostics.csv")
    balance = pd.read_csv(EICU / "eicu_transport_v1_2_gcs_validated_balance_diagnostics.csv")
    grid = pd.read_csv(GRID, low_memory=False)
    severity = pd.read_csv(SEVERITY / "severity_balance_diagnostics_v1_4.csv")
    apache_feasibility = json.loads(
        (SEVERITY / "APACHE_TIME_VALID_SENSITIVITY_FEASIBILITY_v1_4.json").read_text(encoding="utf-8")
    )
    gcs = pd.to_numeric(grid["gcs_value"], errors="coerce")
    checks = {
        "four_estimands_present": set(effect.index) == {"risk_continue", "risk_early", "risk_difference", "risk_ratio"},
        "bootstrap_1000_converged": int(effect["bootstrap_converged"].min()) == 1000,
        "weight_p99_below_10": float(weights["raw_weight_p99"].max()) < 10,
        "maximum_weight_below_20": float(weights["truncated_weight_max"].max()) < 20,
        "ess_ratio_at_least_0_50": float(weights["ess_ratio"].min()) >= 0.50,
        "maximum_absolute_weighted_smd_below_0_10": float(balance["smd_weighted"].abs().max()) < 0.10,
        "gcs_total_valid_or_missing": int((gcs.notna() & ~gcs.between(3, 15)).sum()) == 0,
        "severity_diagnostic_below_0_10": float(severity["weighted_smd"].abs().max()) < 0.10,
        "apache_time_valid_failure_not_reported_as_effect": (
            apache_feasibility["status"] == "FAIL_NONINFERENTIAL"
            and apache_feasibility["effect_estimate_released"] is False
        ),
    }
    result = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis": "eICU transport v1.2 GCS validated",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "key_diagnostics": {
            "eligible_stable_grids": int(len(grid)),
            "maximum_absolute_weighted_smd": float(balance["smd_weighted"].abs().max()),
            "minimum_ess_ratio": float(weights["ess_ratio"].min()),
            "maximum_weight": float(weights["truncated_weight_max"].max()),
            "severity_diagnostic_maximum_absolute_smd": float(severity["weighted_smd"].abs().max()),
        },
        "patient_level_output": False,
    }
    path = EICU / "eicu_transport_v1_2_qa.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
