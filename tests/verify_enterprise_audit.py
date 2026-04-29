import sys
import os
sys.path.append(os.getcwd())

from fsc.enterprise.fsc_commercial import fsc_enterprise_audit, _AUDIT_CHAIN

def test_enterprise_audit():
    print("Testing Enterprise Secure Audit Chain...")

    fsc_enterprise_audit("RECOVERY", {"index": 10, "value": 100})
    fsc_enterprise_audit("RECOVERY", {"index": 11, "value": 200})

    assert len(_AUDIT_CHAIN.chain) == 2
    assert _AUDIT_CHAIN.chain[1]["prev_hash"] == _AUDIT_CHAIN.chain[0]["hash"]

    print("✓ Enterprise Audit Chain Verified")

if __name__ == "__main__":
    test_enterprise_audit()
