"""Offline publication evidence checks. No checkpoint, dataset download or provider."""
import builtins
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest
from ws_lab.io import digest, read_json, write_json
from ws_lab.publication import analyse_data, verify, adult_arrays, lm_rows, ADULT_CONTRASTS
from ws_lab.reproduce import main

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


@pytest.fixture(scope='module')
def computed():
    return analyse_data(DATA)


def test_actual_metrics_and_missing_versions(computed):
    adult = computed['adult']['methods']
    # Exact canonical results from completed original assessment, not rounded chart labels.
    expected = {'baseline': .7858578492717514, 'Sol': .7902068603853925,
                'Astra': .785855151938285, 'joint': .7896680837076668}
    for name, score in expected.items():
        assert adult[name]['n'] == 16281
        assert adult[name]['metrics']['balanced_accuracy'] == score
        assert adult[name]['paired_minus_baseline']['draws'] == 2000
        assert adult[name]['paired_minus_baseline']['seed'] == 101
        assert adult[name]['paired_minus_baseline']['paired_counts']['n'] == 16281
    manifest = read_json(DATA / 'manifest.json')
    assert manifest['summary'] == computed
    assert manifest['adult']['insufficient_damage'] is True
    assert manifest['adult']['solo_candidate_allowance'] == 10
    assert manifest['adult']['joint_candidate_allowance'] == 5
    lm = computed['lm']['versions']
    for method in ('baseline', 'Sol', 'Astra', 'joint'):
        arc = lm['v1']['tasks']['arc_easy'][method]
        piqa = lm['v1']['tasks']['piqa'][method]
        assert arc['metrics'] == {'acc': 396/512, 'acc_norm': 376/512}
        assert piqa['metrics'] == {'acc': 205/256, 'acc_norm': 201/256}
    assert manifest['lm']['main_version'] == 'v2'
    if manifest['lm']['versions']['v2']['status'] == 'PENDING':
        for task in lm['v2']['tasks'].values():
            assert all(row['metrics'] is None and row['n'] is None and row['status'] == 'PENDING' for row in task.values())
    assert manifest['provenance']['original_slots_bound_before_finals'] is True
    assert manifest['provenance']['v2_same_panels_not_independent_replication'] is True


def test_completed_controls_and_canonical_contrasts(computed):
    from ws_lab.metrics import paired_bootstrap
    predictions = read_json(DATA/'adult_predictions.json')['methods']
    contrasts = computed['adult']['contrasts']
    assert set(contrasts) == {a + '_minus_' + b for a, b in ADULT_CONTRASTS}
    for name in ('clean', 'random', 'grid'):
        assert computed['adult']['methods'][name]['status'] == 'MEASURED'
    for a, b in ADULT_CONTRASTS:
        if b == 'baseline':
            assert contrasts[a + '_minus_' + b] == computed['adult']['methods'][a]['paired_minus_baseline']
        else:
            assert contrasts[a + '_minus_' + b] == paired_bootstrap(
                np.asarray(predictions[a]['labels'], dtype=np.int64),
                np.asarray(predictions[a]['probabilities'], dtype=np.float64),
                np.asarray(predictions[b]['probabilities'], dtype=np.float64),
                seed=101, draws=2000, condition=a, reference_name=b)
    assert contrasts['Sol_minus_random']['difference'] == 0.004042111020990946
    assert contrasts['joint_minus_Sol']['difference'] == -0.0005387766777256164
    manifest = read_json(DATA/'manifest.json')
    assert manifest['adult']['contrasts'] == contrasts
    v2 = manifest['lm']['versions']['v2']
    assert v2['status'] == 'MEASURED'
    assert v2['unique_executed_weight_groups'] == [['baseline', 'Sol', 'Astra', 'joint']]
    assert v2['assessment_work']['forwards'] == 2558
    assert v2['assessment_work']['wall_seconds'] == 247.99987179087475
    assert all(row['patch'] == {'ops': []} for row in v2['slots'].values())
    for task, n in (('arc_easy', 512), ('piqa', 256)):
        assert all(row['n'] == n for row in v2['tasks'][task].values())
    joint = v2['candidates']['joint']
    assert joint['evaluations'] == 5
    assert [row['index'] for row in joint['candidates']] == [0, 2, 3, 4, 5]
    assert joint['events'][0] == {'turn': 1, 'status': 'INVALID', 'metrics': None}
    assert read_json(DATA/v2['frozen_patches']) == v2['slots']
    assert read_json(ROOT/'configs/replay-lm.json')['patches'] == '../data/' + v2['frozen_patches']
    assert v2['runtime']['dtype'] == manifest['lm']['versions']['v1']['runtime']['dtype'] == 'float32'
    assert manifest['execution']['portable_real_execution'] == 'NOT_RUN'


