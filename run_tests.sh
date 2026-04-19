# FSC: Forward Sector Correction
# Copyright (C) 2024 FSC Core Team. All Rights Reserved.
# PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
# PATENT PENDING.

#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

echo "===================================================="
echo "   FSC UNIVERSAL FRAMEWORK - MASTER TEST RUNNER"
echo "===================================================="

# List of tests to run
TESTS=(
    "tests/verify_database.py"
    "tests/verify_network.py"
    "tests/verify_storage.py"
    "tests/verify_advanced_binary.py"
    "tests/verify_2d_binary.py"
    "tests/verify_nonlinear.py"
    "tests/verify_multifault_binary.py"
    "prototypes/wallet_recovery.py"
    "prototypes/code_integrity.py"
    "demos/fsc_binary_demo.py"
)

SUCCESS_COUNT=0
TOTAL_COUNT=${#TESTS[@]}

for test in "${TESTS[@]}"; do
    echo "RUNNING: $test"
    python3 "$test"
    if [ $? -eq 0 ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "!!! FAILED: $test"
    fi
done

echo "===================================================="
echo "   SUMMARY: $SUCCESS_COUNT / $TOTAL_COUNT PASSED"
echo "===================================================="
