# WHEN-TO-WAKE ABI v1.0.7

Release date: 2026-08-11

Zenodo concept DOI: https://doi.org/10.5281/zenodo.21761953

Immutable version DOI: https://doi.org/10.5281/zenodo.21883676

This release accompanies the reconstructed manuscript titled “Stability-Triggered Sedation De-escalation and Day-7 Ventilator Liberation After Acute Brain Injury: A Sequential Target-Trial Emulation”.

## Added

- post hoc MIMIC-IV trajectory-and-baseline-dose analysis;
- whole-stay 200-sample bootstrap distribution and aggregate diagnostics;
- stay-balanced target-population diagnostic;
- revised publication figures and manuscript-facing aggregate tables;
- SAP amendment v1.5 documenting the bias-targeted analysis.

## Interpretation boundary

The trajectory-and-dose model narrowly missed the prespecified maximum-balance threshold (maximum weighted absolute standardized mean difference 0.102). The stay-balanced analysis failed balance and effective-sample-size gates and remains diagnostic only. Neither result replaces the frozen primary estimate.

## Identifier reconciliation

The local implementation initially used a `v1_4` working label. Because the public project already used SAP amendment v1.4 for severity measurement, this release candidate normalizes the new post hoc amendment, code, and aggregate-output labels to v1.5. This is a naming correction only; numeric outputs are unchanged.

## Approval and data boundary

All authors approved the revised manuscript, code additions, aggregate outputs, figures, CRediT statement, declarations, AI disclosure, MIT License, GitHub release, and Zenodo archival on 2026-08-11. The release contains aggregate outputs only and no MIMIC-IV or eICU-CRD patient-level records or derivatives. Zenodo archived this release under immutable DOI 10.5281/zenodo.21883676.
