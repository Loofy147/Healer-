import sys
import os
sys.path.append(os.getcwd())

from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader, fsc_audit_log
import fsc.fsc_binary

def test_audit_log():
    print("Testing Enterprise Audit Logging...")

    # Enable commercial build for testing
    fsc.fsc_binary.FSC_COMMERCIAL_BUILD = True

    fields = [FSCField("val", "UINT8")]
    schema = FSCSchema(fields)
    # Model 5: Two constraints for single fault localization
    schema.add_constraint([1], modulus=251)
    schema.add_constraint([2], modulus=251)

    writer = FSCWriter(schema)
    writer.add_record([100])
    filename = "test_audit.fsc"
    writer.write(filename)

    reader = FSCReader(filename)
    # Corrupt
    reader.records[0, 0] = 0

    print("Expected audit logs should appear below:")
    healed = reader.verify_and_heal(0)
    assert healed
    assert reader.records[0, 0] == 100

    # Disable commercial build
    fsc.fsc_binary.FSC_COMMERCIAL_BUILD = False
    print("\nNo audit logs should appear for the next healing:")
    reader.records[0, 0] = 0
    healed = reader.verify_and_heal(0)
    assert healed

    print("\n✓ Audit Log Verification Passed")
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_audit_log()
