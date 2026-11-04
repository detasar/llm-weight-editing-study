"""CPU-only fixed-budget classifier training; repair evaluation is inference-only."""
import numpy as np
import torch
from torch import nn
from safetensors.torch import save_file
from .io import write_json, state_hash
from .data import load_split
from pathlib import Path
from sklearn.metrics import balanced_accuracy_score

torch.set_num_threads(min(4, torch.get_num_threads()))


class AdultMLP(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.fc1 = nn.Linear(d, 32)
        self.fc2 = nn.Linear(32, 16)
        self.fc3 = nn.Linear(16, 1)

    def forward(self, x):
        return self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(x))))).squeeze(-1)


def probabilities(state, x):
    model = AdultMLP(state['fc1.weight'].shape[1])
    model.load_state_dict(state)
    model.eval()
    with torch.inference_mode():
        return torch.sigmoid(model(torch.as_tensor(x, dtype=torch.float32))).numpy()


def train(run, seed=101):
    run = Path(run)
    if (run / 'trained.json').exists():
        raise ValueError('training already exists')
    torch.set_num_threads(min(4, torch.get_num_threads()))
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    fit, calibration = load_split(run, 'fit'), load_split(run, 'calibration')
    model = AdultMLP(fit['x'].shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    loss_fn = nn.BCEWithLogitsLoss()
    generator = torch.Generator().manual_seed(seed)
    x, y = torch.from_numpy(fit['x']), torch.from_numpy(fit['y']).float()
    for _ in range(30):
        for ix in torch.randperm(len(y), generator=generator).split(256):
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(x[ix]), y[ix])
            loss.backward()
            optimizer.step()
    clean = {k: v.detach().clone() for k, v in model.state_dict().items()}
    clean_score = balanced_accuracy_score(calibration['y'], probabilities(clean, calibration['x']) >= .5)
    permutation = np.random.default_rng(seed).permutation(32)
    trials = []
    for rate in [.1, .25, .5]:
        columns = permutation[:int(32 * rate)]
        damaged = {k: v.clone() for k, v in clean.items()}
        damaged['fc2.weight'][:, columns] = 0
        score = balanced_accuracy_score(calibration['y'], probabilities(damaged, calibration['x']) >= .5)
        trials.append({'rate': rate, 'calibration_balanced_accuracy': float(score), 'drop': float(clean_score-score)})
        if clean_score - score >= .05:
            break
    mask = torch.zeros_like(damaged['fc2.weight'], dtype=torch.bool)
    mask[:, columns] = True
    save_file(clean, str(run / 'clean.safetensors'))
    save_file(damaged, str(run / 'damaged.safetensors'))
    save_file({'mask': mask}, str(run / 'mask.safetensors'))
    meta = {'phase': 'TRAINED', 'seed': seed, 'epochs': 30, 'batch_size': 256, 'lr': .001,
            'optimizer': 'Adam', 'loss': 'BCEWithLogitsLoss', 'device': 'cpu', 'dtype': 'float32',
            'threads': torch.get_num_threads(), 'clean_hash': state_hash(clean), 'damaged_hash': state_hash(damaged),
            'lesion_trials': trials, 'lesion_columns_private': columns.tolist(),
            'insufficient_damage': trials[-1]['drop'] < .05}
    write_json(run / 'trained.json', meta)
    return meta
