# WHEN-TO-WAKE ABI Formal MIMIC Analysis Freeze Manifest v1.3

Frozen at: 2026-08-02 (Asia/Shanghai)  
Formal run label: `primary_v1_3`  
Bootstrap: 1,000 whole-ICU-stay replicates, seed 20260802

| Relative path from project root | SHA-256 |
|---|---|
| `02_protocol_and_registration/PROTOCOL_v1.0.md` | `40F49BA59FF6BF5AAF37A150C8A414094FE45FC5984B449E3D2C780E03F70594` |
| `02_protocol_and_registration/SAP_v1.0.md` | `66ECE5C9E7DDF1AE4DC3E96614AA5D2C91384C79640442E05440C13300579ED3` |
| `02_protocol_and_registration/PROTOCOL_AMENDMENT_v1.1_PREOUTCOME.md` | `583869F5CE737558AE951BF1973281B2A40C3519C789347FF24866DAE82309AC` |
| `02_protocol_and_registration/SAP_AMENDMENT_v1.2_METHOD_CORRECTION.md` | `7CC663F4ECC446E50C2BB17D3AC620F3A038C8CB276449D76ED7ABF1B8A2555D` |
| `02_protocol_and_registration/SAP_AMENDMENT_v1.3_WEIGHT_CALIBRATION.md` | `AECACEE2B3A2AC2EF684782AE8EDB9A3ED9CE78B6BBE83940B47B74F176B8602` |
| `02_protocol_and_registration/analysis_config_v1.3.json` | `EC439A952A81293F35DA3C44F8D9A98216FDCDBB982347736DC178FC411E9B67` |
| `04_code/python/run_mimic_ccw_analysis_v1_1.py` | `C3DCBFD6CF4C924C54B64E5DA5CFCE1BC79C4F47FB640E07FC9E03306F4ADB04` |
| `04_code/python/qa_mimic_analysis_ready_v1_1.py` | `99B20496F359D2E01AAEAD08338B045EF83DCF41449D4E2380587DC380C7AA5E` |
| `04_code/python/test_terminal_aware_ccw.py` | `A92858DA3591461A0A030D62FA6F895655D7FBDF2BABE8D6FE3186AD0FC8A881` |
| `00_restricted_data/derived/mimic_v1_1/mimic_analysis_grid_v1_1.csv.gz` | `056E0A225BDBE85F538B3176A510DBFB6BDC12283F0A4B8D7EBD688CCE236E01` |
| `00_restricted_data/derived/mimic_v1_1/mimic_analysis_intervals_v1_1.csv.gz` | `EB5581BAD45A53C64E337DD2CCE39B122444F444465767BF0C6EC2897B5E51C9` |
| `05_results/formal_analysis/mimic/mimic_analysis_ready_qa_v1_1.csv` | `53C742A2B7DBA5793D935CAAC1CF43CA6B78885B127F1F889F04BF337F109270` |
| `05_results/formal_analysis/mimic/mimic_analysis_ready_qa_v1_1.json` | `B05CD7A51EB4F42C2CB045B5DD07B538772F4B75AEE07740B1A9856BB293ACD1` |

The main program filename retains the historical `_v1_1` suffix for path
continuity; its content and all formal outputs are governed by analysis version
1.3. Every output family containing `debug` is excluded from the confirmatory
analysis and from manuscript-facing files.
