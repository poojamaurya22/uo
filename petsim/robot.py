"""Robot + house model, generated as MJCF so dimensions come from one place.

Every number in RobotSpec is chosen to match the planned real build
(see README "Hardware it mirrors"), so a policy trained here sees the
same geometry, speeds and sensor limits it will have on the real robot.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RobotSpec:
    # Body: ~15 x 12 x 6 cm chassis, 2S 18650 pack low in the base.
    chassis_half: tuple = (0.075, 0.06, 0.03)
    clearance: float = 0.008
    chassis_mass: float = 0.45
    head_half: tuple = (0.045, 0.05, 0.03)
    head_mass: float = 0.12
    # Drive: 2x N20 gear motors with encoders, 44 mm wheels with TPU tires.
    wheel_radius: float = 0.022
    wheel_half_width: float = 0.007
    track_half: float = 0.068
    wheel_mass: float = 0.02
    caster_radius: float = 0.008
    max_wheel_speed: float = 20.0  # rad/s -> ~0.44 m/s, capped below N20 300 RPM
    motor_kv: float = 0.05
    motor_torque: float = 0.08  # N*m, roughly an N20 1:100 near stall
    # Sensors.
    tof_fov_deg: float = 45.0  # VL53L5CX, 8x8 zones
    tof_tilt_deg: float = 10.0  # mounted pointing slightly up
    tof_range: float = 4.0
    camera_hfov_deg: float = 102.0  # Pi Camera Module 3 Wide
    camera_vfov_deg: float = 67.0


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


def build_xml(spec: RobotSpec = RobotSpec()) -> str:
    cx, cy, cz = spec.chassis_half
    hx, hy, hz = spec.head_half
    z0 = spec.clearance + cz  # chassis centre height when resting
    wheel_z = spec.wheel_radius - z0
    caster_z = spec.caster_radius - z0 + 0.002  # slightly raised so the wheels carry the load
    caster_x = cx - spec.caster_radius - 0.004
    fovy = spec.camera_vfov_deg

    return f"""
<mujoco model="petbot">
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
      <geom group="1" rgba=".95 .95 .97 1"/>
    </default>
  </default>
  <worldbody>
    <light pos="0 0 4" dir="0 0 -1" diffuse=".7 .7 .7" castshadow="true"/>
    <light pos="2 2 3" dir="-1 -1 -1" diffuse=".3 .3 .3" castshadow="false"/>
    <geom name="ground" type="plane" size="6 6 .1" pos="0 0 -0.6" rgba=".15 .15 .17 1"/>
    {_floor_and_walls()}

    <body name="robot" pos="0 0 {z0}" childclass="robot">
      <freejoint name="root"/>
      <geom name="chassis" type="box" size="{cx} {cy} {cz}" mass="{spec.chassis_mass}"/>
      <geom name="caster_front" type="sphere" size="{spec.caster_radius}"
            pos="{caster_x} 0 {caster_z}" mass="0.005" friction="0.02 0.005 0.0001"/>
      <geom name="caster_back" type="sphere" size="{spec.caster_radius}"
            pos="{-caster_x} 0 {caster_z}" mass="0.005" friction="0.02 0.005 0.0001"/>
      <site name="imu" pos="0 0 0" size="0.005"/>
      <site name="tof" pos="{cx} 0 0.005" size="0.004" rgba="1 .2 .2 1"/>
      <site name="cliff_l" pos="{cx - 0.005} {cy - 0.015} {-cz}" size="0.003"/>
      <site name="cliff_c" pos="{cx - 0.005} 0 {-cz}" size="0.003"/>
      <site name="cliff_r" pos="{cx - 0.005} {-cy + 0.015} {-cz}" size="0.003"/>
      <body name="wheel_left" pos="0 {spec.track_half} {wheel_z}">
        <joint name="wheel_left" type="hinge" axis="0 1 0" armature="0.0001" damping="0.0002"/>
        <geom type="cylinder" size="{spec.wheel_radius} {spec.wheel_half_width}"
              zaxis="0 1 0" mass="{spec.wheel_mass}" friction="1.2 0.01 0.001" rgba=".15 .15 .15 1"/>
      </body>
      <body name="wheel_right" pos="0 {-spec.track_half} {wheel_z}">
        <joint name="wheel_right" type="hinge" axis="0 1 0" armature="0.0001" damping="0.0002"/>
        <geom type="cylinder" size="{spec.wheel_radius} {spec.wheel_half_width}"
              zaxis="0 1 0" mass="{spec.wheel_mass}" friction="1.2 0.01 0.001" rgba=".15 .15 .15 1"/>
      </body>
      <body name="head" pos="0 0 {cz + hz + 0.004}">
        <joint name="head_tilt" type="hinge" axis="0 -1 0" range="-0.3 0.6" damping="0.01"/>
        <geom name="head" type="box" size="{hx} {hy} {hz}" mass="{spec.head_mass}"/>
        <geom name="eye_l" type="cylinder" size="0.012 0.002" pos="{hx} 0.022 0.004"
              zaxis="1 0 0" rgba=".1 .6 .9 1" contype="0" conaffinity="0"/>
        <geom name="eye_r" type="cylinder" size="0.012 0.002" pos="{hx} -0.022 0.004"
              zaxis="1 0 0" rgba=".1 .6 .9 1" contype="0" conaffinity="0"/>
        <camera name="eye" pos="{hx + 0.002} 0 -0.012" xyaxes="0 -1 0 0 0 1" fovy="{fovy}"/>
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

  <actuator>
    <velocity name="left" joint="wheel_left" kv="{spec.motor_kv}"
              ctrlrange="{-spec.max_wheel_speed} {spec.max_wheel_speed}"
              forcerange="{-spec.motor_torque} {spec.motor_torque}"/>
    <velocity name="right" joint="wheel_right" kv="{spec.motor_kv}"
              ctrlrange="{-spec.max_wheel_speed} {spec.max_wheel_speed}"
              forcerange="{-spec.motor_torque} {spec.motor_torque}"/>
    <position name="head_tilt" joint="head_tilt" kp="0.5" ctrlrange="-0.3 0.6"/>
  </actuator>

  <sensor>
    <accelerometer name="accel" site="imu"/>
    <gyro name="gyro" site="imu"/>
    <jointvel name="enc_left" joint="wheel_left"/>
    <jointvel name="enc_right" joint="wheel_right"/>
  </sensor>
</mujoco>
"""
