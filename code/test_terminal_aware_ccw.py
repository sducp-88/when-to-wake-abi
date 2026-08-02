from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("run_mimic_ccw_analysis_v1_1.py")
SPEC = importlib.util.spec_from_file_location("ccw", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ccw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ccw)
pd = ccw.pd


def make_grid(
    stay_id: int,
    terminal_hour: float | None,
    early_valid: int,
    early_compat: tuple[int, int, int, int],
    continue_compat: tuple[int, int, int, int],
) -> pd.DataFrame:
    grid_time = pd.Timestamp("2026-01-01 00:00:00")
    terminal = pd.NaT if terminal_hour is None else grid_time + pd.Timedelta(hours=terminal_hour)
    action = grid_time + pd.Timedelta(hours=2) if early_valid else pd.NaT
    rows = []
    for interval_index in range(1, 5):
        rows.append(
            {
                "stay_id": stay_id,
                "grid_hour": 12,
                "grid_time": grid_time,
                "extubation_time": terminal,
                "tracheostomy_time": pd.NaT,
                "deathtime": pd.NaT,
                "outtime": grid_time + pd.Timedelta(days=10),
                "first_qualifying_action_time": action,
                "early_temporal_valid": early_valid,
                "early_snapshot_compatible": early_compat[interval_index - 1],
                "continue_snapshot_compatible": continue_compat[interval_index - 1],
                "interval_index": interval_index,
            }
        )
    return pd.DataFrame(rows)


def retained_rows(clones: pd.DataFrame) -> pd.DataFrame:
    terminal_within = clones["terminal_hours"].notna() & clones["terminal_hours"].le(24)
    retention_interval = pd.Series(4, index=clones.index)
    retention_interval.loc[terminal_within] = (
        (clones.loc[terminal_within, "terminal_hours"].clip(lower=1e-9) / 6.0).apply(float.__ceil__).clip(1, 4)
    )
    return clones[
        clones["interval_index"].eq(retention_interval)
        & clones["prior_adherent"].eq(1)
        & (clones["assessment_required"].eq(0) | clones["adherent"].eq(1))
    ]


def main() -> None:
    # No action before extubation at hour 4: both grace-period clones survive.
    case1 = ccw.construct_clones(make_grid(1, 4, 0, (0, 0, 0, 0), (0, 0, 0, 0)))
    assert set(retained_rows(case1)["assigned_strategy"]) == {0, 1}

    # A valid action at hour 2 before extubation at hour 4: early survives;
    # continued sedation is artificially censored.
    case2 = ccw.construct_clones(make_grid(2, 4, 1, (1, 1, 1, 1), (0, 0, 0, 0)))
    assert set(retained_rows(case2)["assigned_strategy"]) == {1}

    # Extubation at hour 10 stops the strategy before the 12-hour boundary.
    # The early clone is retained even if the unavailable 12-hour snapshot is 0.
    case3 = ccw.construct_clones(make_grid(3, 10, 1, (1, 0, 0, 0), (0, 0, 0, 0)))
    retained3 = retained_rows(case3)
    assert set(retained3["assigned_strategy"]) == {1}
    assert int(retained3.iloc[0]["interval_index"]) == 2

    # Bootstrap copies with the same original stay/grid must keep separate histories.
    duplicate = pd.concat([make_grid(4, None, 1, (1, 1, 1, 1), (0, 0, 0, 0))] * 2, ignore_index=True)
    duplicate["analysis_stay_id"] = [0] * 4 + [1] * 4
    cloned_duplicate = ccw.construct_clones(duplicate)
    assert cloned_duplicate.groupby(["analysis_stay_id", "grid_hour", "assigned_strategy"]).size().eq(4).all()

    print("terminal-aware CCW unit tests: PASS")


if __name__ == "__main__":
    main()
