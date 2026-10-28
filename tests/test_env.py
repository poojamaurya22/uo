import numpy as np
from gymnasium.utils.env_checker import check_env

from petsim.baseline import follow_controller
from petsim.env import OBS, OBS_DIM, PetFollowEnv
from petsim.safety import safety_filter


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
        cliff = max(cliff, obs[OBS["cliff"]][:3].max())
    assert obs.shape == (OBS_DIM,)
    assert cliff > 0.5


def test_rear_cliff_sensors_see_the_stairwell():
    env = PetFollowEnv(randomize=False)
    env.reset(seed=0)
    q = env.data.qpos
    q[0:2] = [1.25, 0.0]  # just short of the stairwell, backing into it
    q[3:7] = [0, 0, 0, 1]
    env.data.mocap_pos[:, :2] = [-1.5, -1.5]
    rear = 0.0
    for _ in range(30):
        obs, *_ = env.step(np.array([-0.3, -0.3]))
        rear = max(rear, obs[OBS["cliff"]][3:].max())
    assert rear > 0.5


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


def test_safety_reflex_overrides_controller():
    floor, gone = 0.05, 1.0
    go = np.array([1.0, 1.0])
    assert np.allclose(safety_filter(np.full(5, floor), 0.0, go), go)
    assert safety_filter(np.array([gone, floor, floor, floor, floor]), 0.0, go).max() < 0  # backs off
    assert safety_filter(np.array([floor, floor, floor, gone, floor]), 0.0, -go).min() > 0  # drives off
    assert np.allclose(safety_filter(np.full(5, floor), 0.4, go), 0)  # tilted: stop
    assert safety_filter(np.array([floor, floor, floor, gone, gone]), 0.4, go).min() > 0  # cliff beats tilt


def test_tilt_estimate_ignores_driving_jolts():
    env = PetFollowEnv(randomize=False)
    env.reset(seed=0)
    for i in range(60):  # full-speed starts, stops and reversals on flat floor
        env.step(np.array([1.0, 1.0]) if (i // 10) % 2 == 0 else np.array([-1.0, -1.0]))
        assert env.last_tilt < 0.25


def test_hardware_params_match_robot_spec():
    """The printable parts must be generated from the current RobotSpec."""
    import importlib.util
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("gen", os.path.join(root, "scripts", "gen_scad_params.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    with open(os.path.join(root, "hardware", "params.scad")) as f:
        assert f.read() == gen.render(), "run: python scripts/build_hardware.py"
