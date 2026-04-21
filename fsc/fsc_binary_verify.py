    def _verify_record(self, record_idx: int, data_np: np.ndarray) -> bool:
        record = self.records[record_idx]
        targets = np.where(self._is_fiber, record_idx % np.where(self._moduli != 0, self._moduli, 251),
                           np.where(self._has_fixed_target, self._fixed_targets, record[self._stored_indices]))

        if is_native_available():
            # Use native acceleration for syndrome calculation if all constraints use same modulus
            for m in np.unique(self._moduli):
                mask = (self._moduli == m)
                if np.sum(mask) == len(self.constraints):
                    actuals = np.zeros(len(self.constraints), dtype=np.int64)
                    for i in range(len(self.constraints)):
                        actuals[i] = native_calculate_sum64(data_np, self.constraints[i].weights, m)
                    return np.all(actuals == targets)

        actuals = self._weight_matrix @ data_np; mod_mask = self._moduli != 0; actuals[mod_mask] %= self._moduli[mod_mask]
        return np.all(actuals == targets)
