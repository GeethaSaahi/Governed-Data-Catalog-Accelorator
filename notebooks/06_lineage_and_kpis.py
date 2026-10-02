# Databricks notebook source
# MAGIC %md
# MAGIC # 06 - Lineage + governance KPIs
# MAGIC Lineage is captured automatically by Unity Catalog. Also open **Catalog > fund_exposure > Lineage** to show the graph.
# MAGIC System tables may need an admin to enable `system.access` and can lag by several minutes.

# COMMAND ----------
dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")
gov = f"{catalog}.governance"

# COMMAND ----------
try:
    display(spark.sql(f"""
      SELECT DISTINCT source_table_full_name, target_table_full_name
      FROM system.access.table_lineage
      WHERE target_table_full_name = '{catalog}.curated.fund_exposure'"""))
    display(spark.sql(f"""
      SELECT DISTINCT source_table_full_name, source_column_name, target_column_name
      FROM system.access.column_lineage
      WHERE target_table_full_name = '{catalog}.curated.fund_exposure'"""))
except Exception as e:
    print("System lineage tables not available yet - use the Lineage tab in Catalog Explorer.", str(e)[:150])

# COMMAND ----------
spark.sql(f"""
CREATE OR REPLACE VIEW {gov}.v_governance_kpis AS
SELECT
  (SELECT count(*) FROM {gov}.column_inventory)                                              AS total_columns,
  (SELECT count(*) FROM {gov}.classification_results)                                        AS classified_columns,
  (SELECT round(100 * avg(CASE WHEN has_comment THEN 1 ELSE 0 END), 1) FROM {gov}.column_inventory) AS pct_columns_documented,
  (SELECT count(*) FROM {gov}.classification_results WHERE status = 'STEWARD_REVIEW')        AS steward_queue,
  (SELECT count(*) FROM {gov}.classification_results WHERE mask_required)                    AS pii_or_restricted_columns,
  (SELECT count(*) FROM {gov}.applied_controls WHERE control = 'COLUMN_MASK')                AS masks_applied,
  (SELECT count(*) FROM {gov}.access_request_decisions WHERE final_action = 'AUTO_APPROVE')  AS auto_approved_requests,
  (SELECT count(*) FROM {gov}.access_request_decisions WHERE final_action = 'HUMAN_APPROVAL') AS human_review_requests
""")
display(spark.table(f"{gov}.v_governance_kpis"))
