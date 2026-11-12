# Tests of the QVM engine

Unit tests for `../qvm_willow.py`. They check:
- the stim to cirq conversion;
- device validation on `willow_pink`;
- noiseless real-T correctness;
- that fault injection agrees with cliffordea.

Run from `google-quantum/`:

    .venv/bin/python -m pytest -q "qvm-google (main)/tests"
