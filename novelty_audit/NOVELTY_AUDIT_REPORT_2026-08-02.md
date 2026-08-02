# WHEN-TO-WAKE ABI — Formal Novelty and Competing-Study Audit

Date searched: 2026-08-02  
Decision: **retain the topic, refine the estimand, and proceed to protocol/SAP freeze.**

## Working title after audit

**Sedation De-escalation After Physiologic Stabilization in Mechanically Ventilated Adults With Acute Brain Injury: A Two-Cohort Sequential Target-Trial Emulation**

## Search scope and audit trail

Three public discovery sources were searched with predefined layered terms and machine-readable snapshots:

1. PubMed via NCBI E-utilities: 316 unique PMIDs inventoried.
   - direct-repeat query: 7
   - neurological awakening/ABI query: 15
   - MIMIC/eICU sedation query: 99
   - target-trial sedation query: 45
   - time-varying sedation methods query: 2
   - ABI sedative-exposure query: 155
2. ClinicalTrials.gov API v2: 143 unique study records inventoried.
   - ABI sedation: 16
   - TBI sedation: 108
   - neurocritical sedation: 22
   - sedation interruption plus mechanical ventilation: 9
   - sedation de-escalation/weaning plus mechanical ventilation: 3
3. Europe PMC REST API: 7,412 unique records inventoried in a deliberately broad supplementary search.
   - direct dynamic ABI query: 123
   - target-trial ABI/sedation query: 128
   - public ICU database query: 7,188 (low specificity; retained as a broad companion-paper sweep)
   - sedation-trajectory query: 59
   - 305 records occurred in the direct/target-trial/trajectory layers; 55 non-PubMed or preprint records were title-screened.

The exact queries, retrieval timestamps, record inventories, abstracts where available, and screening decisions are preserved in `01_topic_report/novelty_audit/`. Search absence is interpreted as **“not detected in the searched sources on 2026-08-02,” not “never published.”**

## Direct-repeat finding

No study was detected that combined all of the following:

- mechanically ventilated adults with acute structural brain injury;
- repeated eligibility after a prespecified physiologic-stability state;
- a 6-hour clinical decision grid between 12 and 96 hours after invasive ventilation begins;
- an explicit multidrug strategy of relative sedative de-escalation versus continued sedation;
- adjustment for treatment-confounder feedback with a sequential target-trial/cloning-censoring-weighting design;
- a patient-centered short-horizon outcome of being alive and successfully extubated;
- primary estimation in MIMIC-IV with transport replication in eICU using a harmonized relative-dose rule.

This conjunction—not any single component—is the defensible novelty claim.

## Closest competing evidence

| Study | What it answers | Why it does not duplicate the proposed study | Design consequence |
|---|---|---|---|
| Early deep-to-light vs continuous light/deep sedation (PMID 39395660) | General-ICU sedation trajectories and mortality in ICU-HAI plus MIMIC | Coarse trajectory groups; not ABI-specific; no repeated stability-triggered decision | Explicitly contrast dynamic decision points with trajectory phenotyping |
| International 73-ICU ABI sedation cohort (PMID 39776348) | Initial day-1 drug choice and ventilation/outcomes | Initial regimen, not dose reduction timing | Include as main clinical gap comparator |
| MODERNISE (NCT02317497) | Fixed moderate vs deep sedation for 72 hours in cerebrovascular patients | Fixed randomized depth target, then stepwise weaning; status/results unresolved in targeted search | Do not frame the study as “light vs deep sedation” |
| Early neurological wake-up test cohort (PMID 27856146) and physiological NWT studies | Feasibility, failure, ICP/CPP and stress response | Small/TBI-focused; short-term physiology; no dynamic causal clinical outcome | Stability criteria must exclude active rescue physiology and acknowledge unmeasured ICP |
| Prompt extubation target-trial emulation (PMID 39585965) | Extubate on the same day after first successful SBT vs not | Begins after extubation readiness; sedation de-escalation is an upstream decision | Define time zero before an observed extubation-readiness decision and adjust/sensitize for SBT evidence |
| Dexmedetomidine target trial for agitation (PMID 40136231) | Initiate dexmedetomidine after agitation in a general ICU | Different trigger, intervention, population, and estimand | Supports feasibility of causal ICU sedation work but not a repeat |
| MIMIC/eICU drug-comparison papers | Static use of dexmedetomidine/propofol/midazolam and outcomes | Drug identity or combination, not strategy timing; conventional exposure definitions | Avoid drug-superiority claims; disclose cohort overlap |
| Longitudinal command-following study (PMID 42527816) | Recovery of motor command-following and its association with sedation | Descriptive state-transition analysis, not strategy effectiveness | Do not require a single “obeys commands” record for eligibility |
| Ongoing analgesia-first trauma/post-craniotomy studies (NCT05751863; NCT06727435) | Initial/no-hypnotic sedation strategies | Different populations and starting strategies | Keep opioids as time-varying confounders, not core de-escalation drugs |

