import numpy as np
from gymnasium.utils.env_checker import check_env

from petsim.baseline import follow_controller
from petsim.env import OBS_DIM, PetFollowEnv


def test_gymnasium_api():
    check_env(PetFollowEnv(), skip_render_check=True)


def test_drives_straight_at_expected_speed():
    env = PetFollowEnv(randomize=False)
    env.reset(seed=0)
    start, _ = env.robot_pose()
    for _ in range(20):  # 1 s at half speed
        env.step(np.array([0.5, 0.5]))
    end, _ = env.robot_pose()
    expected = 0.5 * env.robot.max_wheel_speed * env.robot.wheel_radius
    assert abs(np.linalg.norm(end[:2] - start[:2]) - expected) < 0.25 * expected


def test_cliff_sensors_see_the_stairwell():
    env = PetFollowEnv(randomize=False)
    env.reset(seed=0)
    q = env.data.qpos
    q[0:2] = [1.25, 0.0]  # just short of the stairwell, facing +x into it
    q[3:7] = [1, 0, 0, 0]
    env.data.mocap_pos[:, :2] = [-1.5, -1.5]
    cliff = 0.0
    for _ in range(30):
        obs, *_ = env.step(np.array([0.3, 0.3]))
        cliff = max(cliff, obs[64:67].max())
    assert obs.shape == (OBS_DIM,)
    assert cliff > 0.5


def test_baseline_beats_random():
    def score(controller, seed):
        env = PetFollowEnv()
        obs, _ = env.reset(seed=seed)
        total, done = 0.0, False
        while not done:
            obs, r, term, trunc, _ = env.step(controller(obs))
            total += r
            done = term or trunc
        return total

    rng = np.random.default_rng(0)
    baseline = np.mean([score(follow_controller, s) for s in range(3)])
    random = np.mean([score(lambda o: rng.uniform(-1, 1, 2), s) for s in range(3)])
    assert baseline > random
