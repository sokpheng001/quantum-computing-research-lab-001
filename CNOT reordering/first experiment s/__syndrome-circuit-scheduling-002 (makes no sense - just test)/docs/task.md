# Task: Verify Depth-7 CNOT L/R Scheduling on the n=72 BB Code before scaling to n=144

## Context & Objective
Before attempting the 144-qubit gross code, you must validate our Left-Right (L/R) block-staggered scheduling pipeline on the smaller n=72 Bivariate Bicycle code. For the 72-qubit code, standard depth-7 permutations often experience a distance deficit. Your task is to implement the matrix definitions, compile the depth-7 Stim circuit, and find an L/R schedule that recovers the maximum possible d_circ.

---

## Experimental Method

### Phase 1: Define the 72-Qubit Code Matrices
1. Define the algebraic cyclic components for the 72-qubit Bivariate Bicycle code over GF(2). 
2. Construct the 36x36 component shift matrices to form H_x and H_z check matrices.
3. Partition the 72 data qubits into two equal, balanced blocks: 
   - Left (L) Block: Qubits 0 to 35
   - Right (R) Block: Qubits 36 to 71

### Phase 2: Apply the Depth-7 L/R Structural Filter
Generate depth-7 CNOT sequence matrices for the weight-6 check operators by forcing spatial balancing:
1. Identify the 3 CNOT targets landing in the L block and the 3 CNOT targets landing in the R block for every check.
2. Build schedules that enforce an asymmetric sequence:
   - Strategy A: Touch L targets in layers 1–3, and R targets in layers 4–6 (Layer 7 used as idle/measurement buffer).
   - Strategy B: Touch R targets in layers 1–3, and L targets in layers 4–6.
   - Strategy C: Interleave checks (X-checks use Strategy A, Z-checks use Strategy B).

### Phase 3: Stim Space-Time Circuit Assembly
Write a function `build_72_stim_circuit(schedule)` that:
1. Generates the full 3D circuit structure via `stim.Circuit()`.
2. Steps sequentially through the 7 layers using precise `TICK` dividers.
3. Sets standard circuit-level depolarizing and readout noise (e.g., p = 0.001).
4. Inserts multi-round stabilizer tracking detectors.

### Phase 4: Compute Shortest Fault Paths & Log Results
1. Transform the generated circuit object to its error model: `circuit.detector_error_model(decompose_errors=True)`.
2. Extract the exact circuit-level graph distance: `dem.shortest_graph_fault_path()`.
3. Track the behavior: If the shortest graph path exceeds the standard baseline limit, save the 7-layer scheduling array structure into `results_72code.json`.

---

## Deliverables Required from Agent
- `bb72_matrices.py`: The exact script computing the 72-qubit check infrastructure.
- `search_scheduler_72.py`: The automated scheduling look-up pipeline computing `shortest_graph_fault_path()`.
- `results_72code.json`: Logs containing any valid schedule sequence successfully optimizing d_circ.
