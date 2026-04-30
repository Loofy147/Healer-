void fsc_syndromes_4way(const uint8_t* data, size_t n, __int128_t* s, int64_t modulus) {
    s[0] = s[1] = s[2] = s[3] = 0;
    if (modulus <= 1) return;

    size_t i = 0;
    __m256i v_s0 = _mm256_setzero_si256();
    __m256i v_s1 = _mm256_setzero_si256();
    __m256i v_s2 = _mm256_setzero_si256();

    // Base weights for the first 8 elements in a 256-bit register (using 32-bit lanes)
    __m256i v_w = _mm256_set_epi32(8, 7, 6, 5, 4, 3, 2, 1);
    __m256i v_step = _mm256_set1_epi32(8);

    for (; i + 7 < n; i += 8) {
        // Load 8 bytes and expand to 32-bit
        __m128i v_data8 = _mm_loadl_epi64((const __m128i*)(data + i));
        __m256i v_data32 = _mm256_cvtepu8_epi32(v_data8);

        // s0: sum of bytes
        v_s0 = _mm256_add_epi64(v_s0, _mm256_sad_epu8(_mm256_extracti128_si256(_mm256_castsi256_si256(v_data32), 0), _mm256_setzero_si256())); // This is not quite right for 8 bytes, but we'll use a simpler way for s0 in the 8-way loop or just use 32-way for s0.

        // Actually, let's keep s0 simple and use 32-way SAD where possible, or just accumulate in s1/s2 loop.
        // For s1: val * w
        __m256i v_prod1 = _mm256_mullo_epi32(v_data32, v_w);
        v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_prod1, 0)));
        v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_prod1, 1)));

        // For s2: val * w * w
        __m256i v_w2 = _mm256_mullo_epi32(v_w, v_w);
        __m256i v_prod2 = _mm256_mullo_epi32(v_data32, v_w2);
        v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_prod2, 0)));
        v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_prod2, 1)));

        // Increment weights
        v_w = _mm256_add_epi32(v_w, v_step);

        if ((i & 0x1FF) == 0x1F8) {
            // Periodically reduce to avoid 64-bit overflow (though unlikely for 1k blocks)
            // We use __int128_t for the final sums s[1], s[2] so we can just extract and add.
        }
    }

    // Extract s1, s2
    uint64_t s1_arr[4], s2_arr[4];
    _mm256_storeu_si256((__m256i*)s1_arr, v_s1);
    _mm256_storeu_si256((__m256i*)s2_arr, v_s2);
    s[1] = s1_arr[0] + s1_arr[1] + s1_arr[2] + s1_arr[3];
    s[2] = s2_arr[0] + s2_arr[1] + s2_arr[2] + s2_arr[3];

    // Recalculate s0 and handle remainder with scalar loop for simplicity and correctness
    // as s0 SAD was optimized for 32-way.
    s[0] = 0;
    for (size_t k = 0; k < n; k++) s[0] += data[k];

    // Remainder for s1, s2
    for (size_t k = i; k < n; k++) {
        __int128_t val = data[k];
        __int128_t w = k + 1;
        s[1] += val * w;
        s[2] += val * w * w;
    }

    s[0] %= modulus; s[1] %= modulus; s[2] %= modulus;
}
