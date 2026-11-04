"""Bounded, tool-free editor transports. Runtime invocation is coordinator-only."""
import copy
import json
import os
from pathlib import Path
from importlib.resources import files
import subprocess
import tempfile
import time
from jsonschema import Draft202012Validator
from .controller import StrictValidator, action_schema
from .io import digest, write_json
import shutil

MODELS = {'Astra': 'gpt-6-astra', 'Sol': 'gpt-6.1-sol'}
def resolve_cli(explicit=None):
    requested = explicit or os.environ.get('WS_LAB_CODEX_CLI') or 'codex'
    found = shutil.which(str(requested))
    if found is None:
        raise BlockedRoute('Codex CLI unavailable: supply --codex-cli or WS_LAB_CODEX_CLI or PATH')
    return found

ENVELOPE = {'type': 'object', 'properties': {'action_json': {'type': 'string'}},
            'required': ['action_json'], 'additionalProperties': False}
INSTRUCTIONS = files('ws_lab').joinpath('resources/adult_editor.txt').read_text()
DISABLED = ('plugins apps multi_agent multi_agent_v2 shell_tool unified_exec unified_exec_tty '
            'shell_snapshot view_image image_generation browser_use browser_use_external '
            'browser_use_full_cdp_access in_app_browser computer_use goals memories tool_suggest '
            'sleep_tool current_time_reminder request_permissions_tool token_budget code_mode '
            'code_mode_only code_mode_host workspace_dependencies hooks plugin_hooks '
            'remote_plugin skill_search skill_mcp_dependency_install worktrees collaboration_modes deferred_executor send_message_to_user_async').split()


class BlockedRoute(RuntimeError):
    pass


class BudgetExhausted(BlockedRoute):
    pass


class InvalidResponse(BlockedRoute):
    pass


def status(editor):
    if editor not in MODELS:
        raise ValueError('unknown editor; no fallback permitted')
    return {'status': 'NOT_RUN', 'requested_model': MODELS[editor], 'resolved_model': None,
            'route': 'https://api.anthropic.com/v1/messages' if editor == 'Claude' else 'native Codex CLI',
            'reasoning': 'medium', 'cost': None, 'timeout_seconds': 120,
            'max_wall_seconds': 900, 'max_active_seconds': 900,
            'time_budget_semantics': 'accumulated editor invocation time; excludes target/other-actor waiting',
            'max_turns': 15,
            'session_mode': 'fresh stateless; own transcript only'}


def bounded_payload(transcript):
    value = json.dumps(transcript, allow_nan=False, separators=(',', ':'))
    if len(value.encode()) > 1048576:
        raise BudgetExhausted('transcript byte budget exhausted')
    return value


def decode_action(value, schema=None):
    try:
        Draft202012Validator(ENVELOPE).validate(value)
        if len(value['action_json'].encode()) > 65536:
            raise ValueError('oversized action')
        action = json.loads(value['action_json'])
        StrictValidator(action_schema() if schema is None else schema).validate(action)
        return action
    except Exception as exc:
        raise InvalidResponse('INVALID: malformed action envelope') from None


def sanitized_event_summary(events, schema=None):
    usage, messages, session, terminal = None, [], None, False
    turn_started = False
    types = []
    for event in events:
        if type(event) is not dict or terminal:
            raise InvalidResponse('INVALID: malformed native sequence')
        kind = event.get('type')
        types.append(kind)
        if kind == 'thread.started':
            if types != ['thread.started'] or not isinstance(event.get('thread_id'), str):
                raise InvalidResponse('INVALID: session')
            session = event['thread_id']
        elif kind == 'turn.started':
            if session is None or turn_started:
                raise InvalidResponse('INVALID: turn sequence')
            turn_started = True
        elif kind == 'turn.completed':
            if not turn_started:
                raise InvalidResponse('INVALID: missing turn start')
            supplied = event.get('usage')
            if type(supplied) is not dict:
                raise InvalidResponse('INVALID: usage')
            usage = {k: v for k, v in supplied.items() if k.endswith('_tokens') and type(v) is int and v >= 0}
            terminal = True
        elif kind in ('item.started', 'item.updated', 'item.completed'):
            if not turn_started:
                raise InvalidResponse('INVALID: item outside turn')
            item = event.get('item')
            if type(item) is not dict or item.get('type') not in ('agent_message', 'reasoning'):
                raise InvalidResponse('INVALID: unexpected native tool or item')
            if kind == 'item.completed' and item['type'] == 'agent_message':
                messages.append(item.get('text'))
        else:
            raise InvalidResponse('INVALID: unknown native event')
    if not terminal or session is None or len(messages) != 1:
        raise InvalidResponse('INVALID: incomplete native turn')
    try:
        action = decode_action(json.loads(messages[0]), schema)
    except (TypeError, ValueError):
        raise InvalidResponse('INVALID: malformed native output') from None
    return {'usage': usage, 'action': action, 'cost': None, 'session_id': session, 'event_types': types}