## Novelty that is strong enough to carry the paper

1. **Decision-centered timing rather than drug-centered exposure.** The exposure is an actionable change in an existing regimen after stability, not “ever received drug X.”
2. **Sequential eligibility.** Each patient can contribute more than one emulated trial while clinical readiness evolves, avoiding an arbitrary single baseline.
3. **Treatment-confounder feedback.** Neurological and physiologic state can both influence and be influenced by prior sedation; the planned method addresses this explicitly.
4. **Separation from the extubation decision.** The study estimates an upstream sedation decision, whereas the closest ABI target trial begins after a successful spontaneous breathing trial.
5. **Cross-database measurement realism.** Relative within-drug changes are harmonized without assuming standard concentrations for eICU mL/h records; eICU pause analysis is conditional because point records cannot prove a two-hour interval.
6. **Patient-centered primary estimand.** Alive and successfully extubated by day 7 is more clinically interpretable than mortality alone or a single neurological assessment.

## Mandatory refinements before outcome opening

- Replace the vague phrase “first stable patient” with a prespecified repeated six-hour eligibility algorithm.
- Require an active core sedative at time zero and define the baseline multidrug vector from observed infusion records.
- Specify that an early strategy starts within a 6-hour grace period and is followed for 24-hour adherence; the comparator maintains the regimen for 24 hours unless rescue criteria occur.
- Define time zero before an observed successful SBT/extubation-readiness decision when such data are available; use a sensitivity exclusion for recent SBT evidence.
- Do not make a single RASS or command-following value mandatory. Use recent GCS/RASS information in treatment/adherence models with missingness/time-since-last-observation terms.
- Treat complete ≥2-hour sedation interruption as a subtype/sensitivity analysis, not the cross-database primary exposure.
- Make MIMIC-IV the primary causal analysis. Treat eICU as transport replication and report non-comparable measurement components rather than forcing pooled doses.
- Keep HiRID conditional on contributor approval and variable compatibility; its absence must not delay the primary two-cohort paper.

## Innovation boundary for manuscript language

Permissible wording:

> In a prespecified search of PubMed, ClinicalTrials.gov, and Europe PMC through August 2, 2026, we did not identify a prior study that emulated repeated stability-triggered decisions to de-escalate versus continue multidrug sedation in mechanically ventilated adults with acute brain injury while addressing time-varying confounding.

Avoid:

- “the first ever”;
- “no prior study has examined sedation in acute brain injury”;
- “causal proof” or “equivalent to a randomized trial”;
- any claim that MIMIC and eICU provide independent clinical practice eras without documenting overlap and measurement differences.

## Go/modify/no-go conclusion

**GO with protocol refinement.** The theme is not replaced. The principal exposure remains ≥30% relative de-escalation of at least one active core sedative within 6 hours, with no ≥30% increase in another active core sedative and no new core sedative start. The primary paper will frame this as a stability-triggered dynamic decision, not as a generic sedation vacation or a drug-comparison study.

## Reproducible files

- `04_code/python/novelty_pubmed_audit.py`
- `04_code/python/clinicaltrials_novelty_audit.py`
- `04_code/python/europepmc_novelty_audit.py`
- `01_topic_report/novelty_audit/novelty_pubmed_inventory_2026-08-02.csv`
- `01_topic_report/novelty_audit/novelty_search_log_2026-08-02.json`
- `01_topic_report/novelty_audit/clinicaltrials_inventory_2026-08-02.csv`
- `01_topic_report/novelty_audit/clinicaltrials_search_log_2026-08-02.json`
- `01_topic_report/novelty_audit/europepmc_inventory_2026-08-02.csv`
- `01_topic_report/novelty_audit/europepmc_search_log_2026-08-02.json`
- `01_topic_report/novelty_audit/novelty_screening_decisions_2026-08-02.csv`
