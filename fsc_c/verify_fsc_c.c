#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "fsc_light.h"

typedef struct {
    int64_t account_id;
    int64_t balance;
    int64_t last_tx;
    int64_t fsc_target;
} BankRecord;

int main() {
    printf("--- FSC C Deployment Demo ---\n");

    // We define a struct that "knows" its own integrity.
    // Schema: weights = {1, 1, 1}, modulus = 2^61-1 (Mersenne prime)
    int8_t weights[] = {1, 1, 1};
    int64_t modulus = 2305843009213693951LL; // 2^61 - 1

    BankRecord rec;
    rec.account_id = 987654321;
    rec.balance = 5000000;
    rec.last_tx = -1200;

    int64_t fields[] = {rec.account_id, rec.balance, rec.last_tx};
    rec.fsc_target = fsc_calculate_sum(fields, weights, 3, modulus);

    printf("Record Created: ID=%ld, Bal=%ld, Target=%ld\n", rec.account_id, rec.balance, rec.fsc_target);

    // Simulate Bit Flip in memory or on disk
    printf("\n[CORRUPTION] Simulating memory corruption in 'balance' field...\n");
    rec.balance = 0; // Balance wiped

    // Verify
    int64_t current_fields[] = {rec.account_id, rec.balance, rec.last_tx};
    int64_t check = fsc_calculate_sum(current_fields, weights, 3, modulus);

    if (check != rec.fsc_target) {
        printf("Integrity Violation Detected! (Actual: %ld, Expected: %ld)\n", check, rec.fsc_target);

        // Healing
        printf("Healing 'balance' (index 1)...\n");
        int64_t recovered = fsc_recover_field(current_fields, weights, 3, rec.fsc_target, modulus, 1);
        rec.balance = recovered;

        printf("Recovery Complete. Healed Balance: %ld\n", rec.balance);
    }

    if (rec.balance == 5000000) {
        printf("\nSUCCESS: Data restored to bit-perfect state.\n");
    } else {
        printf("\nFAILURE: Recovery failed.\n");
    }

    return 0;
}
