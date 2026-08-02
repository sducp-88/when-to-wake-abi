from __future__ import annotations

import os
import argparse
import importlib.util
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
VENDOR = Path(os.environ.get("WTW_VENDOR_DIR", PROJECT_ROOT / "04_code" / "vendor")).resolve()
sys.path.insert(0, str(VENDOR))

import numpy as np
import pandas as pd


warnings.filterwarnings("ignore", message="Skipping features without any observed values")


MIMIC_MODEL_PATH = Path(__file__).with_name("run_mimic_ccw_analysis_v1_1.py")
GRID_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0" / "eicu_analysis_grid_transport_v1_0.csv.gz"
INTERVAL_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0" / "eicu_analysis_intervals_transport_v1_0.csv.gz"
RESTRICTED_DERIVED = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0"
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "eicu"


def load_model():
    spec = importlib.util.spec_from_file_location("mimic_ccw", MIMIC_MODEL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen CCW implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def offset_to_time(values: pd.Series, origin: pd.Timestamp) -> pd.Series:
    return origin + pd.to_timedelta(pd.to_numeric(values, errors="coerce"), unit="m")


def harmonize(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    origin = pd.Timestamp("2000-01-01 00:00:00")
    frame.rename(
        columns={
            "patientunitstayid": "stay_id",
            "ventilation_end_offset": "extubation_offset_source",
            "tracheostomy_offset": "tracheostomy_offset_source",
            "death_offset": "death_offset_source",
            "first_qualifying_action_offset": "action_offset_source",
            "alive_vent_end_day7": "alive_success_extub_day7",
            "unittype": "first_careunit",
            "unitstaytype": "admission_type",
        },
        inplace=True,
    )
    frame["grid_time"] = offset_to_time(frame["grid_offset"], origin)
    frame["extubation_time"] = offset_to_time(frame["extubation_offset_source"], origin)
    frame["tracheostomy_time"] = offset_to_time(frame["tracheostomy_offset_source"], origin)
    frame["deathtime"] = offset_to_time(frame["death_offset_source"], origin)
    frame["outtime"] = offset_to_time(frame["unitdischargeoffset"], origin)
    frame["first_qualifying_action_time"] = offset_to_time(frame["action_offset_source"], origin)
    frame["first_successful_sbt_time"] = pd.NaT
    frame["alive_vent_end_day7"] = frame["alive_success_extub_day7"].astype(int)

    # The shared CCW implementation expects the harmonized MIMIC common-data-model
    # names. Missing eICU concepts are explicit structural-missing indicators or
    # fixed absence flags; no value is inferred from an unavailable field.
    frame["comorbidity_count"] = 0
    frame["gcs_motor"] = frame.get("gcs_value")
    frame["gcs_eye"] = np.nan
    frame["gcs_verbal"] = np.nan
    frame["gcs_motor_1"] = frame.get("gcs_value_1")
    frame["gcs_eye_1"] = np.nan
    frame["gcs_verbal_1"] = np.nan
    frame["successful_sbt_prior6h"] = 0
    frame["any_sbt_prior6h"] = 0
    frame["successful_sbt_prior6h_1"] = 0
    frame["any_sbt_prior6h_1"] = 0
    for column in [
        "diabetes",
        "ckd",
        "chf",
        "atrial_fibrillation",
        "malignancy",
        "liver_disease",
    ]:
        frame[column] = 0
    frame["site_id"] = pd.to_numeric(frame["hospitalid"], errors="coerce").astype("Int64").astype("string").fillna("__missing__")
    frame["baseline_drug_pattern"] = (
        "P" + frame["propofol_active"].fillna(0).astype(int).astype(str)
        + "M" + frame["midazolam_active"].fillna(0).astype(int).astype(str)
        + "D" + frame["dexmed_active"].fillna(0).astype(int).astype(str)
    )
    frame["icp_measured"] = frame["icp_latest"].notna().astype(int).astype(str)
    frame["drug_icp_pattern"] = frame["baseline_drug_pattern"] + "_I" + frame["icp_measured"]
    return frame


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    grid_raw = pd.read_csv(GRID_PATH, low_memory=False)
    interval_raw = pd.read_csv(INTERVAL_PATH, low_memory=False)
    if grid_raw.duplicated(["patientunitstayid", "grid_hour"]).any():
        raise RuntimeError("Duplicate eICU grid keys detected")
    counts = interval_raw.groupby(["patientunitstayid", "grid_hour"], observed=True)["interval_index"].nunique()
    if not counts.eq(4).all():
        raise RuntimeError("Every eICU eligible grid must have four adherence intervals")
    return harmonize(grid_raw), harmonize(interval_raw)


def rake_transport_weights(final: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    calibrated = final.copy()
    calibrated["precalibration_weight"] = calibrated["weight"].astype(float)
    margins = ["baseline_drug_count", "icp_calibration_bin", "fio2_calibration_bin"]
    for strategy in (0, 1):
        mask = calibrated["assigned_strategy"].eq(strategy)
        weights = calibrated.loc[mask, "weight"].astype(float).copy()
        initial_sum = float(weights.sum())
        for _ in range(30):
            for variable in margins:
                target_values = target[variable].fillna("__missing__").astype(str)
                target_proportions = target_values.value_counts(normalize=True)
                current_values = calibrated.loc[mask, variable].fillna("__missing__").astype(str)
                current_weighted = (
                    pd.DataFrame({"level": current_values, "weight": weights})
                    .groupby("level", observed=True)["weight"]
                    .sum()
                )
                current_proportions = current_weighted / current_weighted.sum()
                factors = (target_proportions / current_proportions).replace([np.inf, -np.inf], np.nan).fillna(1.0)
                weights *= current_values.map(factors).fillna(1.0).to_numpy()
        if weights.sum() > 0:
            weights *= initial_sum / weights.sum()
        calibrated.loc[mask, "weight"] = weights
    calibrated["transport_calibrated"] = 1
    return calibrated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--label", default="transport_v1_0")
    parser.add_argument("--regularization-c", type=float, default=10.0)
    args = parser.parse_args()

    module = load_model()
    module.NUMERIC_DENOMINATOR = [
        column for column in module.NUMERIC_DENOMINATOR if column not in {"gcs_eye_1", "gcs_verbal_1"}
    ]
    base_make_pipeline = module.make_pipeline

    def make_transport_pipeline(numeric, categorical):
        pipeline = base_make_pipeline(numeric, categorical)
        pipeline.set_params(model__C=args.regularization_c)
        return pipeline

    module.make_pipeline = make_transport_pipeline
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    RESTRICTED_DERIVED.mkdir(parents=True, exist_ok=True)
    grid, intervals = load_data()
    grid["icp_calibration_bin"] = pd.cut(
        pd.to_numeric(grid["icp_latest"], errors="coerce"),
        bins=[-np.inf, 10, 15, 20, np.inf],
        labels=["le10", "10to15", "15to20", "gt20"],
    ).astype("string").fillna("missing")
    intervals["icp_calibration_bin"] = pd.cut(
        pd.to_numeric(intervals["icp_latest"], errors="coerce"),
        bins=[-np.inf, 10, 15, 20, np.inf],
        labels=["le10", "10to15", "15to20", "gt20"],
    ).astype("string").fillna("missing")
    grid["fio2_calibration_bin"] = pd.cut(
        pd.to_numeric(grid["fio2"], errors="coerce"),
        bins=[-np.inf, 0.30, 0.40, 0.50, np.inf],
        labels=["le030", "030to040", "040to050", "gt050"],
    ).astype("string").fillna("missing")
    intervals["fio2_calibration_bin"] = pd.cut(
        pd.to_numeric(intervals["fio2"], errors="coerce"),
        bins=[-np.inf, 0.30, 0.40, 0.50, np.inf],
        labels=["le030", "030to040", "040to050", "gt050"],
    ).astype("string").fillna("missing")
    base_fit_weights = module.fit_weights

    def fit_transport_weights(frame, collect_diagnostics=False):
        final_frame, diagnostics_frame = base_fit_weights(frame, collect_diagnostics=collect_diagnostics)
        stay_key = "analysis_stay_id" if "analysis_stay_id" in frame.columns else "stay_id"
        target = frame.loc[frame["interval_index"].eq(1)].drop_duplicates([stay_key, "grid_hour"])
        return rake_transport_weights(final_frame, target), diagnostics_frame

    module.fit_weights = fit_transport_weights
    final, calibration = module.fit_weights(intervals, collect_diagnostics=True)
    estimate = module.effect_from_final(final)
    weights = module.weight_diagnostics(final)
    balance = module.balance_diagnostics(final)
    bootstrap = module.cluster_bootstrap(intervals, args.bootstrap, args.jobs, seed=20260802)

    effect_rows = []
    for measure in ("risk_continue", "risk_early", "risk_difference", "risk_ratio"):
        lower, upper = module.interval_confidence(bootstrap, measure)
        effect_rows.append(
            {
                "estimand": measure,
                "estimate": estimate[measure],
                "ci_lower": lower,
                "ci_upper": upper,
                "bootstrap_requested": args.bootstrap,
                "bootstrap_converged": int(bootstrap["converged"].sum()) if len(bootstrap) else 0,
            }
        )
    effect = pd.DataFrame(effect_rows)
    prefix = f"eicu_{args.label}"
    effect_path = RESULT_DIR / f"{prefix}_effect.csv"
    weight_path = RESULT_DIR / f"{prefix}_weight_diagnostics.csv"
    balance_path = RESULT_DIR / f"{prefix}_balance_diagnostics.csv"
    calibration_path = RESULT_DIR / f"{prefix}_adherence_model_diagnostics.csv"
    bootstrap_path = RESULT_DIR / f"{prefix}_bootstrap_distribution.csv"
    restricted_path = RESTRICTED_DERIVED / f"RESTRICTED_{prefix}_retained_clone_weights.csv.gz"

    effect.to_csv(effect_path, index=False, encoding="utf-8-sig")
    weights.to_csv(weight_path, index=False, encoding="utf-8-sig")
    balance.to_csv(balance_path, index=False, encoding="utf-8-sig")
    calibration.to_csv(calibration_path, index=False, encoding="utf-8-sig")
    bootstrap.to_csv(bootstrap_path, index=False, encoding="utf-8-sig")
    final.to_csv(restricted_path, index=False, encoding="utf-8-sig", compression="gzip")

    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "database": "eICU-CRD-2.0",
        "analysis_role": "measurement-aware transport",
        "analysis_version": "1.0",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "bootstrap_requested": args.bootstrap,
        "bootstrap_converged": int(bootstrap["converged"].sum()) if len(bootstrap) else 0,
        "grid_rows": int(len(grid)),
        "interval_rows": int(len(intervals)),
        "retained_clone_rows": int(len(final)),
        "retained_clone_stays": int(final["stay_id"].nunique()),
        "outcome": "alive reconstructed ventilation end by day 7 without renewed ventilation within 48 hours",
        "explicit_extubation_claim_permitted": False,
        "point_gaps_interpreted_as_drug_stops": False,
        "logistic_regularization_c": args.regularization_c,
        "post_weight_calibration": "iterative raking to baseline drug-count and ICP-bin margins",
        "patient_level_output": str(restricted_path),
        "safe_effect_output": str(effect_path),
    }
    metadata_path = RESULT_DIR / f"{prefix}_run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(effect.to_string(index=False))
    print(weights.to_string(index=False))
    print(f"MAX_ABS_WEIGHTED_SMD={balance['smd_weighted'].abs().max():.4f}")
    print(f"EFFECT={effect_path}")
    print(f"WEIGHTS={weight_path}")
    print(f"BALANCE={balance_path}")
    print(f"CALIBRATION={calibration_path}")
    print(f"BOOTSTRAP={bootstrap_path}")
    print(f"RESTRICTED_RETAINED_CLONES={restricted_path}")


if __name__ == "__main__":
    main()
