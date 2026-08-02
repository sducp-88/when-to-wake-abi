# WHEN-TO-WAKE ABI Statistical Analysis Plan v1.0

Frozen: 2026-08-02  
Protocol: `PROTOCOL_v1.0.md`  
Primary database: MIMIC-IV v3.1  
Transport database: eICU-CRD v2.0

## 1. Analysis populations

1. **Source ABI cohort:** all patients meeting baseline inclusion/exclusion criteria.
2. **Candidate-grid cohort:** all 6-hour grids from 12 through 96 hours after ventilation starts.
3. **Stable eligible-grid cohort (primary):** candidate grids meeting all common stability criteria and with a numeric core-sedative baseline rate.
4. **Measurement-complete cohort:** eligible grids with all MAP, FiO2, PEEP, neurologic, and core treatment histories observed without carry-forward beyond their permitted windows.
5. **First-trial cohort:** first eligible grid per patient.

The primary MIMIC-IV analysis uses all stable eligible grids. Patients may enter multiple sequential trials; inference is clustered by patient.

## 2. Time structure

- Trial time zero: an eligible 6-hour grid.
- Treatment grace period: (0, 6] hours.
- Adherence intervals: 0–6, >6–12, >12–18, and >18–24 hours.
- Outcome intervals: 6-hour intervals through day 7.
- Reintubation ascertainment: through 48 hours after extubation, including follow-up through day 9 for an extubation occurring on day 7.

## 3. Cloning, censoring, and weighting

At each time zero, create two clones assigned to:

- `A=1`: initiate de-escalation within 6 hours and remain on the reduced/no-core regimen for 24 hours;
- `A=0`: do not de-escalate for 24 hours.

Artificially censor a clone at the first interval when observed treatment is incompatible with its assigned strategy. Natural censoring occurs at database end or loss of follow-up; death, extubation, tracheostomy, and discharge are outcomes/competing events as defined and are not treated as arbitrary loss.

Estimate interval-specific adherence probabilities separately by assigned strategy and database:

`P(C_k=0 | C_(k-1)=0, A, baseline covariates, time-varying history through k)`

The stabilized artificial-censoring weight through interval K is:

`SW_K = product_k numerator_k / denominator_k`

The numerator includes strategy, trial-start time, ABI subtype, baseline neurologic severity, baseline core-sedative vector, age, sex, and site/ICU strata. The denominator additionally includes updated physiologic, neurologic, ventilation, medication, rescue-therapy, and observation-process variables.

Primary adherence models use pooled logistic regression with restricted cubic splines for continuous variables, prespecified nonlinearities, strategy-specific terms, and trial-time terms. A cross-fitted gradient-boosted classification sensitivity analysis may be used if it improves calibration without violating positivity.

## 4. Outcome model and estimands

Fit a weighted pooled logistic model for the interval probability of achieving first successful extubation, including assigned strategy, flexible follow-up time, strategy-by-time interaction, trial-start time, and database-specific baseline stratification terms. Death before successful extubation remains a failure for the binary day-7 estimand.

From the fitted model, standardize over the eligible-grid population to estimate:

- day-7 risk under early de-escalation, `Risk_1`;
- day-7 risk under continued sedation, `Risk_0`;
- risk difference, `Risk_1 - Risk_0`;
- risk ratio, `Risk_1 / Risk_0`.

Report absolute risks and 95% confidence intervals before relative effects. The primary effect is the MIMIC-IV per-protocol risk difference.

Secondary time-to-event analyses use cause-specific/weighted cumulative-incidence descriptions with death as competing event; they do not replace the binary primary estimand.

## 5. Variance and repeated trials

Use 1,000 patient-level nonparametric bootstrap replicates for the primary 95% percentile confidence intervals, resampling patients and retaining all of their stays, grids, clones, and intervals. If fewer than 950 replicates converge, report the convergence count and use a robust patient-clustered sandwich interval as a clearly labeled backup.

For eICU, the primary transport interval clusters by patient; a sensitivity bootstrap resamples hospitals first and patients within hospital.

## 6. Covariate specification

### 6.1 Fixed/baseline

- age with restricted cubic spline;
- sex;
- ABI subtype;
- admission type and ICU type;
- calendar period;
- database-specific illness severity (MIMIC: harmonized SOFA/SAPS components; eICU: APACHE score/components);
- comorbidity burden;
- documented treatment limitation;
- hospital/site in eICU;
- hours from ventilation start to trial time zero;
- baseline core-sedative drug pattern and cumulative exposure.

### 6.2 Time-varying history

