# WHEN-TO-WAKE ABI v1.0.6

Release date: 2026-08-05

Zenodo concept DOI: https://doi.org/10.5281/zenodo.21761953

## Scope

This patch release corrects a publication-asset inconsistency in v1.0.5. The graphical abstract had retained the superseded eICU v1.1 transport estimate even though the aggregate results, manuscript tables, and v1.0.5 release notes correctly reported the eICU v1.2 GCS-validated analysis.

## Correction

- Updated the graphical abstract eICU proxy estimate from the superseded +3.2 percentage points (95% CI, -2.9 to 10.4) to the released +4.0 percentage points (95% CI, -2.5 to 11.1).
- Re-exported the graphical abstract in PNG, TIFF, SVG, and PDF formats.
- Added an automated release-QA assertion that rejects the superseded graphical-abstract values.

## Unchanged scientific content

No cohort, treatment strategy, outcome, model, bootstrap result, statistical inference, or interpretation changed. The primary MIMIC-IV estimate and corrected eICU v1.2 aggregate result files are unchanged.

## Data boundary

No source records, patient-level derivatives, retained-clone files, passwords, or credentials are included.
