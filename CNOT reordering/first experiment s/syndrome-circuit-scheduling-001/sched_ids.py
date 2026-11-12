"""Schedule lookup helpers: ids <-> (x_order, z_order, z_first)."""
import json
_S = None
def table():
    global _S
    if _S is None:
        _S = {}
        for line in open('results/schedules.jsonl'):
            r = json.loads(line); _S[r['id']] = (r['x'], r['z'], r['z_first'])
    return _S
def named():
    return json.load(open('results/named_ids.json'))
def resolve(spec):
    """'S' | 'Sinv' | 'alt' | '12' | '12+947' -> (label, [schedule tuples])"""
    n = named()
    if spec == 'S': ids = [n['S']]
    elif spec == 'Sinv': ids = [n['Sinv']]
    elif spec == 'alt': ids = [n['S'], n['Sinv']]
    else: ids = [int(t) for t in spec.split('+')]
    return '+'.join(map(str, ids)), [table()[i] for i in ids]
