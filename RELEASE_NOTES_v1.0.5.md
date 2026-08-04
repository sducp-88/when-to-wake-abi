# WHEN-TO-WAKE ABI v1.0.5

Candidate date: 2026-08-04

Immutable version DOI: pending archive deposition

## Scope

This severity-strengthened release corrects eICU neurologic eligibility and updates the eICU transport analysis. The primary MIMIC-IV analysis is unchanged.

## Scientific changes

- Restricted eICU neurologic eligibility to the exact `Glasgow coma score GCS Total` field and valid values from 3 to 15.
- Rebuilt the eICU analysis-ready cohort: 2,351 eligible grids from 536 stays.
- Updated the eICU transport estimate to a risk difference of 4.0 percentage points (95% CI, -2.5 to 11.1) and a risk ratio of 1.07 (95% CI, 0.96 to 1.20).
- Added outcome-blind weighted balance diagnostics for GCS and eICU APACHE IVa severity measures.
- Added a time-valid APACHE IVa feasibility audit. The model failed the prespecified maximum-imbalance and minimum-effective-sample-size gates, so its effect estimate and confidence interval are not released or interpreted.

## Reproducibility changes

- Added versioned eICU v1.1 cohort builder and QA, v1.2 transport analysis and QA, and severity-diagnostic scripts.
- Added severity amendment v1.4, corrected aggregate outputs, and publication assets.
- Retained the superseded eICU v1.1 aggregate family for transparent comparison; it must not be used as the current transport result.

## Data boundary

No source records, patient-level derivatives, retained-clone files, passwords, or credentials are included. Patient-level data remain governed by the PhysioNet data-use agreements.
