"""Export a trained PPO policy to NumPy weights for petsim.policy.NumpyPolicy.

    python scripts/export_policy.py runs/ppo_walle/final.zip models/walle_follow.npz
"""

import argparse

import numpy as np
from stable_baselines3 import PPO


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", help="trained PPO .zip")
    parser.add_argument("out", help="output .npz")
    args = parser.parse_args()

    policy = PPO.load(args.model, device="cpu").policy
    linears = [m for m in policy.mlp_extractor.policy_net if hasattr(m, "weight")] + [policy.action_net]
    weights = {}
    for i, layer in enumerate(linears):
        weights[f"w{i}"] = layer.weight.detach().numpy()
        weights[f"b{i}"] = layer.bias.detach().numpy()
    np.savez_compressed(args.out, **weights)
    print(f"saved {args.out}: layers {[w.shape for k, w in weights.items() if k.startswith('w')]}")


if __name__ == "__main__":
    main()
