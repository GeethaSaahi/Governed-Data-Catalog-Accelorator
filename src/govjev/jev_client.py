"""Thin client for TypeSafe's Jev decision model via OpenRouter's Decisions API.

Jev returns typed answers (noul / choice / score) with probabilities instead of text,
so downstream code can branch deterministically and store the probabilities as audit evidence.
We send column METADATA only (name, type, description) - never row values.
"""
import time
import requests

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"  # pinned (not ~jev-latest) so thresholds stay reproducible

CLASSIFY_QUESTIONS = {
    "is_pii": {
        "type": "noul",
        "instructions": "Does this column likely store personally identifiable information about an individual investor or employee?",
        "criteria": {
            "true": "Identifies or can contact a person: name, email, phone, national ID, PAN, address, date of birth.",
            "false": "Does not identify an individual: fund codes, amounts, trade timestamps, product attributes, status flags.",
        },
    },
    "sensitivity": {
        "type": "choice",
        "instructions": "Assign the enterprise data sensitivity classification for this column.",
        "criteria": {
            "public": "Safe to publish, such as fund names and fund categories.",
            "internal": "Business data for internal use with low impact if leaked, such as fund NAV and AUM.",
            "confidential": "Client financial data such as balances, transaction amounts, account identifiers.",
            "restricted": "Direct personal identifiers or government IDs; regulatory or privacy impact if leaked.",
        },
    },
}

ACCESS_QUESTIONS = {
    "recommendation": {
        "type": "choice",
        "instructions": "Given this access request, what should the entitlement workflow do?",
        "criteria": {
            "approve": "Role-appropriate, clearly justified, time-bound, limited scope.",
            "escalate": "Vague or missing justification, broad scope, or sensitive data that needs a human decision.",
            "deny": "No business need for this role, or permanent access to highly sensitive data.",
        },
    },
    "risk": {
        "type": "score",
        "instructions": "How risky is granting this access?",
        "criteria": ["Low risk", "Medium risk", "High risk"],
    },
}


def decide(state: dict, questions: dict, api_key: str, model: str = MODEL,
           retries: int = 4, timeout: int = 60) -> dict:
    payload = {"model": model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    r = None
    for attempt in range(retries):
        r = requests.post(URL, json=payload, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()
