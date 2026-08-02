from __future__ import annotations

import os
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
VENDOR = Path(os.environ.get("WTW_VENDOR_DIR", PROJECT_ROOT / "04_code" / "vendor")).resolve()
sys.path.insert(0, str(VENDOR))

import duckdb
import pandas as pd


def main() -> None:
    eicu = (
        PROJECT_ROOT
        / "00_restricted_data"
        / "eICU-CRD"
        / "2.0"
        / "extracted"
        / "eicu-collaborative-research-database-2.0"
    )
    restricted_derived = PROJECT_ROOT / "00_restricted_data" / "derived" / "eicu_transport_v1_0"
    result_dir = PROJECT_ROOT / "05_results" / "formal_analysis" / "eicu"
    temp_dir = PROJECT_ROOT / "00_restricted_data" / "_duckdb_tmp"
    restricted_derived.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET threads=4")
    con.execute("SET memory_limit='8GB'")
    con.execute(f"SET temp_directory='{temp_dir.as_posix()}'")
    csv_opts = "header=true, all_varchar=true, quote='\"', escape='\"'"

    con.execute(
        f"""
        CREATE TEMP TABLE first_icu AS
        WITH ranked AS (
          SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
                 patienthealthsystemstayid,uniquepid,gender,ethnicity,hospitalid,wardid,
                 apacheadmissiondx,admissionweight,unittype,unitadmitsource,unitstaytype,
                 TRY_CAST(unitdischargeoffset AS BIGINT) AS unitdischargeoffset,
                 TRY_CAST(hospitaldischargeoffset AS BIGINT) AS hospitaldischargeoffset,
                 unitdischargestatus,hospitaldischargestatus,
                 CASE WHEN age='> 89' THEN 90 ELSE TRY_CAST(age AS INTEGER) END AS age,
                 ROW_NUMBER() OVER (
                   PARTITION BY uniquepid
                   ORDER BY TRY_CAST(unitvisitnumber AS INTEGER),TRY_CAST(patientunitstayid AS BIGINT)
                 ) AS rn
          FROM read_csv(?,{csv_opts})
        )
        SELECT * EXCLUDE(rn) FROM ranked WHERE rn=1 AND age>=18
        """,
        [str(eicu / "patient.csv.gz")],
    )

    con.execute(
        f"""
        CREATE TEMP TABLE diagnoses AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               LOWER(COALESCE(diagnosisstring,'')) AS diagnosisstring,
               UPPER(REPLACE(COALESCE(icd9code,''),'.','')) AS code,
               TRY_CAST(diagnosisoffset AS BIGINT) AS diagnosisoffset,
               LOWER(COALESCE(diagnosispriority,'')) AS diagnosispriority
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "diagnosis.csv.gz")],
    )
    con.execute(
        """
        CREATE TEMP TABLE abi_phenotype AS
        SELECT patientunitstayid,
          MAX(CASE WHEN REGEXP_MATCHES(diagnosisstring,'traumatic brain injury|head injury|cerebral contusion|skull fracture')
                        OR REGEXP_MATCHES(code,'^(80[0-4]|85[0-4])') THEN 1 ELSE 0 END) AS tbi,
          MAX(CASE WHEN diagnosisstring LIKE '%subarachnoid%' OR code LIKE '430%' THEN 1 ELSE 0 END) AS sah,
          MAX(CASE WHEN diagnosisstring LIKE '%intracerebral hemorrhage%' OR diagnosisstring LIKE '%intracranial hemorrhage%'
                        OR code LIKE '431%' THEN 1 ELSE 0 END) AS ich,
          MAX(CASE WHEN diagnosisstring LIKE '%cerebral infarct%' OR diagnosisstring LIKE '%ischemic stroke%'
                        OR code LIKE '436%' OR REGEXP_MATCHES(code,'^(433|434).*1$') THEN 1 ELSE 0 END) AS ais,
          MAX(CASE WHEN REGEXP_MATCHES(diagnosisstring,'anoxic|hypoxic brain|cardiac arrest')
                        OR code LIKE '4275%' THEN 1 ELSE 0 END) AS primary_hypoxic_arrest
        FROM diagnoses GROUP BY patientunitstayid
        """
    )

    con.execute(
        f"""
        CREATE TEMP TABLE respiratory_raw AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(ventstartoffset AS BIGINT) AS ventstartoffset,
               TRY_CAST(ventendoffset AS BIGINT) AS ventendoffset,
               TRY_CAST(priorventstartoffset AS BIGINT) AS priorventstartoffset,
               TRY_CAST(priorventendoffset AS BIGINT) AS priorventendoffset
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "respiratoryCare.csv.gz")],
    )
    con.execute(
        """
        CREATE TEMP TABLE vent_intervals AS
        SELECT DISTINCT patientunitstayid,vent_start,vent_end FROM (
          SELECT patientunitstayid,ventstartoffset AS vent_start,ventendoffset AS vent_end FROM respiratory_raw
          UNION ALL
          SELECT patientunitstayid,priorventstartoffset AS vent_start,priorventendoffset AS vent_end FROM respiratory_raw
        ) x
        WHERE vent_start IS NOT NULL AND vent_end IS NOT NULL AND vent_end>vent_start
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE first_vent AS
        SELECT patientunitstayid,MIN(vent_start) AS first_vent_start
        FROM vent_intervals GROUP BY patientunitstayid
        """
    )

    con.execute(
        f"""
        CREATE TEMP TABLE infusion AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(infusionoffset AS BIGINT) AS infusionoffset,
               LOWER(TRIM(COALESCE(drugname,''))) AS label_key,
               CASE
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'propofol') THEN 'propofol'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'dexmed|precedex') THEN 'dexmedetomidine'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'midazolam|versed') THEN 'midazolam'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'norepinephrine|levophed|epinephrine|vasopressin|phenylephrine|dopamine') THEN 'vasopressor'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'fentanyl|morphine|hydromorphone|remifentanil|sufentanil') THEN 'opioid'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'ketamine') THEN 'ketamine'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'rocuronium|vecuronium|cisatracurium|atracurium|pancuronium|succinylcholine') THEN 'nmba'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'pentobarbital|thiopental') THEN 'barbiturate'
                 WHEN REGEXP_MATCHES(LOWER(COALESCE(drugname,'')),'mannitol|hypertonic saline|sodium chloride 3%|sodium chloride 23') THEN 'hyperosmolar'
               END AS drug_class,
               CASE WHEN TRY_CAST(drugrate AS DOUBLE) IS NOT NULL THEN 'drugrate'
                    WHEN TRY_CAST(infusionrate AS DOUBLE) IS NOT NULL THEN 'infusionrate'
                    ELSE '__UNPARSEABLE__' END AS rate_field,
               COALESCE(TRY_CAST(drugrate AS DOUBLE),TRY_CAST(infusionrate AS DOUBLE)) AS rate_value
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "infusionDrug.csv.gz")],
    )

    con.execute(
        """
        CREATE TEMP TABLE cohort AS
        SELECT f.*,a.tbi,a.sah,a.ich,a.ais,a.primary_hypoxic_arrest,v.first_vent_start,
               CASE WHEN a.tbi=1 THEN 'TBI' WHEN a.sah=1 THEN 'SAH'
                    WHEN a.ich=1 THEN 'ICH' WHEN a.ais=1 THEN 'AIS' END AS abi_subtype
        FROM first_icu f JOIN abi_phenotype a USING(patientunitstayid)
        JOIN first_vent v USING(patientunitstayid)
        JOIN (SELECT DISTINCT patientunitstayid FROM infusion
              WHERE drug_class IN ('propofol','midazolam','dexmedetomidine')
                AND rate_value IS NOT NULL) s USING(patientunitstayid)
        WHERE (a.tbi=1 OR a.sah=1 OR a.ich=1 OR a.ais=1)
          AND COALESCE(a.primary_hypoxic_arrest,0)=0
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE grids AS
        SELECT c.*,h.grid_hour,c.first_vent_start+h.grid_hour*60 AS grid_offset
        FROM cohort c,generate_series(12,96,6) h(grid_hour)
        WHERE c.first_vent_start+h.grid_hour*60<=c.unitdischargeoffset
          AND EXISTS (
            SELECT 1 FROM vent_intervals v WHERE v.patientunitstayid=c.patientunitstayid
              AND v.vent_start<=c.first_vent_start+h.grid_hour*60
              AND v.vent_end>c.first_vent_start+h.grid_hour*60
          )
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE points AS
        SELECT g.patientunitstayid,g.grid_hour,k.interval_index,
               g.grid_offset+k.interval_index*360 AS point_offset
        FROM grids g,generate_series(0,4,1) k(interval_index)
        """
    )

    con.execute(
        f"""
        CREATE TEMP TABLE map_values AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(observationoffset AS BIGINT) AS observationoffset,
               TRY_CAST(systemicmean AS DOUBLE) AS map_value
        FROM read_csv(?,{csv_opts}) WHERE TRY_CAST(systemicmean AS DOUBLE) BETWEEN 20 AND 200
        UNION ALL
        SELECT TRY_CAST(patientunitstayid AS BIGINT),TRY_CAST(observationoffset AS BIGINT),
               TRY_CAST(noninvasivemean AS DOUBLE)
        FROM read_csv(?,{csv_opts}) WHERE TRY_CAST(noninvasivemean AS DOUBLE) BETWEEN 20 AND 200
        """,
        [str(eicu / "vitalPeriodic.csv.gz"), str(eicu / "vitalAperiodic.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE periodic AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(observationoffset AS BIGINT) AS observationoffset,
               TRY_CAST(heartrate AS DOUBLE) AS heart_rate,
               TRY_CAST(temperature AS DOUBLE) AS temperature_c,
               TRY_CAST(icp AS DOUBLE) AS icp
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "vitalPeriodic.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE respiratory_chart AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(respchartoffset AS BIGINT) AS observationoffset,
               LOWER(COALESCE(respchartvaluelabel,'')) AS label,
               TRY_CAST(REPLACE(REPLACE(COALESCE(respchartvalue,''),'%',''),',','') AS DOUBLE) AS value_num
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "respiratoryCharting.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE nurse_chart AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(nursingchartoffset AS BIGINT) AS observationoffset,
               LOWER(COALESCE(nursingchartcelltypevallabel,'')||' '||COALESCE(nursingchartcelltypevalname,'')) AS label,
               TRY_CAST(REPLACE(COALESCE(nursingchartvalue,''),',','') AS DOUBLE) AS value_num
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "nurseCharting.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE labs AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(labresultoffset AS BIGINT) AS observationoffset,
               LOWER(COALESCE(labname,'')) AS label,
               TRY_CAST(labresult AS DOUBLE) AS value_num
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "lab.csv.gz")],
    )
    con.execute(
        f"""
        CREATE TEMP TABLE treatments AS
        SELECT TRY_CAST(patientunitstayid AS BIGINT) AS patientunitstayid,
               TRY_CAST(treatmentoffset AS BIGINT) AS treatmentoffset,
               LOWER(COALESCE(treatmentstring,'')) AS treatmentstring
        FROM read_csv(?,{csv_opts})
        """,
        [str(eicu / "treatment.csv.gz")],
    )

    con.execute(
        """
        CREATE TEMP TABLE point_history AS
        WITH hemodynamics AS (
          SELECT p.patientunitstayid,p.grid_hour,p.interval_index,
                 MEDIAN(m.map_value) AS map_median_2h,MIN(m.map_value) AS map_min_2h,
                 ARG_MAX(v.heart_rate,v.observationoffset) AS heart_rate,
                 ARG_MAX(v.temperature_c,v.observationoffset) AS temperature_c,
                 ARG_MAX(v.icp,v.observationoffset) AS icp_latest,
                 MAX(v.icp) AS icp_max_2h
          FROM points p LEFT JOIN map_values m ON m.patientunitstayid=p.patientunitstayid
            AND m.observationoffset>p.point_offset-120 AND m.observationoffset<=p.point_offset
          LEFT JOIN periodic v ON v.patientunitstayid=p.patientunitstayid
            AND v.observationoffset>p.point_offset-360 AND v.observationoffset<=p.point_offset
          GROUP BY p.patientunitstayid,p.grid_hour,p.interval_index
        ), respiratory AS (
          SELECT p.patientunitstayid,p.grid_hour,p.interval_index,
                 ARG_MAX(CASE WHEN r.value_num>1.5 THEN r.value_num/100.0 ELSE r.value_num END,r.observationoffset)
                   FILTER(WHERE REGEXP_MATCHES(r.label,'fio2|fraction.*inspired')) AS fio2,
                 ARG_MAX(r.value_num,r.observationoffset)
                   FILTER(WHERE r.label LIKE '%peep%' AND r.value_num BETWEEN 0 AND 40) AS peep
          FROM points p LEFT JOIN respiratory_chart r ON r.patientunitstayid=p.patientunitstayid
            AND r.observationoffset>p.point_offset-360 AND r.observationoffset<=p.point_offset
          GROUP BY p.patientunitstayid,p.grid_hour,p.interval_index
        ), neurologic AS (
          SELECT p.patientunitstayid,p.grid_hour,p.interval_index,
                 ARG_MAX(n.value_num,n.observationoffset)
                   FILTER(WHERE n.label LIKE '%rass%' AND n.value_num BETWEEN -5 AND 4) AS rass,
                 ARG_MAX(n.value_num,n.observationoffset)
                   FILTER(WHERE REGEXP_MATCHES(n.label,'glasgow|(^|[^a-z])gcs([^a-z]|$)')) AS gcs_value,
                 COUNT(n.observationoffset)
                   FILTER(WHERE n.label LIKE '%rass%' OR REGEXP_MATCHES(n.label,'glasgow|(^|[^a-z])gcs([^a-z]|$)')) AS neuro_measure_count
          FROM points p LEFT JOIN nurse_chart n ON n.patientunitstayid=p.patientunitstayid
            AND n.observationoffset>p.point_offset-360 AND n.observationoffset<=p.point_offset
          GROUP BY p.patientunitstayid,p.grid_hour,p.interval_index
        ), laboratory AS (
          SELECT p.patientunitstayid,p.grid_hour,p.interval_index,
                 ARG_MAX(l.value_num,l.observationoffset) FILTER(WHERE l.label LIKE '%lactate%') AS lactate,
                 ARG_MAX(l.value_num,l.observationoffset) FILTER(WHERE l.label LIKE '%creatinine%') AS creatinine,
                 ARG_MAX(l.value_num,l.observationoffset) FILTER(WHERE l.label LIKE '%bilirubin%') AS bilirubin,
                 ARG_MAX(l.value_num,l.observationoffset) FILTER(WHERE REGEXP_MATCHES(l.label,'paco2|pco2')) AS paco2,
                 ARG_MAX(l.value_num,l.observationoffset) FILTER(WHERE REGEXP_MATCHES(l.label,'pao2|po2')) AS pao2
          FROM points p LEFT JOIN labs l ON l.patientunitstayid=p.patientunitstayid
            AND l.observationoffset>p.point_offset-1440 AND l.observationoffset<=p.point_offset
          GROUP BY p.patientunitstayid,p.grid_hour,p.interval_index
        ), observed_drugs AS (
          SELECT p.patientunitstayid,p.grid_hour,p.interval_index,
                 MAX(CASE WHEN i.drug_class='vasopressor' THEN 1 ELSE 0 END) AS vasopressor_observed,
                 MAX(CASE WHEN i.drug_class='opioid' THEN 1 ELSE 0 END) AS opioid_observed,
                 MAX(CASE WHEN i.drug_class='ketamine' THEN 1 ELSE 0 END) AS ketamine_observed,
                 MAX(CASE WHEN i.drug_class='nmba' AND i.infusionoffset>p.point_offset-120 THEN 1 ELSE 0 END) AS nmba_recent2h,
                 MAX(CASE WHEN i.drug_class='barbiturate' THEN 1 ELSE 0 END) AS barbiturate_recent6h,
                 MAX(CASE WHEN i.drug_class='hyperosmolar' THEN 1 ELSE 0 END) AS hyperosmolar_recent6h
          FROM points p LEFT JOIN infusion i ON i.patientunitstayid=p.patientunitstayid
            AND i.infusionoffset>p.point_offset-360 AND i.infusionoffset<=p.point_offset
          GROUP BY p.patientunitstayid,p.grid_hour,p.interval_index
        )
        SELECT h.*,r.fio2,r.peep,n.rass,n.gcs_value,n.neuro_measure_count,
               l.lactate,l.creatinine,l.bilirubin,l.paco2,l.pao2,
               d.vasopressor_observed,d.opioid_observed,d.ketamine_observed,
               d.nmba_recent2h,d.barbiturate_recent6h,d.hyperosmolar_recent6h,
               CASE WHEN r.fio2>0 THEN l.pao2/r.fio2 END AS pao2_fio2
        FROM hemodynamics h JOIN respiratory r USING(patientunitstayid,grid_hour,interval_index)
        JOIN neurologic n USING(patientunitstayid,grid_hour,interval_index)
        JOIN laboratory l USING(patientunitstayid,grid_hour,interval_index)
        JOIN observed_drugs d USING(patientunitstayid,grid_hour,interval_index)
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE baseline_core AS
        WITH candidates AS (
          SELECT g.patientunitstayid,g.grid_hour,g.grid_offset,i.drug_class,i.label_key,i.rate_field,
                 i.rate_value,i.infusionoffset,
                 ROW_NUMBER() OVER(
                   PARTITION BY g.patientunitstayid,g.grid_hour,i.drug_class,i.label_key,i.rate_field
                   ORDER BY i.infusionoffset DESC
                 ) AS rn
          FROM grids g JOIN infusion i ON i.patientunitstayid=g.patientunitstayid
          WHERE i.drug_class IN ('propofol','midazolam','dexmedetomidine')
            AND i.rate_value>0 AND i.rate_field<>'__UNPARSEABLE__'
            AND i.infusionoffset>g.grid_offset-360 AND i.infusionoffset<=g.grid_offset
        )
        SELECT * EXCLUDE(rn) FROM candidates WHERE rn=1
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE trach_events AS
        SELECT patientunitstayid,MIN(treatmentoffset) AS tracheostomy_offset
        FROM treatments WHERE REGEXP_MATCHES(treatmentstring,'tracheostom|tracheotomy')
        GROUP BY patientunitstayid
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE eligible AS
        WITH base AS (
          SELECT patientunitstayid,grid_hour,COUNT(*) AS baseline_stream_count,
                 COUNT(DISTINCT drug_class) AS baseline_drug_count,
                 MAX(CASE WHEN drug_class='propofol' THEN 1 ELSE 0 END) AS propofol_active,
                 MAX(CASE WHEN drug_class='midazolam' THEN 1 ELSE 0 END) AS midazolam_active,
                 MAX(CASE WHEN drug_class='dexmedetomidine' THEN 1 ELSE 0 END) AS dexmed_active
          FROM baseline_core GROUP BY patientunitstayid,grid_hour
        )
        SELECT g.*,h.* EXCLUDE(patientunitstayid,grid_hour,interval_index),
               b.* EXCLUDE(patientunitstayid,grid_hour),t.tracheostomy_offset
        FROM grids g JOIN point_history h ON h.patientunitstayid=g.patientunitstayid
          AND h.grid_hour=g.grid_hour AND h.interval_index=0
        JOIN base b ON b.patientunitstayid=g.patientunitstayid AND b.grid_hour=g.grid_hour
        LEFT JOIN trach_events t ON t.patientunitstayid=g.patientunitstayid
        WHERE h.map_median_2h>=65 AND h.map_min_2h>=60
          AND h.fio2<=0.60 AND h.peep<=10
          AND h.neuro_measure_count>0
          AND COALESCE(h.nmba_recent2h,0)=0
          AND COALESCE(h.barbiturate_recent6h,0)=0
          AND COALESCE(h.hyperosmolar_recent6h,0)=0
          AND (h.icp_latest IS NULL OR (h.icp_latest<=22 AND COALESCE(h.icp_max_2h,h.icp_latest)<=22))
          AND (t.tracheostomy_offset IS NULL OR t.tracheostomy_offset>g.grid_offset)
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE treatment_intervals AS
        WITH interval_index AS (
          SELECT e.patientunitstayid,e.grid_hour,e.grid_offset,k.interval_index
          FROM eligible e,generate_series(1,4,1) k(interval_index)
        ), stream AS (
          SELECT x.patientunitstayid,x.grid_hour,x.interval_index,b.drug_class,b.label_key,b.rate_field,
                 b.rate_value AS baseline_rate,
                 MAX(CASE WHEN i.rate_value<=0.70*b.rate_value THEN 1 ELSE 0 END) AS rate_drop,
                 MAX(CASE WHEN i.rate_value>=1.30*b.rate_value THEN 1 ELSE 0 END) AS rate_increase,
                 COUNT(i.infusionoffset) AS followup_records,
                 MIN(i.infusionoffset) FILTER(WHERE i.rate_value<=0.70*b.rate_value) AS first_drop_offset
          FROM interval_index x JOIN baseline_core b USING(patientunitstayid,grid_hour)
          LEFT JOIN infusion i ON i.patientunitstayid=x.patientunitstayid
            AND i.drug_class=b.drug_class AND i.label_key=b.label_key AND i.rate_field=b.rate_field
            AND i.infusionoffset>x.grid_offset+(x.interval_index-1)*360
            AND i.infusionoffset<=x.grid_offset+x.interval_index*360
          GROUP BY x.patientunitstayid,x.grid_hour,x.interval_index,b.drug_class,b.label_key,b.rate_field,b.rate_value
        ), aggregate_stream AS (
          SELECT patientunitstayid,grid_hour,interval_index,
                 MAX(rate_drop) AS any_decrease,MAX(rate_increase) AS any_increase,
                 MIN(CASE WHEN followup_records>0 THEN 1 ELSE 0 END) AS all_streams_observed,
                 MIN(first_drop_offset) AS first_drop_offset
          FROM stream GROUP BY patientunitstayid,grid_hour,interval_index
        ), new_drug AS (
          SELECT x.patientunitstayid,x.grid_hour,x.interval_index,
                 MAX(CASE WHEN i.patientunitstayid IS NOT NULL AND b.drug_class IS NULL THEN 1 ELSE 0 END) AS new_core_drug
          FROM interval_index x
          LEFT JOIN infusion i ON i.patientunitstayid=x.patientunitstayid
            AND i.drug_class IN ('propofol','midazolam','dexmedetomidine') AND i.rate_value>0
            AND i.infusionoffset>x.grid_offset+(x.interval_index-1)*360
            AND i.infusionoffset<=x.grid_offset+x.interval_index*360
          LEFT JOIN (SELECT DISTINCT patientunitstayid,grid_hour,drug_class FROM baseline_core) b
            ON b.patientunitstayid=x.patientunitstayid AND b.grid_hour=x.grid_hour AND b.drug_class=i.drug_class
          GROUP BY x.patientunitstayid,x.grid_hour,x.interval_index
        )
        SELECT s.*,COALESCE(n.new_core_drug,0) AS new_core_drug,
          CASE WHEN s.any_decrease=1 AND s.any_increase=0 AND s.all_streams_observed=1
                    AND COALESCE(n.new_core_drug,0)=0 THEN 1 ELSE 0 END AS early_snapshot_compatible,
          CASE WHEN s.any_decrease=0 AND s.any_increase=0 AND s.all_streams_observed=1
                    AND COALESCE(n.new_core_drug,0)=0 THEN 1 ELSE 0 END AS continue_snapshot_compatible
        FROM aggregate_stream s JOIN new_drug n USING(patientunitstayid,grid_hour,interval_index)
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE outcome_events AS
        WITH vent_end AS (
          SELECT e.patientunitstayid,e.grid_hour,MIN(v.vent_end) AS ventilation_end_offset
          FROM eligible e LEFT JOIN vent_intervals v ON v.patientunitstayid=e.patientunitstayid
            AND v.vent_start<=e.grid_offset AND v.vent_end>e.grid_offset
          GROUP BY e.patientunitstayid,e.grid_hour
        ), renewed AS (
          SELECT x.patientunitstayid,x.grid_hour,MIN(v.vent_start) AS renewed_ventilation_offset
          FROM vent_end x LEFT JOIN vent_intervals v ON v.patientunitstayid=x.patientunitstayid
            AND v.vent_start>x.ventilation_end_offset AND v.vent_start<=x.ventilation_end_offset+2880
          GROUP BY x.patientunitstayid,x.grid_hour
        )
        SELECT e.patientunitstayid,e.grid_hour,v.ventilation_end_offset,r.renewed_ventilation_offset,
               CASE WHEN LOWER(COALESCE(e.unitdischargestatus,''))='expired' THEN e.unitdischargeoffset
                    WHEN LOWER(COALESCE(e.hospitaldischargestatus,''))='expired' THEN e.hospitaldischargeoffset END AS death_offset,
               CASE WHEN v.ventilation_end_offset IS NOT NULL
                          AND v.ventilation_end_offset<=e.grid_offset+10080
                          AND r.renewed_ventilation_offset IS NULL
                          AND (e.tracheostomy_offset IS NULL OR e.tracheostomy_offset>v.ventilation_end_offset+2880)
                          AND LOWER(COALESCE(e.unitdischargestatus,''))<>'expired'
                          AND LOWER(COALESCE(e.hospitaldischargestatus,''))<>'expired'
                    THEN 1 ELSE 0 END AS alive_vent_end_day7
        FROM eligible e JOIN vent_end v USING(patientunitstayid,grid_hour)
        JOIN renewed r USING(patientunitstayid,grid_hour)
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE interval_wide AS
        SELECT patientunitstayid,grid_hour,
               MAX(first_drop_offset) FILTER(WHERE interval_index=1) AS first_qualifying_action_offset,
               MAX(early_snapshot_compatible) FILTER(WHERE interval_index=1) AS early_compat_1,
               MAX(early_snapshot_compatible) FILTER(WHERE interval_index=2) AS early_compat_2,
               MAX(early_snapshot_compatible) FILTER(WHERE interval_index=3) AS early_compat_3,
               MAX(early_snapshot_compatible) FILTER(WHERE interval_index=4) AS early_compat_4,
               MAX(continue_snapshot_compatible) FILTER(WHERE interval_index=1) AS continue_compat_1,
               MAX(continue_snapshot_compatible) FILTER(WHERE interval_index=2) AS continue_compat_2,
               MAX(continue_snapshot_compatible) FILTER(WHERE interval_index=3) AS continue_compat_3,
               MAX(continue_snapshot_compatible) FILTER(WHERE interval_index=4) AS continue_compat_4
        FROM treatment_intervals GROUP BY patientunitstayid,grid_hour
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE analysis_grid AS
        SELECT e.*,o.* EXCLUDE(patientunitstayid,grid_hour),w.* EXCLUDE(patientunitstayid,grid_hour),
          CASE WHEN w.early_compat_1=1 AND w.first_qualifying_action_offset IS NOT NULL
                    AND (o.ventilation_end_offset IS NULL OR w.first_qualifying_action_offset<=o.ventilation_end_offset-60)
               THEN 1 ELSE 0 END AS early_temporal_valid,
          CASE WHEN w.early_compat_1=1 AND w.first_qualifying_action_offset IS NOT NULL
                    AND o.ventilation_end_offset IS NOT NULL
                    AND w.first_qualifying_action_offset>o.ventilation_end_offset-60
               THEN 1 ELSE 0 END AS contemporaneous_weaning,
          CASE WHEN w.early_compat_1=1 AND w.first_qualifying_action_offset IS NOT NULL
                    AND (o.ventilation_end_offset IS NULL OR w.first_qualifying_action_offset<=o.ventilation_end_offset-60)
                 THEN 'early_deescalation'
               WHEN w.continue_compat_1=1 THEN 'continued_at_6h'
               WHEN w.early_compat_1=1 THEN 'contemporaneous_weaning'
               ELSE 'unclassifiable' END AS observed_6h_strategy
        FROM eligible e JOIN outcome_events o USING(patientunitstayid,grid_hour)
        JOIN interval_wide w USING(patientunitstayid,grid_hour)
        """
    )
    con.execute(
        """
        CREATE TEMP TABLE analysis_intervals AS
        SELECT g.*,t.interval_index,t.any_decrease,t.any_increase,t.all_streams_observed,t.new_core_drug,
               t.early_snapshot_compatible,t.continue_snapshot_compatible,
               h.* EXCLUDE(patientunitstayid,grid_hour,interval_index)
        FROM analysis_grid g JOIN treatment_intervals t USING(patientunitstayid,grid_hour)
        JOIN point_history h ON h.patientunitstayid=g.patientunitstayid
          AND h.grid_hour=g.grid_hour AND h.interval_index=t.interval_index
        """
    )

    grid_path = restricted_derived / "eicu_analysis_grid_transport_v1_0.csv.gz"
    interval_path = restricted_derived / "eicu_analysis_intervals_transport_v1_0.csv.gz"
    con.execute(
        f"COPY (SELECT * FROM analysis_grid ORDER BY patientunitstayid,grid_hour) TO '{grid_path.as_posix()}' (HEADER, DELIMITER ',', COMPRESSION GZIP)"
    )
    con.execute(
        f"COPY (SELECT * FROM analysis_intervals ORDER BY patientunitstayid,grid_hour,interval_index) TO '{interval_path.as_posix()}' (HEADER, DELIMITER ',', COMPRESSION GZIP)"
    )

    funnel = []
    for step, query in [
        ("adult_first_icu_abi_vent_sedative", "SELECT COUNT(DISTINCT patientunitstayid) FROM cohort"),
        ("candidate_ventilation_grids", "SELECT COUNT(*) FROM grids"),
        ("eligible_stable_grids", "SELECT COUNT(*) FROM eligible"),
        ("early_temporally_valid_grids", "SELECT COUNT(*) FROM analysis_grid WHERE early_temporal_valid=1"),
        ("continued_at_6h_grids", "SELECT COUNT(*) FROM analysis_grid WHERE observed_6h_strategy='continued_at_6h'"),
        ("contemporaneous_weaning_grids", "SELECT COUNT(*) FROM analysis_grid WHERE contemporaneous_weaning=1"),
        ("unclassifiable_grids", "SELECT COUNT(*) FROM analysis_grid WHERE observed_6h_strategy='unclassifiable'"),
    ]:
        funnel.append({"step": step, "n": int(con.execute(query).fetchone()[0])})
    funnel_path = result_dir / f"eicu_transport_funnel_{date.today().isoformat()}.csv"
    pd.DataFrame(funnel).to_csv(funnel_path, index=False, encoding="utf-8-sig")

    raw = con.execute(
        """
        SELECT observed_6h_strategy,COUNT(*) AS n_grids,COUNT(DISTINCT patientunitstayid) AS n_stays,
               SUM(alive_vent_end_day7) AS outcome_events
        FROM analysis_grid GROUP BY observed_6h_strategy ORDER BY observed_6h_strategy
        """
    ).df()
    raw.to_csv(
        restricted_derived / "RESTRICTED_unadjusted_transport_strategy_outcome_audit.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metadata = {
        "study_id": "WHEN-TO-WAKE-ABI",
        "analysis_role": "eICU measurement-aware transport",
        "analysis_version": "1.0",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "grid_file": str(grid_path),
        "interval_file": str(interval_path),
        "patient_level_outputs_restricted": True,
        "primary_outcome": "alive reconstructed ventilation end by day 7 without renewed ventilation within 48 hours",
        "explicit_extubation_claim_permitted": False,
        "point_gaps_interpreted_as_drug_stops": False,
    }
    (restricted_derived / "eicu_analysis_ready_metadata_v1_0.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(pd.DataFrame(funnel).to_string(index=False))
    print(f"GRID={grid_path}")
    print(f"INTERVALS={interval_path}")
    print(f"FUNNEL={funnel_path}")


if __name__ == "__main__":
    main()