def test_missing_control_contrast_is_unavailable(tmp_path):
    numeric = {'paired_ids': [0, 1, 2, 3], 'labels': [0, 1, 0, 1],
               'probabilities': [.1, .9, .6, .4]}
    methods = {name: {**numeric, 'array_sha256': digest(numeric)}
               for name in ('baseline', 'Sol', 'Astra', 'joint', 'clean', 'grid')}
    write_json(tmp_path/'adult_predictions.json', {'dtype': 'float64', 'methods': methods})
    for version in ('v1', 'v2'):
        write_json(tmp_path/f'lm_{version}_predictions.json', {'methods': {}, 'missing_status': 'MISSING'})
    result = analyse_data(tmp_path)['adult']
    for name in ('Sol', 'Astra', 'joint'):
        row = result['contrasts'][name + '_minus_random']
        assert row['status'] == 'UNAVAILABLE' and row['reason'] == 'missing saved predictions: random'
        assert row['difference'] is None and row['difference_95ci'] is None
        assert result['contrasts'][name + '_minus_grid']['difference'] == 0.0


def test_ordinal_pairing_and_array_integrity():
    data = read_json(DATA / 'adult_predictions.json')
    adult_arrays(data)
    changed = copy.deepcopy(data)
    changed['methods']['Sol']['paired_ids'][0:2] = [1, 0]
    with pytest.raises(ValueError, match='pairing'):
        adult_arrays(changed)
    changed = copy.deepcopy(data)
    changed['methods']['Sol']['labels'][0] ^= 1
    with pytest.raises(ValueError):
        adult_arrays(changed)
    rows = read_json(DATA / 'lm_v1_predictions.json')['methods']['baseline']['arc_easy']
    assert all(r['paired_id'] == i for i,r in enumerate(rows))
    changed = copy.deepcopy(rows)
    changed[0], changed[1] = changed[1], changed[0]
    with pytest.raises(ValueError, match='pairing'):
        lm_rows(changed)
    changed = copy.deepcopy(rows)
    changed[0]['acc_norm'] = 1 - changed[0]['acc_norm']
    with pytest.raises(ValueError, match='choice arrays'):
        lm_rows(changed)


def test_exact_state_reuse_accounting():
    manifest = read_json(DATA / 'manifest.json')
    v1 = manifest['lm']['versions']['v1']
    assert v1['unique_executed_weight_groups'] == [['baseline', 'Sol', 'Astra', 'joint']]
    assert v1['assessment_work']['examples'] == 512
    assert v1['assessment_work']['forwards'] == 2046
    assert v1['piqa_supplement']['work']['examples'] == 256
    assert v1['piqa_supplement']['work']['forwards'] == 512
    assert v1['candidates']['joint']['evaluations'] == 5
    assert v1['candidates']['joint']['target_work']['examples'] == 32  # probes; five no-op slots reused baseline
    assert all(c['prediction_reuse']['hit'] for c in v1['candidates']['joint']['candidates'][1:])
    assert v1['actual_prediction_reuse']['baseline']['arc_easy'] is False
    assert v1['actual_prediction_reuse']['Sol']['arc_easy'] is True


def test_graph_matches_exact_masks_and_executed_patches():
    import torch
    from ws_lab.patches import PatchSpace
    graph = read_json(DATA / 'adult_graph.json')
    space = PatchSpace({k:torch.tensor(v,dtype=torch.float32) for k,v in graph['root'].items()},
                       torch.tensor(graph['permanent_mask'],dtype=torch.bool))
    for name, row in graph['variants'].items():
        state, stats = space.apply(row['patch'])
        assert stats == row['stats']
        assert len(row['changes']) == stats['count']
        assert not torch.count_nonzero(state['fc2.weight'][space._mask])
        for scalar in row['changes']:
            r,c = scalar['row'],scalar['column']
            assert float(state['fc2.weight'][r,c]) == scalar['after']
            assert float(space.origin()['fc2.weight'][r,c]) == scalar['before']


def test_input_corruption_and_summary_binding(tmp_path):
    directory = tmp_path/'data'
    shutil.copytree(DATA, directory)
    manifest = read_json(directory/'manifest.json')
    original = (directory/'adult_predictions.json').read_bytes()
    changed = read_json(directory/'adult_predictions.json')
    changed['methods']['Sol']['probabilities'][0] = .25
    write_json(directory/'adult_predictions.json', changed)
    with pytest.raises(ValueError, match='input hash mismatch'):
        verify(directory,project_root=ROOT)
    (directory/'adult_predictions.json').write_bytes(original)
    manifest['summary']['adult']['methods']['Sol']['n'] = 1
    write_json(directory/'manifest.json',manifest)
    with pytest.raises(ValueError, match='summary'):
        verify(directory,project_root=ROOT)