def rejected_terminal_usage(events):
    """Accounting only: never accepts a rejected stream or retains provider text."""
    terminals = [e for e in events if type(e) is dict and e.get('type') == 'turn.completed']
    if len(terminals) != 1 or not events or terminals[0] is not events[-1]:
        return None
    supplied = terminals[0].get('usage')
    if type(supplied) is not dict:
        return None
    tokens = {k: v for k, v in supplied.items() if k in {
        'input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_output_tokens'}}
    if not tokens or any(type(v) is not int or v < 0 for v in tokens.values()):
        return None
    return tokens


def restricted_catalog(cache, slug, instructions=INSTRUCTIONS):
    """Select model metadata only; never read native config or identity files."""
    selected = [m for m in cache['models'] if m.get('slug') == slug]
    if len(selected) != 1:
        raise BlockedRoute('requested model absent or ambiguous in native catalog')
    model = copy.deepcopy(selected[0])
    model.update(tool_mode='direct', apply_patch_tool_type=None, shell_type='disabled', experimental_supported_tools=[],
                 include_skills_usage_instructions=False, include_plugin_usage_instructions=False,
                 include_apps_usage_instructions=False, base_instructions=instructions)
    return {'models': [model]}


def native_launch(editor, cwd, catalog, instructions, schema, *, cli=None):
    settings = {'model_provider': 'openai', 'forced_login_method': 'chatgpt',
                'model_reasoning_effort': 'medium', 'service_tier': 'default',
                'approval_policy': 'never', 'web_search': 'disabled', 'project_doc_max_bytes': 0,
                'model_catalog_json': str(catalog), 'model_instructions_file': str(instructions),
                'skills.include_instructions': False, 'tools.update_plan.enabled': False,
                'tools.experimental_request_user_input.enabled': False,
                'features.skip_host_skill_discovery': True, 'features.omit_skill_descriptions': True,
                'suppress_unstable_features_warning': True, 'mcp_servers': {}}
    argv = [resolve_cli(cli), '--no-daemon', 'exec', '--ignore-user-config', '--strict-config',
            '--skip-git-repo-check', '--ephemeral', '--sandbox', 'read-only', '--model', MODELS[editor],
            '--cd', str(cwd), '--json', '--output-schema', str(schema)]
    for key, value in settings.items():
        argv += ['-c', key + '=' + ('{}' if value == {} else json.dumps(value))]
    for feature in DISABLED:
        argv += ['--disable', feature]
    return argv + ['-'], settings


