# WHEN-TO-WAKE ABI

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21761953.svg)](https://doi.org/10.5281/zenodo.21761953)

Reproducible code, prespecified protocol, statistical analysis plan, aggregate outputs, and novelty-audit trail for:

> Early Sedation De-escalation After Physiologic Stabilization and Day-7 Ventilator Liberation in Acute Brain Injury: A Two-Cohort Sequential Target-Trial Emulation

## Status

The analyses and aggregate outputs are unchanged. Version 1.0.4 is a metadata-only correction that lists Lifei Wei first and Zhichao Bi second among the two co-first authors; it does not change either author's contribution statement or any cohort, estimate, diagnostic, code, protocol, figure, or statistical-analysis-plan content. Version 1.0.4 is archived at [doi:10.5281/zenodo.21782611](https://doi.org/10.5281/zenodo.21782611), and the Zenodo concept record for all software versions is [doi:10.5281/zenodo.21761953](https://doi.org/10.5281/zenodo.21761953). Version 1.0.3 is archived at [doi:10.5281/zenodo.21768657](https://doi.org/10.5281/zenodo.21768657), version 1.0.2 at [doi:10.5281/zenodo.21766624](https://doi.org/10.5281/zenodo.21766624), version 1.0.1 at [doi:10.5281/zenodo.21762440](https://doi.org/10.5281/zenodo.21762440), and version 1.0.0 at [doi:10.5281/zenodo.21761954](https://doi.org/10.5281/zenodo.21761954). The accompanying manuscript has not yet been accepted or published; the manuscript DOI will be added when available.

## Main analysis

- Primary MIMIC-IV analysis: 9,830 eligible decision grids from 2,027 ICU stays.
- Estimated day-7 successful-extubation risk: 50.2% under early de-escalation versus 42.5% under continued sedation.
- Risk difference: 7.7 percentage points (95% CI, 4.4 to 11.0); risk ratio: 1.18 (95% CI, 1.10 to 1.27).
- eICU transport analysis: 2,964 eligible grids from 657 stays; risk difference 3.2 percentage points (95% CI, -2.9 to 10.4).

The eICU analysis uses a non-equivalent ventilation-end proxy and is a measurement-aware transport analysis, not exact external validation. The estimates are observational associations and do not establish a causal treatment recommendation.

## Data-access boundary

MIMIC-IV and the eICU Collaborative Research Database are credentialed PhysioNet resources. Source records and all patient-level derivatives are **not included** and must not be redistributed. Authorized users must obtain each database under its own credentialing and data-use requirements. No patient-level data are needed to inspect the protocol or reproduce the reported effect and diagnostic tables and figures from the included aggregate outputs; reconstruction of the descriptive cohort table requires authorized local analysis grids.

For full reconstruction from source data, place authorized local copies under this ignored structure:

```text
00_restricted_data/
  MIMIC-IV/3.1/extracted/mimic-iv-3.1/
  eICU-CRD/2.0/extracted/eicu-collaborative-research-database-2.0/
  derived/
```

Never commit `00_restricted_data/` or patient-level derived files.

## Repository layout

```text
code/                 cohort construction, QA, estimation, sensitivity, and figure scripts
protocol/             protocol/SAP, amendments, manifests, DAG, and common data model
aggregate_results/    aggregate estimates, diagnostics, and bootstrap distributions
novelty_audit/        dated search logs, screening ledger, and bounded novelty report
```

## Environment

Python 3.11 or later is recommended.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

The scripts resolve the project root from `WTW_PROJECT_ROOT`; when it is unset, they use the current working directory. Optional vendored dependencies can be provided with `WTW_VENDOR_DIR`.

PowerShell example:

```powershell
$env:WTW_PROJECT_ROOT = (Get-Location).Path
python code/test_terminal_aware_ccw.py
python code/build_mimic_analysis_ready_v1_1.py
python code/qa_mimic_analysis_ready_v1_1.py
python code/run_mimic_ccw_analysis_v1_1.py --bootstrap 1000 --n-jobs 1
python code/run_mimic_sensitivity_v1_3.py
python code/build_eicu_analysis_ready_v1_0.py
python code/qa_eicu_analysis_ready_v1_0.py
python code/run_eicu_transport_ccw_v1_0.py --bootstrap 1000 --n-jobs 1 --calibrate
```

Run the versioned pipeline only with authorized local data. The specification history is documented in `protocol/CHANGELOG.md` and the versioned analysis manifests.

## Novelty-audit boundary

The public repository contains the dated queries, counts, screening decisions, and audit report. Bulk API inventories containing full abstracts are retained in the private audit archive and are not redistributed here. The audit conclusion is deliberately bounded: the exact design conjunction was not detected in the searched sources as of 2026-08-02; this is not proof that no unpublished or unindexed study exists.

## Citation

Use `CITATION.cff` and cite the immutable v1.0.4 record [doi:10.5281/zenodo.21782611](https://doi.org/10.5281/zenodo.21782611). The concept DOI [doi:10.5281/zenodo.21761953](https://doi.org/10.5281/zenodo.21761953) resolves to the latest software version. The manuscript DOI will be added when available.

## License

Original analysis code and documentation are released under the [MIT License](LICENSE). The data providers' terms remain controlling for MIMIC-IV and eICU-CRD and are not altered by this code license.

## Contact

Peng Cheng, Department of Neurology, The Second Qilu Hospital of Shandong University: sducp@email.sdu.edu.cn
