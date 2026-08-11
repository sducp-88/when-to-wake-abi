from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
OLD = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_1"
NEW = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_5_bias_targeted"


def merge_file(old_name: str, new_name: str, keys: list[str]) -> dict[str, int]:
    old = pd.read_csv(OLD / old_name, low_memory=False)
    rebuilt = pd.read_csv(NEW / new_name, low_memory=False)
    added = [column for column in rebuilt.columns if column not in old.columns]
    if rebuilt.duplicated(keys).any() or old.duplicated(keys).any():
        raise RuntimeError(f"Duplicate keys while anchoring {new_name}")
    augmented = old.merge(rebuilt[keys + added], on=keys, how="left", validate="one_to_one")
    augmented.to_csv(NEW / new_name, index=False, encoding="utf-8-sig", compression="gzip")
    return {
        "frozen_rows": int(len(old)),
        "rebuilt_rows": int(len(rebuilt)),
        "augmented_rows": int(len(augmented)),
        "frozen_rows_without_rebuilt_match": int(augmented[added].isna().all(axis=1).sum()),
        "added_columns": int(len(added)),
    }


def main() -> None:
    grid = merge_file(
        "mimic_analysis_grid_v1_1.csv.gz",
        "mimic_analysis_grid_v1_5.csv.gz",
        ["stay_id", "grid_hour"],
    )
    intervals = merge_file(
        "mimic_analysis_intervals_v1_1.csv.gz",
        "mimic_analysis_intervals_v1_5.csv.gz",
        ["stay_id", "grid_hour", "interval_index"],
    )
    print({"grid": grid, "intervals": intervals})
    print("PATIENT_LEVEL_CONSOLE_OUTPUT=NO")


if __name__ == "__main__":
    main()
