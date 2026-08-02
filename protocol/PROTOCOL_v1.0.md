# WHEN-TO-WAKE ABI Protocol v1.0

Frozen: 2026-08-02  
Study type: retrospective, multi-database, sequential target-trial emulation  
Status at freeze: feasibility and novelty audits completed; treatment-effect outcomes not opened.

## 1. Title

Sedation De-escalation After Physiologic Stabilization in Mechanically Ventilated Adults With Acute Brain Injury: A Two-Cohort Sequential Target-Trial Emulation

## 2. Objective

To estimate the per-protocol effect of initiating multidrug sedation de-escalation within 6 hours after an eligible physiologic-stability decision point, compared with not initiating de-escalation for 24 hours, on being alive and successfully extubated by day 7 among mechanically ventilated adults with acute structural brain injury (ABI).

## 3. Data-source roles

- **MIMIC-IV v3.1:** primary causal analysis and complete interval-based exposure/outcome reconstruction.
- **eICU-CRD v2.0:** transport replication using a harmonized relative-dose rule; analyses requiring continuous pause intervals or exact reintubation sequences are conditional on validation.
- **HiRID v1.1.1:** optional high-time-resolution validation only after contributor approval and variable-compatibility review. Its availability is not required for the primary paper.
- Patient-level data will not be pooled across databases. Each database will be analyzed independently.

## 4. Target trial specification

| Component | Specification |
|---|---|
| Eligibility | Adult, first ICU stay, acute structural ABI, invasive ventilation, active numeric-rate core sedative, repeated physiologic-stability criteria met |
| Treatment strategies | Initiate sedation de-escalation within 6 hours vs do not initiate de-escalation for 24 hours |
| Assignment | Emulated by cloning to both strategies, artificial censoring at deviation, and inverse-probability weighting |
| Time zero | Each eligible 6-hour decision grid from 12 through 96 hours after invasive ventilation starts |
| Grace period | 6 hours for the early-de-escalation strategy |
| Adherence period | 24 hours after time zero or until death, extubation, tracheostomy, ICU discharge, or database end |
| Follow-up | Time zero through day 7 for the primary estimand; observe through day 9 to ascertain 48-hour reintubation after a day-7 extubation |
| Primary outcome | Alive and successfully extubated by day 7; successful means no reintubation or renewed invasive ventilation within 48 hours |
| Causal contrast | Per-protocol risk difference and risk ratio at day 7 |
| Analysis | Weighted pooled logistic outcome model with standardized risks; patient-clustered bootstrap inference |

## 5. Study population

### 5.1 Inclusion

1. Age 18 years or older.
2. First recorded ICU stay for the patient in the database.
3. Acute structural ABI identified from diagnosis and procedure data: traumatic brain injury, intracerebral hemorrhage, aneurysmal/nontraumatic subarachnoid hemorrhage, or acute ischemic stroke.
4. An invasive ventilation episode overlapping the ICU stay.
5. At least one continuous core sedative infusion after ventilation begins.

### 5.2 Exclusion

1. Cardiac-arrest/hypoxic-ischemic brain injury as the principal neurologic condition.
2. Principal admission for toxic/metabolic encephalopathy or routine postoperative observation without acute structural ABI.
3. Refractory status epilepticus or active therapeutic barbiturate coma at time zero.
4. Comfort-only care, organ-donation pathway, or documented withdrawal-only treatment goal before time zero when reliably measurable.
5. ICU stay shorter than 24 hours.
6. Missing ventilation start time or internally invalid time ordering that cannot be resolved by the prespecified episode algorithm.

## 6. Sequential eligibility and time zero

Candidate decision grids occur every 6 hours from 12 through 96 hours after the beginning of the first invasive ventilation episode in the first ICU stay. A patient may contribute multiple eligible emulated trials.

At a candidate grid, all of the following must hold:

