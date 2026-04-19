import sys

with open('fsc_domains.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'report("3D tensor / MRI volume (fiber closure)",' in line:
        new_lines.append('report("3D tensor / MRI volume (fiber closure)",\n')
        new_lines.append('       ok_tensor,\n')
        new_lines.append('       "Sum of each torus fiber = invariant. Any 1 voxel in a fiber recoverable.",\n')
        new_lines.append('       f"Voxel ({i0},{j0},{k0}) = {int(T[i0,j0,k0])} → recovered = {recovered_voxel} {\'✓\' if ok_tensor else \'✗\'}",\n')
        new_lines.append('       f"m fiber sums (1 int32 each) = {m*4} bytes for {m**3} voxels = {100*m*4/(m**3*4):.2f}% overhead")\n')
        continue
    if 'ok_tensor,' in line or '"Sum of each torus fiber' in line or 'Voxel ({i0},{j0},{k0})' in line or 'm fiber sums' in line:
        if any(x in line for x in ['report("3D tensor / MRI volume (fiber closure)",', 'ok_tensor,', '"Sum of each torus fiber', 'Voxel ({i0},{j0},{k0})', 'm fiber sums']):
             continue
    new_lines.append(line)

# Clean up duplicate lines from previous script logic errors if any
# Actually, the sed output looked mostly correct but let's be sure.

with open('fsc_domains.py', 'w') as f:
    f.writelines(new_lines)
