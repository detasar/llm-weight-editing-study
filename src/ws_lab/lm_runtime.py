"""Fixed legacy and explicit engineering inference profiles; environment is supplied before Python starts."""
import os
import platform
import time

ENV_KEYS = ('PYTORCH_MPS_METAL_VERSION', 'PYTORCH_MPS_FAST_MATH',
            'PYTORCH_MPS_PREFER_METAL', 'PYTORCH_ENABLE_MPS_FALLBACK')
IMPORT_ENV = {k: os.environ.get(k) for k in ENV_KEYS}
PROFILES = {'mps-metal3-fp16-eager-v1': 'mps', 'cpu-fp16-eager-v1': 'cpu',
            'cpu-fp32-eager-engineering-v1': 'cpu',
            'mps-fp32-eager-engineering-v1': 'mps'}
SCORER = {'batch_size': 1, 'logits_cache': False, 'softmax_dtype': 'float32'}


def validate_profile(config):
    profile = config.get('runtime_profile')
    if (profile not in PROFILES or config.get('device') != PROFILES[profile]
            or config.get('dtype') != ('float32' if 'fp32' in profile else 'float16') or config.get('attention') != 'eager'):
        raise ValueError('unsupported LM runtime profile/configuration')
    actual = {k: os.environ.get(k) for k in ENV_KEYS}
    expected = dict.fromkeys(ENV_KEYS)
    if profile == 'mps-metal3-fp16-eager-v1':
        expected[ENV_KEYS[0]] = '3.1'
    if actual != expected or actual != IMPORT_ENV:
        raise ValueError('LM runtime profile/environment mismatch; launch a fresh interpreter')


def inference_identity(config):
    validate_profile(config)
    import torch
    hardware = {'machine': platform.machine(), 'processor': platform.processor(),
                'host': platform.node()}
    device_name = (torch.backends.mps.get_name() if config['device'] == 'mps'
                   and torch.backends.mps.is_available() else None)
    return {'runtime_profile': config['runtime_profile'], 'device': config['device'],
        'dtype': config['dtype'], 'attention': 'eager', 'scorer': dict(SCORER),
        'environment': {k: os.environ.get(k) for k in ENV_KEYS},
        'torch': {'version': str(torch.__version__), 'git_version': torch.version.git_version,
                  'build': torch.__config__.show()},
        'os': {'system': platform.system(), 'release': platform.release(),
               'build': platform.version(), 'mac_version': platform.mac_ver()[0]},
        'hardware': hardware,
        'device_identity': {'type': config['device'], 'name': device_name, 'hardware': hardware},
        'kernel_execution': 'NOT_OBSERVED'}


def verify_identity(config, expected):
    if inference_identity(config) != expected:
        raise ValueError('prepared inference identity changed')


def leg_identity(identity, *, reference=False):
    return {'inference_identity': identity,
            'actual_device': 'cpu' if reference else identity['device'],
            'role': 'reference-only' if reference else 'profile-inference'}


def launch_evidence():
    # Observed at this boundary, not proof of the environment of an older process.
    return {'pid': os.getpid(), 'observed_unix_time': time.time(),
            'environment_at_module_import': dict(IMPORT_ENV)}
