        self.constraints = []
        self.records = []
        self.ftype_list = list(FSCField.TYPES.keys())
        self._read_file()

    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic != b"FSC1": raise ValueError("Invalid magic")

            # version(1), n_data(2), n_cons(1), n_stored(1), n_recs(4)
            version, n_data_fields, n_constraints, n_stored_fields, n_records = struct.unpack(">B HB B I", f.read(9))

            # Read Data Fields
            for _ in range(n_data_fields):
                name = f.read(16).decode('ascii').strip()
                ftype_idx = struct.unpack(">B", f.read(1))[0]
                self.data_fields.append(FSCField(name, self.ftype_list[ftype_idx]))

            self.all_fields = list(self.data_fields)
            for i in range(n_stored_fields):
                self.all_fields.append(FSCField(f"stored_{i}", "INT64"))

            # Read Constraints
            for _ in range(n_constraints):
                ctype, target, s_idx = struct.unpack(">B q b", f.read(10))
                weights = list(struct.unpack(">" + "b"*n_data_fields, f.read(n_data_fields)))
                c = FSCConstraint(weights, target if ctype == 1 or target != 0 or s_idx == -1 else None,
                                  is_fiber=(ctype == 1))
                c.stored_field_idx = s_idx
                self.constraints.append(c)

            # Read Records
            record_fmt = ">" + "".join(f.fmt for f in self.all_fields)
            record_size = struct.calcsize(record_fmt)
            for _ in range(n_records):
                data = struct.unpack(record_fmt, f.read(record_size))
                self.records.append(list(data))

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1) -> bool:
        """
        Automatically localize and heal corruption using multiple constraints (Model 5).
        If corrupted_field_idx is provided, uses it directly (Model 3/4 style).
        """
        record = self.records[record_idx]
        data = record[:len(self.data_fields)]

        failed_constraints = []
        for i, c in enumerate(self.constraints):
            if c.is_fiber: target = record_idx % 251
            elif c.target is not None: target = c.target
            else: target = record[c.stored_field_idx]

            actual = sum(w * v for w, v in zip(c.weights, data))
            if actual != target:
                failed_constraints.append((i, target))

        if not failed_constraints: return True

        # Manual localization if index provided
        if corrupted_field_idx != -1:
            for i, target in failed_constraints:
                c = self.constraints[i]
                if c.weights[corrupted_field_idx] != 0:
                    others = sum(w * v for j, (w, v) in enumerate(zip(c.weights, data)) if j != corrupted_field_idx)
                    recovered_val = (target - others) // c.weights[corrupted_field_idx]
                    self.records[record_idx][corrupted_field_idx] = recovered_val
                    return True
            return False

        # Model 5 localization (Automatic)
        valid_repairs = []
        for field_idx in range(len(self.data_fields)):
            candidates = []
            possible = True
            for i, target in failed_constraints:
                c = self.constraints[i]
                if c.weights[field_idx] == 0:
                    possible = False
                    break
                others = sum(w * v for j, (w, v) in enumerate(zip(c.weights, data)) if j != field_idx)
                # Division check
                if (target - others) % c.weights[field_idx] != 0:
                    possible = False
                    break
                candidates.append((target - others) // c.weights[field_idx])

            if possible and candidates and len(set(candidates)) == 1:
                recovered_val = candidates[0]
                temp_data = list(data)
                temp_data[field_idx] = recovered_val

                # Verify ALL constraints
                all_ok = True
                for i, c in enumerate(self.constraints):
                    if c.is_fiber: t = record_idx % 251
                    elif c.target is not None: t = c.target
                    else: t = record[c.stored_field_idx]
                    if sum(w * v for w, v in zip(c.weights, temp_data)) != t:
                        all_ok = False
                        break

                if all_ok:
                    valid_repairs.append((field_idx, recovered_val))

        if len(valid_repairs) >= 1:
            # If multiple repairs possible, we take the first one but it implies underdetermination
            f_idx, r_val = valid_repairs[0]
            self.records[record_idx][f_idx] = r_val
            return True

        return False

    def get_data(self) -> List[List[int]]:
        return [r[:len(self.data_fields)] for r in self.records]
