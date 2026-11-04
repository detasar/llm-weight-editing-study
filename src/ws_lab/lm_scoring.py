"""Pinned canonical harness tasks and auditable per-option likelihoods."""
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import time
import numpy as np
from .io import file_hash, digest
from .lm_runtime import inference_identity, verify_identity, leg_identity
from .lm_patches import prediction_binding

HARNESS_COMMIT = 'd6de81643928d653435c431bae19945d41d32520'
MODEL_REVISION = 'effd688a12921b4cc83e3312b6feb579f70f9c71'
REVISIONS = {'arc_easy': '210d026faf9955653af8916fad021475a3f00453',
             'piqa': '142f6d7367fd9877f0fb3b5734ea6a545f54cdd1'}
YAMLS = {'arc_easy': ('arc/arc_easy.yaml', '96da1d9efe1df88659481cedc13985cb347dc068554a2eae561303fa39bfab3f'),
         'piqa': ('piqa/piqa.yaml', 'e874f7956ccac325b888d4a5dc600bad867b79fba2bd358fe8761ab8263270fb')}


def offline():
    os.environ.update(HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')


def provenance(config):
    identity = inference_identity(config)
    import lm_eval
    dist = metadata.distribution('lm_eval')
    direct = json.loads(dist.read_text('direct_url.json') or '{}')
    if metadata.version('lm_eval') != '0.4.14.dev0' or direct.get('vcs_info', {}).get('commit_id') != HARNESS_COMMIT:
        raise ValueError('harness source pin mismatch')
    hashes = {}
    for name, (relative, expected) in YAMLS.items():
        actual = file_hash(Path(lm_eval.__file__).parent / 'tasks' / relative)
        if actual != expected:
            raise ValueError('task YAML pin mismatch')
        hashes[name] = actual
    return {'inference_identity': identity, 'harness_commit': HARNESS_COMMIT, 'task_yaml_sha256': hashes,
            'software': {n: metadata.version(n) for n in [
                'torch', 'transformers', 'datasets', 'accelerate', 'lm_eval', 'numpy', 'safetensors']}}


def task(name):
    offline()
    import lm_eval
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.tasks._yaml_loader import load_yaml
    config = load_yaml(Path(lm_eval.__file__).parent / 'tasks' / YAMLS[name][0], resolve_func=True)
    config['dataset_kwargs'] = {'revision': REVISIONS[name]}
    return ConfigurableTask(config=config)


class CanonicalScorer:
    def __init__(self, model, tokenizer, identity, *, reference=False):
        verify_identity(identity, identity)
        self.runtime = leg_identity(identity, reference=reference)
        self._verify_runtime(model)
        from lm_eval.models.huggingface import HFLM
        self.model = model
        self.lm = HFLM(pretrained=model, tokenizer=tokenizer, batch_size=1,
                       logits_cache=False, dtype=identity['dtype'], softmax_dtype='float32')
        self.work = {'examples': 0, 'requests': 0, 'forwards': 0, 'wall_seconds': 0.}
        self._hook = model.register_forward_pre_hook(self._forward)
        self.verified_predictions = {}

    def _verify_runtime(self, model):
        identity = self.runtime['inference_identity']
        verify_identity(identity, identity)
        if getattr(getattr(self, 'lm', None), 'model', model) is not model:
            raise ValueError('scorer actual model runtime mismatch')
        if (any(p.device.type != self.runtime['actual_device'] or str(p.dtype) != 'torch.' + identity['dtype']
                for p in model.parameters())
                or model.config._attn_implementation != 'eager'):
            raise ValueError('scorer actual model runtime mismatch')

    def prediction_key(self, task, split, indices):
        """Actual weights and canonical ordered requests, scoped to this scorer instance."""
        self._verify_runtime(self.model)
        if (self.lm.batch_size != 1 or self.lm.logits_cache is not False
                or str(self.lm.softmax_dtype) != 'torch.float32'):
            raise ValueError('scorer inference settings changed')
        weights = prediction_binding(self).key()
        documents = []
        for index in indices:
            doc = task.dataset[split][int(index)]
            requests = task.construct_requests(doc, task.doc_to_text(doc))
            documents.append({'index': int(index), 'source_id': str(doc.get('id',
                f'{task.config.task}:{split}:{index}')), 'requests': [list(r.args) for r in requests],
                'choices': task.doc_to_choice(doc), 'gold': task.doc_to_target(doc)})
        def implementation(obj, name):
            method = getattr(obj, name)
            return id(getattr(method, '__func__', method))
        context = {'runtime': self.runtime,
            'scorer': [id(self), id(self.lm), type(self).__module__, type(self).__qualname__,
                       implementation(self.lm, 'loglikelihood'), implementation(self, 'score'),
                       implementation(self.lm, '_encode_pair')],
            'task': [id(task), repr(task.config), getattr(task.dataset[split], '_fingerprint', None),
                     implementation(task, 'process_results'), repr(getattr(task, 'prompt', None))],
            'settings': {name: repr(getattr(self.lm, name, None)) for name in
                ('max_length', 'prefix_token_id', 'truncation', 'add_bos_token', 'backend')},
            'tokenizer': [id(getattr(self.lm, 'tokenizer', None)),
                          repr(getattr(self.lm, 'tokenizer', None)),
                          repr(getattr(getattr(self.lm, 'tokenizer', None), 'init_kwargs', None))],
            'split': split, 'documents': documents}
        # Reconstruct raw canonical requests to catch ordinary prompt/source
        # changes, but tokenize only when that context actually changes.
        raw_key = digest(context)
        if getattr(self, '_prediction_context', None) != raw_key:
            encoded = [[self.lm._encode_pair(*args) for args in doc['requests']]
                       for doc in documents]
            self._prediction_context_hash = digest([context, encoded])
            self._prediction_context = raw_key
        return digest({'weights': weights, 'context': self._prediction_context_hash})

    def _forward(self, *args):
        self.work['forwards'] += 1

    def bind_prediction_space(self, space):
        """Opt in one patch-space lifetime to this scorer's verified receipts."""
        if self.model is not space.model:
            raise ValueError('scorer/patch model binding changed')
        binding = prediction_binding(self)
        binding.check()
        if space._binding is not None and space._binding is not binding:
            raise ValueError('patch space already bound to another scorer')
        if binding.owner not in (None, space):
            # A fresh space starts a new origin lifetime; old receipts cannot
            # authorize it. The old space keeps its version guard independently.
            binding = type(binding)(self.model)
            self._prediction_binding = binding
        if binding.owner is None:
            if space.touched:
                raise ValueError('prediction binding requires rolled-back origin')
            binding.origin()
            binding.owner = space
            space._binding = binding
        space._check_binding()
        return binding.origin()

    def close(self):
        self._hook.remove()
        # A subsequent scorer/device leg establishes its own binding. A bound
        # patch space retains its guard until its owner finishes rollback.
        self._prediction_binding = None

    def score(self, task, split, indices, *, final=False):
        self._verify_runtime(self.model)
        if (self.lm.batch_size != 1 or self.lm.logits_cache is not False
                or str(self.lm.softmax_dtype) != 'torch.float32'):
            raise ValueError('scorer inference settings changed')
        if not final and not (task.config.task == 'arc_easy' and split in ('train', 'validation')):
            raise ValueError('held-out split denied')
        key = self.prediction_key(task, split, indices) if getattr(self, '_prediction_binding', None) is not None and split == 'validation' and not final else None
        rows = []
        self.partial_rows = rows  # Private phase evidence if a later request fails.
        started = time.perf_counter()
        try:
            for index in indices:
                doc = task.dataset[split][int(index)]
                context = task.doc_to_text(doc)
                requests = task.construct_requests(doc, context)
                self.work['examples'] += 1
                self.work['requests'] += len(requests)
                results = self.lm.loglikelihood(requests, disable_tqdm=True)
                metrics = task.process_results(doc, results)
                choices = task.doc_to_choice(doc)
                chars = [len(c) for c in choices]
                tokens = [len(self.lm._encode_pair(*r.args)[1]) for r in requests]
                lls = [float(r[0]) for r in results]
                if not all(np.isfinite(lls)) or min(chars + tokens) < 1:
                    raise ValueError('nonfinite likelihood or empty continuation')
                rows.append({'source_id': str(doc.get('id', f'{task.config.task}:{split}:{index}')),
                    'source_index': int(index), 'split': split, 'task': task.config.task,
                    'request_sha256': [digest(list(r.args)) for r in requests],
                    'choice_count': len(choices), 'choice_char_lengths': chars,
                    'continuation_token_lengths': tokens, 'loglikelihoods': lls,
                    'greedy': [bool(r[1]) for r in results],
                    'preferred': int(np.argmax(lls)), 'preferred_norm': int(np.argmax(np.array(lls) / chars)),
                    'gold': task.doc_to_target(doc), 'acc': float(metrics['acc']),
                    'acc_norm': float(metrics['acc_norm'])})
            if key is not None:
                if self.prediction_key(task, split, indices) != key:
                    raise ValueError('scoring context changed during evaluation')
                self.verified_predictions[key] = digest(rows)
            return rows
        finally:
            self.work['wall_seconds'] += time.perf_counter() - started


def aggregate(rows):
    return {m: float(np.mean([r[m] for r in rows])) for m in ('acc', 'acc_norm')}


def parity_report(cpu, accelerator):
    if len(cpu) != 64 or len(accelerator) != 64:
        raise ValueError('exact first64 diagnostic parity panel required')
    diagnostics = []
    for a, b in zip(cpu, accelerator, strict=True):
        if any(a[k] != b[k] for k in ['source_id', 'request_sha256', 'choice_char_lengths', 'continuation_token_lengths']):
            raise ValueError('parity probe mismatch')
        raw = np.abs(np.array(a['loglikelihoods']) - b['loglikelihoods'])
        per_token = raw / a['continuation_token_lengths']
        cpu_scores = np.array(a['loglikelihoods']) / a['choice_char_lengths']
        other_scores = np.array(b['loglikelihoods']) / b['choice_char_lengths']
        differences = np.abs(cpu_scores - other_scores)
        epsilon = float(differences.max())
        ordered = np.sort(cpu_scores)
        margin = float(ordered[-1] - ordered[-2])
        fragile = epsilon > 0 and margin <= 2 * epsilon
        diagnostics.append({'source_id': a['source_id'], 'absolute_ll_differences': raw.tolist(),
             'per_token_differences': per_token.tolist(), 'cpu_normalized_scores': cpu_scores.tolist(),
             'accelerator_normalized_scores': other_scores.tolist(),
             'normalized_score_differences': differences.tolist(), 'epsilon': epsilon,
             'cpu_top1_minus_top2_margin': margin, 'numerically_fragile': fragile,
             'cpu': a, 'accelerator': b})
    maximum = max(max(d['per_token_differences']) for d in diagnostics)
    changes = sum(a['preferred_norm'] != b['preferred_norm'] for a, b in zip(cpu, accelerator))
    fragile_count = sum(d['numerically_fragile'] for d in diagnostics)
    return {'status': 'PASS' if maximum <= .005 and changes == 0 and fragile_count == 0 else 'BLOCKED',
        'tolerance_per_continuation_token': .005, 'maximum_error': maximum,
        'normalized_choice_changes': changes, 'numerically_fragile_count': fragile_count,
        'scope': 'fixed train64 panel only; no whole-benchmark guarantee', 'diagnostics': diagnostics}


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


def final_task(task, name):
    """Authenticate effective final task semantics, including PIQA."""
    def require(ok, reason):
        if not ok:
            raise ValueError(reason)
    import lm_eval
    from lm_eval.api.task import ConfigurableTask, TaskConfig
    from lm_eval.tasks._yaml_loader import load_yaml
    require(type(task) is ConfigurableTask, 'native final task required')
    expected = load_yaml(Path(lm_eval.__file__).parent / 'tasks' / YAMLS[name][0], resolve_func=True)
    expected['dataset_kwargs'] = {'revision': REVISIONS[name]}
    expected = TaskConfig(**expected)
    fields = ('task', 'dataset_path', 'dataset_name', 'dataset_kwargs', 'output_type',
              'doc_to_text', 'doc_to_target', 'doc_to_choice', 'process_results',
              'target_delimiter', 'fewshot_delimiter', 'num_fewshot', 'metric_list',
              'doc_to_image', 'doc_to_audio', 'generation_kwargs')
    require(all(getattr(task.config, n) == getattr(expected, n) for n in fields)
            and task.prompt is None and task.OUTPUT_TYPE == 'multiple_choice'
            and task.multiple_input == task.multiple_target == 0
            and set(task._metric_fn_list) == {'acc', 'acc_norm'}, 'native final task configuration changed')
    for name in ('doc_to_text', 'doc_to_target', 'doc_to_choice', 'construct_requests', 'process_results'):
        require(getattr(getattr(task, name), '__func__', None) is getattr(ConfigurableTask, name),
                'native final task implementation required')
    return {n: getattr(task.config, n) for n in fields}


