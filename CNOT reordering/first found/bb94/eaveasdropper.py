"""
eavesdropper.py — the eavesdropper in a two-machine BB84 demo (intercept-resend attack).

Eavesdropper sits between Party 1 and Party 2 on the QUANTUM channel only. Start Party 2, then
Eavesdropper, then point Party 1 at Eavesdropper:

    python eavesdropper.py --party_2-host <party_2-ip>                  # listen on 5000, forward to Party 2:5001
    python party_1.py --host <eavesdropper-ip> --qport 5000 --chost <party_2-ip>

For every qubit that passes through, Eavesdropper guesses a basis, measures it (which
destroys the original), and sends Party 2 a fresh qubit in the state she saw.
Half her guesses are wrong, so about 25% of Party 2's sifted bits end up wrong,
and Party 1 and Party 2 catch her in the check phase.

Eavesdropper does NOT touch the classical channel — she can read it in real life, but
reading bases after the qubits are gone gives her nothing.
"""
import argparse
import json
import random
import socket
import time

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

sim = AerSimulator()
STATE = {("Z", 0): "0", ("Z", 1): "1", ("X", 0): "+", ("X", 1): "-"}


def recv_lines(conn):
    buf = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                yield json.loads(line)


def send(conn, obj):
    conn.sendall((json.dumps(obj) + "\n").encode())


def measure(state_label, basis):
    qc = QuantumCircuit(1, 1)
    qc.initialize(state_label, 0)
    if basis == "X":
        qc.h(0)
    qc.measure(0, 0)
    return int(next(iter(sim.run(qc, shots=1).result().get_counts())))


def connect(host, port, retries=30):
    for _ in range(retries):
        try:
            return socket.create_connection((host, port))
        except OSError:
            time.sleep(0.5)
    raise SystemExit(f"[Eavesdropper] could not connect to {host}:{port}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="0.0.0.0")
    ap.add_argument("--listen-port", type=int, default=5000)
    ap.add_argument("--party_2-host", default="localhost")
    ap.add_argument("--party_2-port", type=int, default=5001)
    args = ap.parse_args()

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.listen_host, args.listen_port))
    srv.listen(1)
    print(f"[Eavesdropper] waiting for Party 1 on {args.listen_host}:{args.listen_port} ...")
    a_conn, addr = srv.accept()
    print(f"[Eavesdropper] Party 1 connected from {addr[0]}; connecting to Party 2 {args.party_2_host}:{args.party_2_port}")
    b_conn = connect(args.party_2_host, args.party_2_port)

    guesses, seen = [], []
    for msg in recv_lines(a_conn):
        if msg.get("end"):
            send(b_conn, msg)
            break
        basis = random.choice("ZX")                     # Eavesdropper has to guess
        bit = measure(msg["state"], basis)              # destroys the original
        guesses.append(basis)
        seen.append(bit)
        send(b_conn, {"slot": msg["slot"], "state": STATE[(basis, bit)]})   # re-send her guess

    a_conn.close()
    b_conn.close()
    srv.close()
    print(f"[Eavesdropper] intercepted {len(seen)} qubits")
    print(f"[Eavesdropper] my basis guesses: {''.join(guesses)}")
    print(f"[Eavesdropper] what I saw      : {''.join(map(str, seen))}   (half measured in the wrong basis — I can't tell which)")


if __name__ == "__main__":
    main()