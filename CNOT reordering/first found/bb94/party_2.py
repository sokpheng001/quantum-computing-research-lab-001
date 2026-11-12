"""
party_2.py — the receiver in a two-machine BB84 demo.

Start Party 2 FIRST. He listens on two ports:
  --qport  quantum channel  (Party 1 or Eavesdropper connects here and streams qubits)
  --cport  classical channel (Party 1 connects here afterwards for sifting/check)

    python party_2.py                       # listen on 0.0.0.0, ports 5001 / 5002
    python party_2.py --qport 6001 --cport 6002

NOTE: this is a demonstration of the protocol's message flow. The "qubit" that
travels on the socket is a classical label like "+", which CAN be copied, so
the demo has no real security. Real security needs real photons.
"""
import argparse
import json
import random
import socket

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

sim = AerSimulator()


# ---------------------------------------------------------------- helpers ----
def recv_lines(conn):
    """Yield one JSON object per newline-terminated line."""
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
    """Put a qubit in `state_label` ('0','1','+','-'), read it in `basis`."""
    qc = QuantumCircuit(1, 1)
    qc.initialize(state_label, 0)
    if basis == "X":
        qc.h(0)
    qc.measure(0, 0)
    counts = sim.run(qc, shots=1).result().get_counts()
    return int(next(iter(counts)))


# ------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--qport", type=int, default=5001)
    ap.add_argument("--cport", type=int, default=5002)
    ap.add_argument("--no-plot", dest="plot", action="store_false",
                    help="skip the report figure (saved by default)")
    ap.add_argument("--out", default="party_2_report.png")
    args = ap.parse_args()

    # ---------- Phase 2: receive qubits on the quantum channel, measure ----------
    qsock = socket.socket()
    qsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    qsock.bind((args.host, args.qport))
    qsock.listen(1)
    print(f"[Party 2] quantum channel listening on {args.host}:{args.qport}")
    qconn, addr = qsock.accept()
    print(f"[Party 2] quantum channel connected from {addr[0]}")

    bases, results = [], []
    for msg in recv_lines(qconn):
        if msg.get("end"):
            break
        basis = random.choice("ZX")          # Party 2's private coin flip
        bit = measure(msg["state"], basis)   # the only quantum step Party 2 does
        bases.append(basis)
        results.append(bit)
    qconn.close()
    qsock.close()
    n = len(results)
    print(f"[Party 2] received and measured {n} qubits")
    print(f"[Party 2] my bases  : {''.join(bases)}")
    print(f"[Party 2] my results: {''.join(map(str, results))}   (some are coin flips — I can't tell which yet)")

    # ---------- Phases 3-4: classical channel — sifting and check ----------
    csock = socket.socket()
    csock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    csock.bind((args.host, args.cport))
    csock.listen(1)
    print(f"[Party 2] classical channel listening on {args.host}:{args.cport}")
    cconn, _ = csock.accept()
    lines = recv_lines(cconn)

    # Party 2 announces his bases (safe: bases reveal nothing about bit values)
    send(cconn, {"type": "bases", "bases": bases})
    print("[Party 2] -> Party 1: my bases (public)")

    keep_msg = next(lines)                    # {"type":"keep","positions":[...]}
    kept = keep_msg["positions"]
    sifted = {i: results[i] for i in kept}
    print(f"[Party 2] <- Party 1: keep positions {kept}")
    print(f"[Party 2] sifted key: {''.join(str(sifted[i]) for i in kept)}")

    check_msg = next(lines)                   # {"type":"check","positions":[...],"bits":[...]}
    cpos, abits = check_msg["positions"], check_msg["bits"]
    bbits = [results[i] for i in cpos]
    send(cconn, {"type": "check_reply", "bits": bbits})
    mismatches = sum(a != b for a, b in zip(abits, bbits))
    rate = mismatches / len(cpos) if cpos else 0.0
    print(f"[Party 2] check on {len(cpos)} sample bits: {mismatches} mismatches ({rate:.0%})")

    verdict = next(lines)                     # {"type":"verdict","abort":bool,"report":bool}

    # Demo-only: if Party 1 asked for a report figure, hand over Party 2's raw view.
    # A real BB84 run would NEVER do this — it exists only so the figure can
    # show both sides after the protocol has finished.
    if verdict.get("report"):
        send(cconn, {"type": "report", "bases": bases, "results": results})
        print("[Party 2] -> Party 1: my bases/results for the report figure (demo only)")

    cconn.close()
    csock.close()

    abort = verdict["abort"]
    final = [] if abort else [sifted[i] for i in kept if i not in set(cpos)]
    if abort:
        print("[Party 2] ABORT — error rate too high, someone was listening. Key discarded.")
    else:
        print(f"[Party 2] FINAL KEY ({len(final)} bits): {''.join(map(str, final))}")

    if args.plot:
        make_report(bases, results, kept, cpos, abits, bbits, rate, abort, final, args.out)
        print(f"[Party 2] report figure saved to {args.out}")


