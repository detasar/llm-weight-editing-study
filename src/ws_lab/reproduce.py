"""Explicit publication CLI. Saved-data commands never import inference components."""
import argparse
import importlib.metadata
import json
import shutil
from pathlib import Path
from .io import read_json

EXECUTION_BLOCKER = (
    'Full historical run/replay is BLOCKED: accepted orchestration depends on sealed Adult '
    'DEV_HISTORY audit and prospective train8 backend evidence outside this publication input '
    'closure, plus private source-hash/consumption bindings. Canonical scorers, validators, '
    'controllers and native transport are bundled. Explicit fresh run/replay is available '
    'with offline synthetic verification only; real portable execution is NOT_RUN. '
    'No historical output was created and no model/editor was called.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('verify', 'analyse'):
        p = sub.add_parser(name)
        p.add_argument('--data-dir', type=Path, default=Path('data'))
        p.add_argument('--output', type=Path)
    p = sub.add_parser('doctor')
    p.add_argument('--codex-cli')
    p.add_argument('--model-dir', type=Path)
    p.add_argument('--dataset-dir', type=Path)
    for name in ('replay', 'run'):
        p = sub.add_parser(name, description='Explicit fresh-public execution; historical guards remain separate.')
        p.add_argument('--output', type=Path, required=True)
        p.add_argument('--config', type=Path, required=True)
        p.add_argument('--model-dir', type=Path, required=True)
        p.add_argument('--dataset-dir', type=Path, required=True)
        p.add_argument('--codex-cli')
    args = parser.parse_args(argv)
    try:
        if args.command in ('verify', 'analyse'):
            from .publication import verify, analyse_data
            receipt = verify(args.data_dir)
            value = receipt if args.command == 'verify' else analyse_data(args.data_dir)
            if args.output:
                with args.output.open('x') as stream:
                    json.dump(value, stream, indent=2, allow_nan=False)
                    stream.write('\n')
        elif args.command == 'doctor':
            import os
            packages = {}
            for name in ('numpy', 'scipy', 'scikit-learn', 'torch', 'transformers', 'datasets', 'lm_eval', 'jsonschema'):
                try:
                    packages[name] = importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    packages[name] = None
            value = {'status': 'INSPECTED_NO_DISPATCH', 'packages': packages,
                'codex_cli_available': shutil.which(args.codex_cli or os.environ.get('WS_LAB_CODEX_CLI') or 'codex') is not None,
                'requested_editors': {'Sol': 'gpt-6.1-sol', 'Astra': 'gpt-6-astra'}, 'reasoning': 'medium',
                'editor_model_availability': 'UNKNOWN; no canary or provider request made',
                'model_directory_exists': args.model_dir.is_dir() if args.model_dir else None,
                'dataset_directory_exists': args.dataset_dir.is_dir() if args.dataset_dir else None,
                'execution_status': 'EXPLICIT_FRESH_RUN_OR_REPLAY_ONLY', 'historical_execution_blocker': EXECUTION_BLOCKER}
        else:
            if args.output.exists():
                raise ValueError('new output path required; existing runs may never be consumed')
            from .execution import execute
            value = execute(args)
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED_OR_FAILED', 'error_type': type(exc).__name__,
                          'error': str(exc) if isinstance(exc, (ValueError, KeyError)) else 'execution failed; inspect local terminal receipt'}))
        return 2
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