1. Invasive ventilation is ongoing.
2. At least one of propofol, midazolam, or dexmedetomidine has a numeric infusion rate active at or observed within the preceding 2 hours and has been used during the preceding 6 hours.
3. At least one neurologic assessment (GCS total/component or RASS) is recorded within the preceding 6 hours; a specific score is not required.
4. Median MAP in the preceding 2 hours is at least 65 mm Hg and the minimum observed MAP is at least 60 mm Hg.
5. Latest FiO2 is no greater than 0.60 and latest PEEP is no greater than 10 cm H2O, using values from the preceding 6 hours.
6. No neuromuscular-blocking agent is active or administered during the preceding 2 hours.
7. No barbiturate coma, active refractory status-epilepticus treatment, or new hyperosmolar rescue treatment is recorded during the preceding 6 hours.
8. If ICP is measured, the latest value is no greater than 22 mm Hg and there is no sustained value above 22 mm Hg during the preceding 2 hours. Absence of ICP monitoring does not itself exclude a patient.
9. The patient has not already been extubated or tracheostomized.
10. Where spontaneous-breathing-trial (SBT) or explicit extubation-readiness data are available, no successful SBT/readiness decision has occurred before time zero. A separate sensitivity analysis excludes any SBT evidence in the preceding 6 hours.

The primary common stability definition uses observable MAP, FiO2, PEEP, neurologic-record availability, and absence of rescue treatments. A MIMIC-IV strict-stability sensitivity analysis additionally requires no new vasopressor and no increase in norepinephrine-equivalent dose during the preceding 2 hours. eICU point-record absence is not interpreted as proof of no vasopressor.

## 7. Treatment strategies

### 7.1 Core sedative vector

The treatment vector consists of propofol, midazolam, and dexmedetomidine. Opioids remain analgesic/time-varying confounder variables and are not counted as core hypnotic de-escalation drugs. Ketamine and barbiturates are handled as rescue/co-sedative variables because cross-database exposure is sparse or clinically heterogeneous.

Each drug is evaluated relative to its own database-native numeric rate. Absolute rates are not pooled across drugs or databases, and eICU mL/h records are not converted with assumed standard concentrations.

### 7.2 Initiate early de-escalation

Within the 6-hour grace period:

- at least one active core sedative decreases by at least 30% from its time-zero reference rate or stops;
- no other active core sedative increases by at least 30%; and
- no new core sedative starts.

After the qualifying action, the reduced regimen may remain stable, be reduced further, or stop during the 24-hour adherence period. Re-escalation by at least 30% above the post-action reference or starting a new core sedative is a deviation unless it follows a prespecified rescue condition; rescue is recorded and the clone is censored for the per-protocol contrast.

### 7.3 Continue without de-escalation

No active core sedative decreases by at least 30% or stops during the first 24 hours after time zero. Minor titration below 30% is compatible. A new drug or dose escalation remains compatible with “no de-escalation” but is modeled in the adherence process and described separately.

### 7.4 Complete interruption subtype

All core sedatives absent continuously for at least 2 hours is a prespecified subtype/sensitivity analysis in MIMIC-IV. It is not the cross-database primary exposure because eICU point records cannot establish continuous absence.

## 8. Outcomes

### 8.1 Primary

Alive and successfully extubated by day 7 after time zero. Extubation is successful if no reintubation or renewed invasive ventilation occurs within 48 hours. Death before successful extubation, tracheostomy before successful extubation, or continued invasive ventilation at day 7 is coded as not achieving the primary outcome.

### 8.2 Secondary

1. Successful extubation by day 14.
2. Ventilator-free days through day 28, with death assigned zero.
3. Reintubation/renewed invasive ventilation within 48 hours of first extubation.
4. Tracheostomy by day 14.
5. ICU mortality and in-hospital mortality.
6. ICU and hospital length of stay, interpreted with competing-event limitations.

For eICU, the primary transport outcome requires a validated episode sequence. If exact reintubation cannot meet the prespecified validation gate, eICU will report alive and off invasive ventilation by day 7 as a non-equivalent transport endpoint, clearly labeled and not pooled with the MIMIC-IV primary effect.

## 9. Confounding control

### 9.1 Baseline

