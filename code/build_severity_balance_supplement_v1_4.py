from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
MIMIC_RETAINED = Path(
    os.environ.get(
        "WTW_MIMIC_RETAINED_CLONES",
        PROJECT_ROOT
        / "00_restricted_data"
        / "derived"
        / "mimic_v1_1"
        / "RESTRICTED_mimic_primary_v1_3_retained_clone_weights.csv.gz",
    )
).resolve()
EICU_RETAINED = (
    PROJECT_ROOT
    / "00_restricted_data"
    / "derived"
    / "eicu_transport_v1_1"
    / "RESTRICTED_eicu_transport_v1_2_gcs_validated_retained_clone_weights.csv.gz"
)
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "severity"


VARIABLES = {
    "MIMIC-IV v3.1": [
        ("gcs_motor", "GCS motor", "score"),
        ("gcs_eye", "GCS eye", "score"),
        ("gcs_verbal", "GCS verbal", "score"),
        ("rass", "RASS", "score"),
        ("icp_latest", "Intracranial pressure", "mm Hg"),
        ("map_min_2h", "Minimum MAP in prior 2 h", "mm Hg"),
        ("fio2", "Latest FiO2", "fraction"),
        ("peep", "Latest PEEP", "cm H2O"),
        ("pao2_fio2", "PaO2/FiO2", "ratio"),
        ("lactate", "Lactate", "mmol/L"),
        ("creatinine", "Creatinine", "mg/dL"),
        ("vasopressor_observed", "Vasopressor observed", "proportion"),
        ("opioid_observed", "Opioid observed", "proportion"),
    ],
    "eICU-CRD v2.0": [
        ("apache_iva_score", "APACHE IVa score", "score"),
        ("apache_iva_aps", "APACHE IVa acute physiology score", "score"),
        ("gcs_motor", "GCS Total (valid 3-15)", "score"),
        ("rass", "RASS", "score"),
        ("icp_latest", "Intracranial pressure", "mm Hg"),
        ("map_min_2h", "Minimum MAP in prior 2 h", "mm Hg"),
        ("fio2", "Latest FiO2", "fraction"),
        ("peep", "Latest PEEP", "cm H2O"),
        ("pao2_fio2", "PaO2/FiO2", "ratio"),
        ("lactate", "Lactate", "mmol/L"),
        ("creatinine", "Creatinine", "mg/dL"),
        ("vasopressor_observed", "Vasopressor observed", "proportion"),
        ("opioid_observed", "Opioid observed", "proportion"),
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def summarize_numeric(frame: pd.DataFrame, variable: str) -> dict[str, float]:
    raw = pd.to_numeric(frame[variable], errors="coerce")
    fill = float(raw.median())
    values = raw.fillna(fill)
    groups = []
    for strategy in (0, 1):
        mask = frame["assigned_strategy"].eq(strategy)
        weights = pd.to_numeric(frame.loc[mask, "weight"], errors="coerce").astype(float)
        group_values = values[mask]
        mean = float(np.average(group_values, weights=weights))
        variance = float(np.average(np.square(group_values - mean), weights=weights))
        coverage = float(np.average(raw[mask].notna().astype(float), weights=weights))
        groups.append((mean, variance, coverage))
    denominator = np.sqrt((groups[0][1] + groups[1][1]) / 2)
    smd = float((groups[1][0] - groups[0][0]) / denominator) if denominator > 0 else 0.0
    return {
        "continue_weighted_value": groups[0][0],
        "early_weighted_value": groups[1][0],
        "continue_observed_percent": 100 * groups[0][2],
        "early_observed_percent": 100 * groups[1][2],
        "weighted_smd": smd,
        "median_imputation_value": fill,
    }


def summarize_binary(frame: pd.DataFrame, variable: str) -> dict[str, float]:
    values = pd.to_numeric(frame[variable], errors="coerce").fillna(0).astype(float)
    proportions = []
    coverages = []
    for strategy in (0, 1):
        mask = frame["assigned_strategy"].eq(strategy)
        weights = pd.to_numeric(frame.loc[mask, "weight"], errors="coerce").astype(float)
        proportions.append(float(np.average(values[mask], weights=weights)))
        coverages.append(float(np.average(frame.loc[mask, variable].notna().astype(float), weights=weights)))
    denominator = np.sqrt(
        (proportions[0] * (1 - proportions[0]) + proportions[1] * (1 - proportions[1])) / 2
    )
    smd = float((proportions[1] - proportions[0]) / denominator) if denominator > 0 else 0.0
    return {
        "continue_weighted_value": 100 * proportions[0],
        "early_weighted_value": 100 * proportions[1],
        "continue_observed_percent": 100 * coverages[0],
        "early_observed_percent": 100 * coverages[1],
        "weighted_smd": smd,
        "median_imputation_value": np.nan,
    }


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {"MIMIC-IV v3.1": MIMIC_RETAINED, "eICU-CRD v2.0": EICU_RETAINED}
    rows = []
    source = {}
    for database, path in paths.items():
        frame = pd.read_csv(path, low_memory=False)
        source[database] = {
            "path": "authorized local restricted directory; file not included",
            "sha256": sha256(path),
            "retained_clones": int(len(frame)),
            "unique_stays": int(frame["stay_id"].nunique()),
        }
        for variable, label, unit in VARIABLES[database]:
            if variable not in frame.columns:
                continue
            summary = (
                summarize_binary(frame, variable)
                if unit == "proportion"
                else summarize_numeric(frame, variable)
            )
            rows.append({"database": database, "variable": variable, "label": label, "unit": unit, **summary})
    output = pd.DataFrame(rows)
    csv_path = RESULT_DIR / "severity_balance_diagnostics_v1_4.csv"
    output.to_csv(csv_path, index=False, encoding="utf-8-sig")
    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis_role": "post hoc outcome-blind severity balance diagnostic",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if float(output["weighted_smd"].abs().max()) < 0.10 else "FAIL",
        "maximum_absolute_weighted_smd": float(output["weighted_smd"].abs().max()),
        "patient_level_output": False,
        "source_restricted_files": source,
        "safe_aggregate_output": "aggregate_results/severity/severity_balance_diagnostics_v1_4.csv",
    }
    metadata_path = RESULT_DIR / "severity_balance_diagnostics_v1_4.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(output.to_string(index=False))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
