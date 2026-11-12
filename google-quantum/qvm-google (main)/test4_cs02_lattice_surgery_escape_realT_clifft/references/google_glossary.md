# Glossary: keywords in Google's Willow cultivation paper

Rosenfeld et al., "Magic state cultivation on a superconducting quantum processor", arXiv:2512.13908.
Written Nov 4, 2026 for reading the paper. Grouped from basic to advanced.

## 1. Hardware
| Keyword | Meaning |
|---|---|
| **Willow** | Google's 105-qubit superconducting chip. Qubits sit on a square grid; each couples only to its up to 4 nearest neighbours. |
| **Transmon** | The type of superconducting qubit Willow uses. |
| **CZ gate** | Willow's native two-qubit gate. A CNOT = H + CZ + H. |
| **Readout line** | Shared wiring that reads out several qubits. Measuring one qubit can disturb others on the same line, so circuits must avoid conflicts (Fig. S10a: "readout line constraints"). |
| **Leakage** | The qubit leaves its two levels (0, 1) into a higher level (2). Not a normal Pauli error; Google blames it for the poor grafting result. |
| **Low-frequency phase noise** | Slow random drift of a qubit's frequency, which slowly rotates its phase. |
| **Echo pulses** | Extra X pulses that cancel slow phase noise (like a spin echo). Without them, performance "is dominated by low-frequency phase noise". |
| **RL calibration** | Reinforcement-learning tuning of gate parameters (~4 h). Improved error and retention about 10x. |

## 2. Qubits and codes
| Keyword | Meaning |
|---|---|
| **Physical qubit** | One real qubit on the chip. Noisy. |
| **Logical qubit** | One protected qubit spread over many physical qubits by a code. |
| **Colour code (d = 3)** | The code used for cultivation: 7 data qubits, 6 stabilisers (3 X-type, 3 Z-type). Can detect any single error. |
| **Surface code (d = 5)** | The code used after grafting: larger, better for long-term storage and computing. |
| **Code distance d** | Smallest number of physical errors that can change the logical state undetected (property of the code). |
| **Data qubit** | Holds the encoded information. |
| **Measure / helper / ancilla qubit** | Extra qubit used to check the data, then measured. |
| **Stabiliser** | A check operator (e.g. XXXX on 4 qubits) whose value is +1 when there is no error. |
| **QEC cycle** | One round of measuring all stabilisers. |
| **Superdense colour code cycle** | Google's efficient way of measuring both X and Z stabilisers of the colour code in one cycle (Lacroix et al.). |

## 3. Gates and magic states
| Keyword | Meaning |
|---|---|
| **Clifford gate** | H, S, CNOT, CZ. Easy to simulate and to do fault-tolerantly. Not enough for a universal computer. |
| **T gate** | Rotation by pi/4 about Z. Non-Clifford: needed for universal computing, hard to do fault-tolerantly. |
| **Magic state / T state** | The state T\|+>. Consuming one gives one T gate. Google uses the same state rotated into the X-Z plane, exp(-i pi Y/8)\|0>, which is equivalent. |
| **Real T vs S stand-in** | Simulating with real T is costly; many papers simulate S instead (a Clifford "proxy"). Chan et al. show the proxy hides real-T errors. |
| **Injection angle theta** | Google injects states at many angles theta to map the Bloch sphere; theta = pi/4 is the T state. |

## 4. The protocol (the paper's main story)
| Keyword | Meaning |
|---|---|
| **Injection** | Put a physical magic state onto one qubit, then encode it into the colour code. Not fault-tolerant: about 1 in 230 error. |
| **Cultivation** | Check the encoded T state and throw it away if anything looks wrong. Keeps only good states. |
| **H_L (logical Hadamard-like operator)** | H = T-dagger X T. The T state is its +1 eigenstate, so measuring H_L checks "is this really a T state?" |
| **Double check** | Measures H_L twice: fold, measure, unfold (the time reverse). Any disagreement = discard. |
| **Fold / unfold** | CNOT layers that gather the X parity of all 7 data onto one helper qubit, then undo it. |
| **Time reversal** | The unfold is the fold run backwards, so the stabilisers come back and the helpers become extra detectors. |
| **Flag checks** | Detectors on the helper qubits after the time reversal (3 in Google's circuit, Fig. S11). Catch some errors; not the hook errors Chan finds. |
| **Grafting / escape** | Move the cultivated state into a much bigger surface code (here d = 5, 54 qubits). |
| **Matchable code** | A code that a fast matching decoder can decode (future work in the paper). |

## 5. Errors, detection, statistics
| Keyword | Meaning |
|---|---|
| **Detector** | A combination of measurements that should always give the same result without noise. |
| **Detection event** | A detector gave the wrong result: an error happened. |
| **Post-selection** | Keep only shots with no detection events; discard the rest. |
| **Data retainment rate** | Fraction of shots kept (8 % for the full circuit; 76 % for injection only). Our "acceptance". |
| **Fidelity / infidelity** | How close the state is to the ideal one (1 = perfect). Infidelity = 1 - fidelity = error. |
| **Logical error probability** | Chance the kept logical state is wrong. |
| **Upper bound** | Their kickback tomography can only say "the error is at most this much". |
| **Fault distance** | Smallest number of faults in the circuit (gates, idles, measurements) that cause an undetected logical error. Error scales as p to that power. |
| **Noise strength p** | Error rate per physical operation. |
| **SI1000** | A standard superconducting noise model (measurement and idle errors larger than gate errors), scaled by p. Google matches its data with p = 0.23-0.30 %. |
| **Pauli twirling** | Randomising gates so coherent noise behaves like simple Pauli noise. |
| **Unphysical expectations** | Tomography results outside the Bloch sphere, due to statistics or coherent errors (Sec. IX). |

## 6. Measuring the state
| Keyword | Meaning |
|---|---|
| **Logical state tomography** | Measure the logical X, Y, Z many times to rebuild the state on the Bloch sphere (Fig. 2). |
| **Bloch sphere** | Sphere picture of a qubit state; pure states on the surface, noisy states inside. |
| **Kickback tomography (KT)** | Google's new method: run more cultivation rounds and QEC cycles to measure, fault-tolerantly, an upper bound on the T-state error (Fig. 3). Their headline 1-2 in 10,000. |
| **Phase kickback** | The H_L value is "kicked back" onto the helper qubit, so measuring the helper measures H_L. |

## 7. Simulators (Sec. XI)
| Keyword | Meaning |
|---|---|
| **State vector simulation** | Store all 2^n amplitudes exactly. Fine for 12 qubits, impossible for 54. |
| **kraus-sim** | Google's state-vector "quantum trajectories" simulator (Figs. 2, 3). |
| **qevol** | Google's simulator keeping superpositions of stabiliser states; cheap when there are few T gates. Used for the 54-qubit grafting (Fig. 4). Same idea as Clifft. |
| **qsim / QVM** | Google's public state-vector simulator and "quantum virtual machine" with Willow noise. What we use. |

## How the keywords connect (one line)
Injection (noisy T state) -> encode into colour code -> double check (fold, measure H_L, unfold; flags) ->
post-select -> QEC cycles -> measure with kickback tomography, or graft into the surface code.
