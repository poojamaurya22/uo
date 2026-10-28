"""Wall-E style robot + house model, generated as MJCF so dimensions come from one place.

Every number in RobotSpec is chosen to match the planned real build
(see README "Hardware it mirrors"), so a policy trained here sees the
same geometry, speeds and sensor limits it will have on the real robot.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RobotSpec:
    # Body: ~12 x 11 x 10 cm box, 2S 18650 pack low inside.
    body_half: tuple = (0.06, 0.055, 0.05)
    clearance: float = 0.012
    body_mass: float = 0.55
    # Tracks: 3 coupled road wheels per side (a printed TPU track in reality),
    # the middle one driven by an N20 gear motor with encoder.
    wheel_radius: float = 0.02
    wheel_spacing: float = 0.045
    track_half_width: float = 0.011
    track_gap: float = 0.006  # between body side and track
    wheel_mass: float = 0.015
    max_wheel_speed: float = 20.0  # rad/s -> 0.4 m/s
    motor_kv: float = 0.05
    motor_torque: float = 0.12  # N*m, N20 1:100 near stall
    # Neck (pan + tilt servos) and binocular head; camera in the left eye.
    neck_height: float = 0.06
    eye_radius: float = 0.022
    eye_half_length: float = 0.022
    head_mass: float = 0.1
    pan_range: float = 1.5  # rad, ~ +/-86 degrees
    # Sensors.
    tof_fov_deg: float = 45.0  # VL53L5CX 8x8 in the chest
    tof_tilt_deg: float = 10.0
    tof_range: float = 4.0
    side_tof_yaw_deg: float = 55.0  # VL53L1X in each "hand"
    side_tof_fov_deg: float = 27.0
    camera_hfov_deg: float = 102.0  # Pi Camera Module 3 Wide
    camera_vfov_deg: float = 67.0

    @property
    def track_y(self):
        return self.body_half[1] + self.track_gap + self.track_half_width

    @property
    def body_z(self):
        return self.clearance + self.body_half[2]


# House layout: a 4 x 4 m room raised above the ground, with a stairwell
# opening against the +x wall. The robot must never drive into it.
ROOM_HALF = 2.0
HOLE_X = (1.4, ROOM_HALF)
HOLE_Y = (-0.6, 0.6)

# Furniture, placed at random each episode: (name, geom type, size, rgba).
OBSTACLES = [
    ("sofa", "box", (0.40, 0.20, 0.20), ".45 .3 .25 1"),
    ("cabinet", "box", (0.25, 0.25, 0.30), ".6 .55 .45 1"),
    ("plant_pot", "cylinder", (0.15, 0.18), ".3 .5 .3 1"),
    ("chair_leg_a", "cylinder", (0.02, 0.22), ".35 .25 .2 1"),
    ("chair_leg_b", "cylinder", (0.02, 0.22), ".35 .25 .2 1"),
    ("box", "box", (0.12, 0.12, 0.08), ".7 .6 .3 1"),
]

# Geom groups: 0 = house, 1 = robot, 2 = person. Ray sensors skip group 1.
SENSOR_GEOMGROUP = np.array([1, 0, 1, 0, 0, 0], dtype=np.uint8)

ROBOT_YELLOW = ".85 .62 .15 1"
ROBOT_GREY = ".35 .35 .37 1"


def _floor_and_walls() -> str:
    r, t = ROOM_HALF, 0.05
    hx0, hx1 = HOLE_X
    hy0, hy1 = HOLE_Y
    floor = []
    # Floor slabs (top surface at z=0) surrounding the stairwell hole.
    slabs = [
        ((-r + hx0) / 2, 0, (hx0 + r) / 2, r),
        ((hx0 + hx1) / 2, (hy1 + r) / 2, (hx1 - hx0) / 2, (r - hy1) / 2),
        ((hx0 + hx1) / 2, (hy0 - r) / 2, (hx1 - hx0) / 2, (r + hy0) / 2),
    ]
    for i, (cx, cy, sx, sy) in enumerate(slabs):
        floor.append(
            f'<geom name="floor{i}" type="box" pos="{cx} {cy} -0.05" '
            f'size="{sx} {sy} 0.05" material="floor"/>'
        )
    walls = [
        (0, r + t, r + t, t),
        (0, -r - t, r + t, t),
        (r + t, 0, t, r),
        (-r - t, 0, t, r),
    ]
    for i, (cx, cy, sx, sy) in enumerate(walls):
        floor.append(
            f'<geom name="wall{i}" type="box" pos="{cx} {cy} 0.3" '
            f'size="{sx} {sy} 0.3" rgba=".85 .82 .78 1"/>'
        )
    return "\n    ".join(floor)


def _obstacles() -> str:
    out = []
    for name, kind, size, rgba in OBSTACLES:
        height = size[-1]
        size_str = " ".join(str(s) for s in size)
        out.append(
            f'<body name="{name}" mocap="true" pos="0 0 {height}">'
            f'<geom name="{name}" type="{kind}" size="{size_str}" rgba="{rgba}"/>'
            f"</body>"
        )
    return "\n    ".join(out)


def _track(spec: RobotSpec, side: str, sign: int) -> str:
    """One track: three road wheels coupled by equality constraints + a cosmetic belt."""
    y = sign * spec.track_y
    z = spec.wheel_radius - spec.body_z
    r, w = spec.wheel_radius, spec.track_half_width
    reach = spec.wheel_spacing + r + 0.003
    wheels = []
    for name, x in (("rear", -spec.wheel_spacing), ("mid", 0.0), ("front", spec.wheel_spacing)):
        wheels.append(
            f'<body name="wheel_{side}_{name}" pos="{x} {y} {z}">'
            f'<joint name="wheel_{side}_{name}" type="hinge" axis="0 1 0" armature="0.0001" damping="0.0002"/>'
            f'<geom type="cylinder" size="{r} {w * 0.9}" zaxis="0 1 0" mass="{spec.wheel_mass}" '
            f'friction="1.2 0.01 0.001" rgba=".12 .12 .12 1"/></body>'
        )
    belt = (
        f'<geom name="track_{side}" type="box" size="{reach} {w} {r + 0.003}" pos="0 {y} {z}" '
        f'rgba=".2 .2 .2 1" contype="0" conaffinity="0" mass="0"/>'
    )
    return belt + "\n      ".join(wheels)


def build_xml(spec: RobotSpec = RobotSpec()) -> str:
    bx, by, bz = spec.body_half
    er, el = spec.eye_radius, spec.eye_half_length
    fovy = spec.camera_vfov_deg
    side_yaw = np.radians(spec.side_tof_yaw_deg)
    sx, sy = np.cos(side_yaw), np.sin(side_yaw)

    return f"""
