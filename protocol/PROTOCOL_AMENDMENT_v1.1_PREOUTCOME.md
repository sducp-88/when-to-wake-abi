# WHEN-TO-WAKE ABI Protocol Amendment v1.1 (Pre-outcome)

Created: 2026-08-02, Asia/Shanghai  
Outcome status: **no strategy-outcome comparison had been run or inspected.**  
Parent freeze: Protocol/SAP v1.0, freeze verification 5/5 passed.

## Reason

Source mapping confirmed that MIMIC-IV records explicit successful spontaneous-breathing-trial (SBT), extubation, invasive-ventilation interval, and sedative-infusion timestamps. A stop in sedation charted at extubation could represent completion of the extubation decision rather than an upstream decision to de-escalate. Without an explicit tie-breaking rule, reverse temporal classification could threaten the estimand.

## Amendment

1. The primary early-de-escalation classification requires the first qualifying ≥30% reduction/stop to occur:
   - strictly before any recorded successful SBT after time zero; and
   - at least 1 hour before explicit extubation.
2. A sedative stop/reduction simultaneous with or less than 1 hour before extubation is classified as `contemporaneous_weaning`, not as primary early de-escalation.
3. If an outcome and treatment change share a timestamp, the outcome is ordered first for strategy-adherence classification.
4. The primary MIMIC outcome uses explicit planned/unplanned extubation events plus explicit/new invasive-ventilation starts for 48-hour failure ascertainment.
5. A sensitivity analysis uses the end of a validated `Invasive Ventilation` procedure interval as the liberation event when no explicit extubation is present, after reporting alignment with explicit events.
6. Candidate time zeros with a successful SBT recorded in the prior 6 hours remain excluded. SBT occurring after a valid de-escalation action is allowed as a mediator and is not adjusted away in the outcome model.

## Impact on estimand

The clinical contrast is narrowed to an upstream sedation decision that precedes observed extubation-readiness testing or extubation, distinguishing it from the prompt-extubation target trial literature. The 30% threshold, 6-hour grace period, 24-hour adherence period, population, and day-7 outcome horizon are unchanged.

## Analysis implementation

- `first_qualifying_deescalation_time` is reconstructed from same-unit infusion rate changes and interval stops.
- `contemporaneous_weaning` grids are reported in the flow and excluded from the primary early strategy.
- Sensitivity analyses relax the extubation lead to 30 minutes and 2 hours.

This amendment was made from chronology and literature considerations only and not in response to an effect estimate.
