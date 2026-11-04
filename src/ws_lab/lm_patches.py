"""Complete interventions on one live model; retain only touched CPU origins."""
import math
import re
from pathlib import Path
import torch
from safetensors.torch import save_file, load_file
from .io import digest, state_hash, write_json, read_json, file_hash

TENSOR = r'^model\.layers\.[0-9]+\.mlp\.down_proj\.weight$'


def patch_schema():
    tensor = {'type': 'string', 'pattern': TENSOR}
    integer = {'type': 'integer', 'minimum': 0}
    def op(kind, extra):
        props = {'kind': {'const': kind}, 'tensor': tensor, **extra}
        return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
    return {'type': 'object', 'required': ['ops'], 'additionalProperties': False, 'properties': {
        'ops': {'type': 'array', 'maxItems': 64, 'items': {'oneOf': [
            op('scale_columns', {'columns': {'type': 'array', 'minItems': 1, 'maxItems': 256,
                 'uniqueItems': True, 'items': integer}, 'factor': {'type': 'number'}}),
            op('sparse', {'entries': {'type': 'array', 'minItems': 1, 'maxItems': 2048, 'items': {
                'type': 'array', 'prefixItems': [integer, integer, {'type': 'number'}],
                'minItems': 3, 'maxItems': 3}}})]}}}}


def action_schema():
    def variant(kind, extra):
        props = {'action': {'const': kind}, **extra}
        return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
    idx = {'type': 'integer', 'minimum': 0}
    return {'oneOf': [variant('inspect_stats', {}), variant('inspect_slice', {
        'tensor': {'type': 'string', 'pattern': TENSOR}, 'row': idx, 'start': idx,
        'count': {'type': 'integer', 'minimum': 1, 'maximum': 32}}),
        variant('probe_summary', {'indices': {'type': 'array', 'items': {**idx, 'maximum': 31},
             'minItems': 1, 'maxItems': 32, 'uniqueItems': True}}),
        variant('evaluate_candidate', {'patch': patch_schema()}),
        variant('submit_final', {'candidate': {**idx, 'maximum': 10}})]}


class InvalidLMPatch(ValueError):
    """Expected patch validation failure."""


class PredictionBinding:
    """One trusted model lifetime; inspect metadata, never copy unchanged weights.

    Patch-space writes publish hashes only after postcast verification. Ordinary
    external writes/replacements invalidate the binding. Deliberate .data/version
    counter bypass is outside this local, declarative editing interface.
    """
    def __init__(self, model):
        self.model = model
        self.expected = self.stamp()
        self.origin_hash = None
        self.effective = {}
        self.owner = None

    def stamp(self):
        return tuple((kind, n, id(p), p.data_ptr(), p._version, str(p.dtype),
                      str(p.device), tuple(p.shape), tuple(p.stride()))
                     for kind, values in (('parameter', self.model.named_parameters()),
                                          ('buffer', self.model.named_buffers()))
                     for n, p in values)

    def check(self):
        if self.stamp() != self.expected:
            raise ValueError('immutable prediction origin/model changed outside patch space')

    def origin(self):
        self.check()
        if self.origin_hash is None:
            self.origin_hash = state_hash(self.model.state_dict())
        return self.origin_hash

    def key(self):
        return {'origin': self.origin(), 'postcast_tensors': self.effective}


def prediction_binding(scorer):
    """Scorer-local, in-memory only; never attach cache ownership to a model."""
    binding = getattr(scorer, '_prediction_binding', None)
    if binding is None:
        binding = PredictionBinding(scorer.model)
        scorer._prediction_binding = binding
    if binding.model is not scorer.model:
        raise ValueError('scorer/patch model binding changed')
    return binding