def test_prompt_mismatch_detector(tmp_path):
    manifest=read_json(DATA/'manifest.json')
    for relative in manifest['prompts']:
        dst=tmp_path/relative
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,dst)
    (tmp_path/'prompts/v2/lm_editor.txt').write_text('incorrect paraphrase')
    with pytest.raises(ValueError, match='prompt hash mismatch'):
        verify(DATA, project_root=tmp_path)


def test_no_provider_defaults(monkeypatch, capsys):
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split('.')[0] in {'torch','transformers','lm_eval','datasets','ws_lab.driver'}:
            raise AssertionError('inference imported by saved-data CLI: '+name)
        return original_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    assert main(['verify','--data-dir',str(DATA)]) == 0
    assert json.loads(capsys.readouterr().out)['model_or_provider_calls'] == 0
    assert main(['doctor']) == 0
    assert json.loads(capsys.readouterr().out)['editor_model_availability'].startswith('UNKNOWN')


def test_explicit_execution_is_honest_and_never_consumes_run(tmp_path,capsys):
    for operation in ('run','replay'):
        new = tmp_path/operation
        assert main([operation,'--output',str(new),'--model-dir','model','--dataset-dir','datasets',
                     '--config','configs/defaults.json']) == 2
        assert 'DEV_HISTORY' in json.loads(capsys.readouterr().out)['error']
        assert not new.exists()
    existing=tmp_path/'existing'
    existing.mkdir()
    (existing/'finalized.json').write_text('preserve')
    assert main(['run','--output',str(existing),'--model-dir','model','--dataset-dir','datasets',
                 '--config','configs/defaults.json']) == 2
    assert (existing/'finalized.json').read_text() == 'preserve'