<mujoco model="walle">
  <compiler angle="radian"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <visual><global offwidth="1280" offheight="720"/></visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1=".62 .55 .45"
             rgb2=".56 .5 .4" width="256" height="256"/>
    <material name="floor" texture="grid" texrepeat="6 6" texuniform="true"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1=".5 .6 .7"
             rgb2=".1 .1 .15" width="256" height="256"/>
  </asset>
  <default>
    <default class="robot">
      <geom group="1" rgba="{ROBOT_YELLOW}"/>
    </default>
  </default>
  <worldbody>
    <light pos="0 0 4" dir="0 0 -1" diffuse=".7 .7 .7" castshadow="true"/>
    <light pos="2 2 3" dir="-1 -1 -1" diffuse=".3 .3 .3" castshadow="false"/>
    <geom name="ground" type="plane" size="6 6 .1" pos="0 0 -0.6" rgba=".15 .15 .17 1"/>
    {_floor_and_walls()}

    <body name="robot" pos="0 0 {spec.body_z}" childclass="robot">
      <freejoint name="root"/>
      <geom name="body" type="box" size="{bx} {by} {bz}" mass="{spec.body_mass}"/>
      <geom name="chest_panel" type="box" size="0.002 {by * 0.7} {bz * 0.45}" pos="{bx} 0 {bz * 0.3}"
            rgba="{ROBOT_GREY}" contype="0" conaffinity="0" mass="0"/>
      <geom name="scoop" type="box" size="0.008 {by * 0.9} 0.008" pos="{bx + 0.006} 0 {-bz + 0.004}"
            rgba="{ROBOT_GREY}" mass="0.01"/>
      <geom name="hand_l" type="box" size="0.012 0.008 0.01" pos="{bx - 0.008} {by + 0.004} {-0.01}"
            rgba="{ROBOT_GREY}" mass="0.005"/>
      <geom name="hand_r" type="box" size="0.012 0.008 0.01" pos="{bx - 0.008} {-by - 0.004} {-0.01}"
            rgba="{ROBOT_GREY}" mass="0.005"/>
      <site name="imu" pos="0 0 0" size="0.005"/>
      <site name="tof" pos="{bx + 0.002} 0 {-bz * 0.35}" size="0.005" rgba="1 .2 .2 1"/>
      <site name="side_l" pos="{bx + 0.004} {by + 0.004} -0.01" zaxis="{sx} {sy} 0" size="0.004" rgba="1 .2 .2 1"/>
      <site name="side_r" pos="{bx + 0.004} {-by - 0.004} -0.01" zaxis="{sx} {-sy} 0" size="0.004" rgba="1 .2 .2 1"/>
      <site name="cliff_l" pos="{bx + 0.01} {by * 0.75} {-bz}" size="0.003"/>
      <site name="cliff_c" pos="{bx + 0.01} 0 {-bz}" size="0.003"/>
      <site name="cliff_r" pos="{bx + 0.01} {-by * 0.75} {-bz}" size="0.003"/>
      {_track(spec, "left", 1)}
      {_track(spec, "right", -1)}

      <body name="neck" pos="{-bx * 0.3} 0 {bz}">
        <joint name="head_pan" type="hinge" axis="0 0 1" range="{-spec.pan_range} {spec.pan_range}" damping="0.004"/>
        <geom name="neck" type="capsule" fromto="0 0 0 0 0 {spec.neck_height}" size="0.009"
              rgba="{ROBOT_GREY}" mass="0.03"/>
        <body name="head" pos="0.01 0 {spec.neck_height + er * 0.6}">
          <joint name="head_tilt" type="hinge" axis="0 -1 0" range="-0.4 0.7" damping="0.004"/>
          <geom name="eye_l" type="cylinder" size="{er} {el}" pos="0 {er + 0.004} 0" zaxis="1 0 0"
                rgba="{ROBOT_GREY}" mass="{spec.head_mass / 2}"/>
          <geom name="eye_r" type="cylinder" size="{er} {el}" pos="0 {-er - 0.004} 0" zaxis="1 0 0"
                rgba="{ROBOT_GREY}" mass="{spec.head_mass / 2}"/>
          <geom name="lens_l" type="cylinder" size="{er * 0.6} 0.002" pos="{el} {er + 0.004} 0"
                zaxis="1 0 0" rgba=".05 .05 .08 1" contype="0" conaffinity="0" mass="0"/>
          <geom name="lens_r" type="cylinder" size="{er * 0.6} 0.002" pos="{el} {-er - 0.004} 0"
                zaxis="1 0 0" rgba=".05 .05 .08 1" contype="0" conaffinity="0" mass="0"/>
          <camera name="eye" pos="{el + 0.003} {er + 0.004} 0" xyaxes="0 -1 0 0 0 1" fovy="{fovy}"/>
        </body>
      </body>
    </body>

    <body name="person" mocap="true" pos="1 0 0">
      <geom name="person_legs" type="capsule" fromto="0 0 0.15 0 0 0.9" size="0.13"
            group="2" rgba=".25 .35 .6 1"/>
      <geom name="person_torso" type="capsule" fromto="0 0 1.0 0 0 1.42" size="0.18"
            group="2" rgba=".8 .35 .3 1"/>
      <geom name="person_head" type="sphere" pos="0 0 1.66" size="0.11"
            group="2" rgba=".85 .7 .6 1"/>
    </body>

    {_obstacles()}

    <camera name="overhead" pos="0 -3.2 4.2" xyaxes="1 0 0 0 0.79 0.62" fovy="55"/>
  </worldbody>

  <equality>
    <joint joint1="wheel_left_rear" joint2="wheel_left_mid" polycoef="0 1 0 0 0"/>
    <joint joint1="wheel_left_front" joint2="wheel_left_mid" polycoef="0 1 0 0 0"/>
    <joint joint1="wheel_right_rear" joint2="wheel_right_mid" polycoef="0 1 0 0 0"/>
    <joint joint1="wheel_right_front" joint2="wheel_right_mid" polycoef="0 1 0 0 0"/>
  </equality>

  <actuator>
    <velocity name="left" joint="wheel_left_mid" kv="{spec.motor_kv}"
              ctrlrange="{-spec.max_wheel_speed} {spec.max_wheel_speed}"
              forcerange="{-spec.motor_torque} {spec.motor_torque}"/>
    <velocity name="right" joint="wheel_right_mid" kv="{spec.motor_kv}"
              ctrlrange="{-spec.max_wheel_speed} {spec.max_wheel_speed}"
              forcerange="{-spec.motor_torque} {spec.motor_torque}"/>
    <position name="head_pan" joint="head_pan" kp="0.3" ctrlrange="{-spec.pan_range} {spec.pan_range}"
              forcerange="-0.15 0.15"/>
    <position name="head_tilt" joint="head_tilt" kp="0.3" ctrlrange="-0.4 0.7" forcerange="-0.15 0.15"/>
  </actuator>

  <sensor>
    <accelerometer name="accel" site="imu"/>
    <gyro name="gyro" site="imu"/>
    <jointvel name="enc_left" joint="wheel_left_mid"/>
    <jointvel name="enc_right" joint="wheel_right_mid"/>
  </sensor>
</mujoco>
"""