class LMPatchSpace:
    def __init__(self, model, *, dtype=torch.float16):
        self.model = model
        if dtype not in (torch.float16, torch.float32):
            raise ValueError("unsupported patch dtype")
        self.dtype = dtype
        self.parameters = dict(model.named_parameters())
        self.total = sum(p.numel() for p in model.parameters())  # unique tied identities
        self.max_count = math.floor(self.total * .001)
        self.origins, self.touched = {}, set()
        self._binding = None
        self._origin_versions = {}
        self.legal = {n: self.parameters[n] for n in sorted(
            (n for n in self.parameters if re.fullmatch(TENSOR, n)),
            key=lambda n: int(n.split('.')[2]))}
        if not self.legal:
            raise ValueError('no legal MLP tensors')

    def origin(self, name):
        if name not in self.legal:
            raise InvalidLMPatch('illegal tensor')
        if name not in self.origins:
            with torch.inference_mode(False):
                self.origins[name] = self.legal[name].detach().cpu().clone()
            self._origin_versions[name] = (id(self.origins[name]), self.origins[name]._version)
        return self.origins[name]

    def _check_binding(self):
        if self._binding is not None:
            if self._binding.owner not in (None, self):
                raise ValueError('immutable prediction origin belongs to another patch space')
            self._binding.check()
        for name, (identity, version) in self._origin_versions.items():
            value = self.origins[name]
            if (id(value), value._version) != (identity, version):
                raise ValueError('immutable patch origin changed')

    @torch.inference_mode()
    def rollback(self):
        self._check_binding()
        hashes = {}
        for name in sorted(self.touched):
            self.legal[name].copy_(self.origins[name])
            actual = state_hash({name: self.legal[name]})
            if actual != state_hash({name: self.origins[name]}):
                raise ValueError('rollback hash mismatch')
            hashes[name] = actual
        self.touched.clear()
        if self._binding is not None:
            self._binding.effective = {}
            self._binding.expected = self._binding.stamp()
        return hashes

    @torch.inference_mode()
    def apply(self, patch):
        from .controller import StrictValidator
        self.rollback()
        StrictValidator(patch_schema()).validate(patch)
        proposed, occupied, scaled = {}, {}, {}
        for op in patch['ops']:
            name = op['tensor']
            base = self.origin(name)
            if base.ndim != 2 or base.dtype != self.dtype:
                raise InvalidLMPatch('expected declared patch matrix dtype')
            value = proposed.setdefault(name, base.clone())
            seen = occupied.setdefault(name, set())
            scaled_columns = scaled.setdefault(name, set())
            if op['kind'] == 'scale_columns':
                factor = op['factor']
                if type(factor) not in (float, int) or not math.isfinite(factor):
                    raise InvalidLMPatch('bad factor')
                columns = op['columns']
                if any(type(c) is not int or not 0 <= c < base.shape[1] for c in columns):
                    raise InvalidLMPatch('bad column')
                if scaled_columns.intersection(columns) or any(c in columns for r, c in seen):
                    raise InvalidLMPatch('overlapping operations')
                scaled_columns.update(columns)
                delta = (base[:, columns].float() * (factor - 1)).to(base.dtype)
                value[:, columns] = base[:, columns] + delta
            else:
                for r, c, delta in op['entries']:
                    if type(r) is not int or type(c) is not int or not (0 <= r < base.shape[0] and 0 <= c < base.shape[1]):
                        raise InvalidLMPatch('bad index')
                    if (r, c) in seen or c in scaled_columns:
                        raise InvalidLMPatch('overlapping operations')
                    seen.add((r, c))
                    if type(delta) not in (int, float) or not math.isfinite(delta):
                        raise InvalidLMPatch('bad delta')
                    value[r, c] = base[r, c] + torch.tensor(delta, dtype=base.dtype)
        count, squared, ratios = 0, 0., {}
        for name, value in proposed.items():
            base = self.origins[name]
            if not torch.isfinite(value).all():
                raise InvalidLMPatch('nonfinite patch')
            denominator = float(base.double().norm())
            if denominator == 0:
                raise InvalidLMPatch('zero denominator')
            delta = value.double() - base.double()
            norm = float(delta.norm())
            ratios[name] = norm / denominator
            if ratios[name] > .05:
                raise InvalidLMPatch('norm budget')
            count += int((value != base).sum())
            squared += norm ** 2
        if count > self.max_count:
            raise InvalidLMPatch('scalar budget')
        for name, value in proposed.items():
            self.touched.add(name)
            self.legal[name].copy_(value)
        applied = {n: state_hash({n: self.legal[n]}) for n in proposed}
        if self._binding is not None:
            self._binding.effective = {n: h for n, h in applied.items()
                                       if h != state_hash({n: self.origins[n]})}
            self._binding.expected = self._binding.stamp()
        return {'count': count, 'norm': math.sqrt(squared), 'relative_norms': ratios,
                'unique_parameters': self.total, 'fraction': count / self.total,
                'applied_hashes': applied}

    def prediction_origin(self):
        self._check_binding()
        if self._binding is not None:
            return self._binding.origin()
        # Explicit inspection only; ordinary unbound apply/rollback never hashes
        # the whole model. Substitute saved origins if a patch is active.
        state = self.model.state_dict()
        state.update(self.origins)
        return state_hash(state)

    def stats(self):
        return {'unique_parameters': self.total, 'max_changed_scalars': self.max_count,
                'operations': ['scale_columns', 'sparse'], 'tensors': {
                    n: {'shape': list(p.shape), 'dtype': str(p.dtype),
                        'norm': float(p.detach().cpu().double().norm())}
                    for n, p in self.legal.items()}}

    def save(self, directory, patch):
        directory = Path(directory)
        stats = self.apply(patch)
        directory.mkdir(parents=True, exist_ok=True)
        save_file({n: self.legal[n].detach().cpu().contiguous() for n in self.touched},
                  str(directory / 'weights.safetensors'))
        meta = {'patch': patch, 'stats': stats, 'origins': {
            n: state_hash({n: self.origins[n]}) for n in self.touched},
            'weights_sha256': file_hash(directory / 'weights.safetensors')}
        write_json(directory / 'patch.json', meta)
        return digest(meta)

    def load(self, directory):
        directory = Path(directory)
        meta = read_json(directory / 'patch.json')
        if file_hash(directory / 'weights.safetensors') != meta['weights_sha256']:
            raise ValueError('serialized patch changed')
        for n, h in meta['origins'].items():
            if state_hash({n: self.origin(n)}) != h:
                raise ValueError('immutable origin changed')
        stats = self.apply(meta['patch'])
        stored = load_file(str(directory / 'weights.safetensors'))
        if set(stored) != self.touched or any(not torch.equal(v, self.legal[n].detach().cpu()) for n, v in stored.items()):
            raise ValueError('reload mismatch')
        if stats != meta['stats']:
            raise ValueError('reload stats mismatch')
        return digest(meta)
