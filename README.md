# WHEN-TO-WAKE ABI

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21883676.svg)](https://doi.org/10.5281/zenodo.21883676)

Reproducible code, prespecified protocol, statistical analysis plan, aggregate outputs, and novelty-audit trail for:

> Stability-Triggered Sedation De-escalation and Day-7 Ventilator Liberation After Acute Brain Injury: A Sequential Target-Trial Emulation

## Status

Version 1.0.7 adds a post hoc MIMIC-IV bias-targeted analysis incorporating baseline sedative infusion rates and predecision trajectories, a whole-stay bootstrap distribution, a stay-balanced target-population diagnostic, and revised publication figures and aggregate tables. The trajectory-and-dose model remained close to the frozen primary result but narrowly missed the prespecified balance threshold (maximum weighted absolute standardized mean difference 0.102). The stay-balanced analysis failed balance and effective-sample-size gates and is diagnostic only. Neither analysis replaces the frozen primary estimate.

Version 1.0.7 is archived at [doi:10.5281/zenodo.21883676](https://doi.org/10.5281/zenodo.21883676). Version 1.0.6 remains the preceding immutable archive at [doi:10.5281/zenodo.21806757](https://doi.org/10.5281/zenodo.21806757), and the Zenodo concept record for all software versions is [doi:10.5281/zenodo.21761953](https://doi.org/10.5281/zenodo.21761953). The accompanying manuscript has not yet been accepted or published; its DOI will be added when available.

## Main analysis

- Primary MIMIC-IV analysis: 9,830 eligible decision grids from 2,027 ICU stays.
- Estimated day-7 successful-extubation risk: 50.2% under early de-escalation versus 42.5% under continued sedation.
- Risk difference: 7.7 percentage points (95% CI, 4.4 to 11.0); risk ratio: 1.18 (95% CI, 1.10 to 1.27).
- Corrected eICU transport analysis: 2,351 eligible grids from 536 stays; risk difference 4.0 percentage points (95% CI, -2.5 to 11.1); risk ratio 1.07 (95% CI, 0.96 to 1.20).
- Corrected eICU maximum absolute weighted SMD: 0.099; weighted APACHE IVa score SMD: -0.045; valid GCS Total SMD: 0.022.
- The time-valid APACHE sensitivity failed the prespecified balance and effective-sample-size gates and is explicitly noninferential; its effect estimate is not released.
- Post hoc MIMIC-IV trajectory-and-dose analysis: risk difference 7.2 percentage points (95% CI, 3.9 to 10.6); risk ratio 1.17 (95% CI, 1.09 to 1.26); maximum weighted absolute SMD 0.102.
- Stay-balanced target-population analysis: risk difference 1.4 percentage points and risk ratio 1.024; this diagnostic failed balance and effective-sample-size gates, so no confidence interval or causal interpretation is reported.

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
publication_assets/   publication tables and figures generated from safe aggregate outputs
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
python code/build_eicu_analysis_ready_v1_1.py
python code/qa_eicu_analysis_ready_v1_1.py
python code/run_eicu_transport_ccw_v1_1.py --bootstrap 1000 --n-jobs 1 --calibrate
python code/qa_eicu_transport_v1_2.py
python code/build_severity_balance_supplement_v1_4.py
# Post hoc v1.5 scripts require the same authorized local MIMIC-IV derivatives:
python code/build_mimic_analysis_ready_v1_5.py
python code/merge_v1_5_features_onto_frozen_v1_3_population.py
python code/run_mimic_bias_targeted_sensitivity_v1_5.py
```

Run the versioned pipeline only with authorized local data. The specification history is documented in `protocol/CHANGELOG.md` and the versioned analysis manifests.

## Novelty-audit boundary

The public repository contains the dated queries, counts, screening decisions, and audit report. Bulk API inventories containing full abstracts are retained in the private audit archive and are not redistributed here. The audit conclusion is deliberately bounded: the exact design conjunction was not detected in the searched sources as of 2026-08-02; this is not proof that no unpublished or unindexed study exists.

## Citation

Use `CITATION.cff` and cite the immutable version 1.0.7 archive [doi:10.5281/zenodo.21883676](https://doi.org/10.5281/zenodo.21883676). The concept DOI [doi:10.5281/zenodo.21761953](https://doi.org/10.5281/zenodo.21761953) resolves to the latest archived software version. The manuscript DOI will be added when available.

## License

Original analysis code and documentation are released under the [MIT License](LICENSE). The data providers' terms remain controlling for MIMIC-IV and eICU-CRD and are not altered by this code license.

## Contact

Peng Cheng, Department of Neurology, The Second Qilu Hospital of Shandong University: sducp@email.sdu.edu.cn
