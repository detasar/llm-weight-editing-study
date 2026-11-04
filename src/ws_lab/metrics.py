"""Paired class-stratified intervals and explicitly limited recovery."""
import numpy as np
from scipy.stats import norm
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, accuracy_score, log_loss, brier_score_loss


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    if y.shape != p.shape or not len(y) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('invalid probabilities')
    return {'balanced_accuracy': float(balanced_accuracy_score(y, p >= .5)),
            'roc_auc': float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
            'accuracy': float(accuracy_score(y, p >= .5)),
            'logloss': float(log_loss(y, p, labels=[0, 1])), 'brier': float(brier_score_loss(y, p))}


def paired_bootstrap(y, p, reference, draws=2000, seed=101, *, condition=None, reference_name=None):
    y, p, reference = map(np.asarray, (y, p, reference))
    classes = [np.flatnonzero(y == k) for k in (0, 1)]
    if any(len(ix) == 0 for ix in classes) or draws < 1:
        return {'status': 'UNAVAILABLE', 'reason': 'both classes and positive draws required'}
    rng = np.random.default_rng(seed)
    scores, deltas = [], []
    for _ in range(draws):
        ix = np.concatenate([rng.choice(c, len(c), replace=True) for c in classes])
        a = np.mean([(p[ix[y[ix] == k]] >= .5).mean() if k else (p[ix[y[ix] == k]] < .5).mean() for k in (0, 1)])
        b = np.mean([(reference[ix[y[ix] == k]] >= .5).mean() if k else (reference[ix[y[ix] == k]] < .5).mean() for k in (0, 1)])
        scores.append(a)
        deltas.append(a-b)
    return {'method': 'class-stratified paired bootstrap', 'draws': draws, 'seed': seed,
            'balanced_accuracy_95ci': np.quantile(scores, [.025, .975]).tolist(),
            'condition': condition, 'reference': reference_name,
            'difference': float(balanced_accuracy_score(y, p >= .5) - balanced_accuracy_score(y, reference >= .5)),
            'difference_95ci': np.quantile(deltas, [.025, .975]).tolist(),
            'paired_counts': correctness_flips(y, p, reference),
            'limitation': 'example uncertainty, not editor-session variability'}


def rate_ci(success, total):
    if total == 0:
        return {'count': 0, 'successes': 0, 'rate': None, 'ci95': None}
    z = float(norm.ppf(.975))
    p = success / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total))/denominator
    radius = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))/denominator
    return {'count': total, 'successes': success, 'rate': p, 'ci95': [float(max(0, center-radius)), float(min(1, center+radius))]}


def group_metrics(y, p, groups):
    result = {}
    for j, field in enumerate(['sex', 'race']):
        result[field] = {}
        for group in sorted(set(groups[:, j])):
            ix = groups[:, j] == group
            positive, negative = ix & (y == 1), ix & (y == 0)
            result[field][group] = {'n': int(ix.sum()), 'positive_count': int(positive.sum()),
                                   'negative_count': int(negative.sum()), 'small_group': int(ix.sum()) < 30,
                                   'TPR': rate_ci(int(((p >= .5) & positive).sum()), int(positive.sum())),
                                   'FPR': rate_ci(int(((p >= .5) & negative).sum()), int(negative.sum()))}
    return result


def recovery(repaired, clean, damaged):
    denominator = clean - damaged
    return (repaired - damaged) / denominator if denominator > .01 else None


def correctness_flips(y, p, reference):
    """Raw correctness counts, not balanced-accuracy units or mechanism evidence."""
    y, p, reference = map(np.asarray, (y, p, reference))
    correct, prior = (p >= .5) == y, (reference >= .5) == y
    def counts(mask):
        return {'n': int(mask.sum()), 'rescues': int((mask & correct & ~prior).sum()),
                'regressions': int((mask & ~correct & prior).sum()),
                'condition_correct': int((mask & correct).sum()),
                'reference_correct': int((mask & prior).sum())}
    return {**counts(np.ones(len(y), dtype=bool)),
            'by_class': {str(k): counts(y == k) for k in (0, 1)},
            'units': 'raw example counts; balanced accuracy weights each class equally'}


def editor_contrasts(y, predictions, conditions, claude_enabled, draws=2000):
    editors = ['Astra', 'Sol'] + (['Claude'] if claude_enabled else [])
    pairs = [('Astra', 'Sol')] + [(e, c) for e in editors for c in ('random', 'grid')]
    result = {}
    for a, b in pairs:
        if any(conditions.get(n, {}).get('status') != 'COMPLETE' or n not in predictions for n in (a, b)):
            result[a + '_minus_' + b] = {'status': 'UNAVAILABLE', 'condition': a, 'reference': b,
                                        'reason': 'both methods must be complete'}
        else:
            result[a + '_minus_' + b] = {'status': 'COMPLETE', **paired_bootstrap(
                y, predictions[a], predictions[b], draws=draws, seed=101, condition=a, reference_name=b)}
    return result
