"""Behavior cloning from an explicitly rule-based teacher; no human demos.

Fixed random seeds and a separate state validation set. Kinematic rollouts are
only an offline diagnostic; they do not substitute for Gazebo evaluation.
"""
import os
for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
    os.environ[key] = '1'
import csv
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
import torch
from torch import nn
from policy import Policy, GOAL_RADIUS, MAX_V, MAX_W, relative_goal

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'learned'

def dataset(seed, size):
    rng = np.random.default_rng(seed)
    distance = rng.uniform(GOAL_RADIUS, 5.0, size)
    distance[:size//3] = rng.uniform(GOAL_RADIUS, 0.8, size//3)
    heading = rng.uniform(-math.pi, math.pi, size)
    x = np.column_stack((distance/5.0, heading/math.pi)).astype(np.float32)
    # Smooth speed gate: turn first when far from the target bearing.
    v = np.tanh(distance/0.6) * np.exp(-(heading/0.6)**2)
    w = np.tanh(1.8*heading)
    y = np.column_stack((v, w)).astype(np.float32)
    return x, y

def main():
    if (OUT / 'policy.npz').exists():
        raise SystemExit('Existing model preserved. Choose a new output directory for another experiment.')
    OUT.mkdir(exist_ok=True)
    torch.set_num_threads(1)
    torch.manual_seed(42)
    x, y = dataset(42, 24000)
    vx, vy = dataset(43, 6000)
    np.savez_compressed(OUT / 'teacher_data.npz', train_x=x, train_y=y, validation_x=vx, validation_y=vy)
    model = nn.Sequential(nn.Linear(2, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh(), nn.Linear(32, 2))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    tx, ty = torch.from_numpy(x), torch.from_numpy(y)
    validation_x, validation_y = torch.from_numpy(vx), torch.from_numpy(vy)
    start = time.monotonic()
    history = []
    for step in range(1, 1801):
        idx = torch.randint(len(tx), (512,))
        optimizer.zero_grad()
        loss = ((model(tx[idx])-ty[idx])**2).mean()
        loss.backward()
        optimizer.step()
        if step == 1 or step % 100 == 0:
            with torch.no_grad():
                val = ((model(validation_x)-validation_y)**2).mean().item()
            history.append({'step': step, 'train_batch_mse': loss.item(), 'validation_mse': val})
            print(history[-1], flush=True)
    seconds = time.monotonic()-start
    arrays = {}
    for i, layer in enumerate([model[0], model[2], model[4]]):
        arrays[f'w{i}'] = layer.weight.detach().numpy().T.copy()
        arrays[f'b{i}'] = layer.bias.detach().numpy().copy()
    np.savez(OUT / 'policy.npz', **arrays)
    policy = Policy()
    with torch.no_grad():
        reference = model(validation_x).numpy()
    prediction = policy.raw(vx)
    export_error = float(np.max(np.abs(reference-prediction)))
    if export_error > 1e-5:
        raise RuntimeError('NumPy export differs from PyTorch: ' + str(export_error))
    absolute = np.abs(prediction-vy) * np.array([MAX_V, MAX_W])
    timings = []
    for _ in range(2000):
        tick = time.perf_counter_ns()
        policy.command(2.0, 0.5)
        timings.append((time.perf_counter_ns()-tick)/1e6)
    # Reserved scenario seed, never used to generate the training state pairs.
    rng = np.random.default_rng(20261012)
    rollouts = []
    for index in range(20):
        angle, distance, yaw = rng.uniform(-math.pi, math.pi), rng.uniform(1.5, 4.0), rng.uniform(-math.pi, math.pi)
        gx, gy = distance*math.cos(angle), distance*math.sin(angle)
        px = py = 0.0
        for tick in range(600):
            d, h = relative_goal(px, py, yaw, gx, gy)
            if d <= GOAL_RADIUS:
                break
            v, w = policy.command(d, h)
            px += v*math.cos(yaw)*0.1
            py += v*math.sin(yaw)*0.1
            yaw += w*0.1
        final = math.hypot(gx-px, gy-py)
        rollouts.append({'scenario': index, 'goal': [gx, gy], 'final_distance_m': final,
                         'sim_seconds': tick*0.1, 'success': final <= GOAL_RADIUS})
    metrics = {'teacher': 'Analytic rule-based teacher, not human demonstrations',
        'architecture': [2, 32, 32, 2], 'parameters': sum(p.numel() for p in model.parameters()),
        'input': ['distance / 5 (clipped to 5 m)', 'wrapped target bearing error / pi'],
        'output': ['linear speed / 0.35', 'angular speed / 0.8'],
        'training_seed': 42, 'validation_seed': 43, 'training_states': len(x), 'validation_states': len(vx),
        'steps': 1800, 'batch_size': 512, 'learning_rate': 0.002, 'torch_version': torch.__version__,
        'training_wall_seconds': seconds, 'numpy_export_max_error': export_error,
        'validation_mae_v_mps': float(absolute[:, 0].mean()),
        'validation_mae_w_radps': float(absolute[:, 1].mean()),
        'inference_ms_p50': float(np.percentile(timings, 50)),
        'inference_ms_p95': float(np.percentile(timings, 95)),
        'goal_radius_m': GOAL_RADIUS, 'kinematic_successes': sum(r['success'] for r in rollouts),
        'kinematic_trials': len(rollouts), 'kinematic_rollouts': rollouts,
        'model_sha256': hashlib.sha256((OUT / 'policy.npz').read_bytes()).hexdigest(),
        'limits': 'Obstacle-free planar kinematics only. Gazebo trials required. Goal threshold and stopping are explicit supervisory logic, not learned.'}
    (OUT / 'training_metrics.json').write_text(json.dumps(metrics, indent=2))
    with (OUT / 'training_curve.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    print(json.dumps({k:v for k,v in metrics.items() if k != 'kinematic_rollouts'}, indent=2), flush=True)

if __name__ == '__main__':
    main()
