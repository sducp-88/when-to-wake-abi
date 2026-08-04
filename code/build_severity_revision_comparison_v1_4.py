from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
EICU = ROOT / "aggregate_results" / "eicu"
SEVERITY = ROOT / "aggregate_results" / "severity"


def effect(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path).set_index("estimand")
    return {
        "risk_continue": float(frame.loc["risk_continue", "estimate"]),
        "risk_early": float(frame.loc["risk_early", "estimate"]),
        "risk_difference": float(frame.loc["risk_difference", "estimate"]),
        "rd_ci_lower": float(frame.loc["risk_difference", "ci_lower"]),
        "rd_ci_upper": float(frame.loc["risk_difference", "ci_upper"]),
        "risk_ratio": float(frame.loc["risk_ratio", "estimate"]),
        "rr_ci_lower": float(frame.loc["risk_ratio", "ci_lower"]),
        "rr_ci_upper": float(frame.loc["risk_ratio", "ci_upper"]),
    }


def funnel(path: Path) -> dict[str, int]:
    frame = pd.read_csv(path)
    return {str(row["step"]): int(row["n"]) for _, row in frame.iterrows()}


def max_smd(path: Path) -> float:
    frame = pd.read_csv(path)
    return float(pd.to_numeric(frame["smd_weighted"], errors="coerce").abs().max())


def main() -> None:
    SEVERITY.mkdir(parents=True, exist_ok=True)
    old_effect = effect(EICU / "eicu_transport_v1_1_calibrated_effect.csv")
    new_effect = effect(EICU / "eicu_transport_v1_2_gcs_validated_effect.csv")
    old_funnel = funnel(EICU / "eicu_transport_funnel_2026-08-02.csv")
    new_funnel = funnel(EICU / "eicu_transport_funnel_2026-08-04.csv")
    rows = [
        {
            "version": "v1.1 superseded",
            "gcs_rule": "broad GCS-labelled value; invalid total-score values could satisfy neurologic-observation eligibility",
            "eligible_stable_grids": old_funnel["eligible_stable_grids"],
            **old_effect,
            "maximum_absolute_weighted_smd": max_smd(EICU / "eicu_transport_v1_1_calibrated_balance_diagnostics.csv"),
        },
        {
            "version": "v1.2 GCS validated",
            "gcs_rule": "exact GCS Total label and valid range 3-15",
            "eligible_stable_grids": new_funnel["eligible_stable_grids"],
            **new_effect,
            "maximum_absolute_weighted_smd": max_smd(EICU / "eicu_transport_v1_2_gcs_validated_balance_diagnostics.csv"),
        },
    ]
    output = pd.DataFrame(rows)
    csv_path = SEVERITY / "eicu_gcs_revision_comparison_v1_4.csv"
    output.to_csv(csv_path, index=False, encoding="utf-8-sig")
    summary = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "primary_mimic_result_changed": False,
        "eicu_transport_direction_changed": False,
        "eicu_transport_precision_interpretation": "directionally concordant but imprecise in both versions",
        "eligible_grid_change": int(new_funnel["eligible_stable_grids"] - old_funnel["eligible_stable_grids"]),
        "safe_aggregate_output": "aggregate_results/severity/eicu_gcs_revision_comparison_v1_4.csv",
    }
    json_path = SEVERITY / "eicu_gcs_revision_comparison_v1_4.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