class NativeDriver:
    def __init__(self, editor, run_dir=None, *, instructions=INSTRUCTIONS, schema=None, codex_cli=None):
        self.codex_cli = codex_cli
        self.instructions, self.schema = instructions, schema
        if editor not in ('Astra', 'Sol'):
            raise ValueError('unknown native editor')
        self.editor, self.run_dir = editor, run_dir
        self.metadata, self.calls, self.active_seconds = status(editor), 0, 0.
        self.preflight_done = False
        self.events = []

    def _invoke(self, transcript, *, purpose):
        payload = bounded_payload(transcript)
        remaining = 900 - self.active_seconds
        if remaining <= 0:
            raise BudgetExhausted('editor active time budget exhausted')
        if self.run_dir is None:
            raise BlockedRoute('owned private run directory required')
        root = Path(self.run_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        env = {k: os.environ[k] for k in ('HOME', 'PATH', 'LANG', 'TMPDIR') if k in os.environ}
        accounting = {'status': 'FAILED', 'cost': None, 'usage': None, 'purpose': purpose,
                      'submitted': False}
        before = None
        active_started = time.monotonic()
        event_count = len(self.events)
        result = None
        try:
            cache = json.loads((Path(env['HOME']) / '.codex/models_cache.json').read_text())
            catalog = restricted_catalog(cache, MODELS[self.editor], self.instructions)
            with tempfile.TemporaryDirectory(prefix='editor-', dir=root) as scratch, \
                    tempfile.TemporaryDirectory(prefix='slm-editor-empty-') as empty:
                files = Path(scratch)
                cwd = Path(empty)
                write_json(files / 'catalog.json', catalog)
                write_json(files / 'schema.json', ENVELOPE)
                (files / 'instructions.txt').write_text(self.instructions)
                argv, settings = native_launch(self.editor, cwd, files / 'catalog.json',
                                               files / 'instructions.txt', files / 'schema.json', cli=self.codex_cli)
                # Path-free hash: transient paths are represented by their logical purpose.
                safe = {k: ('<owned-file>' if k in ('model_catalog_json', 'model_instructions_file') else v)
                        for k, v in settings.items()}
                self.metadata.update(cli_version=None, catalog_sha256=digest(catalog),
                                     config_sha256=digest({'settings': safe, 'disabled': DISABLED}),
                                     model_launch={'model': MODELS[self.editor], 'flags':
                                                  ['ignore-user-config', 'strict-config', 'ephemeral', 'read-only'],
                                                  'settings': safe, 'disabled_features': DISABLED},
                                     source_rationale='codex-tools-spec.rs:1249 shell; 1384 clock; 1427 conditional patch; selected metadata removes all three',
                                     preventive_controls={'catalog_tool_mode': catalog['models'][0]['tool_mode'],
                                                          'catalog_shell': 'disabled', 'catalog_patch': None,
                                                          'catalog_experimental_tools': [], 'disabled_features': DISABLED,
                                                          'empty_cwd': True, 'child_env': sorted(env)})
                accounting.update(catalog_sha256=self.metadata['catalog_sha256'],
                                  config_sha256=self.metadata['config_sha256'], cli_version=None,
                                  model_launch=self.metadata['model_launch'],
                                  preventive_controls=self.metadata['preventive_controls'])
                before = time.monotonic()
                version = subprocess.run([resolve_cli(self.codex_cli), '--version'], env=env, cwd=cwd, capture_output=True,
                                         text=True, timeout=min(10, remaining), check=True).stdout.strip()
                if len(version) > 200 or '/' in version or '@' in version:
                    raise BlockedRoute('unexpected CLI version format')
                self.metadata['cli_version'] = accounting['cli_version'] = version
                before = time.monotonic()
                remaining = 900 - self.active_seconds - (before - active_started)
                if remaining <= 0:
                    raise BudgetExhausted('editor active time budget exhausted')
                accounting['submitted'] = None  # Invocation attempted; provider submission is not yet known.
                completed = subprocess.run(argv, input=payload, env=env, cwd=cwd, capture_output=True,
                                           text=True, timeout=min(120, remaining), check=False)
                accounting['elapsed_seconds'] = time.monotonic() - before
                accounting['returncode'] = completed.returncode
                if len(completed.stdout.encode()) > 2_000_000:
                    raise InvalidResponse('native output too large')
                try:
                    parsed_events = [json.loads(line) for line in completed.stdout.splitlines()]
                except (ValueError, TypeError):
                    raise InvalidResponse('INVALID: malformed native event JSON') from None
                accounting['usage'] = rejected_terminal_usage(parsed_events)
                if accounting['usage'] is not None:
                    accounting['submitted'] = True
                if completed.returncode:
                    raise BlockedRoute('native nonzero exit; no retry')
                result = sanitized_event_summary(parsed_events, self.schema)
                result.update(purpose=purpose, status='COMPLETE', submitted=True,
                              elapsed_seconds=time.monotonic() - before)
                self.events.append({k: v for k, v in result.items() if k != 'action'})
                self.metadata.update(status='READY', route_status='OBSERVED_INFERENCE')
                return result
        except BlockedRoute as exc:
            if before is not None:
                accounting['elapsed_seconds'] = time.monotonic() - before
            accounting['status'] = 'INVALID' if isinstance(exc, InvalidResponse) else 'FAILED'
            self.events.append(accounting)
            self.metadata['status'] = accounting['status']
            raise
        except Exception:
            if before is not None:
                accounting['elapsed_seconds'] = time.monotonic() - before
            self.events.append(accounting)
            self.metadata['status'] = accounting['status']
            raise BlockedRoute('native launch/transport failure; no retry') from None
        finally:
            elapsed = max(0., time.monotonic() - active_started)
            self.active_seconds += elapsed
            timing = {'active_elapsed_seconds': elapsed,
                      'accumulated_active_seconds': self.active_seconds,
                      'remaining_active_seconds': max(0., 900 - self.active_seconds)}
            if len(self.events) == event_count:
                self.events.append(accounting)  # Includes interrupted launches.
            self.events[-1].setdefault('elapsed_seconds', elapsed)
            self.events[-1].update(timing)
            self.metadata.update(timing)
            if result is not None:
                result.update(timing)

    def preflight(self):
        canary = [{'role': 'user', 'content': 'Benign capability canary. Return action_json encoding {"action":"inspect_stats"}. Use no tools.'}]
        result = self._invoke(canary, purpose='capability_canary')
        if result.get('action') != {'action': 'inspect_stats'}:
            self.events[-1]['status'] = 'INVALID'
            self.metadata['status'] = 'INVALID'
            raise InvalidResponse('INVALID: capability canary response')
        self.preflight_done = True
        self.metadata['preflight'] = {k: v for k, v in result.items() if k != 'action'}
        return result

    def turn(self, own_transcript):
        if not self.preflight_done:
            raise BlockedRoute('native capability preflight required')
        if self.calls >= 15:
            raise BudgetExhausted('editor turn budget exhausted')
        self.calls += 1
        return self._invoke(own_transcript, purpose='scientific_controller_call')

    def request_manifest(self, own_transcript):
        bounded_payload(own_transcript)
        return {**self.metadata, 'transcript_sha256': digest(own_transcript)}

