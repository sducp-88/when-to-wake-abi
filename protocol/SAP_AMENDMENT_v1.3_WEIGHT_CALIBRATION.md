# WHEN-TO-WAKE ABI Statistical Analysis Plan Amendment v1.3

Date: 2026-08-02  
Status: frozen before the formal 1,000-replicate inferential run  
Scope: artificial-censoring weight calibration in the MIMIC-IV primary analysis

## Diagnostic trigger

The terminal-aware v1.2 smoke test passed execution, weight-tail, and effective
sample-size checks but did not pass the prespecified covariate-balance gate when
one pooled adherence model was used for both assigned strategies. The maximum
absolute weighted standardized mean difference was 0.272. This failure was
diagnostic of insufficient treatment-by-covariate flexibility, not a clinical
effect conclusion.

## Frozen calibration model

1. Fit a separate denominator adherence model for every combination of assigned
   strategy and six-hour interval (eight models in total).
2. Each denominator model uses the v1.0/v1.1 frozen baseline and time-updated
   covariate set. Continuous covariates are median-imputed with missingness
   indicators and standardized; categorical covariates are mode-imputed and
   one-hot encoded.
3. Use logistic regression with L2 regularization (`C=10`), probability clipping
   at 0.005 and 0.995, and no data-driven outcome term.
4. The stabilizing numerator is the marginal observed adherence probability
   within the same assigned-strategy and interval stratum. It contains no patient
   baseline covariates.
5. Accumulate stabilized artificial-censoring weights only while the clone is at
   risk for adherence assessment. Apply the frozen within-strategy 1st/99th
   percentile truncation to retained-clone weights.
6. Keep the terminal-state and grace-period rules from v1.2 unchanged.
7. Use unique ICU-stay copy identifiers in the whole-stay cluster bootstrap.

## Preformal diagnostic result

The selected calibration passed the frozen diagnostics before confidence-interval
estimation: maximum absolute weighted standardized mean difference 0.0988;
strategy-specific truncated-weight maxima 1.95 and 2.37; effective-sample-size
ratios 0.943 and 0.876. The later-interval early-strategy model showed some
predicted probabilities at the upper clipping boundary, but the weight-tail and
effective-sample-size gates remained satisfactory. This feature must be reported
as a positivity/model diagnostic and evaluated in sensitivity analyses.

Alternative exploratory calibration attempts, including pooled models, stronger
regularization, and extra categorical flexibility for time and PEEP, remain
quarantined as development diagnostics. They are not selected using the effect
estimate and must not replace the frozen v1.3 primary model after the formal run.

## Formal run label

All confirmatory MIMIC-IV output files must use the label `primary_v1_3`. Debug
output families containing `debug` are excluded from manuscript-facing artifacts.
