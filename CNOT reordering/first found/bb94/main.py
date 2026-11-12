"""
BB84 simulation with plots.

Figure 1  - one small run, position by position: Alice's bit and basis,
            Bob's basis and result, which positions were kept, and where
            Bob's kept bit disagrees with Alice's.
Figure 2  - error rate over many runs, with and without Eve.

Run:  python bb84_plot.py
"""
import random
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

sim = AerSimulator()


# ----------------------------------------------------------------------------
# Protocol
# ----------------------------------------------------------------------------
def send_one_qubit(alice_bit, alice_basis, bob_basis, eve_present):
    """One qubit's journey: Alice -> (Eve) -> Bob. Basis is 'Z' or 'X'."""
    qc = QuantumCircuit(1, 1)

    # Alice prepares: X if bit is 1, H if basis is X
    if alice_bit == 1:
        qc.x(0)
    if alice_basis == 'X':
        qc.h(0)

    # Eve: measure in a random basis, then re-send what she saw
    if eve_present:
        eve_basis = random.choice(['Z', 'X'])
        if eve_basis == 'X':
            qc.h(0)
        qc.measure(0, 0)
        if eve_basis == 'X':
            qc.h(0)

    # Bob measures: H if basis is X
    if bob_basis == 'X':
        qc.h(0)
    qc.measure(0, 0)

    counts = sim.run(qc, shots=1).result().get_counts()
    return int(next(iter(counts)))


def bb84_run(n, eve_present):
    """Run the protocol once. Returns a dict with every list, for plotting."""
    alice_bits  = [random.randint(0, 1) for _ in range(n)]
    alice_bases = [random.choice('ZX') for _ in range(n)]
    bob_bases   = [random.choice('ZX') for _ in range(n)]
    bob_bits    = [send_one_qubit(a, ab, bb, eve_present)
                   for a, ab, bb in zip(alice_bits, alice_bases, bob_bases)]

    kept     = [ab == bb for ab, bb in zip(alice_bases, bob_bases)]
    mismatch = [k and (a != b) for k, a, b in zip(kept, alice_bits, bob_bits)]

    n_kept = sum(kept)
    n_err  = sum(mismatch)
    return dict(alice_bits=alice_bits, alice_bases=alice_bases,
                bob_bases=bob_bases, bob_bits=bob_bits,
                kept=kept, mismatch=mismatch,
                n_kept=n_kept, n_err=n_err,
                error_rate=(n_err / n_kept) if n_kept else 0.0)


# ----------------------------------------------------------------------------
# Figure 1: one run, position by position
# ----------------------------------------------------------------------------
def plot_single_run(run, title):
    n = len(run['alice_bits'])
    rows = ["Alice bit", "Alice basis", "Bob basis", "Bob result"]
    data = [run['alice_bits'], run['alice_bases'], run['bob_bases'], run['bob_bits']]

    fig, ax = plt.subplots(figsize=(max(8, n * 0.45), 3.6))

    for r, (label, values) in enumerate(zip(rows, data)):
        y = len(rows) - 1 - r
        for i, v in enumerate(values):
            if run['mismatch'][i] and label == "Bob result":
                face = '#e15759'             # kept but wrong  -> red
            elif run['kept'][i]:
                face = '#c8e6c9'             # kept            -> green
            else:
                face = '#eeeeee'             # discarded       -> grey
            ax.add_patch(plt.Rectangle((i, y), 1, 1, facecolor=face,
                                       edgecolor='white', linewidth=1.5))
            ax.text(i + 0.5, y + 0.5, str(v), ha='center', va='center',
                    fontsize=10, family='monospace')
        ax.text(-0.3, y + 0.5, label, ha='right', va='center', fontsize=10)

    ax.set_xlim(0, n)
    ax.set_ylim(0, len(rows))
    ax.set_xticks([i + 0.5 for i in range(n)])
    ax.set_xticklabels([str(i + 1) for i in range(n)], fontsize=8)
    ax.set_yticks([])
    ax.set_xlabel("position")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # legend
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor='#c8e6c9', label='kept (bases match)'),
               plt.Rectangle((0, 0), 1, 1, facecolor='#eeeeee', label='discarded (bases differ)'),
               plt.Rectangle((0, 0), 1, 1, facecolor='#e15759', label='kept but wrong (Eve)')]
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.28),
              ncol=3, frameon=False, fontsize=9)

    ax.set_title(f"{title}   —   kept {run['n_kept']}/{n}, "
                 f"errors {run['n_err']}, error rate {run['error_rate']:.0%}",
                 fontsize=11)
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
# Figure 2: error rate over many runs, with and without Eve
# ----------------------------------------------------------------------------
def plot_error_rates(n_qubits, n_trials):
    rates = {False: [], True: []}
    for eve in (False, True):
        for _ in range(n_trials):
            rates[eve].append(bb84_run(n_qubits, eve)['error_rate'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))

    # left: mean error rate as bars
    means = [sum(rates[False]) / n_trials, sum(rates[True]) / n_trials]
    bars = ax1.bar(["No Eve", "Eve present"], means, color=['#4e79a7', '#e15759'])
    ax1.axhline(0.25, color='grey', linestyle='--', linewidth=1)
    ax1.text(-0.42, 0.255, "25% expected (intercept-resend)", ha='left', va='bottom', fontsize=8, color='grey')
    ax1.axhline(0.11, color='orange', linestyle=':', linewidth=1)
    ax1.text(-0.42, 0.115, "~11% abort threshold", ha='left', va='bottom', fontsize=8, color='orange')
    for b, m in zip(bars, means):
        ax1.text(b.get_x() + b.get_width() / 2, m + 0.01, f"{m:.1%}",
                 ha='center', va='bottom', fontsize=10)
    ax1.set_ylim(0, 0.4)
    ax1.set_ylabel("error rate in sifted key")
    ax1.set_title(f"Mean over {n_trials} runs, {n_qubits} qubits each", fontsize=10)

    # right: distribution per run
    ax2.hist(rates[False], bins=20, range=(0, 0.5), alpha=0.8, color='#4e79a7', label='No Eve')
    ax2.hist(rates[True],  bins=20, range=(0, 0.5), alpha=0.8, color='#e15759', label='Eve present')
    ax2.axvline(0.11, color='orange', linestyle=':', linewidth=1)
    ax2.set_xlabel("error rate in sifted key")
    ax2.set_ylabel("number of runs")
    ax2.set_title("Distribution across runs", fontsize=10)
    ax2.legend(frameon=False, fontsize=9)

    for ax in (ax1, ax2):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
if __name__ == "__main__":
    random.seed(7)   # remove for a different run each time

    fig1 = plot_single_run(bb84_run(10, eve_present=False), "One run, no Eve")
    fig2 = plot_single_run(bb84_run(10, eve_present=True),  "One run, Eve present")
    fig3 = plot_error_rates(n_qubits=200, n_trials=40)

    fig1.savefig("bb84_run_no_eve.png", dpi=150, bbox_inches='tight')
    fig2.savefig("bb84_run_with_eve.png", dpi=150, bbox_inches='tight')
    fig3.savefig("bb84_error_rates.png", dpi=150, bbox_inches='tight')
    print("Saved bb84_run_no_eve.png, bb84_run_with_eve.png, bb84_error_rates.png")
    plt.show()