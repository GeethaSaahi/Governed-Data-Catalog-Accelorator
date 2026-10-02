# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - AI-assisted classification with TypeSafe Jev
# MAGIC Jev returns typed answers with probabilities. Only column **metadata** is sent, never data values.
# MAGIC Setup once (CLI): `databricks secrets create-scope gov` then `databricks secrets put-secret gov openrouter_key`

# COMMAND ----------
import os, sys, json
sys.path.append(os.path.abspath(".."))
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from govjev.jev_client import decide, CLASSIFY_QUESTIONS
from govjev.policy import classification_status, mask_required

dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")
api_key = dbutils.secrets.get("gov", "openrouter_key")

inv = spark.table(f"{catalog}.governance.column_inventory").toPandas()

# COMMAND ----------
def classify(r):
    state = {
        "domain": "asset management: investors, accounts, funds, transactions",
        "table": r.table_name,
        "column": r.column_name,
        "data_type": r.data_type,
        "description": r.comment if isinstance(r.comment, str) else "none",
    }
    res = decide(state, CLASSIFY_QUESTIONS, api_key)
    a = res["answers"]
    pii, sens = a["is_pii"]["noul"], a["sensitivity"]
    return {
        "table_schema": r.table_schema, "table_name": r.table_name,
        "column_name": r.column_name, "data_type": r.data_type,
        "is_pii_prob": float(pii),
        "sensitivity": sens["choice"],
        "sens_confidence": float(sens["confidence"]),
        "sens_probs": json.dumps(sens["probabilities"]),
        "status": classification_status(pii, sens["confidence"]),
        "mask_required": bool(mask_required(pii, sens["choice"])),
        "model": res.get("model"),
        "cost_usd": float(res.get("usage", {}).get("cost", 0.0)),
    }

with ThreadPoolExecutor(max_workers=8) as ex:
    rows = list(ex.map(classify, inv.itertuples()))

out = pd.DataFrame(rows)
out["classified_at"] = pd.Timestamp.now()
(spark.createDataFrame(out).write.mode("overwrite")
      .saveAsTable(f"{catalog}.governance.classification_results"))

display(spark.table(f"{catalog}.governance.classification_results")
        .orderBy("status", "sensitivity"))
print("Total Jev cost (USD):", out.cost_usd.sum())
