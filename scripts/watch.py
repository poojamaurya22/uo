"""Watch a controller drive the robot live in the MuJoCo 3D viewer (needs a display).

    python scripts/watch.py --controller baseline
    python scripts/watch.py --controller models/walle_follow.npz

On macOS run it with `mjpython` instead of `python`.
Viewer tips: double-click a body to select it, Ctrl+right-drag to push it,
Tab/Shift-Tab to toggle panels, and pick the robot's "eye" camera under Rendering.
"""

import argparse
import os
import sys
import time

import mujoco.viewer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluate import load_controller  # noqa: E402

from petsim.env import CONTROL_DT, PetFollowEnv  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--controller", default="baseline")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    controller = load_controller(args.controller)
    env = PetFollowEnv()
    obs, _ = env.reset(seed=args.seed)
    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        episode = 0
        while viewer.is_running():
            start = time.time()
            obs, _, term, trunc, info = env.step(controller(obs))
            if term or trunc:
                episode += 1
                obs, _ = env.reset(seed=args.seed + episode)
            viewer.sync()
            time.sleep(max(0.0, CONTROL_DT - (time.time() - start)))


if __name__ == "__main__":
    main()
