#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

echo "===================================================="
echo "   FSC UNIVERSAL FRAMEWORK - MASTER TEST RUNNER"
echo "===================================================="

# List of tests to run
TESTS=(
    "verify/verify_database.py"
    "verify/verify_network.py"
    "verify/verify_storage.py"
    "verify/verify_advanced_binary.py"
    "verify/verify_2d_binary.py"
    "verify/verify_nonlinear.py"
    "verify/verify_multifault_binary.py"
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
