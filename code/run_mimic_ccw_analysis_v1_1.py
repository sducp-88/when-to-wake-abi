from __future__ import annotations

import os
import argparse
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
from joblib import Parallel, delayed
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore", category=RuntimeWarning)

GRID_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1" / "mimic_analysis_grid_v1_1.csv.gz"
INTERVAL_PATH = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1" / "mimic_analysis_intervals_v1_1.csv.gz"
RESTRICTED_DERIVED = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1"
RESULT_DIR = PROJECT_ROOT / "05_results" / "formal_analysis" / "mimic"


NUMERIC_DENOMINATOR = [
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
    "neuro_measure_count_1",
]

CATEGORICAL_DENOMINATOR = [
    "abi_subtype",
    "gender",
    "admission_type",
    "first_careunit",
    "baseline_drug_count",
    "propofol_active",
    "midazolam_active",
    "dexmed_active",
    "diabetes",
    "ckd",
    "chf",
    "atrial_fibrillation",
    "malignancy",
    "liver_disease",
    "vasopressor_observed_1",
    "opioid_observed_1",
    "ketamine_observed_1",
    "any_sbt_prior6h_1",
]

BALANCE_NUMERIC = [
    "age",
    "grid_hour",
    "comorbidity_count",
    "map_median_2h",
    "map_min_2h",
    "heart_rate",
    "fio2",
    "peep",
    "rass",
    "gcs_motor",
    "icp_latest",
    "temperature_c",
    "lactate",
    "creatinine",
    "paco2",
    "pao2_fio2",
]

BALANCE_CATEGORICAL = [
    "abi_subtype",
    "gender",
    "baseline_drug_count",
    "propofol_active",
    "midazolam_active",
    "dexmed_active",
    "vasopressor_observed",
    "opioid_observed",
    "diabetes",
    "ckd",
    "chf",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    grid = pd.read_csv(GRID_PATH, low_memory=False)
    intervals = pd.read_csv(INTERVAL_PATH, low_memory=False)
    if grid.duplicated(["stay_id", "grid_hour"]).any():
        raise RuntimeError("Duplicate grid keys detected")
    counts = intervals.groupby(["stay_id", "grid_hour"], observed=True)["interval_index"].nunique()
    if not (counts == 4).all():
        raise RuntimeError("Every eligible grid must have four adherence intervals")
    return grid, intervals


def make_pipeline(numeric: list[str], categorical: list[str]) -> Pipeline:
    numeric_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=5)),
        ]
    )
    transformer = ColumnTransformer(
        [
            ("num", numeric_transformer, numeric),
            ("cat", categorical_transformer, categorical),
        ],
        remainder="drop",
    )
    model = LogisticRegression(C=10.0, max_iter=1500, solver="lbfgs")
    return Pipeline([("transform", transformer), ("model", model)])


def calibration(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    if len(np.unique(y)) < 2:
        return float("nan"), float("nan")
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1 - 1e-6)).reshape(-1, 1)
    try:
        model = LogisticRegression(C=1e6, max_iter=1000, solver="lbfgs").fit(logit, y)
        return float(model.intercept_[0]), float(model.coef_[0, 0])
    except Exception:
        return float("nan"), float("nan")


