# WHEN-TO-WAKE ABI eICU Formal Transport Freeze Manifest v1.1

Frozen at: 2026-08-02 (Asia/Shanghai)  
Formal run label: `transport_v1_1_calibrated`  
Bootstrap: 1,000 whole-ICU-stay replicates, seed 20260802

| Relative path from project root | SHA-256 |
|---|---|
| `02_protocol_and_registration/EICU_TRANSPORT_ANALYSIS_PLAN_v1.0.md` | `5E303FD4DF960B5E3DC354C56BFC33D3A47C5F27CC000FB45F96C54106B6F628` |
| `02_protocol_and_registration/EICU_TRANSPORT_AMENDMENT_v1.1_WEIGHT_CALIBRATION.md` | `42D17FE3D4782E6434F5BDF07551CA358E6D2668721F904E69E0517E7A165AE9` |
| `02_protocol_and_registration/eicu_transport_config_v1.1.json` | `87DBBAD65120BD469CBC37FB0305EA5FC7C8EAC5B0344BA135D0B42CF5BFB97E` |
| `04_code/python/build_eicu_analysis_ready_v1_0.py` | `F7F33FC82963AC9C85BBB3A8AD0B3D22DBE3F84DBCD0386E8938CD536CD3D1BC` |
| `04_code/python/qa_eicu_analysis_ready_v1_0.py` | `41B115DD0FD73B6031755F71931D6EDED5CD45BF1266E65DC6DE034E4B97BA7D` |
| `04_code/python/run_eicu_transport_ccw_v1_0.py` | `541C36ABC3A583F3FDA66306D98A78B2CED258898744BBD659D3754B030D3E69` |
| `00_restricted_data/derived/eicu_transport_v1_0/eicu_analysis_grid_transport_v1_0.csv.gz` | `8921AB9A873EDC59EC145310B992B8E5E1BF9139F9AA7ABD6E0F721C25BB58F3` |
| `00_restricted_data/derived/eicu_transport_v1_0/eicu_analysis_intervals_transport_v1_0.csv.gz` | `498F68EB6D62774485832E3A6AB83B6265EFA242085B0C549632E420BBB1413A` |
| `05_results/formal_analysis/eicu/eicu_analysis_ready_qa_v1_0.csv` | `D32B0A125EF8619D5A9E1EF73DE8192FE4F23AF197DA22735DDE3379F76F5402` |
| `05_results/formal_analysis/eicu/eicu_analysis_ready_qa_v1_0.json` | `2F59DE87D77F32382B4110D360EF7066ED1E2CB2C389670E1131200FF66F436C` |

All output families containing `debug` are development diagnostics and are
excluded from manuscript-facing artifacts. The eICU outcome remains a
reconstructed ventilation-end proxy and must not be called explicit successful
extubation.
