# Databricks notebook source
# MAGIC %md
# MAGIC # 05 - Entitlement request triage with Jev
# MAGIC Jev recommends (approve / escalate / deny + risk score). **Policy code decides**: confidential or restricted data always goes to a human.

# COMMAND ----------
import os, sys, json
sys.path.append(os.path.abspath(".."))
import pandas as pd
from govjev.jev_client import decide, ACCESS_QUESTIONS
from govjev.policy import access_action, SENS_RANK

dbutils.widgets.text("catalog", "fin_gov_dev")
catalog = dbutils.widgets.get("catalog")
api_key = dbutils.secrets.get("gov", "openrouter_key")

res = spark.table(f"{catalog}.governance.classification_results").toPandas()
rank_to_name = {v: k for k, v in SENS_RANK.items()}
table_sens = (res.assign(rank=res.sensitivity.map(SENS_RANK))
                 .groupby("table_name")["rank"].max().map(rank_to_name).to_dict())

requests_ = [
    {"requester": "a.rao",   "role": "BI analyst",         "table": "fund_exposure", "duration_days": 30,  "justification": "Monthly AUM dashboard for fund managers"},
    {"requester": "m.iyer",  "role": "Marketing intern",   "table": "investors",     "duration_days": 365, "justification": "need data"},
    {"requester": "s.khan",  "role": "Compliance officer", "table": "investors",     "duration_days": 14,  "justification": "KYC audit sample for regulator review ticket 4411"},
    {"requester": "p.nair",  "role": "Data scientist",     "table": "fund_master",   "duration_days": 90,  "justification": "NAV forecasting research, approved by head of analytics"},
    {"requester": "r.das",   "role": "Contractor",         "table": "transactions",  "duration_days": 180, "justification": "migration testing"},
]

# COMMAND ----------
rows = []
for q in requests_:
    sens = table_sens.get(q["table"], "restricted")
    state = {**q, "dataset_sensitivity": sens}
    out = decide(state, ACCESS_QUESTIONS, api_key)
    a = out["answers"]
    rec, conf = a["recommendation"]["choice"], float(a["recommendation"]["confidence"])
    rows.append({**q, "dataset_sensitivity": sens, "jev_recommendation": rec,
                 "jev_confidence": conf, "risk_score": float(a["risk"]["score"]),
                 "final_action": access_action(rec, conf, sens),
                 "model": out.get("model")})

df = spark.createDataFrame(pd.DataFrame(rows))
df.write.mode("overwrite").saveAsTable(f"{catalog}.governance.access_request_decisions")
display(df)
