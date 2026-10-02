# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02 - Harvest technical metadata
# MAGIC Reads `information_schema` into a governance inventory (what a catalog scanner does in Informatica CDGC).

# COMMAND ----------

dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.governance.column_inventory AS
SELECT table_catalog, table_schema, table_name, column_name, data_type, comment,
       comment IS NOT NULL AND trim(comment) <> '' AS has_comment,
       current_timestamp() AS harvested_at
FROM {catalog}.information_schema.columns
WHERE table_schema IN ('raw', 'curated')
""")
display(spark.table(f"{catalog}.governance.column_inventory"))