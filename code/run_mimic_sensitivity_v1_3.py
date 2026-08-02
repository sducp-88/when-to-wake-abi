from __future__ import annotations

import os
import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
MODEL_PATH = Path(__file__).with_name("run_mimic_ccw_analysis_v1_1.py")
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "mimic" / "sensitivity"


def load_model():
    spec = importlib.util.spec_from_file_location("mimic_ccw", MODEL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen MIMIC CCW module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recompute_lead(intervals, pd, lead_minutes: int):
    frame = intervals.copy()
    action = pd.to_datetime(frame["first_qualifying_action_time"], errors="coerce")
    sbt = pd.to_datetime(frame["first_successful_sbt_time"], errors="coerce")
    extubation = pd.to_datetime(frame["extubation_time"], errors="coerce")
    valid = (
        frame["early_compat_1"].fillna(0).astype(int).eq(1)
        & action.notna()
        & (sbt.isna() | action.lt(sbt))
        & (extubation.isna() | action.le(extubation - pd.Timedelta(minutes=lead_minutes)))
    )
    frame["early_temporal_valid"] = valid.astype(int)
    return frame


def summarize(module, frame, scenario: str, use_raw_weight: bool = False):
    final, _ = module.fit_weights(frame, collect_diagnostics=False)
    if use_raw_weight:
        final["weight"] = final["raw_weight"]
    effect = module.effect_from_final(final)
    return {
        "scenario": scenario,
        **effect,
        "n_retained_clones": int(len(final)),
        "n_stays": int(final["stay_id"].nunique()),
        "use_raw_weight": bool(use_raw_weight),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=200)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    module = load_model()
    pd = module.pd
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    _, intervals = module.load_data()

    first_grid = intervals.groupby("stay_id", observed=True)["grid_hour"].transform("min")
    scenario_frames = {
        "lead_30_min": recompute_lead(intervals, pd, 30),
        "lead_120_min": recompute_lead(intervals, pd, 120),
        "first_eligible_grid_only": intervals.loc[intervals["grid_hour"].eq(first_grid)].copy(),
        "ventilation_end_proxy": intervals.assign(
            alive_success_extub_day7=intervals["alive_vent_end_day7"].astype(int)
        ),
    }
    for subtype in sorted(intervals["abi_subtype"].dropna().astype(str).unique()):
        scenario_frames[f"subtype_{subtype}"] = intervals.loc[
            intervals["abi_subtype"].astype(str).eq(subtype)
        ].copy()

    rows = [summarize(module, intervals, "primary_reference")]
    rows.append(summarize(module, intervals, "primary_untruncated", use_raw_weight=True))
    bootstrap_manifest = []

    for index, (scenario, frame) in enumerate(scenario_frames.items(), start=1):
        point = summarize(module, frame, scenario)
        bootstrap = module.cluster_bootstrap(
            frame,
            replicates=args.bootstrap,
            jobs=args.jobs,
            seed=20260802 + index * 1000,
        )
        point["bootstrap_requested"] = args.bootstrap
        point["bootstrap_converged"] = int(bootstrap["converged"].sum()) if len(bootstrap) else 0
        for measure in ("risk_continue", "risk_early", "risk_difference", "risk_ratio"):
            lower, upper = module.interval_confidence(bootstrap, measure)
            point[f"{measure}_ci_lower"] = lower
            point[f"{measure}_ci_upper"] = upper
        rows.append(point)
        bootstrap_path = RESULT_DIR / f"mimic_{scenario}_bootstrap_{args.bootstrap}.csv"
        bootstrap.to_csv(bootstrap_path, index=False, encoding="utf-8-sig")
        bootstrap_manifest.append(
            {
                "scenario": scenario,
                "path": str(bootstrap_path),
                "requested": args.bootstrap,
                "converged": int(bootstrap["converged"].sum()) if len(bootstrap) else 0,
            }
        )

    summary = pd.DataFrame(rows)
    summary_path = RESULT_DIR / "mimic_sensitivity_summary_v1_3.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis_version": "1.3",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_reference_ci_source": "mimic_primary_v1_3_effect.csv",
        "sensitivity_bootstrap_replicates": args.bootstrap,
        "bootstrap_unit": "ICU stay",
        "bootstrap_manifest": bootstrap_manifest,
        "safe_aggregate_outputs_only": True,
    }
    metadata_path = RESULT_DIR / "mimic_sensitivity_metadata_v1_3.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"SUMMARY={summary_path}")
    print(f"METADATA={metadata_path}")


if __name__ == "__main__":
    main()
