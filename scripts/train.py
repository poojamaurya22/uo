"""Train a follow policy with PPO (Stable-Baselines3).

    python scripts/train.py --steps 2000000 --out runs/ppo
    tensorboard --logdir runs        # optional: watch learning curves
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback  # noqa: E402
from stable_baselines3.common.env_util import make_vec_env  # noqa: E402
from stable_baselines3.common.vec_env import SubprocVecEnv  # noqa: E402

from petsim.env import PetFollowEnv  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steps", type=int, default=2_000_000)
    parser.add_argument("--envs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--out", default="runs/ppo")
    parser.add_argument("--resume", help="continue training from a saved .zip")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    torch.set_num_threads(1)  # the network is tiny; leave the cores to the simulators

    envs = make_vec_env(PetFollowEnv, n_envs=args.envs, seed=args.seed, vec_env_cls=SubprocVecEnv)
    eval_env = make_vec_env(PetFollowEnv, n_envs=1, seed=args.seed + 10_000)
    tensorboard = args.out if _has_tensorboard() else None

    if args.resume:
        model = PPO.load(args.resume, env=envs, device="cpu", tensorboard_log=tensorboard)
    else:
        model = PPO(
            "MlpPolicy",
            envs,
            n_steps=1024,
            batch_size=512,
            gamma=0.98,
            learning_rate=3e-4,
            ent_coef=0.003,
            policy_kwargs={"net_arch": [256, 256]},
            device="cpu",
            seed=args.seed,
            tensorboard_log=tensorboard,
            verbose=1,
        )

    callbacks = [
        CheckpointCallback(save_freq=max(200_000 // args.envs, 1), save_path=args.out, name_prefix="ckpt"),
        EvalCallback(eval_env, n_eval_episodes=5, eval_freq=max(100_000 // args.envs, 1),
                     best_model_save_path=args.out, verbose=1),
    ]
    model.learn(total_timesteps=args.steps, callback=callbacks, reset_num_timesteps=not args.resume)
    model.save(os.path.join(args.out, "final"))
    print(f"saved {args.out}/final.zip and {args.out}/best_model.zip")


def _has_tensorboard():
    try:
        import tensorboard  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
