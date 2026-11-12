# BB84 quantum key distribution: a small simulation

**Purpose.** A teaching example of the BB84 protocol (Bennett and Brassard, 1984), simulated with Qiskit Aer.
Alice sends random bits in random bases (Z or X). Bob measures in random bases, and they keep the positions
where the bases match. An eavesdropper (Eve) who measures in between raises the error rate in the kept bits,
which reveals her.

| File | What it does |
|---|---|
| `main.py` | the protocol and two plots: one run position by position, and the error rate over many runs with and without Eve |
| `party_1.py`, `party_2.py` | the two parties as separate scripts; reports in `party_1_report.png`, `party_2_report.png` |
| `eaveasdropper.py` | the eavesdropper |
| `requirements.txt`, `activate-python-env.sh` | environment |

Run: `pip install -r requirements.txt`, then `python main.py`.
