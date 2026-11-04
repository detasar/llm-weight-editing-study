"""Saved numeric data API. This module cannot call a model or provider."""
from pathlib import Path
import numpy as np
from .io import digest, file_hash, read_json
from .metrics import metrics, paired_bootstrap
from .saved_lm import aggregate, bootstrap

ADULT_METHODS = ('baseline', 'Sol', 'Astra', 'joint', 'clean', 'random', 'grid')
LM_METHODS = ADULT_METHODS[:4]
TASKS = ('arc_easy', 'piqa')
ADULT_CONTRASTS = (tuple((name, 'baseline') for name in ADULT_METHODS)
                   + tuple((name, control) for name in ('Sol', 'Astra', 'joint')
                           for control in ('random', 'grid')) + (('joint', 'Sol'),))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def bound_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'binding escapes data directory')
    return path


def adult_arrays(value):
    require(value['dtype'] == 'float64', 'Adult probability dtype changed')
    predictions = value['methods']
    reference = None
    for name, row in predictions.items():
        require(name in ADULT_METHODS, 'unknown Adult method')
        ids, y, p = row['paired_ids'], row['labels'], row['probabilities']
        require(ids == list(range(len(y))) and len(p) == len(y) and len(y) > 0,
                'Adult ordered pairing changed')
        require(all(type(k) is int and k in (0, 1) for k in y), 'invalid Adult labels')
        current = (ids, y)
        require(reference is None or current == reference, 'Adult panels disagree')
        reference = current
        require(row['array_sha256'] == digest({'paired_ids': ids, 'labels': y, 'probabilities': p}),
                'Adult array hash mismatch')
        metrics(np.asarray(y, dtype=np.int64), np.asarray(p, dtype=np.float64))
    require('baseline' in predictions, 'Adult baseline missing')
    return predictions


def lm_rows(rows):
    require(len(rows) > 0, 'empty LM panel')
    converted = []
    for i, row in enumerate(rows):
        require(row['paired_id'] == i, 'LM ordered pairing changed')
        ll = np.asarray(row['loglikelihoods'], dtype=float)
        chars = np.asarray(row['choice_char_lengths'])
        tokens = row['continuation_token_lengths']
        require(ll.ndim == 1 and len(ll) >= 2 and len(chars) == len(ll) == len(tokens)
                and np.isfinite(ll).all() and all(type(c) is int and c > 0 for c in chars.tolist())
                and all(type(c) is int and c > 0 for c in tokens), 'invalid LM choice arrays')
        gold = row['gold']
        require(type(gold) is int and 0 <= gold < len(ll), 'invalid LM gold')
        preferred, normalized = int(np.argmax(ll)), int(np.argmax(ll / chars))
        require(row['preferred'] == preferred and row['preferred_norm'] == normalized
                and row['acc'] == float(preferred == gold)
                and row['acc_norm'] == float(normalized == gold), 'LM score disagrees with choice arrays')
        converted.append({**row, 'source_id': str(i)})  # Canonical bootstrap receives ordinal IDs only.
    return converted


