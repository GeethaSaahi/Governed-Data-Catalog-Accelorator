"""Deterministic policy layer. Jev advises with probabilities; these rules decide.
Pure functions so they are unit-testable and auditable."""

SENS_RANK = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}


def classification_status(is_pii_prob: float, sens_confidence: float,
                          auto_threshold: float = 0.85, grey_zone=(0.3, 0.7)) -> str:
    lo, hi = grey_zone
    if sens_confidence < auto_threshold or lo <= is_pii_prob <= hi:
        return "STEWARD_REVIEW"
    return "AUTO_APPLIED"


def mask_required(is_pii_prob: float, sensitivity: str) -> bool:
    return is_pii_prob >= 0.5 or sensitivity == "restricted"


def access_action(recommendation: str, confidence: float, dataset_sensitivity: str,
                  auto_threshold: float = 0.9) -> str:
    """Anything confidential/restricted always goes to a human, whatever Jev says."""
    if SENS_RANK.get(dataset_sensitivity, 3) >= SENS_RANK["confidential"]:
        return "HUMAN_APPROVAL"
    if recommendation == "approve" and confidence >= auto_threshold:
        return "AUTO_APPROVE"
    return "HUMAN_APPROVAL"
