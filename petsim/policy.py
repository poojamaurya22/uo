"""Run a trained follow policy with NumPy only.

PyTorch is only needed for training. Exported weights (scripts/export_policy.py)
are a few hundred KB and run anywhere NumPy does, e.g. the robot's Pi Zero 2 W.
"""

import numpy as np


class NumpyPolicy:
    def __init__(self, path):
        weights = np.load(path)
        self.layers = [(weights[f"w{i}"], weights[f"b{i}"]) for i in range(len(weights.files) // 2)]

    def __call__(self, obs):
        x = np.asarray(obs, dtype=np.float32)
        for w, b in self.layers[:-1]:
            x = np.tanh(w @ x + b)
        w, b = self.layers[-1]
        return np.clip(w @ x + b, -1.0, 1.0)
