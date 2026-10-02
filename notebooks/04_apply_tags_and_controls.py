# Databricks notebook source
# MAGIC %md
# MAGIC # 04 - Apply Unity Catalog tags, column masks, row filter, grants
# MAGIC High-confidence results are applied automatically; the rest land in a steward review queue.
# MAGIC Groups `pii_readers`, `global_ops`, `analysts` must exist as account groups (missing groups are skipped gracefully).

# COMMAND ----------
dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")
gov = f"{catalog}.governance"

res = spark.table(f"{gov}.classification_results").toPandas()
applied = []

# COMMAND ----------
# 1) Tags (discoverability + classification as metadata)
for r in res[res.status == "AUTO_APPLIED"].itertuples():
    fq = f"{catalog}.{r.table_schema}.{r.table_name}"
    pii = str(r.is_pii_prob >= 0.5).lower()
    spark.sql(f"ALTER TABLE {fq} ALTER COLUMN {r.column_name} "
              f"SET TAGS ('sensitivity' = '{r.sensitivity}', 'pii' = '{pii}', 'classified_by' = 'jev')")
    applied.append((fq, r.column_name, "TAG"))

# COMMAND ----------
# 2) Column masks (entitlement by group membership) for string/date PII
spark.sql(f"""CREATE OR REPLACE FUNCTION {gov}.mask_string(v STRING) RETURNS STRING
RETURN CASE WHEN is_account_group_member('pii_readers') THEN v ELSE '****' END""")
spark.sql(f"""CREATE OR REPLACE FUNCTION {gov}.mask_date(v DATE) RETURNS DATE
RETURN CASE WHEN is_account_group_member('pii_readers') THEN v ELSE NULL END""")

mask_fn = {"STRING": "mask_string", "DATE": "mask_date"}
for r in res[(res.status == "AUTO_APPLIED") & (res.mask_required)].itertuples():
    fn = mask_fn.get(r.data_type.upper())
    if not fn or r.table_schema != "raw":
        continue
    fq = f"{catalog}.{r.table_schema}.{r.table_name}"
    spark.sql(f"ALTER TABLE {fq} ALTER COLUMN {r.column_name} SET MASK {gov}.{fn}")
    applied.append((fq, r.column_name, "COLUMN_MASK"))

# COMMAND ----------
# 3) Row filter: only global_ops sees non-Indian tax residents
spark.sql(f"""CREATE OR REPLACE FUNCTION {gov}.in_residency_filter(tax_residency STRING) RETURNS BOOLEAN
RETURN is_account_group_member('global_ops') OR tax_residency = 'IN'""")
spark.sql(f"ALTER TABLE {catalog}.raw.accounts SET ROW FILTER {gov}.in_residency_filter ON (tax_residency)")
applied.append((f"{catalog}.raw.accounts", "tax_residency", "ROW_FILTER"))

# COMMAND ----------
# 4) Role-based grants (skipped if the group does not exist in your account)
grants = [
    f"GRANT USE CATALOG ON CATALOG {catalog} TO `analysts`",
    f"GRANT USE SCHEMA, SELECT ON SCHEMA {catalog}.curated TO `analysts`",
    f"GRANT USE SCHEMA, SELECT ON SCHEMA {catalog}.raw TO `pii_readers`",
]
for g in grants:
    try:
        spark.sql(g)
        applied.append((g, "", "GRANT"))
    except Exception as e:
        print("skipped:", g, "->", str(e)[:120])

# COMMAND ----------
ctl = spark.createDataFrame(applied, "object string, column_name string, control string") \
           .withColumn("applied_at", __import__("pyspark.sql.functions", fromlist=["x"]).current_timestamp())
ctl.write.mode("overwrite").saveAsTable(f"{gov}.applied_controls")

spark.sql(f"""CREATE OR REPLACE VIEW {gov}.v_steward_queue AS
SELECT table_schema, table_name, column_name, sensitivity, round(is_pii_prob, 2) AS pii_prob,
       round(sens_confidence, 2) AS confidence, sens_probs
FROM {gov}.classification_results WHERE status = 'STEWARD_REVIEW'""")
display(spark.table(f"{gov}.v_steward_queue"))
