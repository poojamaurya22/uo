"""Gymnasium environment: the Wall-E robot learns to follow a person around a room.

Observations are built only from sensors the real robot will have (8x8 chest
ToF, side ToFs, cliff sensors, IMU, track encoders, neck angle, and a person
detector running on the eye camera), with noise and dropouts, so a trained
policy can transfer to hardware. The reward uses the true person position,
which only the simulator knows.

The neck is not part of the policy: like a real robot's reflex, it turns the
head towards the person whenever the camera sees them, and tilts up to their face.
"""

import math

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from petsim.robot import (
    HOLE_X,
    HOLE_Y,
    OBSTACLES,
    ROOM_HALF,
    SENSOR_GEOMGROUP,
    RobotSpec,
    build_xml,
)

CONTROL_DT = 0.05  # 20 Hz, comfortable for a Pi Zero 2 W + microcontroller
TOF_ZONES = 8
CLIFF_RANGE = 0.2
PERSON_RANGE = 6.0
LOST_MEMORY_S = 5.0
SIDE_RAYS = 3  # rays spread over each side sensor's field of view

# Observation layout, so controllers can read fields by name.
_FIELDS = [("tof", TOF_ZONES * TOF_ZONES), ("cliff", 3), ("side", 2), ("imu", 3), ("tracks", 2),
           ("person", 5), ("pan", 1), ("prev_action", 2)]
OBS = {}
_i = 0
for _name, _size in _FIELDS:
    OBS[_name] = slice(_i, _i + _size)
    _i += _size
OBS_DIM = _i

# Area the person walks in: the room minus a margin, never near the stairwell.
WALK_X = (-ROOM_HALF + 0.3, HOLE_X[0] - 0.3)
WALK_Y = (-ROOM_HALF + 0.3, ROOM_HALF - 0.3)


def _wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


class PersonWalker:
    """Moves the person between random waypoints, pausing now and then."""

    def __init__(self, rng, blocked, robot_xy):
        self.rng = rng
        self.blocked = blocked  # callable(x, y) -> bool
        self.robot_xy = robot_xy  # callable() -> robot position, people don't walk through pets
        self.pos = np.zeros(2)
        self.heading = 0.0
        self.target = np.zeros(2)
        self.speed = 0.0
        self.pause = 0.0

    def sample_point(self):
        for _ in range(100):
            p = self.rng.uniform([WALK_X[0], WALK_Y[0]], [WALK_X[1], WALK_Y[1]])
            if not self.blocked(*p):
                return p
        return p

    def reset(self, pos):
        self.pos = np.array(pos, dtype=float)
        self.heading = self.rng.uniform(-math.pi, math.pi)
        self._new_leg()
        self.pause = self.rng.uniform(0.5, 2.0)

    def _new_leg(self):
        self.target = self.sample_point()
        self.speed = self.rng.uniform(0.15, 0.6)

    def step(self, dt):
        if self.pause > 0:
            self.pause -= dt
            return
        delta = self.target - self.pos
        dist = np.linalg.norm(delta)
        if dist < 0.05:
            self._new_leg()
            if self.rng.random() < 0.4:
                self.pause = self.rng.uniform(1.0, 4.0)
            return
        self.heading = math.atan2(delta[1], delta[0])
        nxt = self.pos + delta / dist * min(self.speed * dt, dist)
        if np.linalg.norm(nxt - self.robot_xy()) < 0.3:
            return  # robot in the way: wait for it to move
        self.pos = nxt


class PetFollowEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": int(1 / CONTROL_DT)}

    def __init__(
        self,
        render_mode=None,
        robot: RobotSpec = RobotSpec(),
        episode_seconds: float = 30.0,
        follow_distance: float = 1.0,
        randomize: bool = True,
    ):
        self.robot = robot
        self.render_mode = render_mode
        self.follow_distance = follow_distance
        self.randomize = randomize
        self.max_steps = int(episode_seconds / CONTROL_DT)

        self.model = mujoco.MjModel.from_xml_string(build_xml(robot))
        self.data = mujoco.MjData(self.model)
        m = self.model
        self.frame_skip = int(round(CONTROL_DT / m.opt.timestep))

        self.robot_body = m.body("robot").id
        self.root_qpos = m.joint("root").qposadr[0]
        self.root_qvel = m.joint("root").dofadr[0]
        self.person_mocap = m.body("person").mocapid[0]
        self.person_geoms = {m.geom(n).id for n in ("person_legs", "person_torso", "person_head")}
        self.obstacle_mocap = [m.body(o[0]).mocapid[0] for o in OBSTACLES]
        self.obstacle_radius = [max(o[2][:2]) if o[1] == "box" else o[2][0] for o in OBSTACLES]
        self.tof_site = m.site("tof").id
        self.cliff_sites = [m.site(n).id for n in ("cliff_l", "cliff_c", "cliff_r")]
        self.cam_id = m.camera("eye").id
        self.side_sites = [m.site("side_l").id, m.site("side_r").id]
        self.head_pan_act = m.actuator("head_pan").id
        self.head_tilt_act = m.actuator("head_tilt").id
        self.pan_qpos = m.joint("head_pan").qposadr[0]

        robot_bodies = {b for b in range(m.nbody) if m.body_rootid[b] == self.robot_body}
        self.is_robot_geom = np.array([m.geom_bodyid[g] in robot_bodies for g in range(m.ngeom)])
        self.is_floor_geom = np.array([m.geom(g).name.startswith("floor") for g in range(m.ngeom)])
        self.wheel_geoms = [g for g in range(m.ngeom) if m.body(m.geom_bodyid[g]).name.startswith("wheel_")]

        # ToF zone directions in the sensor frame: rows top->bottom, cols left->right.
        half = math.radians(robot.tof_fov_deg) / 2 * (1 - 1 / TOF_ZONES)
        tilt = math.radians(robot.tof_tilt_deg)
        dirs = []
        for pitch in np.linspace(half, -half, TOF_ZONES) + tilt:
            for yaw in np.linspace(half, -half, TOF_ZONES):
                dirs.append([math.cos(pitch) * math.cos(yaw),
                             math.cos(pitch) * math.sin(yaw),
                             math.sin(pitch)])
        self.tof_dirs_local = np.array(dirs)
        spread = math.radians(robot.side_tof_fov_deg) / 2 * 0.75
        self.side_offsets = np.linspace(-spread, spread, SIDE_RAYS)

        # Nominal values so domain randomization always starts from the spec.
        self._nominal = {
            "gainprm": m.actuator_gainprm.copy(),
            "biasprm": m.actuator_biasprm.copy(),
            "forcerange": m.actuator_forcerange.copy(),
            "mass": m.body_mass.copy(),
            "friction": m.geom_friction.copy(),
        }

        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(OBS_DIM,), dtype=np.float32)

        self._renderers = {}
        self._ray_geom = np.zeros(TOF_ZONES * TOF_ZONES, dtype=np.int32)
        self._ray_dist = np.zeros(TOF_ZONES * TOF_ZONES)
        self.walker = None

    # ------------------------------------------------------------------ setup

    def _randomize_physics(self):
        m, n, rng = self.model, self._nominal, self.np_random
        m.actuator_gainprm[:] = n["gainprm"]
        m.actuator_biasprm[:] = n["biasprm"]
        m.actuator_forcerange[:] = n["forcerange"]
        m.body_mass[:] = n["mass"]
        m.geom_friction[:] = n["friction"]
        if not self.randomize:
            return
        for a in (0, 1):  # motors are never perfectly matched
            m.actuator_forcerange[a] *= rng.uniform(0.75, 1.15)
            kv = n["gainprm"][a, 0] * rng.uniform(0.8, 1.2)
            m.actuator_gainprm[a, 0] = kv
            m.actuator_biasprm[a, 2] = -kv
        m.body_mass[self.robot_body] *= rng.uniform(0.85, 1.2)
        grip = rng.uniform(0.6, 1.3)  # tile vs. rug vs. wood
        for g in self.wheel_geoms:
            m.geom_friction[g, 0] = n["friction"][g, 0] * grip

    def _blocked(self, x, y, margin=0.25):
        for idx, r in zip(self.obstacle_mocap, self.obstacle_radius):
            ox, oy = self.data.mocap_pos[idx, :2]
            if math.hypot(x - ox, y - oy) < r + margin:
                return True
        return False

    def _place_obstacles(self, keep_clear):
        placed = []
        for idx, r in zip(self.obstacle_mocap, self.obstacle_radius):
            for _ in range(200):
                p = self.np_random.uniform([-ROOM_HALF + r + 0.05] * 2, [HOLE_X[0] - r, ROOM_HALF - r - 0.05])
                if all(math.hypot(*(p - q)) > r + qr + 0.35 for q, qr in placed) and \
                   all(math.hypot(*(p - c)) > r + 0.45 for c in keep_clear):
                    break
            self.data.mocap_pos[idx, :2] = p
            placed.append((p, r))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        rng = self.np_random
        mujoco.mj_resetData(self.model, self.data)
        self._randomize_physics()

        robot_xy = rng.uniform([WALK_X[0], WALK_Y[0]], [WALK_X[1], WALK_Y[1]])
        robot_yaw = rng.uniform(-math.pi, math.pi)
        for _ in range(100):
            ang = rng.uniform(-math.pi, math.pi)
            person_xy = robot_xy + rng.uniform(0.8, 2.2) * np.array([math.cos(ang), math.sin(ang)])
            if WALK_X[0] < person_xy[0] < WALK_X[1] and WALK_Y[0] < person_xy[1] < WALK_Y[1]:
                break
        self.data.mocap_pos[:, :2] = 10.0  # park furniture while placing it
        self._place_obstacles([robot_xy, person_xy])

        q = self.data.qpos
        q[self.root_qpos:self.root_qpos + 3] = [*robot_xy, self.robot.body_z]
        q[self.root_qpos + 3:self.root_qpos + 7] = [math.cos(robot_yaw / 2), 0, 0, math.sin(robot_yaw / 2)]
        self.data.ctrl[self.head_pan_act] = 0.0
        self.data.ctrl[self.head_tilt_act] = 0.2
        self.detection = None

        self.walker = PersonWalker(rng, self._blocked, lambda: self.robot_pose()[0][:2])
        self.walker.reset(person_xy)
        self._sync_person()
        mujoco.mj_forward(self.model, self.data)

        self.steps = 0
        self.prev_action = np.zeros(2)
        self.last_seen = (0.0, 1.0, 0.0)  # sin(bearing), cos(bearing), distance
        self.time_since_seen = LOST_MEMORY_S
        return self._observe(), {}

    def _sync_person(self):
        w = self.walker
        self.data.mocap_pos[self.person_mocap] = [*w.pos, 0.0]
        self.data.mocap_quat[self.person_mocap] = [math.cos(w.heading / 2), 0, 0, math.sin(w.heading / 2)]

    # ---------------------------------------------------------------- sensors

    def robot_pose(self):
        q = self.data.qpos[self.root_qpos:self.root_qpos + 7]
        w, x, y, z = q[3:7]
        yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return q[:3].copy(), yaw

    def person_relative(self):
        """True planar distance and bearing (+ = to the robot's left) to the person."""
        pos, yaw = self.robot_pose()
        delta = self.walker.pos - pos[:2]
        return float(np.linalg.norm(delta)), _wrap(math.atan2(delta[1], delta[0]) - yaw)

    def _tof(self):
        d = self.data
        rot = d.site_xmat[self.tof_site].reshape(3, 3)
        vec = (self.tof_dirs_local @ rot.T).reshape(-1)
        mujoco.mj_multiRay(self.model, d, d.site_xpos[self.tof_site], vec, SENSOR_GEOMGROUP, 1,
                           -1, self._ray_geom, self._ray_dist, None, len(self.tof_dirs_local),
                           self.robot.tof_range)
        dist = np.where(self._ray_dist < 0, self.robot.tof_range, self._ray_dist)
        dist = dist * (1 + 0.02 * self.np_random.standard_normal(dist.shape))
        return np.clip(dist, 0, self.robot.tof_range) / self.robot.tof_range

    def _side(self):
        """Single-zone ToF in each "hand", angled outwards: covers the chest ToF's blind spots."""
        d, out = self.data, []
        _, yaw = self.robot_pose()
        for site, sign in zip(self.side_sites, (1, -1)):
            centre = yaw + sign * math.radians(self.robot.side_tof_yaw_deg)
            vec = np.array([[math.cos(centre + o), math.sin(centre + o), 0.0] for o in self.side_offsets])
            geom = np.zeros(SIDE_RAYS, dtype=np.int32)
            dist = np.zeros(SIDE_RAYS)
            mujoco.mj_multiRay(self.model, d, d.site_xpos[site], vec.reshape(-1), SENSOR_GEOMGROUP, 1,
                               -1, geom, dist, None, SIDE_RAYS, self.robot.tof_range)
            dist = np.where(dist < 0, self.robot.tof_range, dist)
            out.append(dist.min() * (1 + 0.02 * self.np_random.standard_normal()))
        return np.clip(out, 0, self.robot.tof_range) / self.robot.tof_range

    def _pan(self):
        return float(self.data.qpos[self.pan_qpos])

    def _cliff(self):
        d, out = self.data, []
        for s in self.cliff_sites:
            down = -d.site_xmat[s].reshape(3, 3)[:, 2]
            r = mujoco.mj_ray(self.model, d, d.site_xpos[s], down, SENSOR_GEOMGROUP, 1, -1, None)
            out.append(CLIFF_RANGE if r < 0 else min(r, CLIFF_RANGE))
        return np.array(out) / CLIFF_RANGE

    def _detect_person(self):
        """Simulates a camera person detector: field of view, occlusion, noise, misses.

        Returns (distance, bearing relative to the camera) or None.
        """
        dist, _ = self.person_relative()
        cam = self.data.cam_xpos[self.cam_id]
        rot = self.data.cam_xmat[self.cam_id].reshape(3, 3)
        local = rot.T @ (np.array([*self.walker.pos, 0.9]) - cam)
        forward, left = -local[2], -local[0]
        bearing = math.atan2(left, forward)
        if dist > PERSON_RANGE or forward <= 0 or abs(bearing) > math.radians(self.robot.camera_hfov_deg) / 2:
            return None
        target = np.array([*self.walker.pos, 0.5])
        geom = np.zeros(1, dtype=np.int32)
        mujoco.mj_ray(self.model, self.data, cam, target - cam, SENSOR_GEOMGROUP, 1, -1, geom)
        if geom[0] not in self.person_geoms or self.np_random.random() < 0.05:
            return None
        bearing += 0.03 * self.np_random.standard_normal()
        dist *= 1 + 0.06 * self.np_random.standard_normal()
        return dist, bearing

    def _aim_head(self):
        """Neck reflex: look at the person while visible, drift back to centre once lost."""
        pan_range = self.robot.pan_range
        if self.detection is not None:
            dist, bearing_cam = self.detection
            pan = np.clip(self._pan() + 0.8 * bearing_cam, -pan_range, pan_range)
            cam_z = self.data.cam_xpos[self.cam_id][2]
            self.data.ctrl[self.head_pan_act] = pan
            self.data.ctrl[self.head_tilt_act] = np.clip(math.atan2(1.2 - cam_z, max(dist, 0.3)), -0.4, 0.7)
        elif self.time_since_seen > 2.0:
            self.data.ctrl[self.head_pan_act] *= 0.9

    def _observe(self):
        det = self.detection = self._detect_person()
        if det is not None:
            dist, bearing_cam = det
            bearing = _wrap(bearing_cam + self._pan())  # relative to the body, via the pan servo
            self.last_seen = (math.sin(bearing), math.cos(bearing), min(dist, PERSON_RANGE) / PERSON_RANGE)
            self.time_since_seen = 0.0
        sens = self.data.sensordata
        accel = sens[0:3] + 0.05 * self.np_random.standard_normal(3)
        gyro = sens[3:6] + 0.01 * self.np_random.standard_normal(3)
        enc = sens[6:8] / self.robot.max_wheel_speed
        person = [float(det is not None), *self.last_seen,
                  min(self.time_since_seen, LOST_MEMORY_S) / LOST_MEMORY_S]
        obs = np.concatenate([
            self._tof(), self._cliff(), self._side(), [accel[0] / 10, accel[1] / 10, gyro[2] / 5],
            enc, person, [self._pan() / self.robot.pan_range], self.prev_action,
        ]).astype(np.float32)
        assert obs.shape == (OBS_DIM,)
        return obs

    # ------------------------------------------------------------------- step

    def _collided(self):
        d = self.data
        for c in d.contact[:d.ncon]:
            g1, g2 = c.geom1, c.geom2
            if self.is_robot_geom[g1] != self.is_robot_geom[g2]:
                other = g2 if self.is_robot_geom[g1] else g1
                if not self.is_floor_geom[other]:
                    return True
        return False

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=float), -1, 1)
        self.data.ctrl[:2] = action * self.robot.max_wheel_speed
        self._aim_head()
        for _ in range(self.frame_skip):
            mujoco.mj_step(self.model, self.data)
        collided = self._collided()
        self.walker.step(CONTROL_DT)
        self._sync_person()
        self.time_since_seen += CONTROL_DT
        self.steps += 1

        pos, _ = self.robot_pose()
        up = self.data.xmat[self.robot_body][8]
        fell = pos[2] < -0.05
        flipped = up < 0.5
        dist, bearing = self.person_relative()

        reward = math.exp(-((dist - self.follow_distance) / 0.4) ** 2) + 0.3 * math.cos(bearing)
        if dist < 0.45:
            reward -= 1.0  # too close: tripping hazard
        if collided:
            reward -= 3.0  # at -1 the policy learned that bumping furniture was worth it
        reward -= 0.05 * float(np.sum((action - self.prev_action) ** 2))
        terminated = fell or flipped
        if terminated:
            reward = -50.0
        self.prev_action = action

        obs = self._observe()
        info = {"distance": dist, "bearing": bearing, "collided": collided,
                "fell": bool(fell), "flipped": bool(flipped), "person_visible": bool(obs[OBS["person"]][0])}
        return obs, float(reward), terminated, self.steps >= self.max_steps, info

    # --------------------------------------------------------------- cameras

    def _render_camera(self, camera, width, height):
        renderer = self._renderers.get((width, height))
        if renderer is None:
            renderer = self._renderers[(width, height)] = mujoco.Renderer(self.model, height, width)
        renderer.update_scene(self.data, camera=camera)
        return renderer.render()

    def render(self, width=640, height=480):
        return self._render_camera("overhead", width, height)

    def take_photo(self, width=1280, height=720):
        """What the robot's own camera sees: the 'take a picture' command."""
        return self._render_camera("eye", width, height)

    def close(self):
        for renderer in self._renderers.values():
            renderer.close()
        self._renderers.clear()
