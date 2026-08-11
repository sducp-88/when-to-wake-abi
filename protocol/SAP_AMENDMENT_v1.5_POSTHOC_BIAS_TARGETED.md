# WHEN-TO-WAKE ABI Statistical Analysis Plan Amendment v1.5

Date: 2026-08-11
Status: post hoc, defined after the Critical Care editorial decision and before running the analyses described below
Scope: MIMIC-IV bias-targeted sensitivity analyses only

## Reason for amendment

The primary v1.3 analysis adjusted for measured physiologic and neurologic state at each adherence boundary, but it did not explicitly include the direction of change during the six hours before a decision or drug-specific baseline infusion rates. The editorial decision raised the central interpretability concern that clinicians may have de-escalated sedation because a patient was already improving. This amendment targets that specific residual-confounding mechanism. Because the primary outcome has already been examined, these analyses are explicitly post hoc and cannot replace the frozen v1.3 primary estimand.

## Fixed bias-targeted model

1. Reconstruct the same MIMIC-IV eligible decision points, treatment strategies, temporal-precedence rule, terminal-aware clone censoring, outcome, and 1st/99th-percentile weight truncation used in v1.3.
2. Add drug-specific baseline infusion rates and documented rate units for propofol, midazolam, and dexmedetomidine. Rates are transformed as `log1p(rate)` and rate units enter as categorical covariates; a missing rate for an inactive drug is represented as zero with the existing active-drug indicator retained.
3. At each adherence boundary, add six-hour changes in MAP median, MAP minimum, heart rate, FiO2, PEEP, RASS, GCS motor, GCS eye, GCS verbal, latest ICP, and neurologic measurement count. Also add the preceding-window indicators for vasopressor, opioid, and ketamine exposure.
4. Use the same strategy-by-interval logistic adherence models, probability clipping, marginal numerator, whole-stay bootstrap, and diagnostic gates as v1.3.
5. Run a stay-balanced sensitivity analysis by multiplying each retained clone weight by the inverse of the number of eligible decision points contributed by its ICU stay. This changes the target from the eligible-decision distribution toward equal ICU-stay contribution and addresses overrepresentation by longer stays.
6. Report the original v1.3 analysis as primary. Report this amendment only as a bias-targeted sensitivity analysis, regardless of direction or statistical precision.

## Interpretation rule

- If the trajectory- and dose-augmented estimate materially attenuates, the manuscript will emphasize confounding by predecision improvement.
- If it remains similar, the analysis will be described as reducing measured trajectory imbalance, not as eliminating confounding by clinician intent, unmeasured neurologic safety goals, procedures, airway concerns, or goals of care.
- The eICU transport analysis will not be re-engineered to mimic these features because its point-record infusion architecture and non-equivalent outcome do not support the same trajectory operator.

## Non-negotiable reporting

The amendment date, post hoc status, reason, covariate set, missingness, balance, weight tails, effective sample size, and all effect estimates will be included in the supplementary material. No result from this amendment will be relabeled as prespecified or confirmatory.
