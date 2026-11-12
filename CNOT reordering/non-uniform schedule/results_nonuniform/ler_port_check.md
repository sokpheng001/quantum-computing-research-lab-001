# Check: ours/bravyi_ler.py vs bravyi_ref/decoder_run.py (2026-10-18)

Case: [[72,12,6]], Bravyi's schedule S, p = 0.006, 6 noisy cycles (+2 noiseless), Bravyi decoder settings
(min-sum, ms_scaling_factor 0, max_iter 10000, osd_cs order 7). Metric: fraction of runs with any logical failure.

| Run | Failures / shots | Rate |
|---|---|---|
| Reference (decoder_run.py copy, ldpc 0.1.60 environment) | 951 / 2400 | 39.6% |
| Our port, all batches (seeds 100-102, 200-202, 100x1200, 11-13x1200, 21-29x400) | 4160 / 10800 | 38.5% |

Difference -1.1 percentage points, z = -1.0: consistent. An early 1200-shot comparison (36.1%) was a statistical
fluctuation: the sampler statistics, the column order (identical to the reference), the decoder library (ldpc 2.4.1
legacy shim and ldpc 0.1.60 give identical decodes on the same samples) and the batch size were all checked.
