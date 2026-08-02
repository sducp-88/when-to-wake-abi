# WHEN-TO-WAKE ABI eICU-CRD Transport Analysis Plan v1.0

Date: 2026-08-02  
Status: frozen before any eICU strategy-outcome contrast  
Role: measurement-aware transport analysis, not exact replication

## Rationale

eICU-CRD records sedative infusions as timestamped point observations and
ventilation history through current/prior respiratory-care intervals. It cannot
reproduce MIMIC-IV continuous infusion gaps, explicit extubation procedure events,
or the exact spontaneous-breathing-trial temporal rule. The eICU analysis will
therefore test whether the direction and approximate magnitude of the MIMIC-IV
association transport under a database-specific measurement operator. It will not
be labeled external validation of an identical estimand.

## Population and decision times

- Adults aged at least 18 years in their first recorded ICU stay.
- Acute brain injury phenotype: traumatic brain injury, subarachnoid hemorrhage,
  intracerebral hemorrhage, or acute ischemic stroke from diagnosis text/ICD-9.
- Exclude stays with a primary hypoxic/anoxic or cardiac-arrest phenotype.
- Require a reconstructed invasive-ventilation interval and a numeric propofol,
  midazolam, or dexmedetomidine record.
- Generate decisions every six hours from 12 through 96 hours after the first
  reconstructed ventilation start, while the patient remains in the ICU and in a
  reconstructed ventilation interval.

## Stability eligibility

At each decision time require:

- median MAP at least 65 mm Hg and minimum MAP at least 60 mm Hg in the prior two
  hours;
- latest FiO2 at most 0.60 and PEEP at most 10 cm H2O in the prior six hours;
- at least one RASS or GCS observation in the prior six hours;
- no observed neuromuscular blocker in the prior two hours and no observed
  barbiturate or hyperosmolar therapy in the prior six hours;
- ICP at most 22 mm Hg when measured;
- no tracheostomy recorded before time zero.

Absence of an eICU point record is not interpreted as proof of absence. Required
physiologic and exposure fields must be observed; otherwise the decision point is
ineligible or unclassifiable as specified below.

## Database-specific strategies

Baseline sedative streams are the most recent positive numeric rate records within
the six hours before time zero, indexed by drug class, normalized drug label, and
rate field (`drugrate` or `infusionrate`).

- Early de-escalation: during the next six hours, at least one matching stream has
  a recorded rate at least 30% below baseline or an explicit zero, every baseline
  stream has at least one follow-up record, no matching stream increases at least
  30%, and no new core sedative class appears.
- Continued sedation: every baseline stream has at least one follow-up record,
  no stream decreases at least 30%, no stream increases at least 30%, and no new
  core sedative class appears.
- All other patterns are artificially censored as conflicting or unclassifiable.

The same compatibility rule is evaluated at each six-hour interval through 24
hours. Point-record gaps are never interpreted as a two-hour pause or a drug stop.

## Temporal ordering and outcome

The first qualifying rate reduction must precede the reconstructed ventilation end
by at least 60 minutes to qualify as primary early de-escalation. Because a reliable
SBT event is unavailable, the MIMIC-IV SBT precedence rule cannot be transported.

The transport outcome is being alive with a reconstructed ventilation end by day 7,
with no reconstructed renewed ventilation start in the following 48 hours and no
tracheostomy in that 48-hour window. This is a ventilation-end proxy, not explicit
successful extubation.

The intervention strategy ends at the earliest reconstructed ventilation end,
death, tracheostomy, or ICU discharge. Grace-period and terminal-aware cloning rules
follow MIMIC analysis version 1.3.

## Estimation and diagnostics

- Separate adherence models by assigned strategy and interval.
- Stabilized artificial-censoring weights with a marginal numerator within each
  strategy/interval stratum.
- Probability clipping 0.005/0.995 and within-strategy 1st/99th percentile
  truncation.
- Cluster bootstrap by ICU stay, 1,000 replicates.
- Required gates: both strategies 5%-95% at classifiable stable decisions; weight
  p99 below 10, maximum below 20, ESS ratio at least 0.50, and maximum absolute
  weighted SMD below 0.10.

## Interpretation ceiling

Agreement supports transport across two different ICU data-generating and
measurement systems. Disagreement may reflect measurement non-equivalence,
case-mix, care practices, or true effect heterogeneity; it must not automatically be
called biological contradiction. Cross-database pooled absolute dose effects and
formal statistical pooling are not permitted in the primary report.
