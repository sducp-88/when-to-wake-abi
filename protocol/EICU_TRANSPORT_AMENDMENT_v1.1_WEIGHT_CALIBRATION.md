# WHEN-TO-WAKE ABI eICU Transport Amendment v1.1

Date: 2026-08-02  
Status: frozen before the formal 1,000-replicate transport run

## Trigger

The prespecified eICU transport model passed classifiability, weight-tail, and
effective-sample-size gates but had a maximum absolute weighted standardized mean
difference of 0.1097, marginally above the frozen 0.10 balance gate. The largest
imbalances involved the number of baseline sedative classes and baseline ICP.

## Frozen correction

1. Retain the v1.0 separate logistic adherence models by strategy and interval,
   `C=10`, probability clipping at 0.005/0.995, and within-strategy 1st/99th
   percentile truncation.
2. After truncation, apply iterative proportional fitting separately within each
   assigned strategy so that retained-clone weights reproduce the complete
   eligible-decision-point margins for:
   - baseline core-sedative class count;
   - baseline ICP category: missing, at most 10, 10-15, 15-20, or above 20 mm Hg;
   - baseline FiO2 category: at most 0.30, 0.30-0.40, 0.40-0.50, or above 0.50.
3. Run 30 deterministic raking cycles and rescale calibrated weights to preserve
   the strategy-specific pre-calibration weight sum.
4. Do not use outcome status, future ventilation status, or effect estimates in
   calibration.
5. Keep all eICU exposure, eligibility, temporal-ordering, outcome, and
   interpretation definitions unchanged.

## Preformal diagnostic

The selected calibration reduced the maximum absolute weighted SMD to 0.0852.
The calibrated maximum weights were 5.84 and 3.06, and ESS ratios were 0.777 and
0.853 for continued sedation and early de-escalation, respectively. A 10-replicate
two-process cluster-bootstrap smoke test converged in all replicates.

Pooled, more weakly regularized, high-dimensional center, and uncalibrated models
remain quarantined as development diagnostics. Selection of the calibrated model
was based on the frozen balance and weight gates, not on the transport effect.

## Formal label

All confirmatory eICU transport outputs must use `transport_v1_1_calibrated`.
Files containing `debug` are excluded from manuscript-facing artifacts.
