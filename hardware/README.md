# Building the real Wall-E (v0.1)

Everything here is generated from the same `RobotSpec` the simulation uses, so
the printed robot has the size, track layout, sensor positions and camera
height that the trained brain was tested with.

<img src="preview/assembly_front.png" alt="Assembled Wall-E, front" width="420"> <img src="preview/assembly_side.png" alt="Assembled Wall-E, side" width="420">

> **Status: first prototype, not yet printed.** The design is complete and
> every part exports cleanly, but nobody has built one yet. Print the
> [fit tests](#1-print-the-fit-tests-first) first, and expect to tweak a few
> sizes. That's normal for a v0.1.

## What you need to buy

About **$200–250** in total. Search the part names on Amazon, AliExpress,
Adafruit, SparkFun, Pololu or The Pi Hut. Prices are rough.

### Brains and senses

| Qty | Part | What it does | ~$ |
|---|---|---|---|
| 1 | **Raspberry Pi Zero 2 W** + 32 GB microSD | Main computer: camera, Wi-Fi, talking to the PC | 25 |
| 1 | **Raspberry Pi Camera Module 3 Wide** | The left eye | 35 |
| 1 | Pi **Zero** camera cable, **30 cm** | The Zero needs the narrow-end cable; 30 cm leaves slack for the neck | 3 |
| 1 | **Raspberry Pi Pico** | Real-time microcontroller: motors, sensors, **safety reflexes** | 4 |
| 1 | **VL53L5CX** 8×8 ToF breakout, 25.4 mm square (SparkFun Qwiic) | Chest depth sensor | 25 |
| 2 | **VL53L1X** ToF breakout, ~13 × 18 mm (Pololu) | Side sensors in the hands | 24 |
| 5 | **VL6180X** ToF breakout, ~13 × 18 mm (Pololu) | Cliff sensors: 3 front, 2 rear | 40 |
| 1 | **BMI270** or **MPU-6050** IMU breakout | Tilt / bump / picked-up detection | 5 |
| 2 | **INMP441** I2S microphone | Ears (under the lid) | 6 |
| 1 | **MAX98357A** I2S amplifier + **28 mm 8 Ω speaker** | Voice | 9 |
| 1 | 5 mm LED (any colour) + 220 Ω resistor | Right eye status light | 1 |

> Cheaper cliff sensors: 5 × **TCRT5000** IR modules (~$5) work too; the
> pockets fit modules up to ~13 × 18 mm.

### Movement

| Qty | Part | Notes | ~$ |
|---|---|---|---|
| 2 | **N20 gear motor, 6 V, 1:100, with magnetic encoder** | Must have a **3 mm D-shaft at least 9 mm long** | 12 |
| 1 | **DRV8833** dual motor driver | | 3 |
| 2 | **MG90S** servo (metal gears) | Neck pan + tilt. SG90 works, but MG90S lasts longer | 8 |

### Power

| Qty | Part | Notes | ~$ |
|---|---|---|---|
| 2 | **18650 Li-ion cells**, protected, from a reputable brand | Never use unbranded cells | 12 |
| 1 | **2 × 18650 holder** (series, with wires) | | 3 |
| 1 | **2S BMS** board | Protects the cells | 3 |
| 1 | **5 V 3 A buck converter** (mini) | Powers the Pi, Pico, sensors and servos | 3 |
| 1 | **INA219** breakout | Battery voltage / current, so it knows when to charge | 3 |
| 1 | Small slide or rocker switch | | 1 |
| 1 | 18650 charger | For v0.1 charge the cells outside; the dock comes later | 10 |

### Screws and bits

| Qty | Part | Used for |
|---|---|---|
| 4 | M3 × 40 bolt + nyloc nut + 2 washers | Idler and road-wheel axles |
| 12 | M3 × 10 screw (self-tapping into plastic is fine) | Lid (4), hands (4), scoop and lip (4) |
| 1 | M3 × 8 screw | Head tilt pivot |
| ~16 | M2 × 5 self-tapping screws | Camera (4), motor straps (4), eyes onto the head (4), spares |
| 4 | M2.5 × 6 screws | Pi Zero |
| 2 | M2 × 3 grub screw (optional) | Locks the drive sprockets on the motor shafts |
| | Hook-up wire, Dupont / JST connectors, heat-shrink, double-sided foam tape, Velcro | |

### Filament

| Material | Colour | Amount | For |
|---|---|---|---|
| PETG (or PLA) | Yellow | ~250 g | Body, lid, head |
| PETG (or PLA) | Grey | ~150 g | Wheels, scoop, lip, hands, neck, eyes |
| **TPU 95A** | Black | ~40 g | Track belts |

## Printing

All parts are already in print orientation and need **no supports**. Default
settings: 0.2 mm layers, 3 walls, 20% infill.

| File in `stl/` | Qty | Material | Notes |
|---|---|---|---|
| `body.stl` | 1 | PETG/PLA | Biggest part (120 × 110 × 97 mm), ~8 h |
| `lid.stl` | 1 | PETG/PLA | Prints top-down |
| `head.stl` | 1 | PETG/PLA | Plate down |
| `neck.stl` | 1 | PETG/PLA | 4 walls: it carries the head |
| `eye_camera.stl`, `eye_led.stl` | 1 each | PLA | Front face down. Paint or marker the lens recess black |
| `eye_cap.stl` | 2 | PLA | |
| `sprocket_drive.stl` | 2 | PETG | **100% infill** around the hub |
| `sprocket_idler.stl`, `road_wheel.stl` | 2 each | PETG | |
| `spacer.stl` | 4 | any | |
| `motor_strap.stl` | 2 | any | |
| `scoop_front.stl`, `lip_rear.stl` | 1 each | PETG/PLA | |
| `hand_left.stl`, `hand_right.stl` | 1 each | PETG/PLA | |
| `belt.stl` | 2 | **TPU 95A** | Slow (20–30 mm/s), no retraction or very little, 2 walls |

`preview/` has a picture of every part.

## Assembly

### 1. Print the fit tests first

Before the big parts, print **one `sprocket_drive`, one `motor_strap` and one
`belt`** (~2 h) and check:

- The sprocket pushes onto the N20 shaft firmly and doesn't wobble.
- The belt fits snugly over two sprockets held ~89 mm apart (axle to axle).
- Your sensor breakouts fit their pockets (the scoop pocket and hand recess are 13.3 × 18.4 mm).

If something is too tight or loose, change `fit` at the top of `walle.scad`
(or a board size under "bought components") and re-export, see
[Changing the design](#changing-the-design). Or ask Claude to do it.

### 2. Drive

1. Push each N20 motor through the square hole at the back of each side wall from
   the inside, until the gearbox sticks out **1 mm**. Screw a `motor_strap`
   across the two blocks on top of it (2 × M2).
2. Push a `sprocket_drive` onto each shaft, hub first (optional M2 grub screw).
3. Front and middle axles: an M3 × 40 bolt from inside the body, through the
   wall, a `spacer`, the `sprocket_idler` (front) or `road_wheel` (middle),
   a washer, then a nyloc nut. Snug, not tight: the wheels must spin freely.
4. Stretch a `belt` over the three wheels, lugs inwards. The front hole is
   slotted: slide the front axle forward to tension the belt, then tighten.

### 3. Sensors

1. **Cliff sensors**: one board in each pocket of `scoop_front` (3) and `lip_rear`
   (2), sensor facing down through the hole. Run the wires along the channels.
   Screw the scoop and lip to the bottom of the front and back walls (2 × M3
   each), wires through the middle hole.
2. **Chest ToF**: slide the VL53L5CX board down the two rails behind the chest window,
   sensor facing out.
3. **Hands**: a VL53L1X in each hand's recess, facing out; screw the hands to
   the sides (2 × M3 each), wires through the hole into the body.
4. **IMU**: tape it flat to the floor, near the middle.

### 4. Electronics inside the body

- **Pi Zero** on the 4 standoffs on the inside of the back wall.
- **Battery holder** on the floor in the middle (Velcro), with the BMS.
- **Pico, DRV8833, buck converter, INA219, amplifier**: double-sided foam tape on the
  floor and side walls.
- **Speaker** glued behind the grille; **microphones** taped under the lid's two
  small hole clusters, mic port facing the holes.
- **Charging contacts**: two 4 mm holes in the floor at the front, for later.

A wiring diagram comes with the firmware (next step).

### 5. Neck and head

1. Centre both servos before fitting them (power on, send 90°).
2. **Pan servo**: drop it into the lid's rectangular hole with the shaft end towards the back of
   the robot, and screw its tabs down.
3. Screw a round servo horn to the bottom of `neck`, then push it onto the pan servo.
4. **Tilt servo**: drop it into the top of the neck, shaft out to the left side, and screw
   the tabs (2 × M2, from the side).
5. Screw a single-arm horn to the `head`'s arm on the servo side, push it onto
   the tilt servo, and put the M3 × 8 pivot screw through the other arm into
   the neck.
6. **Camera** onto the 4 standoffs inside `eye_camera` (lens through the front
   hole), **LED** into `eye_led`. Screw both eyes onto the head plate (2 × M2
   each from below), then fit the `eye_cap`s.
7. Route the camera cable and tilt servo wires down the back of the neck, through
   the slot in the lid behind the servo. Leave a slack loop inside, because the neck turns ±86°.

### 6. Close up

Lid on, 4 × M3 screws. Done: a Wall-E with no software yet.

## Changing the design

All sizes come from `RobotSpec` in `petsim/robot.py`, plus a few hardware-only
numbers at the top of `walle.scad`. After changing either:

```bash
python scripts/build_hardware.py --previews
```

This needs [OpenSCAD](https://openscad.org). It regenerates `params.scad` and
every STL. Change the robot in `RobotSpec`, and both the simulation and the
printed parts follow, so you can retrain and re-test before printing.

## Not done yet

- Wiring diagram and the Pico firmware (motors, sensors, safety reflexes)
- Pi software: camera → person detector → trained brain → Pico
- Charging dock
- Voice: microphones → speech-to-text → Claude → speaker
