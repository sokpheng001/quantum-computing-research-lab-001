"""Test 6 report: RESULTS.md + figures (PNG) from results/step1_data.json, step23_sim.json,
step4_circuits.json.

    .venv/bin/python -I "<this folder>/t6_report.py"
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import t6_common as C  # noqa: E402

PAPER = {  # values printed in Rosenfeld et al., arXiv:2512.13908 (see test4 references/google_notes.md)
    "injection_retention": ("about 76 %", 0.76),
    "cultivation_retention_T": ("about 45 % (read off Fig. 2D)", 0.45),
    "kt_error": ("1 in 10,000 to 1 in 5,000 (between 1x10^-4 and 2x10^-4), retention 8 %", None),
    "injection_error": ("about 1 in 230 (4.4(2) x 10^-3)", 4.4e-3),
}
COL = dict(hardware="#1f5fa8", google_sim="#6b6b6b", si1000="#d1661c", si1000_036="#8e44ad", qvm="#2e8b57", ideal="#000000")


def rows_by(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def at(rows, basis, theta):
    r = [x for x in rows if x["basis"] == basis and abs(x["theta"] - theta) < 1e-9]
    return r[0] if r else None


def exp_se(r):
    k = r["kept"]
    if not k:
        return float("nan")
    m = (1 - r["expectation_kept"]) / 2
    return 2 * math.sqrt(m * (1 - m) / k)


def ret_se(r):
    p = r["kept"] / r["shots"]
    return math.sqrt(p * (1 - p) / r["shots"])


def z(a, sa, b, sb):
    s = math.hypot(sa, sb)
    return (a - b) / s if s else float("nan")


def merged_retention(rows, theta):
    xs = [at(rows, b, theta) for b in ("X", "Z")]
    xs = [x for x in xs if x]
    n = sum(x["shots"] for x in xs)
    k = sum(x["kept"] for x in xs)
    return (k / n, math.sqrt(k / n * (1 - k / n) / n), n) if n else (float("nan"), float("nan"), 0)


def fmt(x, nd=3):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def figure_retention(s1, sim, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=160)
    series = [("Willow hardware (Google data)", s1.get("fig2/cultivation", {}).get("rows", []), "hardware", "o", 3),
              ("Google simulation (SI1000, p = 0.30 %)", s1.get("fig2/simulation", {}).get("rows", []), "google_sim", "s", 3),
              ("Ours: SI1000, p = 0.30 %", [r for r in sim.get("si1000", []) if r["exp"] == "fig2/cultivation"], "si1000", "D", 5),
              ("Ours: SI1000, p = 0.36 %", [r for r in sim.get("si1000@0.0036", []) if r["exp"] == "fig2/cultivation"], "si1000_036", "v", 5),
              ("Ours: Google QVM (willow_pink)", [r for r in sim.get("qvm", []) if r["exp"] == "fig2/cultivation"], "qvm", "^", 5)]
    for label, rows, key, mk, ms in series:
        th = sorted({r["theta"] for r in rows})
        if not th:
            continue
        ys = [merged_retention(rows, t) for t in th]
        x = [2 * t for t in th]  # theta in units of pi
        ax.errorbar(x, [y[0] for y in ys], yerr=[1.96 * y[1] for y in ys], fmt=mk, ms=ms, lw=0, elinewidth=1,
                    color=COL[key], label=label, mfc="white" if key in ("si1000", "si1000_036", "qvm") else COL[key], mew=1.4)
    inj = s1.get("fig2/injection", {}).get("rows", [])
    if inj:
        th = sorted({r["theta"] for r in inj})
        ax.plot([2 * t for t in th], [merged_retention(inj, t)[0] for t in th], "-", color=COL["hardware"],
                alpha=0.45, lw=1.2, label="Willow hardware, injection only")
    ax.axvline(0.25, color="#999999", lw=0.8, ls=":")
    ax.text(0.26, 0.02, "T state (π/4)", color="#555555", fontsize=8)
    ax.set_xlabel("injected polar angle θ (units of π)")
    ax.set_ylabel("data retention (fraction kept)")
    ax.set_xlim(-0.03, 2.0)
    ax.set_ylim(0, 0.85)
    ax.grid(alpha=0.25, lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7.5, frameon=False, loc="center right")
    ax.set_title("Fig. 2 cultivation circuit: retention vs injected angle", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def figure_T(s1, sim, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.0, 4.4), dpi=160)
    pts = [("Willow hardware", s1.get("fig2/cultivation", {}).get("rows", []), "hardware", "o"),
           ("Google simulation", s1.get("fig2/simulation", {}).get("rows", []), "google_sim", "s"),
           ("Ours: SI1000 0.30 %", [r for r in sim.get("si1000", []) if r["exp"] == "fig2/cultivation"], "si1000", "D"),
           ("Ours: SI1000 0.36 %", [r for r in sim.get("si1000@0.0036", []) if r["exp"] == "fig2/cultivation"], "si1000_036", "v"),
           ("Ours: QVM", [r for r in sim.get("qvm", []) if r["exp"] == "fig2/cultivation"], "qvm", "^")]
    for label, rows, key, mk in pts:
        x, zz = at(rows, "X", C.T_THETA), at(rows, "Z", C.T_THETA)
        if not (x and zz):
            continue
        ax.errorbar(x["expectation_kept"], zz["expectation_kept"], xerr=1.96 * exp_se(x), yerr=1.96 * exp_se(zz),
                    fmt=mk, ms=6, color=COL[key], label=label, capsize=2,
                    mfc="white" if key in ("si1000", "si1000_036", "qvm") else COL[key], mew=1.4)
    t = np.linspace(0.6, 0.8, 50)
    ax.plot(t, np.sqrt(np.clip(1 - t ** 2, 0, None)), color="#000000", lw=1, label="pure states (unit circle)")
    ax.plot([1 / math.sqrt(2)], [1 / math.sqrt(2)], marker="*", ms=12, color="#e0b000", mec="black", lw=0,
            label="ideal T state")
    ax.set_xlim(0.66, 0.73)
    ax.set_ylim(0.66, 0.73)
    ax.set_aspect("equal")
    ax.set_xlabel("⟨X⟩_L (kept shots)")
    ax.set_ylabel("⟨Z⟩_L (kept shots)")
    ax.grid(alpha=0.25, lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=7.5, frameon=False, loc="lower left")
    ax.set_title("T state after cultivation (θ = π/4), 95 % error bars", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    s1 = C.load_json(C.RES / "step1_data.json", {})
    s23 = C.load_json(C.RES / "step23_sim.json", {})
    sim = s23.get("models", {})
    s4 = C.load_json(C.RES / "step4_circuits.json", {})
    L = [f"# RESULTS: test 6, does our simulation match Google's paper? (written {C.kst_now()})", "",
         "Google's release: Zenodo 10.5281/zenodo.17872003 (Rosenfeld et al., arXiv:2512.13908), read-only in "
         "`references/zenodo_17872003/`. Code: `t6_step1_data.py`, `t6_step4_circuits.py`, `t6_sim.py`, `t6_report.py`, "
         "run by `run_t6.sh`. Kept = shots with no detection event (the paper's post-selection). "
         "⟨O⟩ = 1 − 2 × (fraction of kept shots with observable 1). θ = injected polar angle; the T state is θ = π/4.", ""]

    # ---------------- step 4
    L += ["## Step 4: is our Google baseline the circuit Google ran?", "",
          "| released circuit (as run) | ours | same gates every time step | same detectors | same observable | real T / T† in Google's cirq file |",
          "|---|---|---|---|---|---|"]
    for k, r in s4.items():
        exp, ours = k.split(" vs ")
        cs = r["cirq_vs_stim"]
        L.append(f"| {exp} | {ours} | {'yes' if r['gates']['identical'] else 'no (' + str(r['gates']['n_differing_ticks']) + ' time steps differ)'} "
                 f"| {'yes' if r['detectors']['same_set'] else 'no'} | {'yes' if r['detectors']['observables_same'] else 'no'} "
                 f"| {cs['real_T']} / {cs['real_T_dagger']} on {len(cs['real_T_qubits'])} data qubits |")
    L += ["", "- Our G4 (from the paper's Crumble link, Sec. VII) is the X-tomography circuit Google ran for Fig. 2, "
          "gate for gate; G5 = Fig. 3 and G6 = Fig. 4 likewise. The released files add only one trailing idle time step "
          "and different detector coordinate labels. The Z files are the second tomography setting (different final "
          "basis change), so they are not expected to equal the Crumble circuit.", ""]

    # ---------------- step 1
    L += ["## Step 1: Google's numbers recomputed from its hardware data with our code", "",
          "| experiment | shots | kept | retention | our detectors = Google's (first 200,000 shots, X basis) | Google's corrected file = our post-selected raw data |",
          "|---|---|---|---|---|---|"]
    for exp, r in s1.items():
        rows = r["rows"]
        n = sum(x["shots"] for x in rows)
        k = sum(x["kept"] for x in rows)
        m2d = all(v["detectors_equal"] and v["observable_equal"] for v in r["m2d"].values())
        cp = sum(x["corrected_is_postselected_raw"] for x in rows)
        L.append(f"| {exp} | {n:,} | {k:,} | {C.pct(k / n)} | {'yes' if m2d else 'NO'} | {cp} of {len(rows)} (basis, θ) settings |")
    L.append("")
    L += ["Key values at the T angle (θ = π/4), compared with the paper:", "",
          "| quantity | our value from Google's data | paper |", "|---|---|---|"]
    inj = s1.get("fig2/injection", {}).get("rows", [])
    cul = s1.get("fig2/cultivation", {}).get("rows", [])
    if inj:
        th = min({r["theta"] for r in inj}, key=lambda t: abs(t - C.T_THETA))
        rr = merged_retention(inj, th)
        L.append(f"| Fig. 2 injection retention | {C.pct(rr[0])} ± {C.pct(1.96 * rr[1], 2)} | {PAPER['injection_retention'][0]} |")
    if cul:
        rr = merged_retention(cul, C.T_THETA)
        x, zz = at(cul, "X", C.T_THETA), at(cul, "Z", C.T_THETA)
        L.append(f"| Fig. 2 cultivation retention | {C.pct(rr[0])} ± {C.pct(1.96 * rr[1], 2)} | {PAPER['cultivation_retention_T'][0]} |")
        if x and zz:
            L.append(f"| Fig. 2 cultivation ⟨X⟩_L, ⟨Z⟩_L | {fmt(x['expectation_kept'])}, {fmt(zz['expectation_kept'])} "
                     f"(± {fmt(1.96 * exp_se(x))}) | near 0.70, 0.70 (Fig. 2C); ideal 0.707 |")
    for exp in ("fig3/injection", "fig3/without_idle_rounds", "fig3/with_idle_rounds", "fig3/with_idle_rounds_zoom",
                "fig3/simulation", "fig3/simulation_zoom"):
        rows = s1.get(exp, {}).get("rows", [])
        if not rows:
            continue
        th = min({r["theta"] for r in rows}, key=lambda t: abs(t - C.T_THETA))
        sel = [r for r in rows if abs(r["theta"] - th) < 1e-9]
        n = sum(r["shots"] for r in sel)
        k = sum(r["kept"] for r in sel)
        e = sum((1 - r["expectation_kept"]) / 2 * r["kept"] for r in sel)
        ce = sum((1 - r["corrected_expectation"]) / 2 * r["corrected_rows"] for r in sel if r["corrected_rows"])
        cn = sum(r["corrected_rows"] for r in sel)
        lo, hi = C.ci_prop(int(round(e)), k)
        ref = PAPER["injection_error"][0] if "injection" in exp else (PAPER["kt_error"][0] if "with_idle" in exp else "–")
        L.append(f"| {exp} at θ = {2 * th:.3f}π: retention; wrong-sign rate among kept (raw) "
                 f"| {C.pct(k / n, 2)}; {int(round(e)):,} of {k:,} = {C.one_in(e / k) if k and e else '0'} "
                 f"(95 %: {C.one_in(hi)} to {C.one_in(lo) if lo else 'none'}); Google's corrected file: "
                 f"{C.one_in(ce / cn) if cn and ce else '–'} of {cn:,} | {ref} |")
    comb = [s1.get(e, {}).get("rows", []) for e in ("fig3/with_idle_rounds", "fig3/with_idle_rounds_zoom")]
    if all(comb):
        sel = [r for rows in comb for r in rows if abs(r["theta"] - C.T_THETA) < 1e-9]
        k = sum(r["kept"] for r in sel)
        e = int(round(sum((1 - r["expectation_kept"]) / 2 * r["kept"] for r in sel)))
        n = sum(r["shots"] for r in sel)
        lo, hi = C.ci_prop(e, k)
        L.append(f"| **fig3 full cultivation circuit, both hardware runs combined (θ = π/4)** | retention {C.pct(k / n, 2)}; "
                 f"**{e} of {k:,} = {C.one_in(e / k)}** (95 %: {C.one_in(hi)} to {C.one_in(lo)}) | {PAPER['kt_error'][0]} |")
    L += ["", "The wrong-sign rate is the fraction of kept shots whose kickback observable is 1, computed per θ "
          "closest to π/4 from raw data. For Fig. 2 and Fig. 3 Google's corrected file equals our post-selected raw "
          "data exactly; for Fig. 4 (grafting) Google decoded with Tesseract, which we do not re-implement here.", ""]

    # ---------------- step 2
    gs = s1.get("fig2/simulation", {}).get("rows", [])
    si = [r for r in sim.get("si1000", []) if r["exp"] == "fig2/cultivation"]
    for mkey, ptxt in (("si1000", "0.30 % (the value the paper states)"), ("si1000@0.0036", "0.36 % (our fit, see the gap check below)")):
        rows_m = [r for r in sim.get(mkey, []) if r["exp"] == "fig2/cultivation"]
        if not (gs and rows_m):
            continue
        L += [f"## Step 2: our simulator vs Google's simulator, our SI1000 at p = {ptxt}", "",
              "Google's simulated shots are in the release (`fig2/simulation`, SI1000 at p = 0.30 % per the paper, "
              "300,000 per basis per θ). z = (ours − Google) / combined standard error; |z| < 3 = agreement within statistics.", "",
              "| θ (π) | retention: Google sim | ours | z | ⟨X⟩: Google sim | ours | z | ⟨Z⟩: Google sim | ours | z |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        zr, ze = [], []
        for t in sorted({r["theta"] for r in rows_m}):
            g_r, o_r = merged_retention(gs, t), merged_retention(rows_m, t)
            z1 = z(o_r[0], o_r[1], g_r[0], g_r[1])
            zr.append(z1)
            line = [f"{2 * t:.3f}", fmt(g_r[0]), fmt(o_r[0]), f"{z1:+.1f}"]
            for b in ("X", "Z"):
                g, o = at(gs, b, t), at(rows_m, b, t)
                if g and o and o["kept"] and g["kept"]:
                    zz = z(o["expectation_kept"], exp_se(o), g["expectation_kept"], exp_se(g))
                    ze.append(zz)
                    line += [fmt(g["expectation_kept"]), fmt(o["expectation_kept"]), f"{zz:+.1f}"]
                else:
                    line += ["–"] * 3
            L.append("| " + " | ".join(line) + " |")
        zr = [x for x in zr if not math.isnan(x)]
        ze = [x for x in ze if not math.isnan(x)]
        L += ["", f"Retention: {sum(abs(x) < 3 for x in zr)} of {len(zr)} angles agree within 3 standard errors "
              f"(largest |z| {max(abs(x) for x in zr):.1f}). T-state quality ⟨X⟩, ⟨Z⟩: {sum(abs(x) < 3 for x in ze)} of "
              f"{len(ze)} agree (largest |z| {max(abs(x) for x in ze):.1f}).", ""]
    gap = C.load_json(C.RES / "gap_check.json")
    if gap:
        L += ["### Gap check: why our SI1000 at 0.30 % keeps more shots than Google's simulation", "",
              f"Per-detector firing rates at the T angle (X basis), ours ÷ Google's simulated shots "
              f"(`t6_gap_check.py`; Google sim retention {C.pct(gap['google_sim']['retention'])}, "
              f"hardware {C.pct(gap['hardware']['retention'])}):", "",
              "| our p | retention | detector rate ÷ Google's (mean over detectors) | spread |", "|---|---|---|---|"]
        for p_, r in gap["ours"].items():
            L.append(f"| {100 * float(p_):.2f} % | {C.pct(r['retention'])} | {r['ratio_mean']:.2f} | {r['ratio_spread']:.2f} |")
        L += ["", "Every detector is off by the same factor at 0.30 % (small spread), and one p (about 0.36 %) fits all "
              "detectors and the retention at once. So the circuits and detectors agree (step 4); the difference is "
              "one overall noise-strength factor: Google's SI1000 implementation at its stated p = 0.30 % is about "
              "1.2× stronger than ours at 0.30 %. A likely cause is a convention detail in how the depolarising "
              "channels or idle windows are counted; Google's simulator code is not public, so we state the "
              "calibrated equivalence instead (our p ≈ 1.2 × Google's p).", ""]

    # ---------------- step 3
    qv = [r for r in sim.get("qvm", []) if r["exp"] == "fig2/cultivation"]
    if cul and qv:
        L += ["## Step 3: simulation vs Willow hardware (Fig. 2 cultivation circuit)", "",
              "| θ (π) | retention: hardware | QVM | SI1000 0.30 % (ours) | ⟨X⟩: hardware | QVM | ⟨Z⟩: hardware | QVM |",
              "|---|---|---|---|---|---|---|---|"]
        for t in sorted({r["theta"] for r in qv}):
            h, q, s_ = merged_retention(cul, t), merged_retention(qv, t), merged_retention(si, t)
            hx, qx, hz, qz = at(cul, "X", t), at(qv, "X", t), at(cul, "Z", t), at(qv, "Z", t)
            L.append(f"| {2 * t:.3f} | {fmt(h[0])} | {fmt(q[0])} | {fmt(s_[0])} | "
                     f"{fmt(hx['expectation_kept'] if hx else None)} | {fmt(qx['expectation_kept'] if qx else None)} | "
                     f"{fmt(hz['expectation_kept'] if hz else None)} | {fmt(qz['expectation_kept'] if qz else None)} |")
        h, q = merged_retention(cul, C.T_THETA), merged_retention(qv, C.T_THETA)
        L += ["", f"At the T angle: hardware retention {C.pct(h[0])}, QVM {C.pct(q[0])} "
              f"(QVM / hardware = {q[0] / h[0]:.2f}).", ""]
        iq = [r for r in sim.get("qvm", []) if r["exp"] == "fig2/injection"]
        isi = [r for r in sim.get("si1000", []) if r["exp"] == "fig2/injection"]
        if iq and inj:
            th = iq[0]["theta"]
            L.append(f"Injection only at θ = {2 * th:.3f}π: retention hardware {C.pct(merged_retention(inj, th)[0])}, "
                     f"QVM {C.pct(merged_retention(iq, th)[0])}, SI1000 0.30 % {C.pct(merged_retention(isi, th)[0])}.")
            L.append("")
    # figures
    if s1:
        figure_retention(s1, sim, C.FIG / "t6_fig2_retention.png")
        figure_T(s1, sim, C.FIG / "t6_fig2_T_state.png")
        L += ["## Figures", "", "- `figures/t6_fig2_retention.png`: retention vs injected angle (Google's Fig. 2D), "
              "hardware vs Google's simulation vs ours.",
              "- `figures/t6_fig2_T_state.png`: the cultivated T state's ⟨X⟩, ⟨Z⟩ (Google's Fig. 2C), all four sources.", ""]
    L += ["## Limits", "",
          "- Steps 2 and 3 cover the Fig. 2 circuit (12 qubits). The Fig. 3 kickback circuit (14 qubits, error about 1 in "
          "10,000) needs far more shots and is reported here from Google's data only (step 1).",
          "- QVM = willow_pink median calibration (2024), not the calibration of the day Google took the data.",
          "- Google's simulated points are their released shots, so step 2 compares shot data with shot data."]
    (C.HERE / "RESULTS.md").write_text("\n".join(L) + "\n")
    C.log("report written: RESULTS.md")


if __name__ == "__main__":
    main()
