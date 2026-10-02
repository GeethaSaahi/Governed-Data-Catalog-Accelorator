# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Catalog, schemas and synthetic asset-management data
# MAGIC Creates `raw` (investors, accounts, fund_master, transactions), `curated` (fund_exposure) and `governance` schemas.

# COMMAND ----------
dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")

# If you cannot create catalogs, create/choose one in the UI and pass its name in the widget.
spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
for s in ["raw", "curated", "governance"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{s}")

# COMMAND ----------
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.raw.investors AS
SELECT concat('INV', lpad(cast(id AS STRING), 5, '0')) AS investor_id,
       concat('Investor ', id) AS full_name,
       concat('investor', id, '@example.com') AS email,
       concat('9', lpad(cast(cast(rand() * 1000000000 AS BIGINT) AS STRING), 9, '0')) AS phone,
       concat(chr(cast(65 + id % 26 AS INT)), 'ABCD', lpad(cast(id AS STRING), 4, '0'), 'E') AS pan_number,
       date_add(DATE'1960-01-01', cast(rand() * 15000 AS INT)) AS date_of_birth,
       element_at(array('Bengaluru','Mumbai','Chennai','Delhi'), cast(id % 4 + 1 AS INT)) AS city,
       element_at(array('VERIFIED','PENDING'), cast(id % 2 + 1 AS INT)) AS kyc_status
FROM range(1, 501)
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.raw.accounts AS
SELECT concat('ACC', lpad(cast(id AS STRING), 6, '0')) AS account_id,
       concat('INV', lpad(cast(1 + id % 500 AS STRING), 5, '0')) AS investor_id,
       element_at(array('FT_EQ_01','FT_DEBT_02','FT_HYB_03','FT_LIQ_04'), cast(id % 4 + 1 AS INT)) AS fund_code,
       date_add(DATE'2018-01-01', cast(rand() * 2800 AS INT)) AS account_open_date,
       round(rand() * 5000000, 2) AS balance_inr,
       element_at(array('IN','IN','IN','US'), cast(id % 4 + 1 AS INT)) AS tax_residency
FROM range(1, 1001)
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.raw.fund_master AS
SELECT * FROM VALUES
  ('FT_EQ_01',   'Franklin India Equity Fund',    'Equity', 112.45, 8400.5),
  ('FT_DEBT_02', 'Franklin India Debt Fund',      'Debt',    34.10, 5200.0),
  ('FT_HYB_03',  'Franklin India Hybrid Fund',    'Hybrid',  58.72, 3100.7),
  ('FT_LIQ_04',  'Franklin India Liquid Fund',    'Liquid', 1012.30, 9900.2)
AS t(fund_code, fund_name, category, nav, aum_cr)
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.raw.transactions AS
SELECT concat('TXN', lpad(cast(id AS STRING), 7, '0')) AS txn_id,
       concat('ACC', lpad(cast(1 + id % 1000 AS STRING), 6, '0')) AS account_id,
       element_at(array('FT_EQ_01','FT_DEBT_02','FT_HYB_03','FT_LIQ_04'), cast(id % 4 + 1 AS INT)) AS fund_code,
       element_at(array('SUBSCRIPTION','REDEMPTION'), cast(id % 2 + 1 AS INT)) AS txn_type,
       round(rand() * 200000, 2) AS amount_inr,
       timestampadd(MINUTE, cast(rand() * 500000 AS INT), TIMESTAMP'2026-01-01 00:00:00') AS txn_ts
FROM range(1, 3001)
""")

# COMMAND ----------
# A few column descriptions only - the rest stay undocumented on purpose (a governance KPI later)
comments = {
    ("investors", "investor_id"): "Unique investor identifier",
    ("investors", "kyc_status"): "KYC verification state",
    ("accounts", "fund_code"): "Fund the account holds units in",
    ("fund_master", "fund_name"): "Official scheme name",
    ("transactions", "txn_type"): "SUBSCRIPTION or REDEMPTION",
}
for (t, c), text in comments.items():
    spark.sql(f"ALTER TABLE {catalog}.raw.{t} ALTER COLUMN {c} COMMENT '{text}'")

# COMMAND ----------
# Curated, PII-free gold table built from raw -> Unity Catalog captures lineage automatically
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.curated.fund_exposure AS
SELECT f.fund_code, f.fund_name, f.category, i.city,
       count(DISTINCT a.investor_id) AS investors,
       round(sum(a.balance_inr), 2) AS total_balance_inr
FROM {catalog}.raw.accounts a
JOIN {catalog}.raw.investors i ON a.investor_id = i.investor_id
JOIN {catalog}.raw.fund_master f ON a.fund_code = f.fund_code
GROUP BY f.fund_code, f.fund_name, f.category, i.city
""")
