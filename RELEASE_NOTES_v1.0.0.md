# WHEN-TO-WAKE ABI v1.0.0

This is the frozen initial software release accompanying the manuscript:

> Early Sedation De-escalation After Physiologic Stabilization and Day-7 Ventilator Liberation in Acute Brain Injury: A Two-Cohort Sequential Target-Trial Emulation

## Included

- cohort-construction, quality-assurance, estimation, sensitivity-analysis, and figure code;
- the versioned protocol, statistical analysis plan, amendments, freeze manifests, causal diagram, and common data model;
- disclosure-reviewed aggregate estimates and bootstrap distributions;
- dated literature queries, screening decisions, and the bounded novelty audit;
- terminal-aware cloning-censoring-weighting unit tests and a machine-readable public-release QA report.

## Frozen findings represented by the aggregate outputs

- MIMIC-IV: 9,830 eligible decision grids from 2,027 ICU stays; estimated day-7 successful-extubation risk was 50.2% under early sedation de-escalation and 42.5% under continued sedation (risk difference, 7.7 percentage points; 95% CI, 4.4 to 11.0; risk ratio, 1.18; 95% CI, 1.10 to 1.27).
- eICU-CRD transport analysis: 2,964 eligible grids from 657 ICU stays; risk difference, 3.2 percentage points (95% CI, -2.9 to 10.4).

The eICU-CRD analysis uses a non-equivalent ventilation-end proxy and is therefore a measurement-aware transport analysis, not exact external validation. These are observational estimates and do not establish a causal treatment recommendation.

## Data boundary

No patient-level source records or derivatives are included. MIMIC-IV and eICU-CRD remain credentialed PhysioNet resources and must be obtained independently under their applicable data-use requirements.

## License and citation

Code and repository-authored documentation are released under the MIT License. The PhysioNet source databases remain governed by their own terms. Cite the archived Zenodo release and the accompanying manuscript when available; citation metadata are provided in `.zenodo.json` and `CITATION.cff`.
