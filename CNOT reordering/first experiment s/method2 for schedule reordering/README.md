# Method 2 — path-targeted partner search

Question (Bravyi et al. 2024, open question 4): does alternating Bravyi's schedule S with a second depth-7
schedule S' raise the circuit-level distance above S's value?  Codes: [[72,12,6]] (control) -> [[90,8,10]]
-> [[108,8,10]].  [[144]] runs on the Mac mini, never on this server.  Plan with PASS conditions: docs/task.md.
Results: RESULTS_partner.md (summary tables at the top).  Figures: figures_partner/.

Run:  ./launch.sh driver_partner.sh   |   ./launch.sh status   |   ./launch.sh stop
Auto-resume after a reboot: ../resume_all.sh (job "method2 for schedule reordering").  Log: results_partner/driver_partner.log

Code (run from this folder with ../venv/bin/python):
- bb_code.py, dcirc.py — copies of folder 001's library (circuit builder, DEM parsing, BP-OSD bound search, LER).
- partner_lib.py — schedule enumeration, physical fault locations, exact fault injection (stim FlipSimulator), torus families.
- partner.py — stages 0-5 + control check (--n, --stage); resumable, each stage writes results_partner/<n>/stage<k>.json.
- report.py — rebuilds RESULTS_partner.md;  figs.py — F1 (bounds), F2 (screen histogram), F3 (LER, only if Stage 5 ran).

Settings: distance search = randomised BP-OSD (Bravyi Eq. 12): serial min-sum scaling 0.625, 10 iterations, OSD-CS
order 20 (Bravyi's circuit_distance.py value), random priors in [0.005, 0.1], chunks of 100 trials, rng seed fixed
by (seed, chunk, basis, cycles) so every circuit sees the same seeds.  Trials per seed: 300 on [[72]], 600 on
[[90]]/[[108]] (Stage 0 may raise it to 1200 to reach Bravyi's value; Stage 4 then uses the same).  LER decoder
(Stage 5): min-sum 0.625, 100 iterations, OSD-CS order 7.  Noise: uniform circuit-level depolarising.

Exact checks: a fault set is a set of DEM columns; each column's physical representatives come from stim's
error explanation.  A location (cycle, instruction offset inside the cycle, Pauli on qubits) is placed into
another circuit only where that circuit has the same noise channel on the same qubits.  Detector and
observable flips there are computed by FlipSimulator; all representative choices are explored.