def construct_clones(intervals: pd.DataFrame) -> pd.DataFrame:
    frame0 = intervals.copy()
    datetime_columns = [
        "grid_time",
        "extubation_time",
        "tracheostomy_time",
        "deathtime",
        "outtime",
        "first_qualifying_action_time",
    ]
    for column in datetime_columns:
        frame0[column] = pd.to_datetime(frame0[column], errors="coerce")
    terminal_columns = ["extubation_time", "tracheostomy_time", "deathtime", "outtime"]
    frame0["strategy_terminal_time"] = frame0[terminal_columns].min(axis=1)
    frame0["terminal_hours"] = (
        (frame0["strategy_terminal_time"] - frame0["grid_time"]).dt.total_seconds() / 3600.0
    )
    frame0.loc[frame0["terminal_hours"].lt(0), "terminal_hours"] = 0.0
    frame0["interval_start_hour"] = (frame0["interval_index"] - 1) * 6
    frame0["interval_end_hour"] = frame0["interval_index"] * 6
    frame0["terminal_in_interval"] = (
        frame0["terminal_hours"].notna()
        & frame0["terminal_hours"].gt(frame0["interval_start_hour"])
        & frame0["terminal_hours"].le(frame0["interval_end_hour"])
    )
    frame0["early_action_before_terminal"] = (
        frame0["interval_index"].eq(1)
        & frame0["early_temporal_valid"].fillna(0).astype(int).eq(1)
        & frame0["first_qualifying_action_time"].notna()
        & (
            frame0["strategy_terminal_time"].isna()
            | frame0["first_qualifying_action_time"].lt(frame0["strategy_terminal_time"])
        )
    )

    frames = []
    for strategy in (0, 1):
        frame = frame0.copy()
        frame["assigned_strategy"] = strategy
        if strategy == 1:
            regular_adherent = np.where(
                frame["interval_index"].eq(1),
                frame["early_temporal_valid"].fillna(0).astype(int),
                frame["early_snapshot_compatible"].fillna(0).astype(int),
            )
        else:
            regular_adherent = frame["continue_snapshot_compatible"].fillna(0).astype(int).to_numpy()

        frame["adherent"] = regular_adherent
        # Terminal events end the intervention strategy. A clone is not required to
        # demonstrate adherence at a later six-hour boundary after extubation,
        # death, tracheostomy, or ICU discharge. During the initial grace period,
        # both clones remain compatible until a temporally valid early action occurs.
        terminal_before_boundary = frame["terminal_in_interval"]
        frame["assessment_required"] = (~terminal_before_boundary).astype(int)
        first_interval_action = terminal_before_boundary & frame["early_action_before_terminal"]
        frame.loc[terminal_before_boundary & ~first_interval_action, "adherent"] = 1
        frame.loc[first_interval_action, "assessment_required"] = 1
        if strategy == 1:
            frame.loc[first_interval_action, "adherent"] = 1
        else:
            frame.loc[first_interval_action, "adherent"] = 0
        frames.append(frame)
    clones = pd.concat(frames, ignore_index=True)
    stay_key = "analysis_stay_id" if "analysis_stay_id" in clones.columns else "stay_id"
    group_keys = [stay_key, "grid_hour", "assigned_strategy"]
    clones.sort_values(group_keys + ["interval_index"], inplace=True)
    clones["prior_adherent"] = (
        clones.groupby(group_keys, observed=True)["adherent"]
        .cumprod()
        .groupby([clones[key] for key in group_keys], observed=True)
        .shift(fill_value=1)
        .astype(int)
    )
    clones["at_risk_for_adherence"] = (
        clones["prior_adherent"].eq(1)
        & (clones["terminal_hours"].isna() | clones["terminal_hours"].gt(clones["interval_start_hour"]))
    ).astype(int)
    return clones


def constant_probability(y: pd.Series) -> np.ndarray:
    value = float(np.clip(y.mean(), 1e-4, 1 - 1e-4))
    return np.full(len(y), value)


