import os

with open('libfsc/fsc_core.c', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'int fsc_volume_encode8(' in line:
        new_lines.append('int fsc_volume_encode8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {\n')
        new_lines.append('    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;\n')
        new_lines.append('    #pragma omp parallel for\n')
        new_lines.append('    for (size_t i = 0; i < n_data; i++) fsc_block_seal(volume_data + (i * block_size), block_size, (int64_t)i, modulus);\n')
        new_lines.append('\n')
        new_lines.append('    uint32_t* weights = (uint32_t*)malloc(k_parity * n_data * sizeof(uint32_t));\n')
        new_lines.append('    for (size_t i = 0; i < n_data; i++) {\n')
        new_lines.append('        uint32_t w = 1;\n')
        new_lines.append('        for (size_t j = 0; j < k_parity; j++) {\n')
        new_lines.append('            weights[j * n_data + i] = w;\n')
        new_lines.append('            w = (uint32_t)(((__int128_t)w * (i + 1)) % modulus);\n')
        new_lines.append('        }\n')
        new_lines.append('    }\n')
        new_lines.append('\n')
        new_lines.append('    #pragma omp parallel\n')
        new_lines.append('    {\n')
        new_lines.append('        uint32_t* t_acc = (uint32_t*)calloc(k_parity * 64, sizeof(uint32_t));\n')
        new_lines.append('        #pragma omp for schedule(dynamic)\n')
        new_lines.append('        for (size_t c_base = 0; c_base < d_len; c_base += 64) {\n')
        new_lines.append('            size_t stripe = (c_base + 64 > d_len) ? d_len - c_base : 64;\n')
        new_lines.append('            memset(t_acc, 0, k_parity * 64 * sizeof(uint32_t));\n')
        new_lines.append('            for (size_t i = 0; i < n_data; i++) {\n')
        new_lines.append('                const uint8_t* d_ptr = volume_data + (i * block_size) + c_base;\n')
        new_lines.append('                for (size_t j = 0; j < k_parity; j++) {\n')
        new_lines.append('                    uint32_t w = weights[j * n_data + i];\n')
        new_lines.append('                    __m256i v_w = _mm256_set1_epi32((int)w);\n')
        new_lines.append('                    uint32_t* p_acc = t_acc + (j * 64);\n')
        new_lines.append('                    size_t c = 0;\n')
        new_lines.append('                    for (; c + 7 < stripe; c += 8) {\n')
        new_lines.append('                        __m128i d8 = _mm_loadu_si64((const __m128i*)(d_ptr + c));\n')
        new_lines.append('                        __m256i d32 = _mm256_cvtepu8_epi32(d8);\n')
        new_lines.append('                        __m256i v_acc = _mm256_loadu_si256((__m256i*)&p_acc[c]);\n')
        new_lines.append('                        _mm256_storeu_si256((__m256i*)&p_acc[c], _mm256_add_epi32(v_acc, _mm256_mullo_epi32(d32, v_w)));\n')
        new_lines.append('                    }\n')
        new_lines.append('                    for (; c < stripe; c++) p_acc[c] += (uint32_t)d_ptr[c] * w;\n')
        new_lines.append('                }\n')
        new_lines.append('            }\n')
        new_lines.append('            for (size_t j = 0; j < k_parity; j++) {\n')
        new_lines.append('                uint8_t* p_ptr = volume_data + ((n_data + j) * block_size) + c_base;\n')
        new_lines.append('                uint32_t* p_acc = t_acc + (j * 64);\n')
        new_lines.append('                for (size_t c = 0; c < stripe; c++) p_ptr[c] = (uint8_t)(p_acc[c] % modulus);\n')
        new_lines.append('            }\n')
        new_lines.append('        }\n')
        new_lines.append('        free(t_acc);\n')
        new_lines.append('    }\n')
        new_lines.append('    free(weights);\n')
        new_lines.append('    #pragma omp parallel for\n')
        new_lines.append('    for (size_t j = 0; j < k_parity; j++) fsc_block_seal(volume_data + ((n_data + j) * block_size), block_size, (int64_t)(n_data + j), modulus);\n')
        new_lines.append('    return 1;\n')
        new_lines.append('}\n')
        skip = True
    elif skip and line.startswith('}'):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('libfsc/fsc_core.c', 'w') as f:
    f.writelines(new_lines)
