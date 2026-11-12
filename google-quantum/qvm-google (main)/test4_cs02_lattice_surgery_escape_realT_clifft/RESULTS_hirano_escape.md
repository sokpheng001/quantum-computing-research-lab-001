# Test 4, step A2: hardware needs of Hirano et al.'s lattice-surgery escape

Static analysis of the published stim circuits (`references/msc-ls-src/repo/data`, commit e4c90b0). Nearest neighbour = coordinate offset (1, 1) in their diagonal layout (the surface-code convention).

## inject-check-3.stim

- qubits used: 15; noisy (hardware) two-qubit pairs: 20; TICKs: 41
- noiseless two-qubit pairs left out (no DEPOLARIZE2 after them: the test's ideal colour-code encoder): 0
- pairs that are **not** nearest neighbours: 0
- qubits with more than 4 partners: 0

## lattice-surgery-error-detection-3-to-3.stim

- qubits used: 33; noisy (hardware) two-qubit pairs: 46; TICKs: 30
- noiseless two-qubit pairs left out (no DEPOLARIZE2 after them: the test's ideal colour-code encoder): 11
- pairs that are **not** nearest neighbours: 0
- qubits with more than 4 partners: 0

## lattice-surgery-error-detection-3-to-5.stim

- qubits used: 66; noisy (hardware) two-qubit pairs: 104; TICKs: 30
- noiseless two-qubit pairs left out (no DEPOLARIZE2 after them: the test's ideal colour-code encoder): 11
- pairs that are **not** nearest neighbours: 0
- qubits with more than 4 partners: 0

## Reading (Nov 3): the earlier 10 non-neighbour pairs and the >4-partner qubits all came from the noiseless TICK-5 CNOTs, i.e. the test circuit's ideal encoding of |+>_L into the colour code, not from the escape.

## Original reading note

If the non-neighbour pairs and the >4-partner qubits all involve colour-code qubits, the issue is the colour-code part (Gidney's layout drawn in other coordinates, or qubits reused across stages); if they involve the merge boundary, the lattice surgery itself needs re-routing for Willow. Either way, every such pair must be removed (re-routed through a neighbour or re-placed) before the escape can run on Willow.
