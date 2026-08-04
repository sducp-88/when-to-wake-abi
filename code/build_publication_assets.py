from __future__ import annotations

import json
import math
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from PIL import Image


ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
MIMIC_GRID = ROOT / "00_restricted_data" / "derived" / "mimic_v1_1" / "mimic_analysis_grid_v1_1.csv.gz"
EICU_GRID = ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_1" / "eicu_analysis_grid_transport_v1_1.csv.gz"
MIMIC_RESULTS = ROOT / "aggregate_results" / "mimic"
EICU_RESULTS = ROOT / "aggregate_results" / "eicu"
MIMIC_EFFECT = MIMIC_RESULTS / "mimic_primary_v1_3_effect.csv"
EICU_EFFECT = EICU_RESULTS / "eicu_transport_v1_2_gcs_validated_effect.csv"
MIMIC_SENS = MIMIC_RESULTS / "sensitivity" / "mimic_sensitivity_summary_v1_3.csv"
MIMIC_BALANCE = MIMIC_RESULTS / "mimic_primary_v1_3_balance_diagnostics.csv"
EICU_BALANCE = EICU_RESULTS / "eicu_transport_v1_2_gcs_validated_balance_diagnostics.csv"
MIMIC_WEIGHTS = MIMIC_RESULTS / "mimic_primary_v1_3_weight_diagnostics.csv"
EICU_WEIGHTS = EICU_RESULTS / "eicu_transport_v1_2_gcs_validated_weight_diagnostics.csv"
MIMIC_FUNNEL = MIMIC_RESULTS / "mimic_formal_funnel_2026-08-02.csv"
EICU_FUNNEL = EICU_RESULTS / "eicu_transport_funnel_2026-08-04.csv"
SEVERITY_BALANCE = ROOT / "aggregate_results" / "severity" / "severity_balance_diagnostics_v1_4.csv"

GENERATED = ROOT / "generated_publication_assets"
OUT_TABLES = Path(os.environ.get("WTW_TABLE_OUTPUT", str(GENERATED / "tables")))
OUT_FIGURES = Path(os.environ.get("WTW_FIGURE_OUTPUT", str(GENERATED / "figures")))
OUT_SUMMARY = Path(os.environ.get("WTW_SUMMARY_OUTPUT", str(GENERATED / "summary")))


COLORS = {
    "ink": "#26343D",
    "navy": "#3E5568",
    "blue": "#496F82",
    "teal": "#5E817A",
    "ochre": "#9A7B50",
    "aubergine": "#756D7D",
    "rust": "#8C5E58",
    "gray": "#687782",
    "grid": "#D8DEE1",
    "light": "#F3F5F6",
    "blue_light": "#EDF2F4",
    "teal_light": "#EEF3F1",
}