def test_export_requires_explicit_paths_and_checks_private_row_order(tmp_path):
    spec=importlib.util.spec_from_file_location('public_export',ROOT/'scripts/export_private.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(SystemExit) as exc:
        module.main([])
    assert exc.value.code == 2
    sample={'source_id':'private-id','source_index':99,'task':'piqa','split':'validation',
            'gold':0,'preferred':0,'preferred_norm':0,'acc':1.,'acc_norm':1.,
            'choice_char_lengths':[1,2],'continuation_token_lengths':[1,1],'loglikelihoods':[-1.,-3.]}
    safe,panel=module.safe_lm({'baseline':{'piqa':[sample]}})
    assert 'source_id' not in json.dumps(safe) and 'private-id' not in json.dumps(safe)
    sample2={**sample,'source_index':98}
    with pytest.raises(ValueError,match='panel order'):
        module.safe_lm({'baseline':{'piqa':[sample2]}},expected_panels=panel)
    # v2 update accepts terminal numeric input only; original v1 arrays stay separate.
    safe2,_=module.safe_lm({'baseline':{'piqa':[sample]}} ,expected_panels=panel)
    assert safe2==safe


def test_export_keeps_invalid_events_and_candidate_index_gaps():
    spec = importlib.util.spec_from_file_location('public_export', ROOT/'scripts/export_private.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidates = [{'index': i, 'patch': {'ops': []}, 'metrics': {'acc': .5}, 'stats': {}}
                  for i in (0, 2, 3, 4, 5)]
    value = {'evaluations': 5, 'candidate_limit': 5, 'candidates': candidates, 'locked': candidates[0],
             'events': [{'turn': 1, 'status': 'INVALID', 'candidate_index': 1,
                         'reason': '/Users/private/raw prompt', 'request_sha256': 'private-id',
                         'metrics': {'acc': 0}, 'cost': 5, 'peer_text': 'private'},
                        {'turn': 2, 'status': 'BLOCKED', 'slot': 2, 'transcript': 'private'},
                        {'turn': 3, 'status': 'OK', 'action': 'evaluate_candidate', 'index': 3}]}
    result = module.candidate_record(value)
    assert result['evaluations'] == 5
    assert [r['index'] for r in result['candidates']] == [0, 2, 3, 4, 5]
    assert result['events'] == [
        {'turn': 1, 'status': 'INVALID', 'candidate_index': 1, 'metrics': None},
        {'turn': 2, 'status': 'BLOCKED', 'slot': 2, 'metrics': None},
        {'turn': 3, 'status': 'OK', 'action': 'evaluate_candidate', 'index': 3}]
    assert 'reason' not in result['events'][1]  # Never invent a native reason.
    assert 'private' not in json.dumps(result) and 'cost' not in json.dumps(result)


def test_cli_resolution_and_scientific_models(tmp_path,monkeypatch):
    from ws_lab import driver
    binary=tmp_path/'codex'
    binary.write_text('#!/bin/sh\nexit 99\n')
    binary.chmod(0o755)
    monkeypatch.setenv('WS_LAB_CODEX_CLI',str(binary))
    assert driver.resolve_cli()==str(binary)
    argv, settings=driver.native_launch('Sol',tmp_path,tmp_path/'catalog',tmp_path/'instructions',tmp_path/'schema')
    assert argv[0]==str(binary) and argv[argv.index('--model')+1]=='gpt-6.1-sol'
    assert settings['model_reasoning_effort']=='medium'
    with pytest.raises(driver.BlockedRoute):
        driver.resolve_cli(str(tmp_path/'missing'))
    with pytest.raises(ValueError,match='fallback'):
        driver.status('unavailable-substitute')


# Exact native cache regression from the accepted source, with a tiny synthetic tensor
# and a fake scorer. No trained checkpoint or real scoring is involved.
@pytest.fixture
def synthetic():
    import torch
    from ws_lab.lm_patches import LMPatchSpace, prediction_binding
    from ws_lab.lm_scoring import CanonicalScorer
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.anchor=torch.nn.Parameter(torch.ones(1,dtype=torch.float16))
            self.model=torch.nn.Module()
            self.model.layers=torch.nn.ModuleList([torch.nn.Module()])
            self.model.layers[0].mlp=torch.nn.Module()
            self.model.layers[0].mlp.down_proj=torch.nn.Linear(100,100,bias=False).half()
            with torch.no_grad():
                self.model.layers[0].mlp.down_proj.weight.fill_(1.)
    space=LMPatchSpace(Model())
    class Scorer(CanonicalScorer):
        def __init__(self):
            self.model=space.model
            self.runtime={'device':'cpu','dtype':'float16'}
            self.work={'examples':0,'forwards':0}
            self.verified_predictions={}
        def _verify_runtime(self,model):
            pass
        def prediction_key(self,task,split,indices):
            return digest([prediction_binding(self).key(),self.runtime,task,split,indices])
        def score(self,task,split,indices):
            self.work['examples']+=len(indices)
            self.work['forwards']+=len(indices)
            rows=[{'acc':1.,'acc_norm':1.,'source_id':str(i)} for i in indices]
            self.verified_predictions[self.prediction_key(task,split,indices)]=digest(rows)
            return rows
    return space,Scorer()


def test_native_postcast_reuse_charges_slots_not_forwards(synthetic):
    from ws_lab.lm_controller import LMController
    from ws_lab.saved_lm import aggregate
    space,scorer=synthetic
    rows=scorer.score('prompt-v1','validation',[0,1])
    baseline={'index':0,'patch':{'ops':[]},'stats':space.apply({'ops':[]}),
              'predictions':rows,'metrics':aggregate(rows)}
    controller=LMController(space,scorer,'prompt-v1',{'feedback':[0,1]},baseline,5)
    def evaluate(delta=None):
        patch={'ops':[]} if delta is None else {'ops':[{'kind':'sparse',
               'tensor':next(iter(space.legal)),'entries':[[0,0,delta]]}]}
        return controller.handle({'action':'evaluate_candidate','patch':patch})
    work=dict(scorer.work)
    evaluate()
    evaluate(1e-12)
    assert scorer.work==work
    evaluate(.001)
    changed=dict(scorer.work)
    assert changed['forwards']==work['forwards']+2
    evaluate(.00101)
    assert scorer.work==changed
    scorer.runtime['dtype']='changed'
    evaluate(.001)
    assert scorer.work['forwards']==changed['forwards']+2
    assert controller.evaluations==5 and len(controller.candidates)==6


def test_exported_data_has_no_private_fields_and_exact_prompt_versions():
    banned = {'source_id','source_ids','source_index','request_sha256','question','features','session_id',
              'session_hash','cost','ledger','transcript','financial','reservation_id'}
    def inspect(value):
        if isinstance(value,dict):
            assert not (banned & value.keys())
            for v in value.values():inspect(v)
        elif isinstance(value,list):
            for v in value:inspect(v)
        elif isinstance(value,str):
            assert '/Users/' not in value and '/private/tmp/' not in value
    for path in DATA.glob('*.json'):
        inspect(read_json(path))
    old=(ROOT/'prompts/v1/lm_editor.txt').read_text()
    new=(ROOT/'prompts/v2/lm_editor.txt').read_text()
    assert old.count('float16 before application.')==1
    assert new==old.replace('float16 before application.','float32 before application.')
