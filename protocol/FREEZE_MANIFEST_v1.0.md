# WHEN-TO-WAKE ABI Freeze Manifest v1.0

Freeze created: 2026-08-02, Asia/Shanghai  
Freeze status: valid  
Outcome-opening status at freeze: **no strategy-outcome comparison had been run or inspected.**

## Locked files

| File | SHA256 |
|---|---|
| `COMMON_DATA_MODEL_v1.0.csv` | `C864130D2BE37B95852997624DD5B9D2F0659855E0DD327D78E07BC454FD4D40` |
| `DAG_v1.0.md` | `CFE95D2388A095239C76872DE25A18B44AA3F6297D0E12FE84644EA289195854` |
| `project_config_v1.0.json` | `8CC632829A45A100E29E8E7DFF3F9C87665610CFF3DBD61ADC15423F1FD44C15` |
| `PROTOCOL_v1.0.md` | `40F49BA59FF6BF5AAF37A150C8A414094FE45FC5984B449E3D2C780E03F70594` |
| `SAP_v1.0.md` | `66ECE5C9E7DDF1AE4DC3E96614AA5D2C91384C79640442E05440C13300579ED3` |

## Evidence available before freeze

- feasibility-only cohort, exposure, unit, pause, ventilation, stability, and marginal-support audits;
- PubMed, ClinicalTrials.gov, Europe PMC novelty inventories and manual priority screening;
- no early-vs-continued mortality, successful-extubation, ventilator-free-day, or length-of-stay contrast;
- no outcome-targeted model, P value, confidence interval, or threshold optimization.

## Authorization to open outcomes

After this manifest is copied into `02_protocol_and_registration/freeze_v1.0/` and its files reverify against the hashes above, formal effect analysis under Protocol/SAP v1.0 is authorized. Any code or definition change after outcome opening requires a dated amendment that preserves the old frozen files and explicitly states whether the change was outcome-aware.

## Verification command

Use SHA256 file hashing on every file in `freeze_v1.0/` and compare the five locked-file values above. The manifest itself is not recursively included in its own hash table.
