"""Unchanged saved-row functions from accepted lm_scoring.py; no inference imports."""
import numpy as np

def aggregate(rows):
    return {m: float(np.mean([r[m] for r in rows])) for m in ('acc', 'acc_norm')}

def bootstrap(a, b, seed, draws=2000):
    if [r['source_id'] for r in a] != [r['source_id'] for r in b]:
        raise ValueError('unpaired outputs')
    rng = np.random.default_rng(seed)
    result = {}
    for metric in ['acc', 'acc_norm']:
        delta = np.array([x[metric]-y[metric] for x, y in zip(a, b)])
        samples = [float(delta[rng.integers(0, len(delta), len(delta))].mean()) for _ in range(draws)]
        result[metric] = {'difference': float(delta.mean()), 'ci95': np.quantile(samples, [.025, .975]).tolist(),
            'rescues': int((delta > 0).sum()), 'regressions': int((delta < 0).sum()),
            'condition_correct': int(sum(x[metric] for x in a)),
            'reference_correct': int(sum(x[metric] for x in b))}
    return result
