"""Original UCI records, fit-only encoding and explicit source provenance."""
import csv
from pathlib import Path
import urllib.request
import numpy as np
from sklearn.model_selection import train_test_split
from .io import file_hash, digest, write_json

NAMES = ['age', 'workclass', 'fnlwgt', 'education', 'education_num', 'marital_status',
         'occupation', 'relationship', 'race', 'sex', 'capital_gain', 'capital_loss',
         'hours_per_week', 'native_country']
NUMERIC = [0, 2, 4, 10, 11, 12]
CATEGORICAL = [i for i in range(14) if i not in NUMERIC + [8, 9]]
URL = 'https://archive.ics.uci.edu/ml/machine-learning-databases/adult/'


def download(directory):
    """Explicit coordinator-invoked network operation; never runs on import."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ['adult.data', 'adult.test']:
        destination = directory / name
        if destination.exists():
            raise ValueError('refusing to overwrite source')
        with urllib.request.urlopen(URL + name, timeout=60) as response:
            content = response.read(20_000_001)
        if len(content) > 20_000_000:
            raise ValueError('source too large')
        destination.write_bytes(content)


def read_records(path):
    rows, labels, ids, groups = [], [], [], []
    with Path(path).open(newline='') as stream:
        for line, row in enumerate(csv.reader(stream), 1):
            if not row or row[0].startswith('|'):
                continue
            row = [x.strip() for x in row]
            if len(row) != 15 or row[-1].rstrip('.') not in ['<=50K', '>50K']:
                raise ValueError('invalid Adult record')
            rows.append([x if x != '?' else '__MISSING__' for x in row[:14]])
            labels.append(int(row[-1].rstrip('.') == '>50K'))
            ids.append(f'{Path(path).name}:{line}')
            groups.append([row[9], row[8]])
    return np.asarray(rows), np.asarray(labels, dtype=np.int64), np.asarray(ids), np.asarray(groups)


def fit_encoder(rows):
    numeric = rows[:, NUMERIC].astype(np.float64)
    mean, std = numeric.mean(0), numeric.std(0)
    std[std == 0] = 1
    return {'numeric': NUMERIC, 'categorical': CATEGORICAL, 'mean': mean.tolist(),
            'std': std.tolist(), 'categories': {str(i): sorted(set(rows[:, i]) | {'__MISSING__'}) for i in CATEGORICAL},
            'excluded': ['sex', 'race'], 'unknown_category': 'all_zero'}


def encode(rows, encoder):
    blocks = [(rows[:, NUMERIC].astype(float) - encoder['mean']) / encoder['std']]
    for i in CATEGORICAL:
        blocks.append(np.asarray([[float(v == c) for c in encoder['categories'][str(i)]] for v in rows[:, i]]))
    result = np.concatenate(blocks, axis=1).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError('nonfinite encoded features')
    return result


def prepare(source, run, seed=101, fixture=False):
    run, source = Path(run), Path(source)
    if (run / 'prepared.json').exists():
        raise ValueError('preparation already exists')
    rows, y, ids, groups = read_records(source / 'adult.data')
    test_rows, test_y, test_ids, test_groups = read_records(source / 'adult.test')
    if not fixture and (len(y) != 32561 or len(test_y) != 16281):
        raise ValueError('original UCI row counts required; synthetic data needs fixture flag')
    fit, rest = train_test_split(np.arange(len(y)), test_size=.3, stratify=y, random_state=seed)
    calibration, development = train_test_split(rest, test_size=2/3, stratify=y[rest], random_state=seed)
    encoder = fit_encoder(rows[fit])
    run.mkdir(parents=True, exist_ok=True)
    splits = {}
    for name, indices in [('fit', fit), ('calibration', calibration), ('development', development)]:
        x = encode(rows[indices], encoder)
        np.savez_compressed(run / f'{name}.npz', x=x, y=y[indices], ids=ids[indices], groups=groups[indices])
        splits[name] = {'n': len(indices), 'source_ids_sha256': digest(ids[indices].tolist()),
                        'file_sha256': file_hash(run / f'{name}.npz')}
    np.savez_compressed(run / 'test.npz', x=encode(test_rows, encoder), y=test_y, ids=test_ids, groups=test_groups)
    splits['test'] = {'n': len(test_y), 'source_ids_sha256': digest(test_ids.tolist()), 'file_sha256': file_hash(run / 'test.npz')}
    write_json(run / 'encoder.json', encoder)
    meta = {'phase': 'PREPARED', 'seed': seed, 'synthetic_fixture': fixture,
            'source': {'adult.data': file_hash(source / 'adult.data'), 'adult.test': file_hash(source / 'adult.test')},
            'split': 'original train stratified 70/10/20; original test untouched',
            'splits': splits, 'encoder_sha256': file_hash(run / 'encoder.json')}
    write_json(run / 'prepared.json', meta)
    return meta


def load_split(run, name):
    if name not in ['fit', 'calibration', 'development', 'test']:
        raise ValueError('unknown split')
    with np.load(Path(run) / f'{name}.npz', allow_pickle=False) as data:
        return {k: data[k].copy() for k in data.files}