# ------------------------------------------------------------------ report ----
def make_report(bases, results, kept, sample, their_bits, my_bits, rate, abort, final, out):
    """Party 2's own view: his bases and results, which positions were kept,
    which were revealed in the check, and how the revealed ones compared."""
    n = len(results)
    kept_set, sample_set = set(kept), set(sample)
    check_wrong = {p for p, a, b in zip(sample, their_bits, my_bits) if a != b}

    rows = [("Party 2 basis", bases), ("Party 2 result", results)]
    fig = plt.figure(figsize=(max(9, n * 0.32), 5.0))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 2.2], hspace=0.7)
    ax = fig.add_subplot(gs[0])
    axs = fig.add_subplot(gs[1])

    for r, (label, values) in enumerate(rows):
        y = len(rows) - 1 - r
        for i, v in enumerate(values):
            if label == "Party 2 result" and i in check_wrong:
                face = "#e15759"
            elif i in kept_set:
                face = "#c8e6c9"
            else:
                face = "#eeeeee"
            edge = "#ff9800" if i in sample_set else "white"
            lw = 2.2 if i in sample_set else 1.2
            ax.add_patch(plt.Rectangle((i, y), 1, 1, facecolor=face, edgecolor=edge, linewidth=lw))
            ax.text(i + 0.5, y + 0.5, str(v), ha="center", va="center",
                    fontsize=8 if n > 40 else 10, family="monospace")
        ax.text(-0.3, y + 0.5, label, ha="right", va="center", fontsize=10)

    ax.set_xlim(0, n); ax.set_ylim(0, len(rows)); ax.set_yticks([])
    step = 1 if n <= 40 else 5
    ax.set_xticks([i + 0.5 for i in range(0, n, step)])
    ax.set_xticklabels([str(i + 1) for i in range(0, n, step)], fontsize=8)
    ax.set_xlabel("position")
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor="#c8e6c9", label="kept (bases match)"),
               plt.Rectangle((0, 0), 1, 1, facecolor="#eeeeee", label="discarded (bases differ)"),
               plt.Rectangle((0, 0), 1, 1, facecolor="#e15759", label="check mismatch"),
               plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#ff9800", linewidth=2, label="revealed in check")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.45), ncol=4, frameon=False, fontsize=9)
    ax.set_title(f"BB84 run — Party 2 report — {n} qubits", fontsize=12)

    axs.axis("off")
    verdict = "ABORT — eavesdropper suspected" if abort else "OK — key accepted"
    color = "#e15759" if abort else "#2e7d32"
    axs.text(0.0, 0.85, f"received {n}   →   sifted {len(kept)} ({len(kept) / n:.0%})   →   "
                        f"checked {len(sample)}   →   final key {len(final)} bits",
             fontsize=10, family="monospace", va="top")
    axs.text(0.0, 0.55, f"error rate seen in check sample: {rate:.0%}   (abort above 11%)",
             fontsize=10, family="monospace", va="top")
    axs.text(0.0, 0.22, verdict, fontsize=13, weight="bold", color=color, va="top")
    if not abort:
        key = "".join(map(str, final))
        axs.text(0.0, 0.0, f"key: {key if len(key) <= 64 else key[:64] + '…'}",
                 fontsize=9, family="monospace", va="top")
    fig.savefig(out, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()