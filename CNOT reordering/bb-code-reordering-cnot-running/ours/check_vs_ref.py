"""Check ours/bravyi_d1.py against the reference decoder_setup (parameter-only copies in ours/): for Bravyi's
schedule the column sets of HX / HZ (detector + logical supports) and the merged priors must be identical."""
import pickle, sys
import numpy as np
from bravyi_d1 import BBRef, decoding_matrices
for n in map(int, sys.argv[1:]):
    ref = pickle.load(open(f'TMP/mydata_{n}_{8 if n != 72 else 12}_p_0.003_cycles_1', 'rb'))
    code = BBRef(n); sX, sZ = ref['sX'], ref['sZ']
    assert code.check_cycle(sX, sZ)
    # reference logical operators come from css_code too; use them to compare like with like
    for kind, key, pk in (('X', 'HX', 'probX'), ('Z', 'HZ', 'probZ')):
        M = decoding_matrices(code, sX, sZ, kind)
        R = ref[key].tocsc(); rcols = {}
        for j in range(R.shape[1]):
            supp = tuple(sorted(R.indices[R.indptr[j]:R.indptr[j + 1]]))
            rcols[supp] = ref[pk][j]
        rcols.pop((), None)
        ours = {kk: pr for kk, pr in zip(M['keys'], M['probs'])}
        same = set(ours) == set(rcols); pmax = max(abs(ours[k] - rcols[k]) for k in ours) if same else None
        print(f'[[{n}]] {kind}-type: ours {len(ours)} columns, reference {len(rcols)}; identical supports: {same}; max prior diff: {pmax}')
