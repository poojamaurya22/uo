# PetSim: simulate the companion robot before building it

A physics simulation of a small companion robot (a "pet") that follows you
around the house. Train and test its behaviour here first, then buy parts and
build the real one once the idea works.

Everything is open source: [MuJoCo](https://mujoco.org) (physics),
[Gymnasium](https://gymnasium.farama.org) (environment API) and
[Stable-Baselines3](https://stable-baselines3.readthedocs.io) (reinforcement learning).

![Left: overhead view of the room. Right: what the robot's camera sees.](docs/preview.png)

## What's simulated

**The robot** is about 15 × 12 × 13 cm and 0.6 kg. Each part mirrors the planned real build:

| Simulated | Real part it stands in for |
|---|---|
| Differential drive, 44 mm wheels, velocity-controlled, torque-limited | 2 × N20 gear motors with encoders, DRV8833 driver |
| Two ball casters | Printed ball casters |
| 8 × 8 depth grid, 45° field of view, 4 m range, ±2% noise | VL53L5CX multi-zone ToF |
| 3 downward distance sensors on the front edge | VL6180X / TCRT5000 cliff sensors |
| Accelerometer + gyro | BMI270 IMU |
| Wheel speed | Motor encoders |
| 102° camera on a tilting head, photos via `env.take_photo()` | Pi Camera Module 3 Wide + SG90 tilt servo |
| Person detector: field of view, occlusion, distance noise, 5% missed frames | MediaPipe/YOLO running on the camera feed |

All dimensions are in `RobotSpec` (`petsim/robot.py`). Change them there to try a
different design, such as bigger wheels or a wider ToF.

**The house** is a 4 × 4 m room with a **stairwell opening** the robot must not
drive into. Furniture is placed at random each episode: a sofa, a cabinet, a plant pot,
thin chair legs and a low box.

**You** are a person who walks between random spots at varying speeds and
sometimes stops. You wait if the robot is in your way.

**Domain randomization** varies the robot's physics each episode: motor strength
(±20%, left and right differ), mass and floor grip (tile vs. rug). This makes a
trained policy robust enough to have a chance on real hardware.

## The task: follow me

- **Action**: left and right wheel speeds, in −1 … 1.
- **Observation** (79 numbers): the 8×8 depth grid, 3 cliff readings, the IMU,
  wheel speeds, the person detector's output (seen?, direction, distance,
  seconds since last seen) and the previous action. All of these come from
  real sensors, so the same policy can run on the robot.
- **Reward**: staying about 1 m from you and facing you. It's penalized for
  bumping into things, getting closer than 0.45 m (a tripping hazard) and
  jerky driving. Falling down the stairs ends the episode with a big penalty.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q tests                          # sanity checks (~10 s)
python scripts/evaluate.py --controller baseline   # score the hand-written controller
python scripts/watch.py --controller baseline      # live 3D view (macOS: mjpython)
python scripts/train.py --steps 2000000            # train (~40 min on 4 cores)
python scripts/evaluate.py --controller runs/ppo/best_model.zip --video follow.mp4 --photo photo.png
```

On a server with no screen, set `MUJOCO_GL=egl` (NVIDIA) or
`MUJOCO_GL=osmesa` (CPU) before saving videos or photos.

`evaluate.py` reports the numbers that decide whether the idea works:

```
time at 0.6-1.4 m:      how much of the time it's at a good following distance
person in view:         how often its camera can see you
too close (<0.45 m):    tripping-hazard time
collision steps / min:  bumping into furniture
falls / flips:          stairs
```

## Layout

```
petsim/robot.py      robot + house model (MJCF generated from RobotSpec)
petsim/env.py        Gymnasium environment: sensors, person, reward
petsim/baseline.py   hand-written follow controller (yardstick + safe fallback)
scripts/train.py     PPO training
scripts/evaluate.py  metrics, videos, robot-camera photos
scripts/watch.py     live 3D viewer
tests/               physics and sensor sanity checks
```

## Roadmap

1. **Follow me**: done, and the current task.
2. **Hardware questions to answer in sim**: Is one forward ToF enough, or do you
   need side sensors? (The baseline's bumps suggest side sensors help.) How
   much does camera field of view matter? Is the robot fast enough?
3. **More behaviours**: "come here" (go to a voice-call location), return to the
   charging dock, explore and map rooms, react to being picked up (IMU).
4. **Voice and memory**: a speech + Claude layer that turns "take a picture" or
   "follow me" into these behaviours. It runs on a PC, separate from the policy.
5. **Real build**: same observation vector, read from real sensors on a
   Pi Zero 2 W + microcontroller, running the exported policy.

Known simplifications: one room, walls and furniture are simple shapes, and the
person can pass through furniture (but not through the robot).
