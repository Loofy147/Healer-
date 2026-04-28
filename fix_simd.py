import os

with open('libfsc/fsc_core.c', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'static inline void fsc_syndromes_4way' in line:
        new_lines.append('static inline void fsc_syndromes_4way(const uint8_t* block, size_t n, __int128_t* s) {\n')
        new_lines.append('    s[0] = 0; s[1] = 0; s[2] = 0; s[3] = 0;\n')
        new_lines.append('    __m256i v_s0 = _mm256_setzero_si256(), v_s1 = _mm256_setzero_si256();\n')
        new_lines.append('    __m256i v_s2 = _mm256_setzero_si256(), v_s3 = _mm256_setzero_si256();\n')
        new_lines.append('    __m256i v_w = _mm256_set_epi32(8, 7, 6, 5, 4, 3, 2, 1);\n')
        new_lines.append('    __m256i v_8 = _mm256_set1_epi32(8);\n')
        new_lines.append('    size_t i = 0, iter = 0;\n')
        new_lines.append('    for (; i + 7 < n; i += 8) {\n')
        new_lines.append('        __m128i d8 = _mm_loadu_si64((const __m128i*)(block + i));\n')
        new_lines.append('        __m256i d32 = _mm256_cvtepu8_epi32(d8);\n')
        new_lines.append('        __m256i d_lo = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(d32, 0));\n')
        new_lines.append('        __m256i d_hi = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(d32, 1));\n')
        new_lines.append('        __m256i w_lo = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_w, 0));\n')
        new_lines.append('        __m256i w_hi = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_w, 1));\n')
        new_lines.append('\n')
        new_lines.append('        v_s0 = _mm256_add_epi64(v_s0, _mm256_add_epi64(d_lo, d_hi));\n')
        new_lines.append('        __m256i p1_lo = _mm256_mul_epu32(d_lo, w_lo), p1_hi = _mm256_mul_epu32(d_hi, w_hi);\n')
        new_lines.append('        v_s1 = _mm256_add_epi64(v_s1, _mm256_add_epi64(p1_lo, p1_hi));\n')
        new_lines.append('\n')
        new_lines.append('        __m256i w2_lo = _mm256_mul_epu32(w_lo, w_lo), w2_hi = _mm256_mul_epu32(w_hi, w_hi);\n')
        new_lines.append('        __m256i p2_lo = _mm256_add_epi64(_mm256_mul_epu32(d_lo, w2_lo), _mm256_slli_epi64(_mm256_mul_epu32(d_lo, _mm256_srli_epi64(w2_lo, 32)), 32));\n')
        new_lines.append('        __m256i p2_hi = _mm256_add_epi64(_mm256_mul_epu32(d_hi, w2_hi), _mm256_slli_epi64(_mm256_mul_epu32(d_hi, _mm256_srli_epi64(w2_hi, 32)), 32));\n')
        new_lines.append('        v_s2 = _mm256_add_epi64(v_s2, _mm256_add_epi64(p2_lo, p2_hi));\n')
        new_lines.append('\n')
        new_lines.append('        __m256i w3_lo = _mm256_add_epi64(_mm256_mul_epu32(w2_lo, w_lo), _mm256_slli_epi64(_mm256_mul_epu32(_mm256_srli_epi64(w2_lo, 32), w_lo), 32));\n')
        new_lines.append('        __m256i w3_hi = _mm256_add_epi64(_mm256_mul_epu32(w2_hi, w_hi), _mm256_slli_epi64(_mm256_mul_epu32(_mm256_srli_epi64(w2_hi, 32), w_hi), 32));\n')
        new_lines.append('        __m256i p3_lo = _mm256_add_epi64(_mm256_mul_epu32(d_lo, w3_lo), _mm256_slli_epi64(_mm256_mul_epu32(d_lo, _mm256_srli_epi64(w3_lo, 32)), 32));\n')
        new_lines.append('        __m256i p3_hi = _mm256_add_epi64(_mm256_mul_epu32(d_hi, w3_hi), _mm256_slli_epi64(_mm256_mul_epu32(d_hi, _mm256_srli_epi64(w3_hi, 32)), 32));\n')
        new_lines.append('        v_s3 = _mm256_add_epi64(v_s3, _mm256_add_epi64(p3_lo, p3_hi));\n')
        new_lines.append('\n')
        new_lines.append('        v_w = _mm256_add_epi32(v_w, v_8);\n')
        new_lines.append('        if (++iter >= 256) {\n')
        new_lines.append('            uint64_t r[16];\n')
        new_lines.append('            _mm256_storeu_si256((__m256i*)&r[0], v_s0); _mm256_storeu_si256((__m256i*)&r[4], v_s1);\n')
        new_lines.append('            _mm256_storeu_si256((__m256i*)&r[8], v_s2); _mm256_storeu_si256((__m256i*)&r[12], v_s3);\n')
        new_lines.append('            s[0] += (__int128_t)r[0]+r[1]+r[2]+r[3]; s[1] += (__int128_t)r[4]+r[5]+r[6]+r[7];\n')
        new_lines.append('            s[2] += (__int128_t)r[8]+r[9]+r[10]+r[11]; s[3] += (__int128_t)r[12]+r[13]+r[14]+r[15];\n')
        new_lines.append('            v_s0 = v_s1 = v_s2 = v_s3 = _mm256_setzero_si256(); iter = 0;\n')
        new_lines.append('        }\n')
        new_lines.append('    }\n')
        new_lines.append('    uint64_t r[16];\n')
        new_lines.append('    _mm256_storeu_si256((__m256i*)&r[0], v_s0); _mm256_storeu_si256((__m256i*)&r[4], v_s1);\n')
        new_lines.append('    _mm256_storeu_si256((__m256i*)&r[8], v_s2); _mm256_storeu_si256((__m256i*)&r[12], v_s3);\n')
        new_lines.append('    s[0] += (__int128_t)r[0]+r[1]+r[2]+r[3]; s[1] += (__int128_t)r[4]+r[5]+r[6]+r[7];\n')
        new_lines.append('    s[2] += (__int128_t)r[8]+r[9]+r[10]+r[11]; s[3] += (__int128_t)r[12]+r[13]+r[14]+r[15];\n')
        new_lines.append('    for (; i < n; i++) {\n')
        new_lines.append('        __int128_t v = block[i], w = i + 1;\n')
        new_lines.append('        s[0] += v; s[1] += v * w; s[2] += v * w * w; s[3] += v * w * w * w;\n')
        new_lines.append('    }\n')
        new_lines.append('}\n')
        skip = True
    elif skip and line.startswith('}'):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('libfsc/fsc_core.c', 'w') as f:
    f.writelines(new_lines)
