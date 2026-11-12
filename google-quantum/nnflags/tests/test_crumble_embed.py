"""Crumble converter, z_reset_idle refinement, and the task-B embedding search."""
from pathlib import Path

import stim

from cliffordea import enum
from nnflags import constraints as C
from nnflags import embed_search as E
from nnflags.crumble import crumble_to_stim
from nnflags.verify import bundled_paths

DATA = Path(__file__).parents[1] / "data" / "google_circuits"


def test_crumble_syntax():
    c = crumble_to_stim("https://algassert.com/crumble#circuit=Q(0,1)0;Q(1,1)1;"
                        "POLYGON(0,0,1,0.25)0_1;TICK;S_DAG_0;H%5Binjection%5D_1;TICK;"
                        "MPP_X0*X1;CX_0_1;MX_1;DT(1,1,0)rec[-1]_rec[-2];OI(0)rec[-1]")
    assert c == stim.Circuit("QUBIT_COORDS(0,1) 0\nQUBIT_COORDS(1,1) 1\nTICK\nS_DAG 0\n"
                             "H[injection] 1\nTICK\nMPP X0*X1\nCX 0 1\nMX 1\n"
                             "DETECTOR(1,1,0) rec[-1] rec[-2]\nOBSERVABLE_INCLUDE(0) rec[-1]")


def test_chan_sec5_crumble_link_is_cliffordea_d3a4():
    url = (DATA / "chan2609_sec5_experimental_double_check.url.txt").read_text().strip()
    assert crumble_to_stim(url) == stim.Circuit.from_file(str(bundled_paths("d3a4")[0]))


def test_z_reset_idle_refinement():
    emb = {0: (6, 4), 1: (5, 5), 2: (4, 6)}
    c = stim.Circuit("MPP X0\nTICK\nR 1 2\nTICK\nMR 2\nTICK\nH 1\nTICK\nM 1 2")
    strict = [(x.detail["measured"], x.detail["victim"])
              for x in C.readout_violations(c, emb, z_reset_idle="live")]
    refined = [(x.detail["measured"], x.detail["victim"])
               for x in C.readout_violations(c, emb, z_reset_idle="not_live")]
    assert strict == [(2, 0), (2, 1)] and refined == [(2, 0)]   # 1 is idle in |0>
    cx = stim.Circuit("MPP X0\nTICK\nRX 1 2\nTICK\nMR 2\nTICK\nH 1\nTICK\nM 1 2")
    assert len(C.readout_violations(cx, emb, z_reset_idle="not_live")) == 2  # |+> is live
    # Option-1 default (live_rule="gate") agrees with the refinement here.
    assert [(x.detail["measured"], x.detail["victim"])
            for x in C.readout_violations(c, emb)] == refined


def test_embedding_search_on_a_small_grid():
    # Path 0-1-2 on a 2x2 grid: 4 starting points x 2 directions = 8 embeddings.
    grid = frozenset({(0, 0), (0, 1), (1, 0), (1, 1)})
    graph = {0: {1}, 1: {0, 2}, 2: {1}}
    embs = list(E.embeddings(graph, grid))
    assert len(embs) == 8 and all(len(set(e.values())) == 3 for e in embs)


def test_d3a6_search_counts_and_fast_counter():
    c = enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT
    graph = E.interaction_graph(c)
    events = E.readout_events(c, "exempt")
    assert events == [(6, 5, sorted(set(range(13)) - {5}))]
    n = 0
    for emb in E.embeddings(graph):
        n += 1
        if n % 5000 == 1:
            assert E.count_violations(events, emb) == len(C.readout_violations(c, emb)) >= 1
    assert n == 182968
