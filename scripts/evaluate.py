"""Score a controller on the follow task, optionally saving videos.

    python scripts/evaluate.py --controller baseline
    python scripts/evaluate.py --controller runs/ppo/final.zip --video out.mp4
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from petsim.baseline import follow_controller  # noqa: E402
from petsim.env import CONTROL_DT, PetFollowEnv  # noqa: E402


def load_controller(name):
    if name == "baseline":
        return follow_controller
    if name == "random":
        rng = np.random.default_rng(0)
        return lambda obs: rng.uniform(-1, 1, 2)
    from stable_baselines3 import PPO

    model = PPO.load(name, device="cpu")
    return lambda obs: model.predict(obs, deterministic=True)[0]


def run(controller, episodes, seed, video=None, photo=None, safety=True):
    env = PetFollowEnv(safety=safety)
    frames, totals = [], []
    stats = {"in_range": 0, "visible": 0, "collisions": 0, "too_close": 0, "steps": 0, "falls": 0}
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        total, done = 0.0, False
        while not done:
            obs, reward, term, trunc, info = env.step(controller(obs))
            total += reward
            done = term or trunc
            stats["steps"] += 1
            stats["in_range"] += 0.6 < info["distance"] < 1.4
            stats["visible"] += info["person_visible"]
            stats["collisions"] += info["collided"]
            stats["too_close"] += info["distance"] < 0.45
            stats["falls"] += info["fell"] or info["flipped"]
            if video and ep == 0:
                frames.append(env.render())
        totals.append(total)
        if photo and ep == 0:
            import imageio.v3 as iio

            iio.imwrite(photo, env.take_photo())
    env.close()

    n = stats["steps"]
    minutes = n * CONTROL_DT / 60
    print(f"episodes:               {episodes}")
    print(f"mean episode reward:    {np.mean(totals):.1f} (+/- {np.std(totals):.1f})")
    print(f"time at 0.6-1.4 m:      {100 * stats['in_range'] / n:.0f}%")
    print(f"person in view:         {100 * stats['visible'] / n:.0f}%")
    print(f"too close (<0.45 m):    {100 * stats['too_close'] / n:.0f}%")
    print(f"collision steps / min:  {stats['collisions'] / minutes:.1f}")
    print(f"falls / flips:          {stats['falls']}")
    if video:
        import imageio.v3 as iio

        iio.imwrite(video, np.stack(frames), fps=int(1 / CONTROL_DT))
        print(f"video saved to {video}")
    return np.mean(totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--controller", default="baseline", help="baseline, random, or a path to a PPO .zip")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--video", help="save the first episode as an mp4")
    parser.add_argument("--photo", help="save a photo from the robot's camera at the end of episode 1")
    parser.add_argument("--no-safety", action="store_true", help="disable the cliff safety reflex")
    args = parser.parse_args()
    run(load_controller(args.controller), args.episodes, args.seed, args.video, args.photo, not args.no_safety)
