/**
 * FSC: Forward Sector Correction
 * Copyright (C) 2024 FSC Core Team. All Rights Reserved.
 *
 * PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
 * COMMERCIAL LICENSE: Required for proprietary/enterprise use.
 *
 * PATENT PENDING: Industrial applications of these algebraic primitives
 * for database pages, kernel block devices, and network protocols.
 */

/**
 * fsc_sqlite_shim.c - Real-world B-Tree Page integration for SQLite Pager
 *
 * This shim demonstrates protecting a realistic SQLite B-Tree page
 * including internal pointers (child pointers) and header metadata.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "../libfsc.h"

#define PAGE_SIZE 4096

/* Realistic SQLite B-Tree Page Header */
typedef struct {
    uint8_t  flag;         /* 1: Leaf, 2: Interior */
    uint16_t free_start;   /* Offset to start of free space */
    uint16_t cell_count;   /* Number of cells on this page */
    uint16_t cell_start;   /* Offset to start of cell content */
    uint8_t  frag_count;   /* Fragmented free bytes */
    uint32_t right_child;  /* Right child pointer (if interior) */
} BTreeHeader;

/* Mock SQLite Page structure */
typedef struct {
    uint32_t pgno;
    union {
        unsigned char raw[PAGE_SIZE];
        struct {
            BTreeHeader header;
            unsigned char payload[PAGE_SIZE - sizeof(BTreeHeader)];
        } page;
    } data;
    int64_t fsc_target1;
    int64_t fsc_target2;
} PgHdr;

/* Global weights for the shim demo */
int32_t w1[PAGE_SIZE];
int32_t w2[PAGE_SIZE];

/* Mock SQLite Pager function with FSC injection */
int sqlite3PagerGet_fsc(PgHdr *pPage) {
    FSCBuffer b = {
        .buffer = pPage->data.raw,
        .len = PAGE_SIZE,
        .modulus = 2305843009213693951LL, // Mersenne Prime p=2^61-1
        .target = pPage->fsc_target1,
        .target2 = pPage->fsc_target2,
        .weights = w1,
        .weights2 = w2
    };

    if (!fsc_buffer_verify(&b)) {
        printf("[FSC] SQLite Page %d corruption detected in B-Tree structure!\n", pPage->pgno);
        int healed_idx = fsc_buffer_heal(&b);
        if (healed_idx >= 0) {
            printf("[FSC] SUCCESS: Recovered corrupted field at offset %d.\n", healed_idx);
            return 0; // SQLITE_OK
        } else {
            return -1; // SQLITE_CORRUPT
        }
    }

    return 0; // SQLITE_OK
}

int main() {
    for(int i=0; i<PAGE_SIZE; i++) {
        w1[i] = 1;
        w2[i] = i + 1;
    }

    PgHdr page;
    memset(&page, 0, sizeof(page));
    page.pgno = 123;
    page.data.page.header.flag = 2; // Interior page
    page.data.page.header.cell_count = 50;
    page.data.page.header.right_child = 0xDEADBEEF;
    memset(page.data.page.payload, 'D', sizeof(page.data.page.payload));

    // Seal the page with FSC
    FSCBuffer b = {
        .buffer = page.data.raw,
        .len = PAGE_SIZE,
        .modulus = 2305843009213693951LL,
        .weights = w1,
        .weights2 = w2
    };
    fsc_buffer_seal(&b);
    page.fsc_target1 = b.target;
    page.fsc_target2 = b.target2;

    printf("--- Realistic SQLite FSC Shim Demo ---\n");
    printf("B-Tree Page %d initialized.\n", page.pgno);
    printf("Internal Child Pointer: 0x%08X\n", page.data.page.header.right_child);

    // Simulate corruption in a CRITICAL field (the child pointer)
    printf("\n[CORRUPTION] Bit-flip in the Right Child pointer...\n");
    uint32_t orig_ptr = page.data.page.header.right_child;
    page.data.page.header.right_child ^= 0x01000000;
    printf("Corrupted Pointer: 0x%08X\n", page.data.page.header.right_child);

    // Retrieve and heal
    if (sqlite3PagerGet_fsc(&page) == 0) {
        if (page.data.page.header.right_child == orig_ptr) {
            printf("RESULT: Critical B-Tree pointer HEALED exactly. Database integrity preserved.\n");
        } else {
            printf("RESULT: Healing failed to restore the pointer.\n");
        }
    }

    return 0;
}
