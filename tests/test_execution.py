"""Tiny injected execution fixtures: no real checkpoint, dataset, CLI or network."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ws_lab import execution as ex
from ws_lab.io import digest, read_json, write_json
from ws_lab.reproduce import main


@pytest.fixture
def tiny(tmp_path, monkeypatch):
    import torch
    from ws_lab.lm_patches import LMPatchSpace, prediction_binding
    from ws_lab.lm_scoring import CanonicalScorer
    from ws_lab import cowork

    models, drivers, finals = [], [], []
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList([torch.nn.Module()])
            self.model.layers[0].mlp = torch.nn.Module()
            self.model.layers[0].mlp.down_proj = torch.nn.Linear(100, 100, bias=False)
            with torch.no_grad():
                self.model.layers[0].mlp.down_proj.weight.fill_(1.)
            self.config = SimpleNamespace(to_dict=lambda: {'fixture': True})
    class Scorer(CanonicalScorer):
        def __init__(self, model):
            self.model = model
            self.runtime = {'inference_identity': {'dtype': 'float32', 'device': 'cpu'}}
            self.work = {'examples': 0, 'requests': 0, 'forwards': 0, 'wall_seconds': 0.}
            self.verified_predictions = {}
            self.partial_rows = []
        def _verify_runtime(self, model):
            assert model is self.model
        def prediction_key(self, task, split, indices):
            return digest([prediction_binding(self).key(), task.config.task, split, indices, self.runtime])
        def score(self, task, split, indices, *, final=False):
            if final:
                frozen = read_json(tmp_path/'output/frozen.json')
                assert set(frozen['slots']) == set(ex.SLOTS)
                finals.append((task.config.task, split, list(indices)))
            self.partial_rows = []
            for i in indices:
                self.work['examples'] += 1
                self.work['requests'] += 2
                self.work['forwards'] += 1
                # Synthetic model work only, exercised by the real patch space.
                with torch.no_grad():
                    self.model.model.layers[0].mlp.down_proj(torch.ones(1, 100))
                if getattr(self, 'fail_piqa', False) and task.config.task == 'piqa':
                    raise RuntimeError('synthetic second task failure')
                self.partial_rows.append({'source_id': str(i), 'source_index': i,
                    'task': task.config.task, 'split': split, 'choice_count': 2,
                    'choice_char_lengths': [1, 1], 'continuation_token_lengths': [1, 1],
                    'loglikelihoods': [-1., -2.], 'greedy': [True, False],
                    'preferred': 0, 'preferred_norm': 0, 'gold': 0, 'acc': 1., 'acc_norm': 1.})
            rows = copy.deepcopy(self.partial_rows)
            self.verified_predictions[self.prediction_key(task, split, indices)] = digest(rows)
            return rows
        def close(self):
            pass
    class Backend(ex.LMExecution):
        def __init__(self, config, model_dir, dataset_dir):
            self.config, self.runtime = config, config['lm']
            self.identity = {'dtype': 'float32', 'device': 'cpu'}
            self.provenance = {'fixture': True}
            self.model_hashes = {'fixture': digest('fixture')}
            self.data_revisions = {'arc_easy': digest('arc'), 'piqa': digest('piqa')}
            self.panels = {'diagnostic': [0, 1], 'feedback': [0, 1], 'extra_probes': [0, 1],
                           'arc_final': [0, 1], 'piqa_final': [0, 1]}
            self.model = self.space = self.scorer = None
            self.tasks = {}
            models.append(self)
        def load(self):
            self.model = Model()
            self.scorer = Scorer(self.model)
            self.space = LMPatchSpace(self.model, dtype=torch.float32)
            self.scorer.bind_prediction_space(self.space)
        def task(self, name):
            if name not in self.tasks:
                docs = [{'id': str(i), 'question': 'synthetic', 'answerKey': 'A',
                         'choices': {'text': ['a', 'b'], 'label': ['A', 'B']}} for i in range(2)]
                self.tasks[name] = SimpleNamespace(config=SimpleNamespace(task=name),
                    dataset={'train': docs, 'validation': docs, 'test': docs})
            return self.tasks[name]
    class Driver:
        def __init__(self, editor, directory, instructions, schema, cli):
            from ws_lab.driver import status
            self.editor, self.run_dir, self.instructions, self.schema = editor, directory, instructions, schema
            self.metadata = status(editor)
            self.calls, self.preflight_done, self.events = 0, False, []
            self.transcripts = []
            drivers.append(self)
        def result(self, action):
            result = {'action': action, 'status': 'COMPLETE', 'submitted': True,
                      'usage': {'input_tokens': 1, 'output_tokens': 1}, 'cost': None,
                      'session_id': 'synthetic-'+str(id(self))}
            self.events.append({k: v for k,v in result.items() if k != 'action'})
            return result
        def preflight(self):
            self.preflight_done = True
            self.metadata['status'] = 'READY'
            return self.result({'action': 'inspect_stats'})
        def turn(self, transcript):
            self.calls += 1
            self.transcripts.append(copy.deepcopy(transcript))
            context = transcript[-1]['content']
            if 'role' in context:
                assert context.get('initial_view', {}).get('inference', {'dtype':'float32'})['dtype'] == 'float32'
                if context['role'] == 'proposer':
                    action = {'action': 'propose', 'patch': {'ops': []}, 'hypothesis': 'fixture',
                              'expected_observable': 'same', 'risk': 'none', 'evidence_ids': ['baseline']}
                else:
                    action = {'action': 'accept', 'rationale': 'fixture'}
            else:
                assert 'float32 before application.' in self.instructions
                assert 'float16 before application.' not in self.instructions
                action = {'action': 'evaluate_candidate', 'patch': {'ops': []}}
            return self.result(action)
    monkeypatch.setattr(ex, 'lm_factory', Backend)
    monkeypatch.setattr(ex, 'driver_factory', Driver)
    monkeypatch.setattr(cowork, 'lm_architecture', lambda model, supplied: supplied)
    model_dir, data_dir = tmp_path/'model', tmp_path/'datasets'
    model_dir.mkdir(); data_dir.mkdir()
    (model_dir/'fixture').write_text('synthetic, no real model')
    (data_dir/'fixture').write_text('synthetic, no real data')
    config = {'execution':'fresh-public-v1', 'arm':'LM', 'seed':101,
              'backend_acceptance':'declared-runtime-engineering-not-native64',
              'lm': {'dtype':'float32', 'device':'cpu', 'attention':'eager',
                     'runtime_profile':'cpu-fp32-eager-engineering-v1', 'candidate_limit':5}}
    config_path = tmp_path/'config.json'
    write_json(config_path, config)
    def argv(command='run'):
        return [command, '--config', str(config_path), '--model-dir', str(model_dir),
                '--dataset-dir', str(data_dir), '--output', str(tmp_path/'output')]
    return SimpleNamespace(root=tmp_path, config=config, config_path=config_path,
        models=models, drivers=drivers, finals=finals, argv=argv)


def test_cli_complete_native_fresh_run(tiny, capsys):
    assert main(tiny.argv()) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['status'] == 'COMPLETE' and receipt['historical_exact_validation'] is False
    out = tiny.root/'output'
    assert read_json(out/'consumed.json')['run_id'] == receipt['run_id']
    assert read_json(out/'prepared.json')['backend_gate']['status'].endswith('NOT_NATIVE64')
    # Real native controllers and scheduler: 5 each, independent rollbacks, no final until freeze.
    assert len(tiny.drivers) == 4
    assert len(tiny.finals) == 2
    records = [read_json(out/f'sources/{name}_candidates.json') for name in ('Sol','Astra')]
    assert all(r['controller']['evaluations'] == 5 for r in records)
    assert all(r['controller']['candidates'][0]['patch'] == {'ops':[]} for r in records)
    assert tiny.drivers[0].transcripts[0] == tiny.drivers[1].transcripts[0]
    assert all('experience_packet_utf8' not in json.dumps(t) for d in tiny.drivers[:2] for t in d.transcripts)
    history = read_json(out/'history.canonical.json')
    assert history['feedback_mode'] == 'DEV_HISTORY'
    assert {s['editor'] for s in history['sources']} == {'Sol', 'Astra'}
    assert [s['evaluations'] for s in history['sources']] == [5,5]
    for driver in tiny.drivers[2:]:
        context = driver.transcripts[0][-1]['content']
        assert json.loads(context['experience_packet_utf8']) == history
    joint = read_json(out/'joint.json')
    assert joint['status'] == 'COMPLETE' and joint['completed_slots'] == 5
    assert joint['context_policy'] == ex.FRESH
    assert all(g == [list(ex.SLOTS)] for g in read_json(out/'assessment_groups.json').values())
    before = len(tiny.finals)
    assert main(tiny.argv()) == 2
    capsys.readouterr()
    assert len(tiny.finals) == before and len(tiny.models) == 1


def replay_config(tiny, distinct=False):
    patch = {'ops': [{'kind':'sparse','tensor':'model.layers.0.mlp.down_proj.weight','entries':[[0,0,.001]]}]}
    slots = {name: {'ops':[]} for name in ex.SLOTS}
    if distinct:
        slots['Sol'] = patch
        slots['Astra'] = copy.deepcopy(patch)
        slots['Astra']['ops'][0]['entries'][0][2] = .00100001  # same executed float32 value
        slots['joint'] = copy.deepcopy(patch)
        slots['joint']['ops'][0]['entries'][0][2] = .002
    write_json(tiny.root/'patches.json', slots)
    tiny.config['patches'] = 'patches.json'
    write_json(tiny.config_path, tiny.config)


def test_cli_replay_groups_actual_states_without_editors(tiny, monkeypatch, capsys):
    replay_config(tiny, distinct=True)
    monkeypatch.setattr(ex, 'driver_factory', lambda *a: pytest.fail('editor in replay'))
    assert main(tiny.argv('replay')) == 0
    capsys.readouterr()
    groups = read_json(tiny.root/'output/assessment_groups.json')
    assert groups == {name: [['baseline'], ['Sol','Astra'], ['joint']] for name in ('arc_easy','piqa')}
    assert len(tiny.finals) == 6
    assert not tiny.drivers


def test_failed_second_task_retains_first_and_consumes_scope(tiny, monkeypatch, capsys):
    replay_config(tiny)
    factory = ex.lm_factory
    def fail(*args):
        b = factory(*args)
        load = b.load
        def loading():
            load()
            b.scorer.fail_piqa = True
        b.load = loading
        return b
    monkeypatch.setattr(ex, 'lm_factory', fail)
    assert main(tiny.argv('replay')) == 2
    capsys.readouterr()
    out = tiny.root/'output'
    assert read_json(out/'terminal.json')['status'] == 'FAILED_CONSUMED_NO_RETRY'
    predictions = read_json(out/'assessment_predictions.json')
    assert all(set(r) == {'arc_easy'} for r in predictions.values())
    assert read_json(out/'assessment_failure.json')['partial_results']
    assert read_json(out/'work.json')['forwards'] == 3
    assert main(tiny.argv('replay')) == 2
    capsys.readouterr()
    assert len(tiny.models) == 1


def test_no_final_without_freeze(tiny):
    b = ex.lm_factory(tiny.config, tiny.root/'model', tiny.root/'datasets')
    b.load()
    with pytest.raises((OSError, ValueError)):
        ex.assess_lm(tiny.root, b, {'slots': {}})
    assert not tiny.finals and b.work()['forwards'] == 0
    b.close()


def test_source_mutation_blocks_history(tiny, capsys):
    from ws_lab.experience import SourceRun, build_experience
    assert main(tiny.argv()) == 0
    capsys.readouterr()
    out = tiny.root/'output'
    (out/'sources/Sol_transcript.json').write_text('[]')
    specs = [SourceRun(out/'sources','LM', e) for e in ('Sol','Astra')]
    with pytest.raises(ValueError, match='source freeze changed'):
        build_experience(specs, out/'source-audit')


def test_precision_and_explicit_admission_before_load(tiny, capsys):
    tiny.config['lm']['dtype'] = 'float16'
    write_json(tiny.config_path, tiny.config)
    assert main(tiny.argv()) == 2
    capsys.readouterr()
    assert not tiny.models and not (tiny.root/'output').exists()


def test_adult_frozen_reconstruction_no_feature_export(tmp_path, monkeypatch, capsys):
    import numpy as np
    import torch
    from ws_lab.model import AdultMLP
    from ws_lab.patches import PatchSpace
    from ws_lab.io import state_hash
    model_dir, dataset_dir = tmp_path/'model', tmp_path/'datasets'
    model_dir.mkdir(); dataset_dir.mkdir()
    torch.manual_seed(101)
    clean = AdultMLP(2).state_dict()
    mask = torch.zeros(16,32,dtype=torch.bool)
    mask[:,0] = True
    root = {k:v.clone() for k,v in clean.items()}
    root['fc2.weight'][mask] = 0
    space = PatchSpace(root,mask)
    state, stats = space.apply({'ops':[]})
    graph = {'root':{k:v.tolist() for k,v in root.items()}, 'clean':{k:v.tolist() for k,v in clean.items()},
        'root_state_sha256':state_hash(root),'clean_state_sha256':state_hash(clean),
        'permanent_mask':mask.tolist(), 'variants':{name:{'patch':{'ops':[]},'stats':stats,
        'executed_weight_sha256':state_hash(state)} for name in ex.SLOTS}}
    write_json(model_dir/'adult_graph.json',graph)
    np.savez(dataset_dir/'test.npz', x=np.array([[0.,1.],[1.,0.]],dtype=np.float32), y=np.array([0,1]))
    config = tmp_path/'config.json'
    write_json(config, {'execution':'fresh-public-v1','arm':'Adult','seed':101})
    monkeypatch.setattr(ex, 'lm_factory', lambda *a:pytest.fail('LM loaded by Adult replay'))
    monkeypatch.setattr(ex, 'driver_factory', lambda *a:pytest.fail('editor in Adult replay'))
    argv = ['replay','--config',str(config),'--model-dir',str(model_dir),
            '--dataset-dir',str(dataset_dir),'--output',str(tmp_path/'output')]
    assert main(argv) == 0
    capsys.readouterr()
    predictions = read_json(tmp_path/'output/assessment_predictions.json')
    assert set(predictions) == {'clean', *ex.SLOTS}
    assert read_json(tmp_path/'output/assessment_work.json')['forwards'] == 2
    assert not list((tmp_path/'output').glob('*.npz'))
    assert 'features' not in json.dumps(predictions)
    assert main(argv) == 2
    capsys.readouterr()


def test_final_consumption_invalidates_source_dev_history(tiny, capsys):
    from ws_lab.experience import SourceRun, build_experience
    assert main(tiny.argv()) == 0
    capsys.readouterr()
    out = tiny.root/'output'
    assert (out/'assessment-consumed.json').exists()
    with pytest.raises(ValueError, match='missing or stale exposure audit'):
        build_experience([SourceRun(out/'sources','LM',e) for e in ('Sol','Astra')], out/'source-audit')
