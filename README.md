# Governed Data Catalog Accelerator - Unity Catalog + TypeSafe Jev

AI-assisted data classification, entitlement enforcement, lineage and governance KPIs on Databricks Unity Catalog,
for an asset-management domain (investors, accounts, funds, transactions).

## What it does
| Step | Notebook | Governance capability |
|---|---|---|
| 1 | `01_setup_data` | Catalog / schemas, synthetic data, curated gold table (lineage source) |
| 2 | `02_harvest_metadata` | Technical metadata scan from `information_schema` into a column inventory |
| 3 | `03_jev_classify` | **TypeSafe Jev** classifies each column: `is_pii` (Noul) + `sensitivity` (Choice) with probabilities |
| 4 | `04_apply_tags_and_controls` | UC tags, column masks, row filter, GRANTs; low-confidence items go to a steward queue |
| 5 | `05_access_request_triage` | **Jev** recommends approve / escalate / deny + risk score; policy code makes the final call |
| 6 | `06_lineage_and_kpis` | Lineage from `system.access`, governance KPI view for a SQL dashboard |

## Design decisions (interview talking points)
- **Why Jev, not a chat LLM:** it returns typed answers with probabilities, so thresholds are deterministic, testable and auditable. No free text to parse.
- **Advisor vs decider:** Jev advises; `src/govjev/policy.py` decides. Confidential/restricted access always needs a human.
- **Privacy by design:** only column metadata (name, type, description) is sent to the model, never row values.
- **Audit:** probabilities, model version and cost are stored per decision. Model is pinned (`typesafe/jev-1.13`) so thresholds stay reproducible.
- **Human in the loop:** low confidence or PII probability in the 0.3-0.7 grey zone goes to `v_steward_queue`.
- **Limits:** Jev is a new early-access model that gives no reasoning trace. Thresholds should be tuned on steward-labelled columns before production.

## Concept mapping (Informatica CDGC -> this project)
Catalog scan -> `02`; classification / auto-tagging -> `03`+`04`; entitlements (RBAC, masking) -> `04`; lineage -> `06`; governance reports -> KPI view + dashboard.

## Run it (about 90 min)
1. Databricks workspace with Unity Catalog. Clone this repo into a **Git folder**.
2. Store your OpenRouter key (no waitlist needed for Jev on OpenRouter):
   `databricks secrets create-scope gov` then `databricks secrets put-secret gov openrouter_key`
3. Run notebooks 01 to 06 in order (set the `catalog` widget; default `fin_gov_dev`).
4. Dashboard: SQL editor, query `SELECT * FROM <catalog>.governance.v_governance_kpis` plus `v_steward_queue`, add to a dashboard.
5. Optional: `databricks bundle validate && databricks bundle deploy -t dev` runs the same notebooks as a Lakeflow Job (edit `host` in `databricks.yml`).

## Notes
- Needs outbound internet to `openrouter.ai`. If blocked, run notebook 03/05 logic locally and upload results as tables.
- Create account groups `pii_readers`, `global_ops`, `analysts` to see masks/filters/grants take effect.
- CI: `pytest` runs on every push (`.github/workflows/ci.yml`).
