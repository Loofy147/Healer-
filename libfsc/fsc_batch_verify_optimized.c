size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices) {
    size_t total_corrupted = 0;
    if (modulus <= 1) return 0;

    #pragma omp parallel for
    for (size_t b = 0; b < n_blocks; b++) {
        if (!fsc_block_verify(data + b * block_size, block_size, (int64_t)b, modulus)) {
            size_t idx;
            #pragma omp critical
            {
                idx = total_corrupted++;
                if (corrupted_indices) corrupted_indices[idx] = b;
            }
        }
    }
    return total_corrupted;
}
