"""Complete interventions from an immutable damaged origin; no autograd."""
import json
import math
from pathlib import Path
import torch
from safetensors.torch import load_file, save_file
from .io import digest, read_json, state_hash, write_json, file_hash

MAX_BYTES = 65536
MAX_OPS = 256


class InvalidPatch(ValueError):
    pass


def integer(value, limit):
    if type(value) is not int or not 0 <= value < limit:
        raise InvalidPatch("invalid index")
    return value


def number(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise InvalidPatch("nonfinite or nonnumeric value")
    return float(value)


class PatchSpace:
    """Only fc2 surviving weights are editable in Adult; all parameters count."""
    def __init__(self, origin, mask, fraction=0.1, relative=0.05):
        if type(fraction) not in (int, float) or type(relative) not in (int, float) or not 0 < fraction <= .1 or not 0 < relative <= .05:
            raise InvalidPatch('invalid patch-space budgets')
        self._origin = {k: v.detach().cpu().clone() for k, v in origin.items()}
        self._mask = mask.detach().cpu().clone()
        if set(origin) != {"fc1.weight", "fc1.bias", "fc2.weight", "fc2.bias", "fc3.weight", "fc3.bias"}:
            raise InvalidPatch("unexpected architecture")
        shapes = {'fc1.weight': (32, origin['fc1.weight'].shape[1]), 'fc1.bias': (32,),
                  'fc2.weight': (16, 32), 'fc2.bias': (16,), 'fc3.weight': (1, 16), 'fc3.bias': (1,)}
        if any(tuple(origin[k].shape) != shape for k, shape in shapes.items()):
            raise InvalidPatch('unexpected tensor shape')
        if any(t.dtype != torch.float32 or not torch.isfinite(t).all() for t in origin.values()):
            raise InvalidPatch("origin must be finite float32")
        if self._mask.dtype != torch.bool or self._mask.shape != origin['fc2.weight'].shape:
            raise InvalidPatch("invalid permanent mask")
        if torch.count_nonzero(self._origin['fc2.weight'][self._mask]):
            raise InvalidPatch("origin violates permanent mask")
        self.max_count = math.floor(sum(v.numel() for v in origin.values()) * fraction)
        self.relative = relative
        self.origin_hash = state_hash(self._origin)

    def origin(self):
        return {k: v.clone() for k, v in self._origin.items()}

    def rollback(self):
        return self.origin()

    def stats(self):
        w = self._origin['fc2.weight']
        return {"tensor": "fc2.weight", "shape": list(w.shape), "norm": float(w.norm()),
                "eligible_scalars": int((~self._mask).sum()), "max_changed": self.max_count,
                "relative_limit": self.relative, "families": ["scale_columns", "sparse"]}

    def apply(self, patch):
        try:
            encoded = json.dumps(patch, allow_nan=False).encode()
        except (ValueError, TypeError, OverflowError) as exc:
            raise InvalidPatch("invalid JSON patch") from exc
        if len(encoded) > MAX_BYTES or type(patch) is not dict or set(patch) != {"ops"}:
            raise InvalidPatch("invalid patch envelope")
        ops = patch['ops']
        if type(ops) is not list or len(ops) > MAX_OPS:
            raise InvalidPatch("too many operations")
        result = self.origin()
        base = self._origin['fc2.weight']
        out = result['fc2.weight']
        touched = set()
        with torch.no_grad():
            for op in ops:
                if type(op) is not dict or op.get('tensor') != 'fc2.weight':
                    raise InvalidPatch("tensor outside scope")
                if op.get('kind') == 'scale_columns':
                    if set(op) != {'kind', 'tensor', 'columns', 'factor'} or type(op['columns']) is not list or not 1 <= len(op['columns']) <= 32:
                        raise InvalidPatch("invalid column scaling")
                    factor = number(op['factor'])
                    entries = [(r, integer(c, base.shape[1])) for c in op['columns'] for r in range(base.shape[0])]
                    values = [float(base[r, c]) * factor for r, c in entries]
                elif op.get('kind') == 'sparse':
                    if set(op) != {'kind', 'tensor', 'entries'} or type(op['entries']) is not list or not 1 <= len(op['entries']) <= 256:
                        raise InvalidPatch("invalid sparse delta")
                    entries, values = [], []
                    for e in op['entries']:
                        if type(e) is not list or len(e) != 3:
                            raise InvalidPatch("invalid sparse entry")
                        r, c = integer(e[0], base.shape[0]), integer(e[1], base.shape[1])
                        entries.append((r, c))
                        values.append(float(base[r, c]) + number(e[2]))
                else:
                    raise InvalidPatch("unsupported family")
                for (r, c), value in zip(entries, values):
                    if (r, c) in touched or bool(self._mask[r, c]):
                        raise InvalidPatch("overlapping or permanently masked entry")
                    touched.add((r, c))
                    try:
                        out[r, c] = value
                    except (RuntimeError, OverflowError) as exc:
                        raise InvalidPatch("cast overflow") from exc
            if not torch.isfinite(out).all():
                raise InvalidPatch("nonfinite result")
            delta = out - base
            count = int(torch.count_nonzero(delta))
            norm = float(torch.linalg.vector_norm(delta.double()))
            denominator = float(torch.linalg.vector_norm(base.double()))
            if ops and denominator == 0:
                raise InvalidPatch("zero norm denominator")
            if count > self.max_count or (count and norm > self.relative * denominator):
                raise InvalidPatch("scalar or relative norm budget exceeded")
            if torch.count_nonzero(out[self._mask]):
                raise InvalidPatch("permanent mask violation")
        return result, {"count": count, "norm": norm, "relative_norm": norm / denominator if denominator else 0.0}

    def save(self, directory, patch):
        directory = Path(directory)
        state, stats = self.apply(patch)
        directory.mkdir(parents=True, exist_ok=True)
        save_file({'fc2.weight': state['fc2.weight']}, str(directory / 'patch.safetensors'))
        metadata = {"version": 1, "origin": self.origin_hash, "patch": patch, "stats": stats,
                    "tensor_sha256": file_hash(directory / 'patch.safetensors')}
        metadata['patch_hash'] = digest(metadata)
        write_json(directory / 'patch.json', metadata)
        return metadata['patch_hash']

    def load(self, directory):
        directory = Path(directory)
        meta = read_json(directory / 'patch.json')
        supplied = meta.pop('patch_hash')
        if digest(meta) != supplied or meta['origin'] != self.origin_hash or file_hash(directory / 'patch.safetensors') != meta['tensor_sha256']:
            raise InvalidPatch("patch hash mismatch")
        state, stats = self.apply(meta['patch'])
        stored = load_file(str(directory / 'patch.safetensors'))
        if set(stored) != {'fc2.weight'} or not torch.equal(stored['fc2.weight'], state['fc2.weight']) or stats != meta['stats']:
            raise InvalidPatch("serialized patch mismatch")
        return state, supplied


def patch_schema():
    """Public declarative patch family; runtime validation additionally enforces budgets."""
    index_r = {'type': 'integer', 'minimum': 0, 'maximum': 15}
    index_c = {'type': 'integer', 'minimum': 0, 'maximum': 31}
    scale = {'type': 'object', 'additionalProperties': False,
             'properties': {'kind': {'const': 'scale_columns'}, 'tensor': {'const': 'fc2.weight'},
                            'columns': {'type': 'array', 'minItems': 1, 'maxItems': 32, 'uniqueItems': True, 'items': index_c},
                            'factor': {'type': 'number'}},
             'required': ['kind', 'tensor', 'columns', 'factor']}
    sparse = {'type': 'object', 'additionalProperties': False,
              'properties': {'kind': {'const': 'sparse'}, 'tensor': {'const': 'fc2.weight'},
                             'entries': {'type': 'array', 'minItems': 1, 'maxItems': 256,
                                         'items': {'type': 'array', 'minItems': 3, 'maxItems': 3,
                                                   'prefixItems': [index_r, index_c, {'type': 'number'}], 'items': False}}},
              'required': ['kind', 'tensor', 'entries']}
    return {'type': 'object', 'additionalProperties': False, 'required': ['ops'],
            'properties': {'ops': {'type': 'array', 'maxItems': 256, 'items': {'oneOf': [scale, sparse]}}}}
