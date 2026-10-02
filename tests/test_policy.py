import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from govjev.policy import classification_status, mask_required, access_action


def test_low_confidence_goes_to_steward():
    assert classification_status(0.95, 0.60) == "STEWARD_REVIEW"


def test_pii_grey_zone_goes_to_steward():
    assert classification_status(0.5, 0.95) == "STEWARD_REVIEW"


def test_confident_auto_applied():
    assert classification_status(0.98, 0.92) == "AUTO_APPLIED"


def test_mask_rules():
    assert mask_required(0.9, "internal")
    assert mask_required(0.1, "restricted")
    assert not mask_required(0.1, "internal")


def test_sensitive_access_always_human():
    assert access_action("approve", 0.99, "restricted") == "HUMAN_APPROVAL"
    assert access_action("approve", 0.99, "confidential") == "HUMAN_APPROVAL"


def test_low_sensitivity_auto_approve():
    assert access_action("approve", 0.95, "internal") == "AUTO_APPROVE"
    assert access_action("approve", 0.60, "internal") == "HUMAN_APPROVAL"
    assert access_action("escalate", 0.99, "public") == "HUMAN_APPROVAL"
