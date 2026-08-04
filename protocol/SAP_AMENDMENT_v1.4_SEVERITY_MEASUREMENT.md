# WHEN-TO-WAKE ABI SAP amendment v1.4: severity measurement correction and diagnostic

Date: 4 August 2026

Timing: after the primary MIMIC-IV and earlier eICU transport results were available. This is an outcome-visible data-quality correction and post hoc severity-confounding diagnostic. It does not alter the primary MIMIC-IV estimand, treatment strategies, outcome, or inference procedure.

## Trigger

External methodological review correctly emphasized confounding by indication: patients who cannot undergo sedation de-escalation may be more severely ill and may also be less likely to achieve ventilator liberation. Audit of the eICU neurologic extraction identified values below 3 in a field previously treated as GCS Total.

## eICU GCS correction

The eICU extraction is restricted to the exact combined label `Glasgow coma score GCS Total` and valid numeric values from 3 through 15. Values outside that range do not count as a valid neurologic observation. RASS continues to count only when it is within -5 through +4. The corrected analysis-ready dataset is version 1.1, and the resulting transport analysis is version 1.2. The earlier eICU transport estimate is superseded because its stability gate could be satisfied by invalid GCS values.

## APACHE IVa diagnostic

APACHE IVa total score and acute physiology score are joined at the ICU-stay level for an outcome-blind post-weight balance diagnostic. They are not added to the full eICU adherence model because candidate decisions begin at 12 hours and an APACHE first-day score can include information measured after an early decision.

## Time-valid sensitivity feasibility audit

An exploratory complete-case model restricted decisions to at least 1,440 minutes after ICU admission and added APACHE IVa score to the denominator model. This subset failed the prespecified maximum absolute weighted-SMD and minimum ESS-ratio gates. It is therefore classified as noninferential; no effect estimate from that model is reported.

## Reporting consequence

The manuscript reports the corrected eICU transport estimate, the APACHE/GCS severity-balance diagnostic, and the failed feasibility status of the time-valid APACHE sensitivity. The primary MIMIC-IV result remains unchanged. All claims remain associational, and residual unmeasured clinical severity is retained as a central limitation.
