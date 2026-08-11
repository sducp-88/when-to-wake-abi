from __future__ import annotations

import os
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
VENDOR = Path(os.environ.get("WTW_VENDOR_DIR", PROJECT_ROOT / "04_code" / "vendor")).resolve()
sys.path.insert(0, str(VENDOR))

import pandas as pd


def main() -> None:
    import duckdb

    mimic = PROJECT_ROOT / "00_restricted_data" / "MIMIC-IV" / "3.1" / "extracted" / "mimic-iv-3.1"
    restricted_derived = PROJECT_ROOT / "00_restricted_data" / "derived" / "mimic_v1_5_bias_targeted"
    restricted_derived.mkdir(parents=True, exist_ok=True)
    result_dir = PROJECT_ROOT / "05_results" / "formal_analysis" / "mimic"
    result_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = PROJECT_ROOT / "00_restricted_data" / "_duckdb_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads=4")
    con.execute("SET memory_limit='8GB'")
    con.execute(f"SET temp_directory='{temp_dir.as_posix()}'")
    csv_opts = "header=true, all_varchar=true, quote='\"', escape='\"'"

    icu = mimic / "icu"
    hosp = mimic / "hosp"

    # ------------------------------------------------------------------
    # Baseline cohort and ABI phenotype. No outcome contrast is created
    # until the final grid table exists under the frozen v1.1 rules.
    # ------------------------------------------------------------------
    con.execute(
        f"""
        CREATE TEMP TABLE first_icu AS
        WITH ranked AS (
          SELECT i.subject_id,i.hadm_id,i.stay_id,
                 TRY_CAST(i.intime AS TIMESTAMP) AS intime,
                 TRY_CAST(i.outtime AS TIMESTAMP) AS outtime,
                 i.first_careunit,
                 TRY_CAST(a.admittime AS TIMESTAMP) AS admittime,
                 TRY_CAST(a.dischtime AS TIMESTAMP) AS dischtime,
                 TRY_CAST(a.deathtime AS TIMESTAMP) AS deathtime,
                 TRY_CAST(a.hospital_expire_flag AS INTEGER) AS hospital_expire_flag,
                 a.admission_type,a.race,p.gender,
                 TRY_CAST(p.anchor_age AS INTEGER)
                   + EXTRACT(YEAR FROM TRY_CAST(a.admittime AS TIMESTAMP))
                   - TRY_CAST(p.anchor_year AS INTEGER) AS age,
                 ROW_NUMBER() OVER(
                   PARTITION BY i.subject_id
                   ORDER BY TRY_CAST(i.intime AS TIMESTAMP),TRY_CAST(i.stay_id AS BIGINT)
                 ) AS rn
          FROM read_csv(?,{csv_opts}) i
          JOIN read_csv(?,{csv_opts}) a USING(subject_id,hadm_id)
          JOIN read_csv(?,{csv_opts}) p USING(subject_id)
        )
        SELECT * EXCLUDE(rn) FROM ranked WHERE rn=1 AND age>=18
        """,
        [str(icu / "icustays.csv.gz"), str(hosp / "admissions.csv.gz"), str(hosp / "patients.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE dx AS
        SELECT d.subject_id,d.hadm_id,TRY_CAST(d.seq_num AS INTEGER) AS seq_num,
               UPPER(REPLACE(d.icd_code,'.','')) AS code,d.icd_version
        FROM read_csv(?,{csv_opts}) d JOIN first_icu f USING(subject_id,hadm_id)
        """,
        [str(hosp / "diagnoses_icd.csv.gz")],
    )
    con.execute(
        """
        CREATE TEMP TABLE phenotype AS
        WITH flags AS (
          SELECT subject_id,hadm_id,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'S06%') OR (icd_version='9' AND REGEXP_MATCHES(code,'^(80[0-4]|85[0-4])')) THEN 1 ELSE 0 END) AS tbi,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'I60%') OR (icd_version='9' AND code LIKE '430%') THEN 1 ELSE 0 END) AS sah,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'I61%') OR (icd_version='9' AND code LIKE '431%') THEN 1 ELSE 0 END) AS ich,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'I63%') OR (icd_version='9' AND (code LIKE '436%' OR REGEXP_MATCHES(code,'^(433|434).*1$'))) THEN 1 ELSE 0 END) AS ais,
            MAX(CASE WHEN seq_num=1 AND ((icd_version='10' AND (code LIKE 'I46%' OR code LIKE 'G931%')) OR (icd_version='9' AND (code LIKE '4275%' OR code LIKE '3481%'))) THEN 1 ELSE 0 END) AS primary_hypoxic_arrest,
            MAX(CASE WHEN (icd_version='10' AND (code LIKE 'E10%' OR code LIKE 'E11%' OR code LIKE 'E13%')) OR (icd_version='9' AND code LIKE '250%') THEN 1 ELSE 0 END) AS diabetes,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'N18%') OR (icd_version='9' AND code LIKE '585%') THEN 1 ELSE 0 END) AS ckd,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'I50%') OR (icd_version='9' AND code LIKE '428%') THEN 1 ELSE 0 END) AS chf,
            MAX(CASE WHEN (icd_version='10' AND code LIKE 'I48%') OR (icd_version='9' AND code LIKE '4273%') THEN 1 ELSE 0 END) AS atrial_fibrillation,
            MAX(CASE WHEN (icd_version='10' AND REGEXP_MATCHES(code,'^C[0-9]')) OR (icd_version='9' AND REGEXP_MATCHES(code,'^(14[0-9]|1[5-9][0-9]|20[0-8])')) THEN 1 ELSE 0 END) AS malignancy,
            MAX(CASE WHEN (icd_version='10' AND REGEXP_MATCHES(code,'^K7[0-7]')) OR (icd_version='9' AND code LIKE '571%') THEN 1 ELSE 0 END) AS liver_disease,
            MIN(seq_num) FILTER(WHERE (icd_version='10' AND code LIKE 'S06%') OR (icd_version='9' AND REGEXP_MATCHES(code,'^(80[0-4]|85[0-4])'))) AS rank_tbi,
            MIN(seq_num) FILTER(WHERE (icd_version='10' AND code LIKE 'I60%') OR (icd_version='9' AND code LIKE '430%')) AS rank_sah,
            MIN(seq_num) FILTER(WHERE (icd_version='10' AND code LIKE 'I61%') OR (icd_version='9' AND code LIKE '431%')) AS rank_ich,
            MIN(seq_num) FILTER(WHERE (icd_version='10' AND code LIKE 'I63%') OR (icd_version='9' AND (code LIKE '436%' OR REGEXP_MATCHES(code,'^(433|434).*1$')))) AS rank_ais
          FROM dx GROUP BY subject_id,hadm_id
        )
        SELECT *,
          CASE
            WHEN LEAST(COALESCE(rank_tbi,9999),COALESCE(rank_sah,9999),COALESCE(rank_ich,9999),COALESCE(rank_ais,9999))=COALESCE(rank_tbi,9999) THEN 'TBI'
            WHEN LEAST(COALESCE(rank_tbi,9999),COALESCE(rank_sah,9999),COALESCE(rank_ich,9999),COALESCE(rank_ais,9999))=COALESCE(rank_sah,9999) THEN 'SAH'
            WHEN LEAST(COALESCE(rank_tbi,9999),COALESCE(rank_sah,9999),COALESCE(rank_ich,9999),COALESCE(rank_ais,9999))=COALESCE(rank_ich,9999) THEN 'ICH'
            WHEN LEAST(COALESCE(rank_tbi,9999),COALESCE(rank_sah,9999),COALESCE(rank_ich,9999),COALESCE(rank_ais,9999))=COALESCE(rank_ais,9999) THEN 'AIS'
          END AS abi_subtype,
          diabetes+ckd+chf+atrial_fibrillation+malignancy+liver_disease AS comorbidity_count
        FROM flags WHERE tbi=1 OR sah=1 OR ich=1 OR ais=1
        """
    )

    # ------------------------------------------------------------------
    # Airway and invasive-ventilation intervals.
    # ------------------------------------------------------------------
    con.execute(
        f"""
        CREATE TEMP TABLE airway AS
        SELECT p.stay_id,TRY_CAST(p.itemid AS BIGINT) AS itemid,
               TRY_CAST(p.starttime AS TIMESTAMP) AS starttime,
               TRY_CAST(p.endtime AS TIMESTAMP) AS endtime
        FROM read_csv(?,{csv_opts}) p JOIN first_icu f USING(stay_id)
        WHERE TRY_CAST(p.itemid AS BIGINT) IN (224385,225792,227194,225477,225468,225448,226237)
          AND TRY_CAST(p.starttime AS TIMESTAMP) IS NOT NULL
        """,
        [str(icu / "procedureevents.csv.gz")],
    )
    con.execute(
        """
        CREATE TEMP TABLE vent_intervals AS
        SELECT stay_id,starttime AS vent_start,COALESCE(endtime,starttime) AS vent_end
        FROM airway WHERE itemid=225792 AND endtime>starttime
        """
    )

    # Medication mappings are label-based but item IDs are preserved in the mapping audit.
    con.execute(
        f"""
        CREATE TEMP TABLE item_map AS
        SELECT TRY_CAST(itemid AS BIGINT) AS itemid,label,
          CASE
            WHEN REGEXP_MATCHES(LOWER(label),'propofol') AND NOT REGEXP_MATCHES(LOWER(label),'ingredient|intubation') THEN 'propofol'
            WHEN REGEXP_MATCHES(LOWER(label),'dexmed|precedex') THEN 'dexmedetomidine'
            WHEN REGEXP_MATCHES(LOWER(label),'midazolam|versed') THEN 'midazolam'
            WHEN REGEXP_MATCHES(LOWER(label),'fentanyl|morphine|hydromorphone|remifentanil|sufentanil') THEN 'opioid'
            WHEN REGEXP_MATCHES(LOWER(label),'norepinephrine|epinephrine|phenylephrine|vasopressin|dopamine|dobutamine') THEN 'vasopressor'
            WHEN REGEXP_MATCHES(LOWER(label),'rocuronium|vecuronium|cisatracurium|atracurium|pancuronium') THEN 'nmba'
            WHEN REGEXP_MATCHES(LOWER(label),'pentobarbital|thiopental') THEN 'barbiturate'
            WHEN REGEXP_MATCHES(LOWER(label),'mannitol|nacl 3%|hypertonic') THEN 'hyperosmolar'
            WHEN REGEXP_MATCHES(LOWER(label),'ketamine') THEN 'ketamine'
          END AS drug_class
        FROM read_csv(?,{csv_opts})
        WHERE REGEXP_MATCHES(LOWER(COALESCE(label,'')),
          'propofol|dexmed|precedex|midazolam|versed|fentanyl|morphine|hydromorphone|remifentanil|sufentanil|norepinephrine|epinephrine|phenylephrine|vasopressin|dopamine|dobutamine|rocuronium|vecuronium|cisatracurium|atracurium|pancuronium|pentobarbital|thiopental|mannitol|nacl 3%|hypertonic|ketamine')
        """,
        [str(icu / "d_items.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE drug_events AS
        SELECT e.stay_id,m.itemid,m.label,m.drug_class,
               TRY_CAST(e.starttime AS TIMESTAMP) AS starttime,
               TRY_CAST(e.endtime AS TIMESTAMP) AS endtime,
               TRY_CAST(e.rate AS DOUBLE) AS rate_value,
               COALESCE(NULLIF(LOWER(TRIM(e.rateuom)),''),'__missing__') AS rate_unit,
               TRY_CAST(e.amount AS DOUBLE) AS amount_value
        FROM read_csv(?,{csv_opts}) e JOIN item_map m USING(itemid)
        JOIN first_icu f USING(stay_id)
        WHERE m.drug_class IS NOT NULL
          AND LOWER(COALESCE(e.statusdescription,''))<>'rewritten'
          AND TRY_CAST(e.starttime AS TIMESTAMP) IS NOT NULL
        """,
        [str(icu / "inputevents.csv.gz")],
    )
    con.execute(
        """
        CREATE TEMP TABLE core_stays AS
        SELECT f.*,p.* EXCLUDE(subject_id,hadm_id)
        FROM first_icu f JOIN phenotype p USING(subject_id,hadm_id)
        JOIN (SELECT DISTINCT stay_id FROM vent_intervals) v USING(stay_id)
        JOIN (SELECT DISTINCT stay_id FROM drug_events WHERE drug_class IN ('propofol','midazolam','dexmedetomidine') AND rate_value>0) s USING(stay_id)
        WHERE p.primary_hypoxic_arrest=0
        """
    )

    # ------------------------------------------------------------------
    # Restricted chart/lab extracts and repeated assessment points.
    # ------------------------------------------------------------------
    con.execute(
        f"""
        CREATE TEMP TABLE chart AS
        SELECT c.stay_id,TRY_CAST(c.charttime AS TIMESTAMP) AS charttime,
               TRY_CAST(c.itemid AS BIGINT) AS itemid,TRY_CAST(c.valuenum AS DOUBLE) AS value_num,c.value
        FROM read_csv(?,{csv_opts}) c JOIN core_stays s USING(stay_id)
        WHERE TRY_CAST(c.itemid AS BIGINT) IN (
          220052,220181,225312,220045,223835,220339,224700,
          228096,220739,223900,223901,220765,223762,223761,
          224715,224716,224717,224833,223849,229314
        )
          AND TRY_CAST(c.charttime AS TIMESTAMP) IS NOT NULL
        """,
        [str(icu / "chartevents.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE lab_item_map AS
        SELECT TRY_CAST(itemid AS BIGINT) AS itemid,
          CASE
            WHEN LOWER(label)='lactate' THEN 'lactate'
            WHEN REGEXP_MATCHES(LOWER(label),'^creatinine') THEN 'creatinine'
            WHEN REGEXP_MATCHES(LOWER(label),'bilirubin, total|total bilirubin') THEN 'bilirubin'
            WHEN LOWER(label) IN ('pco2','pco2, arterial') THEN 'paco2'
            WHEN LOWER(label) IN ('po2','po2, arterial') THEN 'pao2'
          END AS concept
        FROM read_csv(?,{csv_opts})
        WHERE LOWER(COALESCE(fluid,'')) IN ('blood','')
          AND (LOWER(label)='lactate' OR REGEXP_MATCHES(LOWER(label),'^creatinine|bilirubin, total|total bilirubin|^pco2$|pco2, arterial|^po2$|po2, arterial'))
        """,
        [str(hosp / "d_labitems.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE labs AS
        SELECT f.stay_id,TRY_CAST(l.charttime AS TIMESTAMP) AS charttime,m.concept,TRY_CAST(l.valuenum AS DOUBLE) AS value_num
        FROM read_csv(?,{csv_opts}) l JOIN core_stays f USING(subject_id,hadm_id)
        JOIN lab_item_map m USING(itemid)
        WHERE m.concept IS NOT NULL AND TRY_CAST(l.valuenum AS DOUBLE) IS NOT NULL
        """,
        [str(hosp / "labevents.csv.gz")],
    )

    con.execute(
        """
        CREATE TEMP TABLE grids AS
        WITH first_vent AS (
          SELECT s.stay_id,MIN(v.vent_start) AS first_vent_start
          FROM core_stays s JOIN vent_intervals v USING(stay_id) GROUP BY s.stay_id
        )
        SELECT s.*,f.first_vent_start,h.grid_hour,
               f.first_vent_start+h.grid_hour*INTERVAL 1 HOUR AS grid_time
        FROM core_stays s JOIN first_vent f USING(stay_id),generate_series(12,96,6) h(grid_hour)
        WHERE f.first_vent_start+h.grid_hour*INTERVAL 1 HOUR<=s.outtime
          AND EXISTS(
            SELECT 1 FROM vent_intervals v
            WHERE v.stay_id=s.stay_id
              AND v.vent_start<=f.first_vent_start+h.grid_hour*INTERVAL 1 HOUR
              AND v.vent_end>f.first_vent_start+h.grid_hour*INTERVAL 1 HOUR
          )
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE points AS
        SELECT g.stay_id,g.grid_hour,g.grid_time,k.interval_index,
               g.grid_time+k.interval_index*INTERVAL 6 HOUR AS point_time
        FROM grids g,generate_series(-1,4,1) k(interval_index)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE point_features AS
        SELECT p.stay_id,p.grid_hour,p.interval_index,p.point_time,
          MEDIAN(c.value_num) FILTER(WHERE c.itemid IN (220052,220181,225312) AND c.value_num BETWEEN 20 AND 200 AND c.charttime>p.point_time-INTERVAL 2 HOUR) AS map_median_2h,
          MIN(c.value_num) FILTER(WHERE c.itemid IN (220052,220181,225312) AND c.value_num BETWEEN 20 AND 200 AND c.charttime>p.point_time-INTERVAL 2 HOUR) AS map_min_2h,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=220045 AND c.value_num BETWEEN 20 AND 250) AS heart_rate,
          ARG_MAX(CASE WHEN c.value_num>1.5 THEN c.value_num/100.0 ELSE c.value_num END,c.charttime) FILTER(WHERE c.itemid=223835 AND c.value_num>0) AS fio2,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid IN (220339,224700) AND c.value_num BETWEEN 0 AND 40) AS peep,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=228096 AND c.value_num BETWEEN -5 AND 4) AS rass,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=223901 AND c.value_num BETWEEN 1 AND 6) AS gcs_motor,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=220739 AND c.value_num BETWEEN 1 AND 4) AS gcs_eye,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=223900 AND c.value_num BETWEEN 1 AND 5) AS gcs_verbal,
          ARG_MAX(c.value_num,c.charttime) FILTER(WHERE c.itemid=220765 AND c.value_num BETWEEN 0 AND 100) AS icp_latest,
          MAX(c.value_num) FILTER(WHERE c.itemid=220765 AND c.value_num BETWEEN 0 AND 100 AND c.charttime>p.point_time-INTERVAL 2 HOUR) AS icp_max_2h,
          COUNT(*) FILTER(WHERE c.itemid IN (228096,220739,223900,223901)) AS neuro_measure_count,
          MAX(CASE WHEN c.itemid=224717 THEN 1 ELSE 0 END) AS successful_sbt_prior6h,
          MAX(CASE WHEN c.itemid IN (224715,224716,224717,224833) THEN 1 ELSE 0 END) AS any_sbt_prior6h,
          ARG_MAX(CASE WHEN c.itemid=223762 THEN c.value_num WHEN c.itemid=223761 THEN (c.value_num-32)*5.0/9.0 END,c.charttime)
            FILTER(WHERE c.itemid IN (223762,223761) AND c.value_num IS NOT NULL) AS temperature_c
        FROM points p LEFT JOIN chart c ON c.stay_id=p.stay_id
          AND c.charttime>p.point_time-INTERVAL 6 HOUR AND c.charttime<=p.point_time
        GROUP BY p.stay_id,p.grid_hour,p.interval_index,p.point_time
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE point_labs AS
        SELECT p.stay_id,p.grid_hour,p.interval_index,
          ARG_MAX(l.value_num,l.charttime) FILTER(WHERE l.concept='lactate') AS lactate,
          ARG_MAX(l.value_num,l.charttime) FILTER(WHERE l.concept='creatinine') AS creatinine,
          ARG_MAX(l.value_num,l.charttime) FILTER(WHERE l.concept='bilirubin') AS bilirubin,
          ARG_MAX(l.value_num,l.charttime) FILTER(WHERE l.concept='paco2') AS paco2,
          ARG_MAX(l.value_num,l.charttime) FILTER(WHERE l.concept='pao2') AS pao2
        FROM points p LEFT JOIN labs l ON l.stay_id=p.stay_id
          AND l.charttime>p.point_time-INTERVAL 24 HOUR AND l.charttime<=p.point_time
        GROUP BY p.stay_id,p.grid_hour,p.interval_index
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE point_drugs AS
        SELECT p.stay_id,p.grid_hour,p.interval_index,
          MAX(CASE WHEN d.drug_class='vasopressor' AND COALESCE(d.rate_value,1)>0 THEN 1 ELSE 0 END) AS vasopressor_observed,
          MAX(CASE WHEN d.drug_class='opioid' AND COALESCE(d.rate_value,1)>0 THEN 1 ELSE 0 END) AS opioid_observed,
          MAX(CASE WHEN d.drug_class='ketamine' AND COALESCE(d.rate_value,1)>0 THEN 1 ELSE 0 END) AS ketamine_observed,
          MAX(CASE WHEN d.drug_class='nmba' AND d.starttime>p.point_time-INTERVAL 2 HOUR THEN 1 ELSE 0 END) AS nmba_recent2h,
          MAX(CASE WHEN d.drug_class='barbiturate' AND d.starttime>p.point_time-INTERVAL 6 HOUR THEN 1 ELSE 0 END) AS barbiturate_recent6h,
          MAX(CASE WHEN d.drug_class='hyperosmolar' AND d.starttime>p.point_time-INTERVAL 6 HOUR THEN 1 ELSE 0 END) AS hyperosmolar_recent6h
        FROM points p LEFT JOIN drug_events d ON d.stay_id=p.stay_id
          AND d.starttime<=p.point_time
          AND COALESCE(d.endtime,d.starttime)>=p.point_time-INTERVAL 6 HOUR
        GROUP BY p.stay_id,p.grid_hour,p.interval_index
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE history AS
        SELECT f.*,l.lactate,l.creatinine,l.bilirubin,l.paco2,l.pao2,
               d.vasopressor_observed,d.opioid_observed,d.ketamine_observed,
               d.nmba_recent2h,d.barbiturate_recent6h,d.hyperosmolar_recent6h,
               CASE WHEN f.fio2>0 THEN l.pao2/f.fio2 END AS pao2_fio2
        FROM point_features f JOIN point_labs l USING(stay_id,grid_hour,interval_index)
        JOIN point_drugs d USING(stay_id,grid_hour,interval_index)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE history_with_trajectory AS
        SELECT h.*,
               h.map_median_2h-p.map_median_2h AS delta_map_median_6h,
               h.map_min_2h-p.map_min_2h AS delta_map_min_6h,
               h.heart_rate-p.heart_rate AS delta_heart_rate_6h,
               h.fio2-p.fio2 AS delta_fio2_6h,
               h.peep-p.peep AS delta_peep_6h,
               h.rass-p.rass AS delta_rass_6h,
               h.gcs_motor-p.gcs_motor AS delta_gcs_motor_6h,
               h.gcs_eye-p.gcs_eye AS delta_gcs_eye_6h,
               h.gcs_verbal-p.gcs_verbal AS delta_gcs_verbal_6h,
               h.icp_latest-p.icp_latest AS delta_icp_latest_6h,
               h.neuro_measure_count-p.neuro_measure_count AS delta_neuro_measure_count_6h,
               p.vasopressor_observed AS vasopressor_observed_prev6h,
               p.opioid_observed AS opioid_observed_prev6h,
               p.ketamine_observed AS ketamine_observed_prev6h
        FROM history h
        LEFT JOIN history p
          ON p.stay_id=h.stay_id
         AND p.grid_hour=h.grid_hour
         AND p.interval_index=h.interval_index-1
        """
    )

    # ------------------------------------------------------------------
    # Core-sedative snapshots at time zero and each 6-hour boundary.
    # ------------------------------------------------------------------
    con.execute(
        """
        CREATE TEMP TABLE core_snapshots AS
        WITH candidates AS (
          SELECT p.stay_id,p.grid_hour,p.interval_index,p.point_time,d.drug_class,d.rate_unit,d.rate_value,d.starttime,d.endtime,
                 ROW_NUMBER() OVER(
                   PARTITION BY p.stay_id,p.grid_hour,p.interval_index,d.drug_class
                   ORDER BY d.starttime DESC,d.endtime DESC
                 ) AS rn
          FROM points p JOIN drug_events d ON p.stay_id=d.stay_id
          WHERE d.drug_class IN ('propofol','midazolam','dexmedetomidine')
            AND d.rate_value>0 AND d.rate_unit<>'__missing__'
            AND d.starttime<=p.point_time AND COALESCE(d.endtime,d.starttime)>p.point_time
        )
        SELECT * EXCLUDE(rn) FROM candidates WHERE rn=1
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE baseline_core AS
        SELECT * FROM core_snapshots WHERE interval_index=0
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE treatment_intervals AS
        WITH interval_index AS (
          SELECT g.stay_id,g.grid_hour,k.interval_index
          FROM grids g,generate_series(1,4,1) k(interval_index)
        ), base_follow AS (
          SELECT i.stay_id,i.grid_hour,i.interval_index,b.drug_class,b.rate_unit AS baseline_unit,
                 b.rate_value AS baseline_rate,s.rate_unit AS follow_unit,s.rate_value AS follow_rate,
                 CASE WHEN s.drug_class IS NULL OR s.rate_value<=0.70*b.rate_value THEN 1 ELSE 0 END AS decreased_or_stopped,
                 CASE WHEN s.rate_value>=1.30*b.rate_value THEN 1 ELSE 0 END AS increased,
                 CASE WHEN s.drug_class IS NOT NULL AND s.rate_unit<>b.rate_unit THEN 1 ELSE 0 END AS unit_conflict
          FROM interval_index i JOIN baseline_core b USING(stay_id,grid_hour)
          LEFT JOIN core_snapshots s ON s.stay_id=i.stay_id AND s.grid_hour=i.grid_hour
            AND s.interval_index=i.interval_index AND s.drug_class=b.drug_class
        ), base_agg AS (
          SELECT stay_id,grid_hour,interval_index,COUNT(*) AS baseline_drug_count,
                 MAX(decreased_or_stopped) AS any_decrease,
                 MAX(increased) AS any_increase,
                 MAX(unit_conflict) AS any_unit_conflict
          FROM base_follow GROUP BY stay_id,grid_hour,interval_index
        ), new_drug AS (
          SELECT i.stay_id,i.grid_hour,i.interval_index,
                 MAX(CASE WHEN s.drug_class IS NOT NULL AND b.drug_class IS NULL THEN 1 ELSE 0 END) AS new_core_drug
          FROM interval_index i
          LEFT JOIN core_snapshots s ON s.stay_id=i.stay_id AND s.grid_hour=i.grid_hour AND s.interval_index=i.interval_index
          LEFT JOIN baseline_core b ON b.stay_id=i.stay_id AND b.grid_hour=i.grid_hour AND b.drug_class=s.drug_class
          GROUP BY i.stay_id,i.grid_hour,i.interval_index
        )
        SELECT a.*,COALESCE(n.new_core_drug,0) AS new_core_drug,
          CASE WHEN a.any_decrease=1 AND a.any_increase=0 AND a.any_unit_conflict=0 AND COALESCE(n.new_core_drug,0)=0 THEN 1 ELSE 0 END AS early_snapshot_compatible,
          CASE WHEN a.any_decrease=0 AND a.any_unit_conflict=0 THEN 1 ELSE 0 END AS continue_snapshot_compatible
        FROM base_agg a JOIN new_drug n USING(stay_id,grid_hour,interval_index)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE first_actions AS
        WITH reduced_records AS (
          SELECT b.stay_id,b.grid_hour,b.drug_class,
                 MIN(d.starttime) FILTER(
                   WHERE d.starttime>b.point_time AND d.starttime<=b.point_time+INTERVAL 6 HOUR
                     AND d.rate_unit=b.rate_unit AND d.rate_value<=0.70*b.rate_value
                 ) AS first_reduced_record,
                 CASE WHEN b.endtime>b.point_time AND b.endtime<=b.point_time+INTERVAL 6 HOUR THEN b.endtime END AS baseline_stop_time
          FROM baseline_core b LEFT JOIN drug_events d
            ON d.stay_id=b.stay_id AND d.drug_class=b.drug_class
          GROUP BY b.stay_id,b.grid_hour,b.drug_class,b.point_time,b.endtime
        )
        SELECT stay_id,grid_hour,MIN(COALESCE(first_reduced_record,baseline_stop_time)) AS first_qualifying_action_time
        FROM reduced_records
        WHERE first_reduced_record IS NOT NULL OR baseline_stop_time IS NOT NULL
        GROUP BY stay_id,grid_hour
        """
    )

    # ------------------------------------------------------------------
    # Eligibility, explicit outcomes, temporal ordering, and interval rows.
    # ------------------------------------------------------------------
    con.execute(
        """
        CREATE TEMP TABLE eligible AS
        WITH baseline_count AS (
          SELECT stay_id,grid_hour,COUNT(*) AS baseline_drug_count,
                 MAX(CASE WHEN drug_class='propofol' THEN 1 ELSE 0 END) AS propofol_active,
                 MAX(CASE WHEN drug_class='midazolam' THEN 1 ELSE 0 END) AS midazolam_active,
                 MAX(CASE WHEN drug_class='dexmedetomidine' THEN 1 ELSE 0 END) AS dexmed_active,
                 MAX(CASE WHEN drug_class='propofol' THEN rate_value END) AS propofol_baseline_rate,
                 MAX(CASE WHEN drug_class='propofol' THEN rate_unit END) AS propofol_baseline_unit,
                 MAX(CASE WHEN drug_class='midazolam' THEN rate_value END) AS midazolam_baseline_rate,
                 MAX(CASE WHEN drug_class='midazolam' THEN rate_unit END) AS midazolam_baseline_unit,
                 MAX(CASE WHEN drug_class='dexmedetomidine' THEN rate_value END) AS dexmed_baseline_rate,
                 MAX(CASE WHEN drug_class='dexmedetomidine' THEN rate_unit END) AS dexmed_baseline_unit
          FROM baseline_core GROUP BY stay_id,grid_hour
        ), trach_before AS (
          SELECT g.stay_id,g.grid_hour,MAX(CASE WHEN a.starttime<=g.grid_time THEN 1 ELSE 0 END) AS trach_before_timezero
          FROM grids g LEFT JOIN airway a ON a.stay_id=g.stay_id AND a.itemid IN (225448,226237)
          GROUP BY g.stay_id,g.grid_hour
        )
        SELECT g.*,h.* EXCLUDE(stay_id,grid_hour,interval_index,point_time),
               b.* EXCLUDE(stay_id,grid_hour),t.trach_before_timezero
        FROM grids g JOIN history_with_trajectory h ON h.stay_id=g.stay_id AND h.grid_hour=g.grid_hour AND h.interval_index=0
        JOIN baseline_count b ON b.stay_id=g.stay_id AND b.grid_hour=g.grid_hour
        JOIN trach_before t ON t.stay_id=g.stay_id AND t.grid_hour=g.grid_hour
        WHERE h.map_median_2h>=65 AND h.map_min_2h>=60
          AND h.fio2<=0.60 AND h.peep<=10
          AND h.neuro_measure_count>0
          AND COALESCE(h.nmba_recent2h,0)=0
          AND COALESCE(h.barbiturate_recent6h,0)=0
          AND COALESCE(h.hyperosmolar_recent6h,0)=0
          AND (h.icp_latest IS NULL OR (h.icp_latest<=22 AND COALESCE(h.icp_max_2h,h.icp_latest)<=22))
          AND COALESCE(h.successful_sbt_prior6h,0)=0
          AND COALESCE(t.trach_before_timezero,0)=0
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE outcome_events AS
        WITH extub AS (
          SELECT e.stay_id,e.grid_hour,MIN(a.starttime) AS extubation_time
          FROM eligible e LEFT JOIN airway a ON a.stay_id=e.stay_id
            AND a.itemid IN (227194,225477,225468)
            AND a.starttime>e.grid_time AND a.starttime<=e.grid_time+INTERVAL 7 DAY
          GROUP BY e.stay_id,e.grid_hour
        ), trach AS (
          SELECT e.stay_id,e.grid_hour,MIN(a.starttime) AS tracheostomy_time
          FROM eligible e LEFT JOIN airway a ON a.stay_id=e.stay_id
            AND a.itemid IN (225448,226237) AND a.starttime>e.grid_time
          GROUP BY e.stay_id,e.grid_hour
        ), sbt AS (
          SELECT e.stay_id,e.grid_hour,MIN(c.charttime) AS first_successful_sbt_time
          FROM eligible e LEFT JOIN chart c ON c.stay_id=e.stay_id AND c.itemid=224717
            AND c.charttime>e.grid_time AND c.charttime<=e.grid_time+INTERVAL 6 HOUR
          GROUP BY e.stay_id,e.grid_hour
        ), reint AS (
          SELECT x.stay_id,x.grid_hour,
                 MIN(a.starttime) AS explicit_reintubation_time
          FROM extub x LEFT JOIN airway a ON a.stay_id=x.stay_id AND a.itemid=224385
            AND a.starttime>x.extubation_time AND a.starttime<=x.extubation_time+INTERVAL 48 HOUR
          GROUP BY x.stay_id,x.grid_hour
        ), renewed AS (
          SELECT x.stay_id,x.grid_hour,MIN(v.vent_start) AS renewed_ventilation_time
          FROM extub x LEFT JOIN vent_intervals v ON v.stay_id=x.stay_id
            AND v.vent_start>x.extubation_time AND v.vent_start<=x.extubation_time+INTERVAL 48 HOUR
          GROUP BY x.stay_id,x.grid_hour
        ), broad_end AS (
          SELECT e.stay_id,e.grid_hour,MIN(v.vent_end) AS first_ventilation_end
          FROM eligible e LEFT JOIN vent_intervals v ON v.stay_id=e.stay_id
            AND v.vent_start<=e.grid_time AND v.vent_end>e.grid_time
          GROUP BY e.stay_id,e.grid_hour
        )
        SELECT e.stay_id,e.grid_hour,x.extubation_time,t.tracheostomy_time,s.first_successful_sbt_time,
               r.explicit_reintubation_time,n.renewed_ventilation_time,b.first_ventilation_end,
               CASE WHEN x.extubation_time IS NOT NULL
                          AND x.extubation_time<=e.grid_time+INTERVAL 7 DAY
                          AND (e.deathtime IS NULL OR e.deathtime>e.grid_time+INTERVAL 7 DAY)
                          AND (e.deathtime IS NULL OR e.deathtime>x.extubation_time+INTERVAL 48 HOUR)
                          AND r.explicit_reintubation_time IS NULL
                          AND n.renewed_ventilation_time IS NULL
                          AND (t.tracheostomy_time IS NULL OR t.tracheostomy_time>x.extubation_time+INTERVAL 48 HOUR)
                    THEN 1 ELSE 0 END AS alive_success_extub_day7,
               CASE WHEN b.first_ventilation_end IS NOT NULL
                          AND b.first_ventilation_end<=e.grid_time+INTERVAL 7 DAY
                          AND (e.deathtime IS NULL OR e.deathtime>e.grid_time+INTERVAL 7 DAY)
                    THEN 1 ELSE 0 END AS alive_vent_end_day7
        FROM eligible e JOIN extub x USING(stay_id,grid_hour)
        JOIN trach t USING(stay_id,grid_hour) JOIN sbt s USING(stay_id,grid_hour)
        JOIN reint r USING(stay_id,grid_hour) JOIN renewed n USING(stay_id,grid_hour)
        JOIN broad_end b USING(stay_id,grid_hour)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE analysis_grid AS
        WITH interval_wide AS (
          SELECT stay_id,grid_hour,
            MAX(CASE WHEN interval_index=1 THEN early_snapshot_compatible END) AS early_compat_1,
            MAX(CASE WHEN interval_index=2 THEN early_snapshot_compatible END) AS early_compat_2,
            MAX(CASE WHEN interval_index=3 THEN early_snapshot_compatible END) AS early_compat_3,
            MAX(CASE WHEN interval_index=4 THEN early_snapshot_compatible END) AS early_compat_4,
            MAX(CASE WHEN interval_index=1 THEN continue_snapshot_compatible END) AS continue_compat_1,
            MAX(CASE WHEN interval_index=2 THEN continue_snapshot_compatible END) AS continue_compat_2,
            MAX(CASE WHEN interval_index=3 THEN continue_snapshot_compatible END) AS continue_compat_3,
            MAX(CASE WHEN interval_index=4 THEN continue_snapshot_compatible END) AS continue_compat_4,
            MAX(CASE WHEN interval_index=1 THEN any_unit_conflict END) AS unit_conflict_1
          FROM treatment_intervals GROUP BY stay_id,grid_hour
        )
        SELECT e.*,o.* EXCLUDE(stay_id,grid_hour),a.first_qualifying_action_time,w.* EXCLUDE(stay_id,grid_hour),
          CASE
            WHEN w.early_compat_1=1 AND a.first_qualifying_action_time IS NOT NULL
                 AND (o.first_successful_sbt_time IS NULL OR a.first_qualifying_action_time<o.first_successful_sbt_time)
                 AND (o.extubation_time IS NULL OR a.first_qualifying_action_time<=o.extubation_time-INTERVAL 60 MINUTE)
              THEN 1 ELSE 0 END AS early_temporal_valid,
          CASE
            WHEN w.early_compat_1=1 AND a.first_qualifying_action_time IS NOT NULL
                 AND ((o.first_successful_sbt_time IS NOT NULL AND a.first_qualifying_action_time>=o.first_successful_sbt_time)
                      OR (o.extubation_time IS NOT NULL AND a.first_qualifying_action_time>o.extubation_time-INTERVAL 60 MINUTE))
              THEN 1 ELSE 0 END AS contemporaneous_weaning,
          CASE
            WHEN w.early_compat_1=1 AND a.first_qualifying_action_time IS NOT NULL
                 AND (o.first_successful_sbt_time IS NULL OR a.first_qualifying_action_time<o.first_successful_sbt_time)
                 AND (o.extubation_time IS NULL OR a.first_qualifying_action_time<=o.extubation_time-INTERVAL 60 MINUTE)
              THEN 'early_deescalation'
            WHEN w.continue_compat_1=1 THEN 'continued_at_6h'
            WHEN w.early_compat_1=1 THEN 'contemporaneous_weaning'
            ELSE 'unclassifiable'
          END AS observed_6h_strategy
        FROM eligible e JOIN outcome_events o USING(stay_id,grid_hour)
        LEFT JOIN first_actions a USING(stay_id,grid_hour)
        JOIN interval_wide w USING(stay_id,grid_hour)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE analysis_intervals AS
        SELECT g.*,t.interval_index,t.any_decrease,t.any_increase,t.any_unit_conflict,t.new_core_drug,
               t.early_snapshot_compatible,t.continue_snapshot_compatible,
               h.* EXCLUDE(stay_id,grid_hour,interval_index,point_time)
        FROM analysis_grid g JOIN treatment_intervals t USING(stay_id,grid_hour)
        JOIN history_with_trajectory h ON h.stay_id=g.stay_id AND h.grid_hour=g.grid_hour AND h.interval_index=t.interval_index-1
        """
    )

    grid_path = restricted_derived / "mimic_analysis_grid_v1_5.csv.gz"
    interval_path = restricted_derived / "mimic_analysis_intervals_v1_5.csv.gz"
    con.execute(
        f"COPY (SELECT * FROM analysis_grid ORDER BY stay_id,grid_hour) TO '{grid_path.as_posix()}' (FORMAT CSV, HEADER, COMPRESSION GZIP)"
    )
    con.execute(
        f"COPY (SELECT * FROM analysis_intervals ORDER BY stay_id,grid_hour,interval_index) TO '{interval_path.as_posix()}' (FORMAT CSV, HEADER, COMPRESSION GZIP)"
    )

    # Safe aggregate audit; no patient-level values leave restricted_derived.
    funnel = []
    for step, table, condition in [
        ("adult_first_icu_abi", "core_stays", "TRUE"),
        ("candidate_ventilation_grids", "grids", "TRUE"),
        ("stable_eligible_grids", "eligible", "TRUE"),
        ("early_temporally_valid", "analysis_grid", "early_temporal_valid=1"),
        ("continued_at_6h", "analysis_grid", "observed_6h_strategy='continued_at_6h'"),
        ("contemporaneous_weaning", "analysis_grid", "contemporaneous_weaning=1"),
        ("unclassifiable", "analysis_grid", "observed_6h_strategy='unclassifiable'"),
    ]:
        n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}").fetchone()[0]
        stays = con.execute(f"SELECT COUNT(DISTINCT stay_id) FROM {table} WHERE {condition}").fetchone()[0]
        funnel.append({"step": step, "n_rows_or_grids": int(n), "n_stays": int(stays)})
    funnel_df = pd.DataFrame(funnel)
    funnel_path = result_dir / f"mimic_formal_funnel_{date.today().isoformat()}.csv"
    funnel_df.to_csv(funnel_path, index=False, encoding="utf-8-sig")

    strategy_outcome = con.execute(
        """
        SELECT observed_6h_strategy,COUNT(*) AS n_grids,COUNT(DISTINCT stay_id) AS n_stays,
               SUM(alive_success_extub_day7) AS outcome_events
        FROM analysis_grid GROUP BY observed_6h_strategy ORDER BY observed_6h_strategy
        """
    ).df()
    # This table is raw/unadjusted and remains restricted; it is not exported to the results directory.
    raw_audit_path = restricted_derived / "RESTRICTED_unadjusted_strategy_outcome_audit.csv"
    strategy_outcome.to_csv(raw_audit_path, index=False, encoding="utf-8-sig")

    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis_version": "1.5-posthoc-bias-targeted",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "PROTOCOL_v1.0.md + PROTOCOL_AMENDMENT_v1.1_PREOUTCOME.md + SAP_AMENDMENT_v1.5_POSTHOC_BIAS_TARGETED.md",
        "grid_file": str(grid_path),
        "interval_file": str(interval_path),
        "patient_level_outputs_restricted": True,
        "primary_outcome_source": "explicit extubation procedureevent",
        "broad_sensitivity_source": "invasive ventilation procedure interval end",
        "minimum_action_lead_minutes": 60,
        "posthoc_features": "six-hour predecision physiologic trajectories and baseline drug-specific rates/units",
    }
    metadata_path = restricted_derived / "analysis_ready_metadata_v1_1.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(funnel_df.to_string(index=False))
    print(f"GRID_RESTRICTED={grid_path}")
    print(f"INTERVAL_RESTRICTED={interval_path}")
    print(f"FUNNEL_SAFE={funnel_path}")
    print(f"UNADJUSTED_AUDIT_RESTRICTED={raw_audit_path}")
    print("PATIENT_LEVEL_CONSOLE_OUTPUT=NO")


if __name__ == "__main__":
    main()