- latest/mean/minimum MAP and vasopressor observation/intensity;
- latest FiO2, PEEP, ventilator mode, oxygenation, PaCO2;
- latest/worst GCS total and motor, latest RASS, pupil reactivity where available;
- ICP/CPP where measured;
- temperature, lactate, creatinine, bilirubin;
- current and cumulative propofol, midazolam, dexmedetomidine, ketamine, and opioid exposure;
- neuromuscular blockade, hyperosmolar therapy, antiseizure/rescue therapy, antipsychotic use;
- SBT/readiness evidence;
- time since last observation and missingness indicators.

No automated univariable screening will remove prespecified confounders.

## 7. Missingness

- No imputation for treatment, adherence, ventilation episodes, extubation, reintubation, tracheostomy, or death.
- Physiologic summaries use only observed data within prespecified windows.
- Permitted carry-forward: at most 6 hours for neuro/ventilation measurements and 24 hours for laboratory measurements.
- Include time-since-last-measurement and missingness indicators in adherence models.
- If a baseline covariate has more than 5% missingness, perform chained-equation multiple imputation within database (20 datasets) as a sensitivity analysis; the primary pragmatic time-series model uses explicit missingness indicators.

## 8. Positivity, calibration, and balance diagnostics

Before interpreting an effect, report by strategy and grid-time stratum:

- observed compatibility proportions;
- predicted adherence probability distribution;
- stabilized-weight median, IQR, 1st, 5th, 95th, 99th percentiles, and maximum;
- proportion truncated;
- effective sample size `ESS=(sum w)^2/sum(w^2)` and ESS ratio;
- weighted standardized mean differences for every model covariate;
- calibration slope/intercept and Brier score for adherence models.

Primary truncation is at the 1st and 99th percentiles within strategy. The predeclared warning gates are p99 ≥10, maximum ≥20, ESS ratio <0.50, or any major covariate absolute SMD ≥0.10. If triggered, report the failure and run the 0.5th/99.5th sensitivity; do not choose thresholds based on favorable outcomes.

## 9. Database-specific estimation and transport

1. Fit all mapping, adherence, and outcome models independently in MIMIC-IV and eICU.
2. Report eICU measurement differences, particularly mL/h conversion gaps, point-record pause limitations, and respiratoryCare sequence limitations.
3. Compare effect direction, absolute risk scale, covariate balance, and support rather than using a pass/fail replication P value.
4. An exploratory inverse-variance random-effects summary may be shown only if the same exposure and primary outcome pass the harmonization gates. With only two databases, heterogeneity estimates will be described as imprecise.

## 10. Secondary analyses

- Day-14 successful extubation risk difference/risk ratio.
- Day-28 ventilator-free days using weighted mean difference, death assigned zero.
- Reintubation within 48 hours among extubated patients, explicitly labeled as a selected post-treatment population.
- Tracheostomy by day 14 with death as competing event.
- ICU/hospital mortality and lengths of stay as secondary association estimates.

## 11. Sensitivity analyses

1. De-escalation thresholds 20% and 40%.
2. Grace period 12 hours.
3. Complete ≥2-hour interruption in MIMIC-IV.
4. First eligible trial only.
5. Strict MIMIC stability with non-increasing vasopressor support.
6. Exclude recent SBT/readiness evidence.
7. Measurement-complete cohort.
8. Weight truncation at 0.5th/99.5th percentiles and no truncation.
9. Gradient-boosted cross-fitted adherence model.
10. Alternative successful-extubation definition using 72-hour reintubation window.
11. Exclude comfort-limitation transitions within the first 24 hours when reliably measured.

## 12. Effect modification

Estimate interaction contrasts for ABI subtype, decision-window timing, baseline neurologic severity, invasive ICP monitoring, age (<65 vs ≥65), and baseline sedative pattern. Report subgroup-specific absolute risks with interaction confidence intervals. These analyses are exploratory and multiplicity-aware; no subgroup is declared definitive from within-subgroup P values.

## 13. Falsification and robustness checks

- Verify that assigned strategies do not predict events timestamped before time zero after weighting.
- Repeat exposure classification after shifting treatment records by a small negative/positive tolerance permitted by source timestamp resolution; large effect instability indicates immortal-time or ordering error.
- Audit impossible sequences, duplicate events, and treatment entries outside ICU/ventilation bounds.
- Compare first-trial and repeated-trial estimates to assess overrepresentation by long stays.

## 14. Reporting

Use the TARGET statement where applicable, RECORD/STROBE, and a target-trial specification table. Report cohort flow, missingness, support, weights, balance, model calibration, and every prespecified sensitivity analysis. Do not describe observational estimates as randomized or proven causal.

## 15. Outcome-opening lock

No primary or secondary strategy-outcome comparison may be run until the protocol, SAP, configuration, common data model, and their SHA256 manifest are present in `02_protocol_and_registration/freeze_v1.0/`. Any later amendment must state whether outcome data had been opened.