Age, sex, calendar year, ICU type, admission type, ABI subtype, comorbidity burden, illness-severity score, hospital/site where applicable, pre-ICU ventilation, and documented treatment limitations.

### 9.2 Time-varying history before and during adherence

GCS total/components, RASS, pupil reactivity when available, ICP/CPP when available, MAP and other vital signs, vasopressor intensity/observation, FiO2, PEEP, ventilator mode, PaO2/FiO2, PaCO2, lactate, creatinine, bilirubin, temperature, cumulative and current core-sedative rates, opioid rates, ketamine, antipsychotics, antiseizure/rescue therapy, hyperosmolar therapy, neuromuscular blockade, SBT/airway-readiness evidence, and time since last measurement.

Variables measured after a treatment action are used only in adherence/censoring models for subsequent time intervals, not as baseline confounders for the initial action.

## 10. Missing data and measurement

- Treatment, ventilation, extubation, reintubation, death, and strategy adherence are never imputed.
- Vital signs are summarized from observed records; no observation is not treated as physiologic normality.
- Limited carry-forward is prespecified: 6 hours for ventilation/neuro measurements and 24 hours for laboratory measurements, always accompanied by time-since-last-observation and missingness indicators.
- Baseline covariates may use database-specific multiple imputation if missingness exceeds 5%; imputation is performed within database and bootstrap replicate where computationally feasible.
- All data-source-specific concept mappings are versioned in the common data model and mapping tables.

## 11. Analysis overview

Each eligible grid creates a nested trial. Records are cloned to both strategies, censored when observed treatment becomes incompatible, and weighted by the inverse probability of remaining adherent. Weighted discrete-time outcome models estimate strategy-specific standardized risks at day 7. Uncertainty is obtained by patient-clustered bootstrap; eICU additionally uses a hospital-cluster sensitivity bootstrap.

MIMIC-IV is the primary analysis. eICU is analyzed independently as transport replication. Pooling is exploratory and allowed only if the exposure and outcome pass harmonization gates.

## 12. Validation gates

Before reporting an effect:

1. Infusion start/stop/rate timeline audit positive predictive value at least 85% in a structured sample.
2. Ventilation/extubation/reintubation invalid ordering below 5% after the validated episode algorithm.
3. Both strategies at least 10% of classifiable stable grids overall and at least 5% in each major grid-time stratum.
4. Stabilized weight 99th percentile below 10 and maximum below 20 after prespecified truncation.
5. Weighted effective sample size at least 50% of the uncensored clone sample.
6. Absolute standardized mean differences below 0.10 for prespecified covariates after weighting, with exceptions reported rather than hidden.

Failure triggers a prespecified diagnostic/sensitivity pathway, not outcome-directed alteration of the 30% threshold.

## 13. Prespecified sensitivity and subgroup analyses

- 20% and 40% relative reduction thresholds.
- 12-hour grace period.
- Complete ≥2-hour interruption in MIMIC-IV.
- First eligible trial per patient only.
- Strict stability including non-increasing vasopressor support in MIMIC-IV.
- Exclusion of recent SBT/readiness evidence.
- Weight truncation at 1st/99th and 0.5th/99.5th percentiles.
- Alternative limited carry-forward windows and measurement-complete analysis.
- ABI subtype: TBI, ICH, SAH, and AIS.
- Early (12–36 h), middle (>36–60 h), and late (>60–96 h) decision windows.
- Baseline neurologic severity and invasive ICP monitoring status.

Subgroup results are interaction estimates with uncertainty, not separate significance claims.

## 14. Ethics and governance

Only deidentified public/credentialed databases are used under their data-use agreements. Raw data and patient-level derivatives remain in the restricted local directory. Outputs leaving that directory must satisfy cell-size and disclosure review. No patient-level record will be uploaded to chat, public cloud storage, or an unauthorized AI service.

## 15. Freeze rule

Protocol v1.0, SAP v1.0, configuration v1.0, and common data model v1.0 will be hashed together. Any subsequent change requires a dated amendment specifying whether outcome data had been opened. No effect estimate may be examined before the freeze manifest is created.