def fit_weights(intervals: pd.DataFrame, collect_diagnostics: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    clones = construct_clones(intervals)
    stay_key = "analysis_stay_id" if "analysis_stay_id" in clones.columns else "stay_id"
    group_keys = [stay_key, "grid_hour", "assigned_strategy"]
    clones["increment"] = 1.0
    diagnostics: list[dict] = []

    for interval_index in (1, 2, 3, 4):
        for strategy in (0, 1):
            mask = (
                clones["interval_index"].eq(interval_index)
                & clones["assigned_strategy"].eq(strategy)
                & clones["at_risk_for_adherence"].eq(1)
                & clones["assessment_required"].eq(1)
            )
            work = clones.loc[mask].copy()
            y = work["adherent"].astype(int)
            if y.nunique() < 2:
                p_den = constant_probability(y)
            else:
                denominator = make_pipeline(NUMERIC_DENOMINATOR, CATEGORICAL_DENOMINATOR)
                denominator.fit(work, y)
                p_den = denominator.predict_proba(work)[:, 1]
            # Stabilization is marginal within each strategy and six-hour interval.
            p_num = constant_probability(y)
            p_den = np.clip(p_den, 0.005, 0.995)
            p_num = np.clip(p_num, 0.005, 0.995)
            clones.loc[mask, "increment"] = p_num / p_den
            if collect_diagnostics:
                intercept, slope = calibration(y.to_numpy(), p_den)
                diagnostics.append(
                    {
                        "interval_index": interval_index,
                        "strategy": "early_deescalation" if strategy == 1 else "continue_24h",
                        "model": "denominator_adherence",
                        "n_at_risk_clones": int(len(work)),
                        "observed_adherence": float(y.mean()),
                        "mean_predicted": float(p_den.mean()),
                        "brier_score": float(brier_score_loss(y, p_den)),
                        "auc": float(roc_auc_score(y, p_den)) if y.nunique() > 1 else np.nan,
                        "calibration_intercept": intercept,
                        "calibration_slope": slope,
                        "probability_floor_count": int((p_den <= 0.0050001).sum()),
                        "probability_ceiling_count": int((p_den >= 0.9949999).sum()),
                    }
                )

    clones["cumulative_sw"] = (
        clones["increment"]
        .groupby([clones[key] for key in group_keys], observed=True)
        .cumprod()
    )
    terminal_within_strategy = clones["terminal_hours"].notna() & clones["terminal_hours"].le(24)
    clones["retention_interval"] = np.where(
        terminal_within_strategy,
        np.ceil(clones["terminal_hours"].clip(lower=1e-9) / 6.0).clip(1, 4),
        4,
    ).astype(int)
    retained_mask = (
        clones["interval_index"].eq(clones["retention_interval"])
        & clones["prior_adherent"].eq(1)
        & (clones["assessment_required"].eq(0) | clones["adherent"].eq(1))
    )
    final = clones.loc[retained_mask].copy()
    final.rename(columns={"cumulative_sw": "raw_weight"}, inplace=True)
    final["weight"] = final["raw_weight"]
    for strategy in (0, 1):
        smask = final["assigned_strategy"].eq(strategy)
        if smask.sum() == 0:
            continue
        lower, upper = final.loc[smask, "raw_weight"].quantile([0.01, 0.99])
        final.loc[smask, "weight"] = final.loc[smask, "raw_weight"].clip(lower, upper)
        final.loc[smask, "truncated"] = (
            (final.loc[smask, "raw_weight"] < lower) | (final.loc[smask, "raw_weight"] > upper)
        ).astype(int)
    return final, pd.DataFrame(diagnostics)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & np.isfinite(weights)
    if mask.sum() == 0 or weights[mask].sum() <= 0:
        return float("nan")
    return float(np.average(values[mask].astype(float), weights=weights[mask].astype(float)))


def effect_from_final(final: pd.DataFrame) -> dict[str, float]:
    risks = {}
    for strategy in (0, 1):
        group = final[final["assigned_strategy"].eq(strategy)]
        risks[strategy] = weighted_mean(group["alive_success_extub_day7"], group["weight"])
    rd = risks[1] - risks[0]
    rr = risks[1] / risks[0] if risks[0] > 0 else np.nan
    return {"risk_continue": risks[0], "risk_early": risks[1], "risk_difference": rd, "risk_ratio": rr}


def weight_diagnostics(final: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy, label in ((0, "continue_24h"), (1, "early_deescalation")):
        group = final[final["assigned_strategy"].eq(strategy)]
        w = group["weight"].astype(float)
        raw = group["raw_weight"].astype(float)
        rows.append(
            {
                "strategy": label,
                "n_retained_clones": int(len(group)),
                "n_decision_points": int(group[["stay_id", "grid_hour"]].drop_duplicates().shape[0]),
                "n_stays": int(group["stay_id"].nunique()),
                "raw_weight_mean": float(raw.mean()),
                "raw_weight_p01": float(raw.quantile(0.01)),
                "raw_weight_p50": float(raw.quantile(0.50)),
                "raw_weight_p95": float(raw.quantile(0.95)),
                "raw_weight_p99": float(raw.quantile(0.99)),
                "raw_weight_max": float(raw.max()),
                "truncated_weight_max": float(w.max()),
                "truncated_percent": float(100 * group["truncated"].fillna(0).mean()),
                "ess": float(w.sum() ** 2 / np.square(w).sum()),
                "ess_ratio": float((w.sum() ** 2 / np.square(w).sum()) / len(group)),
            }
        )
    return pd.DataFrame(rows)


def smd_numeric(frame: pd.DataFrame, variable: str, weight_col: str | None) -> float:
    groups = []
    for strategy in (0, 1):
        sub = frame[frame["assigned_strategy"].eq(strategy)][[variable] + ([weight_col] if weight_col else [])].copy()
        values = pd.to_numeric(sub[variable], errors="coerce")
        fill = frame[variable].median() if pd.api.types.is_numeric_dtype(frame[variable]) else values.median()
        values = values.fillna(fill)
        weights = sub[weight_col].astype(float) if weight_col else pd.Series(np.ones(len(sub)), index=sub.index)
        mean = np.average(values, weights=weights)
        variance = np.average(np.square(values - mean), weights=weights)
        groups.append((mean, variance))
    denom = np.sqrt((groups[0][1] + groups[1][1]) / 2)
    return float((groups[1][0] - groups[0][0]) / denom) if denom > 0 else 0.0


def smd_binary(frame: pd.DataFrame, series: pd.Series, weight_col: str | None) -> float:
    ps = []
    for strategy in (0, 1):
        mask = frame["assigned_strategy"].eq(strategy)
        values = series[mask].astype(float)
        weights = frame.loc[mask, weight_col].astype(float) if weight_col else np.ones(mask.sum())
        ps.append(float(np.average(values, weights=weights)))
    denom = np.sqrt((ps[0] * (1 - ps[0]) + ps[1] * (1 - ps[1])) / 2)
    return float((ps[1] - ps[0]) / denom) if denom > 0 else 0.0


def balance_diagnostics(final: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in BALANCE_NUMERIC:
        if variable not in final:
            continue
        rows.append(
            {
                "variable": variable,
                "level": "continuous",
                "smd_unweighted": smd_numeric(final, variable, None),
                "smd_weighted": smd_numeric(final, variable, "weight"),
            }
        )
    for variable in BALANCE_CATEGORICAL:
        if variable not in final:
            continue
        for level in sorted(final[variable].fillna("__missing__").astype(str).unique()):
            indicator = final[variable].fillna("__missing__").astype(str).eq(level)
            rows.append(
                {
                    "variable": variable,
                    "level": level,
                    "smd_unweighted": smd_binary(final, indicator, None),
                    "smd_weighted": smd_binary(final, indicator, "weight"),
                }
            )
    return pd.DataFrame(rows)


def bootstrap_once(interval_sample: pd.DataFrame, seed: int) -> dict[str, float]:
    try:
        final, _ = fit_weights(interval_sample, collect_diagnostics=False)
        estimate = effect_from_final(final)
        estimate["seed"] = seed
        estimate["converged"] = 1
        return estimate
    except Exception:
        return {
            "risk_continue": np.nan,
            "risk_early": np.nan,
            "risk_difference": np.nan,
            "risk_ratio": np.nan,
            "seed": seed,
            "converged": 0,
        }


def cluster_bootstrap(intervals: pd.DataFrame, replicates: int, jobs: int, seed: int = 20260802) -> pd.DataFrame:
    if replicates <= 0:
        return pd.DataFrame()
    groups = {stay: idx.to_numpy() for stay, idx in intervals.groupby("stay_id", observed=True).groups.items()}
    stays = np.array(list(groups))
    seeds = np.random.SeedSequence(seed).spawn(replicates)

    def sample_and_fit(rep: int) -> dict[str, float]:
        rng = np.random.default_rng(seeds[rep])
        sampled = rng.choice(stays, size=len(stays), replace=True)
        index_parts = [groups[stay] for stay in sampled]
        indices = np.concatenate(index_parts)
        copy_ids = np.concatenate(
            [np.full(len(index_parts[copy_id]), copy_id, dtype=np.int64) for copy_id in range(len(sampled))]
        )
        sample = intervals.loc[indices].copy().reset_index(drop=True)
        # A resampled stay can appear more than once. The copy identifier prevents
        # cumulative weights from leaking across bootstrap multiplicities that share
        # the original stay_id and grid_hour.
        sample["analysis_stay_id"] = copy_ids
        return bootstrap_once(sample, int(rng.integers(1, 2**31 - 1)))

    results = Parallel(n_jobs=jobs, backend="loky", verbose=10)(
        delayed(sample_and_fit)(rep) for rep in range(replicates)
    )
    return pd.DataFrame(results)


def interval_confidence(bootstrap: pd.DataFrame, column: str) -> tuple[float, float]:
    if bootstrap.empty or "converged" not in bootstrap.columns or column not in bootstrap.columns:
        return np.nan, np.nan
    values = bootstrap.loc[bootstrap["converged"].eq(1), column].dropna()
    if len(values) == 0:
        return np.nan, np.nan
    return float(values.quantile(0.025)), float(values.quantile(0.975))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--label", default="primary")
    args = parser.parse_args()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    RESTRICTED_DERIVED.mkdir(parents=True, exist_ok=True)
    grid, intervals = load_data()
    final, calibration_frame = fit_weights(intervals, collect_diagnostics=True)
    estimate = effect_from_final(final)
    weights = weight_diagnostics(final)
    balance = balance_diagnostics(final)

    bootstrap = cluster_bootstrap(intervals, args.bootstrap, args.jobs)
    output_rows = []
    for key in ("risk_continue", "risk_early", "risk_difference", "risk_ratio"):
        lower, upper = interval_confidence(bootstrap, key)
        output_rows.append(
            {
                "estimand": key,
                "estimate": estimate[key],
                "ci_lower": lower,
                "ci_upper": upper,
                "bootstrap_requested": args.bootstrap,
                "bootstrap_converged": int(bootstrap["converged"].sum()) if len(bootstrap) else 0,
            }
        )
    effect = pd.DataFrame(output_rows)

    prefix = f"mimic_{args.label}"
    effect_path = RESULT_DIR / f"{prefix}_effect.csv"
    weight_path = RESULT_DIR / f"{prefix}_weight_diagnostics.csv"
    balance_path = RESULT_DIR / f"{prefix}_balance_diagnostics.csv"
    calibration_path = RESULT_DIR / f"{prefix}_adherence_model_diagnostics.csv"
    bootstrap_path = RESULT_DIR / f"{prefix}_bootstrap_distribution.csv"
    restricted_weights_path = RESTRICTED_DERIVED / f"RESTRICTED_{prefix}_retained_clone_weights.csv.gz"

    effect.to_csv(effect_path, index=False, encoding="utf-8-sig")
    weights.to_csv(weight_path, index=False, encoding="utf-8-sig")
    balance.to_csv(balance_path, index=False, encoding="utf-8-sig")
    calibration_frame.to_csv(calibration_path, index=False, encoding="utf-8-sig")
    bootstrap.to_csv(bootstrap_path, index=False, encoding="utf-8-sig")
    final.to_csv(restricted_weights_path, index=False, encoding="utf-8-sig", compression="gzip")

    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis_version": "1.3",
        "run_label": args.label,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "bootstrap_requested": args.bootstrap,
        "bootstrap_jobs": args.jobs,
        "bootstrap_converged": int(bootstrap["converged"].sum()) if len(bootstrap) else 0,
        "grid_rows": int(len(grid)),
        "interval_rows": int(len(intervals)),
        "retained_clone_rows": int(len(final)),
        "retained_clone_stays": int(final["stay_id"].nunique()),
        "terminal_strategy_rule": "adherence assessment stops at first extubation, death, tracheostomy, or ICU discharge",
        "grace_period_rule": "both clones remain compatible until a temporally valid early action or the first strategy-terminal event",
        "weight_truncation": "within strategy 1st/99th percentile",
        "probability_clipping": [0.005, 0.995],
        "censoring_models": "separate logistic models by assigned strategy and six-hour interval",
        "stabilizing_numerator": "marginal adherence probability within strategy and interval",
        "logistic_regularization_c": 10.0,
        "patient_level_output": str(restricted_weights_path),
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
    print(f"RESTRICTED_RETAINED_CLONES={restricted_weights_path}")


if __name__ == "__main__":
    main()
