"""
party_1.py — the sender in a two-machine BB84 demo.

Start Party 2 first (and Eavesdropper, if you want an eavesdropper), then run Party 1:

    python party_1.py --host <party_2-ip>                    # direct to Party 2
    python party_1.py --host <eavesdropper-ip> --qport 5000       # through Eavesdropper's proxy

  --host    where to send qubits (Party 2, or Eavesdropper if she is in the middle)
  --qport   quantum-channel port on that host (Party 2 5001, Eavesdropper 5000 by default)
  --chost   Party 2's address for the classical channel (defaults to --host)
  --cport   Party 2's classical-channel port (default 5002)
  -n        number of qubits to send (e.g. -n 100)
  --sample  fraction of sifted bits sacrificed for the eavesdropper check
  --no-plot skip the report figure (party_1_report.png is saved by default)
  --out     file name for the report figure

NOTE: this is a demonstration of the protocol's message flow. The "qubit" that
travels on the socket is a classical label like "+", which CAN be copied, so
the demo has no real security. Real security needs real photons.
"""
import argparse
import json
import random
import socket
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ABORT_THRESHOLD = 0.11   # BB84 is insecure above ~11% error; intercept-resend gives ~25%

STATE = {("Z", 0): "0", ("Z", 1): "1", ("X", 0): "+", ("X", 1): "-"}


# ---------------------------------------------------------------- helpers ----
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


def connect(host, port, retries=30):
    for _ in range(retries):
        try:
            return socket.create_connection((host, port))
        except OSError:
            time.sleep(0.5)
    raise SystemExit(f"[Party 1] could not connect to {host}:{port}")


# ------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--qport", type=int, default=5001)
    ap.add_argument("--chost", default=None)
    ap.add_argument("--cport", type=int, default=5002)
    ap.add_argument("-n", type=int, default=64)
    ap.add_argument("--sample", type=float, default=0.3)
    ap.add_argument("--no-plot", dest="plot", action="store_false",
                    help="skip the report figure (saved by default)")
    ap.add_argument("--out", default="party_1_report.png")
    args = ap.parse_args()
    chost = args.chost or args.host

    # ---------- Phase 1: random bits and bases, prepare and send qubits ----------
    bits  = [random.randint(0, 1) for _ in range(args.n)]      # classical coin
    bases = [random.choice("ZX")  for _ in range(args.n)]      # classical coin
    print(f"[Party 1] raw bits : {''.join(map(str, bits))}")
    print(f"[Party 1] my bases : {''.join(bases)}")

    qconn = connect(args.host, args.qport)
    print(f"[Party 1] quantum channel connected to {args.host}:{args.qport}")
    for i, (b, B) in enumerate(zip(bits, bases)):
        send(qconn, {"slot": i, "state": STATE[(B, b)]})       # the "qubit"
    send(qconn, {"end": True})
    qconn.close()
    print(f"[Party 1] sent {args.n} qubits")

    # ---------- Phases 3-4: classical channel — sifting and check ----------
    cconn = connect(chost, args.cport)
    lines = recv_lines(cconn)
    print(f"[Party 1] classical channel connected to {chost}:{args.cport}")

    party_2_bases = next(lines)["bases"]
    print(f"[Party 1] <- Party 2: his bases (public)")

    kept = [i for i in range(args.n) if bases[i] == party_2_bases[i]]
    send(cconn, {"type": "keep", "positions": kept})
    sifted = {i: bits[i] for i in kept}
    print(f"[Party 1] -> Party 2: keep positions {kept}")
    print(f"[Party 1] sifted key: {''.join(str(sifted[i]) for i in kept)}")

    # eavesdropper check: sacrifice a random sample of kept bits
    k = max(1, int(len(kept) * args.sample)) if kept else 0
    cpos = sorted(random.sample(kept, k)) if k else []
    abits = [bits[i] for i in cpos]
    send(cconn, {"type": "check", "positions": cpos, "bits": abits})
    bbits = next(lines)["bits"]
    mismatches = sum(a != b for a, b in zip(abits, bbits))
    rate = mismatches / len(cpos) if cpos else 0.0
    print(f"[Party 1] check on {len(cpos)} sample bits: {mismatches} mismatches ({rate:.0%})")

    abort = rate > ABORT_THRESHOLD
    send(cconn, {"type": "verdict", "abort": abort, "report": args.plot})

    party_2_view = next(lines) if args.plot else None      # demo-only, see party_2.py
    cconn.close()

    final = [] if abort else [sifted[i] for i in kept if i not in set(cpos)]
    if abort:
        print("[Party 1] ABORT — error rate too high, someone was listening. Key discarded.")
    else:
        print(f"[Party 1] FINAL KEY ({len(final)} bits): {''.join(map(str, final))}")

    if args.plot:
        make_report(bits, bases, party_2_view["bases"], party_2_view["results"],
                    kept, cpos, rate, abort, final, args.out)
        print(f"[Party 1] report figure saved to {args.out}")


