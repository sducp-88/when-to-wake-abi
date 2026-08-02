# WHEN-TO-WAKE ABI Statistical Analysis Plan Amendment v1.2

Date: 2026-08-02  
Status: frozen before the formal inferential run  
Scope: MIMIC-IV primary sequential target-trial emulation

## Reason for amendment

The v1.1 debug implementation retained only clones that remained observable and
adherent through the entire 24-hour strategy window. This implementation would
exclude a clone when extubation, death, tracheostomy, or ICU discharge occurred
before 24 hours, even though the intervention strategy is no longer applicable
after that terminal state. The resulting conditioning on post-baseline events can
induce selection bias.

The 10-replicate debug output is therefore classified as a software-validation
artifact only. It is not a confirmatory analysis and must not be used in the
manuscript, figures, tables, abstract, or clinical interpretation.

## Frozen correction

1. The intervention strategy ends at the earliest of first extubation, death,
   tracheostomy, or ICU discharge.
2. Adherence is evaluated at six-hour boundaries only while the clone remains
   under the intervention strategy.
3. If a strategy-terminal event occurs before the next six-hour boundary, no
   later boundary adherence is required and the clone is retained with the
   cumulative artificial-censoring weight accrued up to that point.
4. During the first six-hour grace period, both clones remain compatible until a
   temporally valid early de-escalation occurs or the strategy-terminal event
   occurs. If a valid early action occurs first, the early clone remains adherent
   and the continued-sedation clone is artificially censored.
5. The v1.1 temporal precedence rule remains unchanged: an action must precede a
   recorded successful spontaneous-breathing trial and must lead explicit
   extubation by at least 60 minutes to qualify as primary early de-escalation.
6. The intervention definitions, eligibility criteria, primary outcome, day-7
   horizon, 48-hour reintubation rule, covariates, weight truncation, and
   patient-cluster bootstrap remain unchanged.
7. Bootstrap resampling assigns a unique copy identifier to every sampled ICU
   stay so that repeated bootstrap multiplicities cannot share cumulative-weight
   histories.

## Primary estimand after correction

The primary estimand remains the standardized risk difference and risk ratio for
being alive and successfully extubated by day 7 under early sedation
de-escalation versus continued sedation, averaged over eligible six-hour decision
points in MIMIC-IV. Inference uses stabilized inverse-probability-of-artificial-
censoring weights and a whole-ICU-stay cluster bootstrap.

## Audit rule

All formal outputs must use an explicit `v1_2_terminal_aware` run label. Files
with the `debug10_v1_1` label are quarantined as noninferential development
artifacts. Any later modification to this correction requires a new numbered
amendment and an updated SHA-256 freeze manifest.