def q1(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").quantile(0.25))


def q3(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").quantile(0.75))


def fmt_median_iqr(series: pd.Series, digits: int = 1) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return "Not available"
    return f"{values.median():.{digits}f} ({q1(values):.{digits}f}-{q3(values):.{digits}f})"


def fmt_n_pct(mask: pd.Series, denominator: int) -> str:
    n = int(pd.Series(mask).fillna(False).astype(bool).sum())
    if n < 10:
        return "<10 (suppressed)"
    return f"{n} ({100*n/denominator:.1f}%)"


def first_decision(frame: pd.DataFrame, stay_col: str) -> pd.DataFrame:
    return frame.sort_values([stay_col, "grid_hour"]).drop_duplicates(stay_col, keep="first").copy()


def cohort_characteristics() -> pd.DataFrame:
    mimic = pd.read_csv(MIMIC_GRID, low_memory=False)
    eicu = pd.read_csv(EICU_GRID, low_memory=False)
    m = first_decision(mimic, "stay_id")
    e = first_decision(eicu, "patientunitstayid")
    rows: list[dict[str, str]] = []

    def add(label: str, mv: str, ev: str, note: str = "") -> None:
        rows.append({"Characteristic": label, "MIMIC-IV v3.1": mv, "eICU-CRD v2.0": ev, "Notes": note})

    add("Unique ICU stays, n", str(len(m)), str(len(e)), "First eligible decision point per stay")
    add("Eligible decision points, n", str(len(mimic)), str(len(eicu)), "Repeated 6-hour nested trials")
    add("Age, years", fmt_median_iqr(m["age"]), fmt_median_iqr(e["age"]))
    add("Male sex", fmt_n_pct(m["gender"].astype(str).str.upper().eq("M"), len(m)), fmt_n_pct(e["gender"].astype(str).str.upper().eq("MALE"), len(e)))
    for subtype, label in [("AIS", "Acute ischemic stroke"), ("ICH", "Intracerebral hemorrhage"), ("SAH", "Subarachnoid hemorrhage"), ("TBI", "Traumatic brain injury")]:
        add(label, fmt_n_pct(m["abi_subtype"].astype(str).eq(subtype), len(m)), fmt_n_pct(e["abi_subtype"].astype(str).eq(subtype), len(e)))
    add("Time zero after ventilation start, h", fmt_median_iqr(m["grid_hour"], 0), fmt_median_iqr(e["grid_hour"], 0))
    add("Active core sedative classes, n", fmt_median_iqr(m["baseline_drug_count"], 0), fmt_median_iqr(e["baseline_drug_count"], 0))
    add("Propofol active", fmt_n_pct(m["propofol_active"].eq(1), len(m)), fmt_n_pct(e["propofol_active"].eq(1), len(e)))
    add("Midazolam active", fmt_n_pct(m["midazolam_active"].eq(1), len(m)), fmt_n_pct(e["midazolam_active"].eq(1), len(e)))
    add("Dexmedetomidine active", fmt_n_pct(m["dexmed_active"].eq(1), len(m)), fmt_n_pct(e["dexmed_active"].eq(1), len(e)))
    add("Median MAP in prior 2 h, mm Hg", fmt_median_iqr(m["map_median_2h"]), fmt_median_iqr(e["map_median_2h"]))
    add("Latest FiO2", fmt_median_iqr(m["fio2"], 2), fmt_median_iqr(e["fio2"], 2))
    add("Latest PEEP, cm H2O", fmt_median_iqr(m["peep"]), fmt_median_iqr(e["peep"]))
    add("RASS", fmt_median_iqr(m["rass"], 0), fmt_median_iqr(e["rass"], 0), "eICU RASS availability was sparse")
    add("GCS motor (MIMIC) / total (eICU)", fmt_median_iqr(m["gcs_motor"], 0), fmt_median_iqr(e["gcs_value"], 0), "Database-native neurologic measurement")
    add("ICP measured", fmt_n_pct(m["icp_latest"].notna(), len(m)), fmt_n_pct(e["icp_latest"].notna(), len(e)))
    add("Vasopressor observed", fmt_n_pct(m["vasopressor_observed"].eq(1), len(m)), fmt_n_pct(e["vasopressor_observed"].eq(1), len(e)), "Absence of eICU point records was not treated as proof of no use")
    add("Opioid observed", fmt_n_pct(m["opioid_observed"].eq(1), len(m)), fmt_n_pct(e["opioid_observed"].eq(1), len(e)))
    add("Unweighted day-7 liberation outcome", fmt_n_pct(m["alive_success_extub_day7"].eq(1), len(m)), fmt_n_pct(e["alive_vent_end_day7"].eq(1), len(e)), "Explicit successful extubation in MIMIC; ventilation-end proxy in eICU")

    result = pd.DataFrame(rows)
    del mimic, eicu, m, e
    return result


def load_effect(path: Path, database: str, outcome: str) -> dict[str, object]:
    raw = pd.read_csv(path)
    if "estimand" in raw.columns:
        row = raw.set_index("estimand").to_dict(orient="index")
        return {
            "Database": database,
            "Outcome": outcome,
            "Risk under continued sedation": row["risk_continue"]["estimate"],
            "Risk under early de-escalation": row["risk_early"]["estimate"],
            "Risk difference": row["risk_difference"]["estimate"],
            "RD lower 95% CI": row["risk_difference"]["ci_lower"],
            "RD upper 95% CI": row["risk_difference"]["ci_upper"],
            "Risk ratio": row["risk_ratio"]["estimate"],
            "RR lower 95% CI": row["risk_ratio"]["ci_lower"],
            "RR upper 95% CI": row["risk_ratio"]["ci_upper"],
            "Bootstrap converged": row["risk_difference"].get("bootstrap_converged", np.nan),
        }
    row = raw.iloc[0].to_dict()
    return {
        "Database": database,
        "Outcome": outcome,
        "Risk under continued sedation": row["risk_continue"],
        "Risk under early de-escalation": row["risk_early"],
        "Risk difference": row["risk_difference"],
        "RD lower 95% CI": row["risk_difference_ci_lower"],
        "RD upper 95% CI": row["risk_difference_ci_upper"],
        "Risk ratio": row["risk_ratio"],
        "RR lower 95% CI": row["risk_ratio_ci_lower"],
        "RR upper 95% CI": row["risk_ratio_ci_upper"],
        "Bootstrap converged": row.get("bootstrap_converged", np.nan),
    }


def effect_table() -> pd.DataFrame:
    return pd.DataFrame([
        load_effect(MIMIC_EFFECT, "MIMIC-IV v3.1", "Alive and successfully extubated by day 7"),
        load_effect(EICU_EFFECT, "eICU-CRD v2.0", "Alive with reconstructed ventilation end by day 7 and no renewed ventilation within 48 h"),
    ])


def sensitivity_table() -> pd.DataFrame:
    frame = pd.read_csv(MIMIC_SENS)
    primary = pd.read_csv(MIMIC_EFFECT).set_index("estimand")
    mask = frame["scenario"].eq("primary_reference")
    for measure in ["risk_continue", "risk_early", "risk_difference", "risk_ratio"]:
        frame.loc[mask, f"{measure}_ci_lower"] = primary.loc[measure, "ci_lower"]
        frame.loc[mask, f"{measure}_ci_upper"] = primary.loc[measure, "ci_upper"]
    labels = {
        "primary_reference": "Primary repeated-trial analysis",
        "primary_untruncated": "No weight truncation (point estimate)",
        "lead_30_min": "Extubation lead threshold 30 min",
        "lead_120_min": "Extubation lead threshold 120 min",
        "first_eligible_grid_only": "First eligible decision per stay",
        "ventilation_end_proxy": "Ventilation-end proxy outcome",
        "subtype_AIS": "Acute ischemic stroke",
        "subtype_ICH": "Intracerebral hemorrhage",
        "subtype_SAH": "Subarachnoid hemorrhage",
        "subtype_TBI": "Traumatic brain injury",
    }
    frame.insert(1, "Analysis", frame["scenario"].map(labels).fillna(frame["scenario"]))
    return frame


def diagnostics_table() -> pd.DataFrame:
    rows = []
    for database, wpath, bpath in [
        ("MIMIC-IV v3.1", MIMIC_WEIGHTS, MIMIC_BALANCE),
        ("eICU-CRD v2.0", EICU_WEIGHTS, EICU_BALANCE),
    ]:
        w = pd.read_csv(wpath)
        b = pd.read_csv(bpath)
        strategy_col = "strategy" if "strategy" in w.columns else w.columns[0]
        max_smd_col = "smd_weighted" if "smd_weighted" in b.columns else "weighted_smd" if "weighted_smd" in b.columns else [c for c in b.columns if "weighted" in c.lower() and "unweighted" not in c.lower() and "smd" in c.lower()][0]
        for _, row in w.iterrows():
            rows.append({
                "Database": database,
                "Strategy": row[strategy_col],
                "Retained clones": row.get("n_retained_clones", row.get("n", row.get("n_retained", np.nan))),
                "Unique stays": row.get("n_stays", np.nan),
                "Weight p99": row.get("raw_weight_p99", row.get("p99", row.get("weight_p99", np.nan))),
                "Maximum weight": row.get("truncated_weight_max", row.get("max", row.get("weight_max", np.nan))),
                "ESS": row.get("ess", np.nan),
                "ESS ratio": row.get("ess_ratio", np.nan),
                "Maximum absolute weighted SMD": float(pd.to_numeric(b[max_smd_col], errors="coerce").abs().max()),
            })
    return pd.DataFrame(rows)


def severity_balance_table() -> pd.DataFrame:
    raw = pd.read_csv(SEVERITY_BALANCE)
    rows = []
    for _, row in raw.iterrows():
        digits = 2 if row["unit"] in {"fraction", "ratio", "mg/dL", "mmol/L"} else 1
        suffix = "%" if row["unit"] == "proportion" else ""
        rows.append({
            "Database": row["database"],
            "Severity measure": row["label"],
            "Unit": row["unit"],
            "Continued strategy": f"{row['continue_weighted_value']:.{digits}f}{suffix}",
            "Early de-escalation": f"{row['early_weighted_value']:.{digits}f}{suffix}",
            "Observed coverage, continued / early": (
                f"{row['continue_observed_percent']:.1f}% / {row['early_observed_percent']:.1f}%"
            ),
            "Weighted SMD": f"{row['weighted_smd']:.3f}",
        })
    return pd.DataFrame(rows)


def save_figure(fig: plt.Figure, stem: str, width_in: float, height_in: float) -> None:
    fig.set_size_inches(width_in, height_in)
    fig.savefig(OUT_FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(
        OUT_FIGURES / f"{stem}.tiff",
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    tiff_path = OUT_FIGURES / f"{stem}.tiff"
    with Image.open(tiff_path) as image:
        rgb = image.convert("RGB")
        rgb.save(tiff_path, compression="tiff_lzw", dpi=(600, 600))
    fig.savefig(OUT_FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_FIGURES / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def flow_figure() -> None:
    m = pd.read_csv(MIMIC_FUNNEL)
    e = pd.read_csv(EICU_FUNNEL)
    m_map = dict(zip(m["step"], m["n_rows_or_grids"]))
    e_map = dict(zip(e["step"], e["n"]))
    fig, ax = plt.subplots()
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    columns = [
        (0.24, "MIMIC-IV v3.1", [
            ("Adults with acute brain injury", m_map["adult_first_icu_abi"]),
            ("Candidate ventilation\ndecision grids", m_map["candidate_ventilation_grids"]),
            ("Stable eligible grids", m_map["stable_eligible_grids"]),
            ("Early de-escalation\ncompatible", m_map["early_temporally_valid"]),
            ("Continued sedation\ncompatible at 6 h", m_map["continued_at_6h"]),
        ], COLORS["blue"]),
        (0.76, "eICU-CRD v2.0", [
            ("Adults with ABI, ventilation,\nand sedation", e_map["adult_first_icu_abi_vent_sedative"]),
            ("Candidate ventilation\ndecision grids", e_map["candidate_ventilation_grids"]),
            ("Stable eligible grids", e_map["eligible_stable_grids"]),
            ("Early de-escalation\ncompatible", e_map["early_temporally_valid_grids"]),
            ("Continued sedation\ncompatible at 6 h", e_map["continued_at_6h_grids"]),
        ], COLORS["teal"]),
    ]
    # Fixed geometry prevents text wrapping from changing box height or the
    # apparent length of connectors. Every box and every arrow is identical
    # within and across the two cohort columns.
    ys = np.linspace(0.82, 0.14, 5)
    box_width = 0.37
    box_height = 0.112
    arrow_clearance = 0.008
    for x, title, items, color in columns:
        ax.text(x, 0.94, title, ha="center", fontsize=12.5, fontweight="bold", color=COLORS["ink"])
        ax.plot([x - 0.12, x + 0.12], [0.91, 0.91], color=color, lw=2.2, solid_capstyle="round")
        for idx, ((label, n), y) in enumerate(zip(items, ys)):
            fill = COLORS["blue_light"] if color == COLORS["blue"] else COLORS["teal_light"]
            ax.add_patch(
                FancyBboxPatch(
                    (x - box_width / 2, y - box_height / 2),
                    box_width,
                    box_height,
                    boxstyle="round,pad=0.008,rounding_size=0.012",
                    facecolor=fill,
                    edgecolor=color,
                    linewidth=1.15,
                    transform=ax.transAxes,
                )
            )
            ax.text(
                x,
                y,
                f"{label}\n{int(n):,}",
                ha="center",
                va="center",
                fontsize=8.5,
                color=COLORS["ink"],
                linespacing=1.12,
                transform=ax.transAxes,
            )
            if idx < len(items)-1:
                arrow_start = y - box_height / 2 - arrow_clearance
                arrow_end = ys[idx + 1] + box_height / 2 + arrow_clearance
                ax.annotate(
                    "",
                    xy=(x, arrow_end),
                    xytext=(x, arrow_start),
                    xycoords=ax.transAxes,
                    textcoords=ax.transAxes,
                    arrowprops=dict(
                        arrowstyle="-|>",
                        mutation_scale=9,
                        lw=1.0,
                        color=COLORS["gray"],
                        shrinkA=0,
                        shrinkB=0,
                    ),
                )
    save_figure(fig, "Figure_1_cohort_flow", 7.4, 6.5)


def forest_figure(effects: pd.DataFrame, sens: pd.DataFrame) -> None:
    rows = [
        ("MIMIC-IV primary", effects.iloc[0]["Risk difference"], effects.iloc[0]["RD lower 95% CI"], effects.iloc[0]["RD upper 95% CI"], "Primary"),
        ("eICU transport", effects.iloc[1]["Risk difference"], effects.iloc[1]["RD lower 95% CI"], effects.iloc[1]["RD upper 95% CI"], "Transport"),
    ]
    for key in ["lead_30_min", "lead_120_min", "first_eligible_grid_only", "ventilation_end_proxy", "subtype_AIS", "subtype_ICH", "subtype_SAH", "subtype_TBI"]:
        r = sens.loc[sens["scenario"].eq(key)].iloc[0]
        rows.append((r["Analysis"], r["risk_difference"], r["risk_difference_ci_lower"], r["risk_difference_ci_upper"], "Sensitivity"))
    frame = pd.DataFrame(rows, columns=["label", "estimate", "low", "high", "type"])
    for column in ["estimate", "low", "high"]:
        frame[column] = 100 * pd.to_numeric(frame[column], errors="coerce")
    y = np.arange(len(frame))[::-1]
    fig = plt.figure(constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=[3.4, 1.45], wspace=0.04)
    ax = fig.add_subplot(grid[0, 0])
    annotation_ax = fig.add_subplot(grid[0, 1], sharey=ax)
    ax.axvline(0, color=COLORS["ink"], lw=0.9, ls=(0, (4, 3)))
    for i, row in frame.iterrows():
        color = COLORS["blue"] if row["type"] == "Primary" else COLORS["teal"] if row["type"] == "Transport" else COLORS["gray"]
        marker = "s" if row["type"] == "Primary" else "D" if row["type"] == "Transport" else "o"
        size = 6.8 if row["type"] != "Sensitivity" else 5.2
        ax.errorbar(
            row["estimate"],
            y[i],
            xerr=[[row["estimate"]-row["low"]], [row["high"]-row["estimate"]]],
            fmt=marker,
            color=color,
            ecolor=color,
            capsize=2.5,
            elinewidth=1.35,
            capthick=1.1,
            markersize=size,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(frame["label"], fontsize=8.7, color=COLORS["ink"])
    ax.set_xlabel("Risk difference for day-7 liberation, percentage points", color=COLORS["ink"])
    ax.grid(axis="x", color=COLORS["grid"], lw=0.7)
    ax.set_axisbelow(True)
    ax.axhline(y[1] - 0.55, color=COLORS["grid"], lw=0.8)
    xmin = min(-5.0, float(frame["low"].min()) - 1.5)
    xmax = max(30.0, float(frame["high"].max()) + 1.5)
    ax.set_xlim(xmin, xmax)
    annotation_ax.set_xlim(0, 1)
    annotation_ax.text(0.02, y.max() + 0.72, "Risk difference (95% CI)", ha="left", va="bottom", fontsize=8.2, color=COLORS["gray"], fontweight="bold")
    for i, row in frame.iterrows():
        annotation_ax.text(
            0.02,
            y[i],
            f"{row['estimate']:.1f} ({row['low']:.1f} to {row['high']:.1f})",
            ha="left",
            va="center",
            fontsize=8.0,
            color=COLORS["ink"],
        )
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["gray"])
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", colors=COLORS["gray"])
    annotation_ax.axis("off")
    save_figure(fig, "Figure_2_effect_forest", 8.2, 5.55)


def balance_figure() -> None:
    display_names = {
        "peep": "PEEP",
        "grid_hour": "Decision hour",
        "gcs_motor": "GCS motor",
        "temperature_c": "Temperature",
        "vasopressor_observed": "Vasopressor observed",
        "propofol_active": "Propofol active",
        "midazolam_active": "Midazolam active",
        "paO2_fio2": "PaO2/FiO2",
        "pao2_fio2": "PaO2/FiO2",
        "creatinine": "Creatinine",
        "opioid_observed": "Opioid observed",
        "rass": "RASS",
        "abi_subtype": "ABI subtype",
        "comorbidity_count": "Comorbidity count",
        "dexmed_active": "Dexmedetomidine active",
        "paco2": "PaCO2",
        "apache_iva_score": "APACHE IVa score",
        "apache_iva_aps": "APACHE IVa acute physiology score",
        "gender": "Sex",
        "heart_rate": "Heart rate",
        "age": "Age",
    }

    def publication_label(row: pd.Series, variable_col: str) -> str:
        raw = str(row[variable_col])
        label = display_names.get(raw, raw.replace("_", " ").title())
        level = str(row.get("level", ""))
        if level == "continuous":
            return label
        if raw == "gender":
            return f"{label}: {level}"
        if level in {"0", "1"}:
            return f"{label}: {'yes' if level == '1' else 'no'}"
        return f"{label}: {level}"

    fig, axes = plt.subplots(1, 2, sharex=True)
    for ax, database, path, color in [
        (axes[0], "MIMIC-IV", MIMIC_BALANCE, COLORS["blue"]),
        (axes[1], "eICU-CRD", EICU_BALANCE, COLORS["teal"]),
    ]:
        frame = pd.read_csv(path)
        variable_col = "variable" if "variable" in frame.columns else frame.columns[0]
        before_col = "smd_unweighted" if "smd_unweighted" in frame.columns else "unweighted_smd" if "unweighted_smd" in frame.columns else [c for c in frame.columns if "unweighted" in c.lower() and "smd" in c.lower()][0]
        after_col = "smd_weighted" if "smd_weighted" in frame.columns else "weighted_smd" if "weighted_smd" in frame.columns else [c for c in frame.columns if "weighted" in c.lower() and "unweighted" not in c.lower() and "smd" in c.lower()][0]
        frame = frame.assign(before=pd.to_numeric(frame[before_col], errors="coerce").abs(), after=pd.to_numeric(frame[after_col], errors="coerce").abs()).sort_values("after", ascending=False).head(18).sort_values("after")
        frame["display_label"] = frame.apply(lambda r: publication_label(r, variable_col), axis=1)
        yy = np.arange(len(frame))
        ax.hlines(yy, xmin=np.minimum(frame["before"], frame["after"]), xmax=np.maximum(frame["before"], frame["after"]), color=COLORS["grid"], lw=0.75, zorder=1)
        ax.scatter(frame["before"], yy, s=25, facecolors="white", edgecolors=COLORS["gray"], linewidths=1.0, label="Before weighting", zorder=2)
        ax.scatter(frame["after"], yy, s=27, color=color, edgecolors="white", linewidths=0.35, label="After weighting", zorder=3)
        ax.axvline(0.10, color=COLORS["ochre"], ls=(0, (3, 3)), lw=1.0)
        ax.set_yticks(yy)
        ax.set_yticklabels(frame["display_label"], fontsize=7.0, color=COLORS["ink"])
        ax.set_title(database, fontweight="bold", color=COLORS["ink"], fontsize=11.5, pad=8)
        ax.grid(axis="x", color=COLORS["grid"], lw=0.65)
        ax.set_axisbelow(True)
        for side in ["top", "right", "left"]:
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(COLORS["gray"])
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", colors=COLORS["gray"])
    axes[0].set_xlabel("Absolute standardized mean difference")
    axes[1].set_xlabel("Absolute standardized mean difference")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=8.2, bbox_to_anchor=(0.5, 0.995))
    fig.text(0.5, 0.955, "Dotted line: absolute standardized mean difference = 0.10", ha="center", va="top", fontsize=7.8, color=COLORS["gray"])
    fig.tight_layout(rect=(0, 0, 1, 0.91), w_pad=4.0)
    save_figure(fig, "Figure_3_covariate_balance", 10.2, 6.35)


def graphical_abstract(effects: pd.DataFrame) -> None:
    m = effects.iloc[0]
    e = effects.iloc[1]
    fig, ax = plt.subplots()
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    panel_specs = [
        (0.025, 0.17, 0.265, 0.67, COLORS["light"]),
        (0.325, 0.17, 0.32, 0.67, "white"),
        (0.68, 0.17, 0.295, 0.67, COLORS["light"]),
    ]
    for x, y, w, h, fill in panel_specs:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fill, edgecolor=COLORS["grid"], lw=0.8))
    ax.text(0.025, 0.93, "WHEN-TO-WAKE ABI", fontsize=14.5, fontweight="bold", color=COLORS["ink"], va="top")
    ax.text(0.045, 0.76, "Population", fontsize=8.4, fontweight="bold", color=COLORS["gray"])
    ax.text(0.045, 0.62, "Adults with acute\nbrain injury", fontsize=11.0, fontweight="bold", color=COLORS["ink"], va="top")
    ax.text(0.045, 0.33, "Mechanical ventilation\nRepeated stable decisions", fontsize=8.2, color=COLORS["gray"], va="top")
    ax.text(0.345, 0.76, "Sequential strategy contrast", fontsize=8.4, fontweight="bold", color=COLORS["gray"])
    ax.text(0.485, 0.59, "Early de-escalation within 6 h", ha="center", va="center", fontsize=8.2, color=COLORS["ink"], bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.05", fc=COLORS["blue_light"], ec=COLORS["blue"], lw=1.0))
    ax.text(0.485, 0.47, "versus", ha="center", va="center", fontsize=7.2, color=COLORS["gray"])
    ax.text(0.485, 0.36, "Continued sedation for 24 h", ha="center", va="center", fontsize=8.2, color=COLORS["ink"], bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.05", fc="white", ec=COLORS["gray"], lw=1.0))
    ax.text(0.485, 0.225, "Clone-censor-weight estimation", ha="center", fontsize=7.7, color=COLORS["gray"])
    ax.text(0.70, 0.76, "Day-7 liberation", fontsize=8.4, fontweight="bold", color=COLORS["gray"])
    ax.text(0.72, 0.60, f"MIMIC-IV   {100*m['Risk difference']:+.1f} pp", fontsize=11.0, fontweight="bold", color=COLORS["blue"])
    ax.text(0.72, 0.49, f"95% CI {100*m['RD lower 95% CI']:.1f} to {100*m['RD upper 95% CI']:.1f}", fontsize=8.2, color=COLORS["ink"])
    ax.text(0.72, 0.34, f"eICU proxy   {100*e['Risk difference']:+.1f} pp", fontsize=10.2, fontweight="bold", color=COLORS["teal"])
    ax.text(0.72, 0.24, f"95% CI {100*e['RD lower 95% CI']:.1f} to {100*e['RD upper 95% CI']:.1f}", fontsize=8.2, color=COLORS["ink"])
    ax.text(0.025, 0.075, "Observational associations; eICU used a non-equivalent ventilation-end proxy.", fontsize=7.6, color=COLORS["gray"])
    save_figure(fig, "Graphical_Abstract", 9.2, 3.0)


def summary_report(effects: pd.DataFrame, sens: pd.DataFrame, diagnostics: pd.DataFrame) -> str:
    m = effects.iloc[0]
    e = effects.iloc[1]
    first = sens.loc[sens["scenario"].eq("first_eligible_grid_only")].iloc[0]
    lines = [
        "# WHEN-TO-WAKE ABI publication result summary",
        "",
        "Generated from versioned aggregate outputs. Patient-level data were not exported.",
        "",
        "## Main finding",
        "",
        f"In MIMIC-IV, the standardized day-7 successful-extubation risk was {100*m['Risk under early de-escalation']:.1f}% under early de-escalation and {100*m['Risk under continued sedation']:.1f}% under continued sedation (risk difference {100*m['Risk difference']:.1f} percentage points, 95% CI {100*m['RD lower 95% CI']:.1f} to {100*m['RD upper 95% CI']:.1f}; risk ratio {m['Risk ratio']:.2f}, 95% CI {m['RR lower 95% CI']:.2f} to {m['RR upper 95% CI']:.2f}).",
        "",
        f"In eICU-CRD, using the non-equivalent ventilation-end proxy, the risk difference was {100*e['Risk difference']:.1f} percentage points (95% CI {100*e['RD lower 95% CI']:.1f} to {100*e['RD upper 95% CI']:.1f}). The result was directionally concordant but imprecise and was interpreted within the database-specific measurement framework.",
        "",
        "## Robustness boundary",
        "",
        f"Timing-tolerance, alternative-outcome, and ABI-subtype estimates were directionally consistent. Restricting to the first eligible decision per stay reduced information and attenuated the estimate to {100*first['risk_difference']:.1f} percentage points (95% CI {100*first['risk_difference_ci_lower']:.1f} to {100*first['risk_difference_ci_upper']:.1f}).",
        "",
        "## Interpretation ceiling",
        "",
        "The estimates are compatible with a clinically important association but do not prove a causal treatment effect. Residual confounding, decision-trigger misclassification, sedation documentation differences, and outcome-measurement non-equivalence remain central limitations.",
        "",
        "## Weight and balance diagnostics",
        "",
        dataframe_markdown(diagnostics),
        "",
    ]
    return "\n".join(lines)


def dataframe_markdown(frame: pd.DataFrame) -> str:
    columns = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append("" if math.isnan(value) else f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    for path in [OUT_TABLES, OUT_FIGURES, OUT_SUMMARY]:
        path.mkdir(parents=True, exist_ok=True)
    required = [
        MIMIC_EFFECT,
        EICU_EFFECT,
        MIMIC_SENS,
        MIMIC_BALANCE,
        EICU_BALANCE,
        MIMIC_WEIGHTS,
        EICU_WEIGHTS,
        MIMIC_FUNNEL,
        EICU_FUNNEL,
        SEVERITY_BALANCE,
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Required formal outputs missing:\n" + "\n".join(missing))

    effects = effect_table()
    sens = sensitivity_table()
    diagnostics = diagnostics_table()
    severity = severity_balance_table()

    cohort_table_generated = MIMIC_GRID.exists() and EICU_GRID.exists()
    if cohort_table_generated:
        char = cohort_characteristics()
        char.to_csv(OUT_TABLES / "Table_1_cohort_characteristics.csv", index=False, encoding="utf-8-sig")
    else:
        print("Table 1 skipped: authorized local patient-level analysis grids were not found.")
    effects.to_csv(OUT_TABLES / "Table_2_primary_and_transport_effects.csv", index=False, encoding="utf-8-sig")
    sens.to_csv(OUT_TABLES / "Table_S1_sensitivity_analyses.csv", index=False, encoding="utf-8-sig")
    diagnostics.to_csv(OUT_TABLES / "Table_S2_weight_and_balance_diagnostics.csv", index=False, encoding="utf-8-sig")
    severity.to_csv(OUT_TABLES / "Table_S4_severity_balance_diagnostics.csv", index=False, encoding="utf-8-sig")

    flow_figure()
    forest_figure(effects, sens)
    balance_figure()
    graphical_abstract(effects)

    report = summary_report(effects, sens, diagnostics)
    (OUT_SUMMARY / "RESULTS_SUMMARY_PUBLICATION_v1.4.md").write_text(report, encoding="utf-8")
    manifest = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "input_effect_files": [str(MIMIC_EFFECT), str(EICU_EFFECT)],
        "tables": sorted(str(p) for p in OUT_TABLES.glob("*.csv")),
        "figures": sorted(str(p) for p in OUT_FIGURES.glob("*.*")),
        "safe_aggregate_outputs_only": True,
        "cohort_table_generated": cohort_table_generated,
        "small_cell_policy": "Counts below 10 are suppressed when publication Table 1 is generated from authorized local data",
    }
    (OUT_SUMMARY / "PUBLICATION_ASSET_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