def analyse_data(directory):
    """Recompute every reported final score and paired interval from numeric inputs."""
    directory = Path(directory)
    adult = adult_arrays(read_json(directory / 'adult_predictions.json'))
    result = {'adult': {'methods': {}}, 'lm': {'versions': {}}}
    base = adult['baseline']['probabilities']
    for name in ADULT_METHODS:
        row = adult.get(name)
        if row is None:
            result['adult']['methods'][name] = {'status': 'MISSING', 'n': None, 'metrics': None}
            continue
        y = np.asarray(row['labels'], dtype=np.int64)
        p = np.asarray(row['probabilities'], dtype=np.float64)
        result['adult']['methods'][name] = {'status': 'MEASURED', 'n': len(y), 'metrics': metrics(y, p),
            'paired_minus_baseline': paired_bootstrap(y, p, np.asarray(base, dtype=np.float64),
                seed=101, draws=2000, condition=name, reference_name='baseline')}
    contrasts = {}
    for condition, reference in ADULT_CONTRASTS:
        missing = [name for name in (condition, reference) if name not in adult]
        if missing:
            comparison = {'status': 'UNAVAILABLE', 'condition': condition, 'reference': reference,
                          'difference': None, 'difference_95ci': None,
                          'reason': 'missing saved predictions: ' + ', '.join(missing)}
        elif reference == 'baseline':
            comparison = result['adult']['methods'][condition]['paired_minus_baseline']
        else:
            row = adult[condition]
            comparison = paired_bootstrap(np.asarray(row['labels'], dtype=np.int64),
                np.asarray(row['probabilities'], dtype=np.float64),
                np.asarray(adult[reference]['probabilities'], dtype=np.float64),
                seed=101, draws=2000, condition=condition, reference_name=reference)
        contrasts[condition + '_minus_' + reference] = comparison
    result['adult']['contrasts'] = contrasts
    for version in ('v1', 'v2'):
        path = directory / f'lm_{version}_predictions.json'
        data = read_json(path)
        methods = data['methods']
        summaries = {}
        for task in TASKS:
            available = {name: lm_rows(row[task]) for name, row in methods.items() if task in row}
            reference = available.get('baseline')
            for name, rows in available.items():
                require(name in LM_METHODS, 'unknown LM method')
                require(reference is not None and [r['gold'] for r in rows] == [r['gold'] for r in reference]
                        and [r['choice_char_lengths'] for r in rows] == [r['choice_char_lengths'] for r in reference]
                        and [r['continuation_token_lengths'] for r in rows] == [r['continuation_token_lengths'] for r in reference],
                        'unpaired LM panel')
            summaries[task] = {name: ({'status': 'MEASURED', 'n': len(available[name]),
                'metrics': aggregate(available[name]),
                'paired_minus_baseline': bootstrap(available[name], reference, seed=101, draws=2000)}
                if name in available else {'status': data['missing_status'], 'n': None, 'metrics': None})
                for name in LM_METHODS}
        result['lm']['versions'][version] = {'tasks': summaries}
    return result


def verify(directory, *, project_root=None):
    directory = Path(directory).resolve()
    manifest = read_json(directory / 'manifest.json')
    require(manifest['schema_version'] == 1, 'unsupported manifest')
    for name, expected in manifest['files'].items():
        require(file_hash(bound_path(directory, name)) == expected, 'input hash mismatch: ' + name)
    for name in ('adult_predictions.json', 'lm_v1_predictions.json', 'lm_v2_predictions.json'):
        require(name in manifest['files'], 'unbound numeric input')
    for name in ('v1', 'v2'):
        data = read_json(directory / f'lm_{name}_predictions.json')
        require(data['arrays_sha256'] == digest(data['methods']), 'LM array hash mismatch')
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
    for name, expected in manifest['prompts'].items():
        require(file_hash(bound_path(root, name)) == expected, 'prompt hash mismatch: ' + name)
    actual = analyse_data(directory)
    require(manifest['adult']['methods'] == actual['adult']['methods']
            and manifest['adult']['contrasts'] == actual['adult']['contrasts'], 'Adult API metrics disagree')
    for version in ('v1', 'v2'):
        require(manifest['lm']['versions'][version]['tasks'] == actual['lm']['versions'][version]['tasks'], 'LM API metrics disagree')
    require(digest(actual) == manifest['summary_sha256'] == digest(manifest['summary']),
            'saved summary disagrees with numeric inputs')
    payload = {k: v for k, v in manifest.items() if k != 'manifest_sha256'}
    require(digest(payload) == manifest['manifest_sha256'], 'manifest hash mismatch')
    return {'status': 'VERIFIED', 'manifest_sha256': manifest['manifest_sha256'],
            'summary_sha256': manifest['summary_sha256'], 'model_or_provider_calls': 0}
