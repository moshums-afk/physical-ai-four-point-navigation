"""Small learned velocity policy. Runtime requires NumPy, not PyTorch."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
GOAL_RADIUS = 0.20
MAX_V = 0.35
MAX_W = 0.8

def features(distance, heading):
    return np.array([min(max(distance, 0.0), 5.0) / 5.0,
                     math.atan2(math.sin(heading), math.cos(heading)) / math.pi], dtype=np.float32)

class Policy:
    def __init__(self, path=None):
        with np.load(path or ROOT / 'learned' / 'policy.npz', allow_pickle=False) as data:
            self.weights = [(data[f'w{i}'].copy(), data[f'b{i}'].copy()) for i in range(3)]

    def raw(self, inputs):
        x = np.asarray(inputs, dtype=np.float32)
        for i, (w, b) in enumerate(self.weights):
            x = x @ w + b
            if i < 2:
                x = np.tanh(x)
        return x

    def command(self, distance, heading):
        y = self.raw(features(distance, heading))
        return float(np.clip(y[0], 0, 1) * MAX_V), float(np.clip(y[1], -1, 1) * MAX_W)

def relative_goal(x, y, yaw, gx, gy):
    dx, dy = gx-x, gy-y
    return math.hypot(dx, dy), math.atan2(math.sin(math.atan2(dy, dx)-yaw),
                                         math.cos(math.atan2(dy, dx)-yaw))
