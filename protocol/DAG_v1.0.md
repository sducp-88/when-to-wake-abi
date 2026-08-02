# WHEN-TO-WAKE ABI Causal Diagram v1.0

Frozen: 2026-08-02

```mermaid
flowchart LR
  B["Baseline patient, ABI subtype, severity, site"] --> H["Prior physiologic and neurologic history"]
  B --> A["Sedation de-escalation decision"]
  B --> Y["Alive and successfully extubated by day 7"]
  H --> A
  H --> Y
  P["Prior sedative and opioid exposure"] --> H
  P --> A
  A --> L["Post-decision physiology, neurologic state, ventilation, agitation"]
  L --> A2["Subsequent adherence, rescue, or re-escalation"]
  L --> Y
  A --> A2
  A --> Y
  S["Observation process and measurement frequency"] --> H
  S --> A
  S --> Y
  W["Treatment limitations and withdrawal decisions"] --> A
  W --> Y
```

Interpretation:

- `H` contains time-varying confounders affected by prior treatment, so ordinary baseline adjustment is insufficient.
- Variables in `L` are not adjusted as baseline covariates for the initial treatment action; they enter later adherence/censoring models.
- Successful SBT/extubation readiness is a downstream/neighboring decision. When recorded before time zero it is an eligibility/confounding variable; after time zero it may be on the causal pathway and is not adjusted as a baseline covariate.
- ICP monitoring is partly determined by severity and practice. Absence of monitoring is not encoded as normal ICP.
- Treatment limitation/withdrawal is a major potential source of confounding and informative outcome processes; it is included when measurable and addressed by sensitivity analysis.
