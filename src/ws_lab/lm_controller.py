"""LM-only declarative controller with fixed train/validation capabilities."""
import copy
import json
from .controller import StrictValidator, SharedBudget
from jsonschema import ValidationError
from .lm_patches import action_schema, InvalidLMPatch
from .lm_scoring import aggregate
from .io import digest


class InvalidAction(ValueError):
    """Expected declarative validation failure, never a target runtime failure."""


def validated_apply(space, patch):
    try:
        return space.apply(patch)
    except (InvalidLMPatch, ValidationError) as exc:
        raise InvalidAction(str(exc)) from exc


class LMController:
    def __init__(self, space, scorer, task, panels, baseline, limit, shared=None, *, turn_limit=15):
        if limit not in (5, 10):
            raise InvalidAction('invalid candidate limit')
        if type(turn_limit) is not int or turn_limit not in (15, 30):
            raise InvalidAction('invalid broker turn limit')
        self.turn_limit = turn_limit
        self.space, self.scorer, self.task, self.panels = space, scorer, task, panels
        self.limit = limit
        self.shared = shared if shared is not None else SharedBudget()
        self.probes, self.probe_limit = 0, 5
        self.candidates = [copy.deepcopy(baseline)]
        self.evaluations, self.turns = 0, 0
        self.locked, self.events = None, []
        self.start_work = dict(scorer.work)
        self.current = {'ops': []}
        self._prediction_cache = {}
        bind = getattr(scorer, 'bind_prediction_space', None)
        self._origin = bind(space) if bind is not None else None

    def best(self):
        return min(self.candidates, key=lambda c: (-c['metrics']['acc_norm'], c['stats']['norm'], c['stats']['count'], c['index']))

    def lock_best(self):
        self.locked = self.best()
        return {'status': 'LOCKED', 'candidate': self.locked['index']}

    def handle(self, action):
        self.turns += 1
        self.shared.turns += 1
        kind = action.get('action') if type(action) is dict else None
        if kind == 'evaluate_candidate':
            self.evaluations += 1
        if kind == 'probe_summary':
            self.probes += 1
        event = {'turn': self.turns, 'status': 'INVALID'}
        try:
            if self.locked is not None or self.turns > self.turn_limit or self.shared.turns > self.shared.limit:
                raise InvalidAction('turn/lock budget')
            try:
                size = len(json.dumps(action, allow_nan=False).encode())
            except (ValueError, TypeError) as exc:
                raise InvalidAction('unserializable action') from exc
            if size > 65536:
                raise InvalidAction('oversized action')
            try:
                StrictValidator(action_schema()).validate(action)
            except ValidationError as exc:
                raise InvalidAction('action schema') from exc
            event['request_sha256'] = digest(action)
            if kind == 'inspect_stats':
                result = self.space.stats()
            elif kind == 'inspect_slice':
                if action['tensor'] not in self.space.legal:
                    raise InvalidAction('illegal tensor')
                value = self.space.origin(action['tensor'])
                row, start, count = action['row'], action['start'], action['count']
                if row >= value.shape[0] or start + count > value.shape[1]:
                    raise InvalidAction('slice bounds')
                result = {'values': value[row, start:start+count].tolist()}
            elif kind == 'evaluate_candidate':
                if self.evaluations > self.limit:
                    raise InvalidAction('evaluation budget')
                if getattr(self.scorer, 'model', self.space.model) is not self.space.model:
                    raise ValueError('scorer/patch model binding changed')
                stats = validated_apply(self.space, action['patch'])
                if self._origin is not None and self.space.prediction_origin() != self._origin:
                    raise ValueError('immutable controller origin changed')
                key_method = getattr(self.scorer, 'prediction_key', None)
                key = key_method(self.task, 'validation', self.panels['feedback']) if key_method else None
                receipts = getattr(self.scorer, 'verified_predictions', {})
                baseline = self.candidates[0]
                if (key is not None and stats['count'] == 0 and 'predictions' in baseline
                        and receipts.get(key) == digest(baseline['predictions'])):
                    self._prediction_cache.setdefault(key, (0, copy.deepcopy(baseline['predictions'])))
                cached = self._prediction_cache.get(key) if key is not None else None
                if cached is not None:
                    source, rows = cached
                    rows = copy.deepcopy(rows)
                    reuse = {'hit': True, 'candidate': source, 'key_sha256': key}
                else:
                    rows = self.scorer.score(self.task, 'validation', self.panels['feedback'])
                    reuse = {'hit': False, 'candidate': None, 'key_sha256': key}
                    # A scorer without a verifiable receipt is always scored, never reused.
                    if key is not None and receipts.get(key) == digest(rows):
                        self._prediction_cache[key] = (self.evaluations, copy.deepcopy(rows))
                self.current = copy.deepcopy(action['patch'])
                item = {'index': self.evaluations, 'patch': self.current, 'stats': stats,
                        'metrics': aggregate(rows), 'predictions': rows, 'prediction_reuse': reuse}
                self.candidates.append(item)
                event['prediction_reuse'] = reuse
                result = {k: item[k] for k in ['index', 'stats', 'metrics', 'prediction_reuse']}
            elif kind == 'probe_summary':
                if self.probes > self.probe_limit:
                    raise InvalidAction('probe budget')
                validated_apply(self.space, self.current)
                indices = [self.panels['extra_probes'][i] for i in action['indices']]
                result = {'predictions': self.scorer.score(self.task, 'train', indices)}
            else:
                if action['candidate'] != self.best()['index']:
                    raise InvalidAction('must select best eligible candidate')
                result = self.lock_best()
            event['status'] = 'OK'
            return result
        except InvalidAction as exc:
            return {'status': 'INVALID', 'reason': type(exc).__name__}
        except Exception as exc:
            event.update(status='BLOCKED', error_type=type(exc).__name__)
            raise
        finally:
            self.events.append(event)

    def record(self):
        return {'candidates': self.candidates, 'locked': self.locked, 'evaluations': self.evaluations,
            'candidate_limit': self.limit, 'editor_turns': self.turns, 'combined_turns': self.shared.turns,
            'probe_queries': self.probes, 'probe_limit': self.probe_limit, 'events': self.events,
            'target_work': {k: self.scorer.work[k]-self.start_work[k] for k in self.start_work}}