# ------------------------------------------------------------------ report ----
def make_report(a_bits, a_bases, b_bases, b_results, kept, sample, rate, abort, final, out):
    """Per-position grid of the run plus a summary panel. Uses Party 2's view,
    which he hands over AFTER the protocol purely for this figure."""
    n = len(a_bits)
    kept_set, sample_set = set(kept), set(sample)
    wrong = {i for i in kept if a_bits[i] != b_results[i]}

    rows = [("Party 1 bit", a_bits), ("Party 1 basis", a_bases),
            ("Party 2 basis", b_bases), ("Party 2 result", b_results)]

    fig = plt.figure(figsize=(max(9, n * 0.32), 6.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 2.2], hspace=0.55)
    ax = fig.add_subplot(gs[0])
    axs = fig.add_subplot(gs[1])

    for r, (label, values) in enumerate(rows):
        y = len(rows) - 1 - r
        for i, v in enumerate(values):
            if label == "Party 2 result" and i in wrong:
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
    for s in ax.spines.values():
        s.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor="#c8e6c9", label="kept (bases match)"),
               plt.Rectangle((0, 0), 1, 1, facecolor="#eeeeee", label="discarded (bases differ)"),
               plt.Rectangle((0, 0), 1, 1, facecolor="#e15759", label="kept but wrong"),
               plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#ff9800", linewidth=2, label="revealed in check")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=4, frameon=False, fontsize=9)
    ax.set_title(f"BB84 run — Party 1 report — {n} qubits", fontsize=12)

    # summary panel
    axs.axis("off")
    n_kept, n_sample, n_wrong = len(kept), len(sample), len(wrong)
    verdict = "ABORT — eavesdropper suspected" if abort else "OK — key accepted"
    color = "#e15759" if abort else "#2e7d32"
    lines_txt = [
        f"sent {n}   →   sifted {n_kept} ({n_kept / n:.0%})   →   checked {n_sample}   →   final key {len(final)} bits",
        f"sifted bits actually wrong: {n_wrong} of {n_kept} ({(n_wrong / n_kept if n_kept else 0):.0%})      "
        f"error rate seen in check sample: {rate:.0%}   (abort above {ABORT_THRESHOLD:.0%})",
    ]
    axs.text(0.0, 0.85, lines_txt[0], fontsize=10, family="monospace", va="top")
    axs.text(0.0, 0.55, lines_txt[1], fontsize=10, family="monospace", va="top")
    axs.text(0.0, 0.22, verdict, fontsize=13, weight="bold", color=color, va="top")
    if not abort:
        key = "".join(map(str, final))
        axs.text(0.0, 0.0, f"key: {key if len(key) <= 64 else key[:64] + '…'}", fontsize=9, family="monospace", va="top")

    fig.savefig(out, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()