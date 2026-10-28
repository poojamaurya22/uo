// Printable Wall-E companion robot, v0.1.
//
// Dimensions come from params.scad, generated from the simulation's RobotSpec,
// so the printed robot matches the one the brain was trained on.
//
// Render one part:   openscad -D 'part="body"' -o body.stl walle.scad
// Or build all STLs: python scripts/build_hardware.py
//
// Coordinates: x forward, y left, z up. Body origin = centre of the body's
// footprint, on its underside. All sizes in mm.

include <params.scad>

part = "assembly";
$fn = 48;

// --------------------------------------------------------------- tolerances
fit = 0.3;  // clearance for parts that slide together (tune for your printer)
wall = 2.4;
floor_t = 2.4;
lid_t = 3;

// ------------------------------------------------------- bought components
// Measure yours and adjust if they differ.
n20 = [12, 10];              // N20 gearbox cross-section (w x h)
n20_shaft_d = 3; n20_shaft_flat = 2.5;
n20_len = 34;                // gearbox + motor + encoder
n20_protrude = 1;            // push the motor in until its gearbox pokes out of the side wall this much
sg90 = [22.8, 12.2, 22.7];   // body: length, width, height (shaft direction)
sg90_tab_len = 32.4; sg90_tab_t = 2.5; sg90_tab_z = 15.9; sg90_tab_hole = 27.8;
sg90_shaft_from_end = 5.9;
pi_holes = [58, 49];         // Raspberry Pi 5, M2.5
pi_z = 60;                   // centre of the Pi's holes above the body's underside (on the back wall)
battery_bay = [78, 84];      // two 2 x 18650 holders side by side (2S2P), x by y
battery_x = 8;               // bay centre: clear of the motors at the back, the ToF rails at the front
dc_jack_d = 8;               // panel DC barrel jack (5.5 x 2.1 mm) for plug-in charging
switch_cut = [19, 13];       // KCD1 mini rocker switch cutout, y by z
pogo_cut = [8, 5];           // 2-pin magnetic pogo connector (2.54 mm pitch), y by z: glued in
cam_holes = [21, 12.5];      // Pi Camera Module 3, M2
cam_lens_offset = -1.2;      // lens centre below the hole-pattern centre
tof_board = [25.4, 25.4];    // VL53L5CX breakout (SparkFun Qwiic size)
side_board = [12.7, 17.8];   // VL53L1X breakout (Pololu size)
cliff_board = [12.7, 17.8];  // VL6180X breakout (Pololu size)
speaker_d = 28;

// ------------------------------------------------------------ derived sizes
axle_z = wheel_r - clearance;          // wheel axles, above the body's underside
belt_t = 2;
rp = wheel_r - belt_t;                 // wheel radius under the belt
lug = [3.2, 8, 2];                     // belt drive lugs: along, across, height
sprocket_teeth = 14;
pitch = 2 * PI * rp / sprocket_teeth;
belt_lugs = round((4 * wheel_spacing_nominal + 2 * PI * rp) / pitch);
belt_len = belt_lugs * pitch;
spacing = (belt_len - 2 * PI * rp) / 4;    // half the distance between front and rear axles
flange = 1.2;
wheel_w = track_w + 2 * flange;
track_y = body_w / 2 + track_gap + track_w / 2;
wheel_y0 = track_y - wheel_w / 2;          // inner face of the wheels
shell_h = body_h - lid_t;
neck_base_z = 13;      // pan servo horn top, above the lid
plate_z = 24;          // head plate above the tilt axis (clears the tilt servo block when tilting)
pivot_h = eye_centre_above_lid - eye_r - 3 - plate_z - neck_base_z;  // tilt axis above the neck base
assert(pivot_h >= 17, "neck too short for the tilt servo: raise RobotSpec.neck_height");

echo(str("belt: ", belt_lugs, " lugs, pitch ", pitch, " mm, axle spacing ", 2 * spacing, " mm"));

// ------------------------------------------------------------------ helpers
module rbox(size, r) {  // box with rounded vertical edges, sitting on z=0, centred in x/y
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (size[0] / 2 - r), sy * (size[1] / 2 - r), 0]) cylinder(r = r, h = size[2]);
}

module board_pocket(board, depth, window) {  // a PCB pocket, sensor facing -z through a window
    translate([0, 0, -0.01]) cylinder(d = window, h = 20, center = true);
    translate([-board[0] / 2 - fit, -board[1] / 2 - fit, 0]) cube([board[0] + 2 * fit, board[1] + 2 * fit, depth]);
}

// --------------------------------------------------------------- body shell
strap_dx = n20[0] / 2 + fit + 2;  // cradle blocks either side of the motor
module motor_cradle(side) {  // two blocks the motor sits between; motor_strap screws across the top
    y_in = side * (body_w / 2 - wall);
    for (dx = [-1, 1])
        translate([-spacing + dx * strap_dx, y_in - side * 11, 0]) difference() {
            translate([-2, -10, 0]) cube([4, 20, axle_z + n20[1] / 2 + fit]);
            translate([0, 0, 2]) cylinder(d = 1.8, h = 20);
        }
}

module motor_strap() {
    difference() {
        translate([-strap_dx - 3, -4, 0]) cube([2 * strap_dx + 6, 8, 2]);
        for (dx = [-1, 1]) translate([dx * strap_dx, 0, -1]) cylinder(d = 2.3, h = 4);
    }
}

module tof_rail(sy) {  // one of two slotted rails holding the chest ToF board 2 mm behind the window
    x_wall = body_l / 2 - wall;
    y_edge = sy * tof_board[0] / 2;
    difference() {
        translate([x_wall - 6, y_edge - (sy > 0 ? 1.5 : 3.5), floor_t]) cube([6, 5, tof_z + tof_board[1] / 2 - floor_t]);
        translate([x_wall - 2 - 1.9, y_edge - (sy > 0 ? 2 : 0) - sy * fit, tof_z - tof_board[1] / 2])
            cube([1.9, 2 + fit, 40]);
    }
}

module body() {
    difference() {
        union() {
            difference() {
                rbox([body_l, body_w, shell_h], 6);
                translate([0, 0, floor_t]) rbox([body_l - 2 * wall, body_w - 2 * wall, shell_h], 6 - wall);
            }
            // lid screw posts
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx * (body_l / 2 - wall - 3.5), sy * (body_w / 2 - wall - 3.5), 0])
                    cylinder(d = 8, h = shell_h);
            for (side = [-1, 1]) motor_cradle(side);
            // Pi Zero standoffs on the rear wall
            for (sy = [-1, 1], sz = [-1, 1])
                translate([-body_l / 2 + wall, sy * pi_holes[0] / 2, pi_z + sz * pi_holes[1] / 2])
                    rotate([0, 90, 0]) cylinder(d = 5, h = 5);
            // rails holding the chest ToF board, sensor looking out through the window
            for (sy = [-1, 1]) tof_rail(sy);
            // low fence keeping the battery holders in place (plus Velcro)
            translate([battery_x, 0, 0]) difference() {
                rbox([battery_bay[0] + 2 * fit + 4, battery_bay[1] + 2 * fit + 4, floor_t + 5], 2);
                translate([0, 0, floor_t]) rbox([battery_bay[0] + 2 * fit, battery_bay[1] + 2 * fit, 10], 1);
                for (sx = [-1, 1]) translate([sx * battery_bay[0] / 2, 0, floor_t + 3]) cube([10, 30, 6], center = true);
            }
        }
        // lid screw holes (M3, self-tapping)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (body_l / 2 - wall - 3.5), sy * (body_w / 2 - wall - 3.5), shell_h - 14])
                cylinder(d = 2.6, h = 15);
        // drive motor gearboxes pass through the side walls
        for (side = [-1, 1])
            translate([-spacing, side * body_w / 2, axle_z])
                cube([n20[0] + 2 * fit, 4 * wall, n20[1] + 2 * fit], center = true);
        // idler (front, slotted to tension the belt) and road wheel (middle) axles, M3
        for (side = [-1, 1]) {
            translate([0, side * body_w / 2, axle_z]) rotate([90, 0, 0]) cylinder(d = 3.3, h = 4 * wall, center = true);
            hull() for (dx = [-1.5, 1.5])
                translate([spacing + dx, side * body_w / 2, axle_z]) rotate([90, 0, 0]) cylinder(d = 3.3, h = 4 * wall, center = true);
        }
        // Pi Zero standoff holes
        for (sy = [-1, 1], sz = [-1, 1])
            translate([-body_l / 2, sy * pi_holes[0] / 2, pi_z + sz * pi_holes[1] / 2])
                rotate([0, 90, 0]) cylinder(d = 2.2, h = 30, center = true);
        // chest: ToF window and speaker grille
        translate([body_l / 2, 0, tof_z]) cube([4 * wall, 12, 10], center = true);
        for (gy = [-12:4:12], gz = [-12:4:12])
            if (gy * gy + gz * gz <= 12 * 12)
                translate([body_l / 2, gy, 72 + gz]) rotate([0, 90, 0]) cylinder(d = 2.4, h = 4 * wall, center = true);
        // hand mounts (side ToFs): 2 x M3 + a wire hole, on each side near the front
        for (side = [-1, 1]) {
            for (dx = [-6, 6])
                translate([body_l / 2 - 14 + dx, side * body_w / 2, side_tof_z]) rotate([90, 0, 0])
                    cylinder(d = 2.6, h = 4 * wall, center = true);
            translate([body_l / 2 - 14, side * body_w / 2, side_tof_z + 7]) rotate([90, 0, 0])
                cylinder(d = 5, h = 4 * wall, center = true);
        }
        // scoop (front) and lip (rear) mounts: 2 x M3 each, plus a wire hole
        for (sx = [-1, 1]) {
            for (dy = [-20, 20])
                translate([sx * body_l / 2, dy, 9]) rotate([0, 90, 0]) cylinder(d = 2.6, h = 4 * wall, center = true);
            translate([sx * body_l / 2, 0, 9]) rotate([0, 90, 0]) cylinder(d = 6, h = 4 * wall, center = true);
        }
        // back wall: charging socket, power switch, and air intake behind the Pi
        translate([-body_l / 2, -30, 22]) rotate([0, 90, 0]) cylinder(d = dc_jack_d, h = 4 * wall, center = true);
        translate([-body_l / 2, 30, 24]) cube([4 * wall, switch_cut[0], switch_cut[1]], center = true);
        for (dy = [-20 : 6 : 20]) translate([-body_l / 2, dy, pi_z]) cube([4 * wall, 3, 24], center = true);
    }
}

// ---------------------------------------------------------------------- lid
pan_x = neck_x;  // pan servo shaft position
module lid() {
    difference() {
        union() {
            rbox([body_l, body_w, lid_t], 6);
            // locating lip that drops inside the shell
            translate([0, 0, -3]) difference() {
                rbox([body_l - 2 * wall - 2 * fit, body_w - 2 * wall - 2 * fit, 3.5], 6 - wall);
                translate([0, 0, -1]) rbox([body_l - 4 * wall, body_w - 4 * wall, 5], 3);
                for (sx = [-1, 1], sy = [-1, 1])
                    translate([sx * (body_l / 2 - wall - 3.5), sy * (body_w / 2 - wall - 3.5), -1]) cylinder(d = 9, h = 5);
            }
        }
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (body_l / 2 - wall - 3.5), sy * (body_w / 2 - wall - 3.5), -5]) {
                cylinder(d = 3.4, h = 20);
                translate([0, 0, 5 + lid_t - 1.8]) cylinder(d1 = 3.4, d2 = 6.6, h = 1.81);
            }
        // pan servo: drops in from above, tabs rest on the lid
        translate([pan_x - sg90_shaft_from_end + sg90[0] / 2, 0, 0]) {
            cube([sg90[0] + 2 * fit, sg90[1] + 2 * fit, 20], center = true);
            for (sx = [-1, 1]) translate([sx * sg90_tab_hole / 2, 0, -5]) cylinder(d = 1.8, h = 20);
        }
        // camera ribbon + tilt servo cable, behind the neck
        translate([pan_x - 20, 0, 0]) cube([4, 18, 20], center = true);
        // two I2S microphones under the lid, listening through small holes
        for (sy = [-1, 1]) for (d = [[0, 0], [2.5, 0], [-2.5, 0], [0, 2.5], [0, -2.5]])
            translate([20 + d[0], sy * 35 + d[1], -5]) cylinder(d = 1.2, h = 20);
        // vents above the Pi 5's fan, either side of the cable slot
        for (sy = [-1, 1], dy = [14 : 6 : 44]) translate([-body_l / 2 + 12, sy * dy, 0]) cube([14, 3, 20], center = true);
        // decorative hatch lines
        for (dy = [-46, -24, 24, 46]) translate([25, dy, lid_t - 0.6]) cube([40, 0.8, 2], center = true);
    }
}

// ----------------------------------------------------------- track system
function stadium(s) =  // point and outward angle at arc length s along the belt's inner surface
    let(L = belt_len, a = 2 * spacing, c = PI * rp, t = s % L)
    t < a ? [-spacing + t, -rp, -90] :
    t < a + c ? let(th = -90 + (t - a) / rp * 180 / PI) [spacing + rp * cos(th), rp * sin(th), th] :
    t < 2 * a + c ? [spacing - (t - a - c), rp, 90] :
    let(th = 90 + (t - 2 * a - c) / rp * 180 / PI) [-spacing + rp * cos(th), rp * sin(th), th];

module belt() {  // TPU, printed standing up as a loop
    linear_extrude(track_w) difference() {
        hull() for (sx = [-1, 1]) translate([sx * spacing, 0]) circle(r = rp + belt_t, $fn = 96);
        hull() for (sx = [-1, 1]) translate([sx * spacing, 0]) circle(r = rp, $fn = 96);
    }
    for (i = [0 : belt_lugs - 1]) {
        p = stadium(i * pitch);
        g = stadium((i + 0.5) * pitch);
        // drive lug on the inside
        translate([p[0], p[1], track_w / 2]) rotate([0, 0, p[2]])
            translate([-lug[2] / 2 + 0.01, 0, 0]) cube([lug[2], lug[0], lug[1]], center = true);
        // grouser rib on the outside, for grip
        translate([g[0], g[1], track_w / 2]) rotate([0, 0, g[2]])
            translate([belt_t + 0.5, 0, 0]) cube([1.2, 1.2, track_w], center = true);
    }
}

module wheel_body() {  // flanges stop the belt walking off, but stay inside its outer surface
    cylinder(r = rp, h = track_w);
    for (z = [-flange, track_w]) translate([0, 0, z]) cylinder(r = rp + belt_t - 0.4, h = flange);
}

module sprocket(driven) {  // printed flat; teeth slots catch the belt lugs
    difference() {
        union() {
            wheel_body();
            if (driven) translate([0, 0, -flange - 4]) cylinder(d = 9, h = 4);  // hub toward the motor
        }
        for (i = [0 : sprocket_teeth - 1]) rotate([0, 0, i * 360 / sprocket_teeth])
            translate([rp - lug[2] / 2 - 0.25, 0, track_w / 2])
                cube([lug[2] + 0.5 + 0.02, lug[0] + 0.8, lug[1] + 1], center = true);
        if (driven) {
            translate([0, 0, -20]) intersection() {  // D-shaft bore
                cylinder(d = n20_shaft_d + 0.15, h = 50);
                translate([-n20_shaft_d, -n20_shaft_d / 2 + (n20_shaft_d - n20_shaft_flat), 0])
                    cube([2 * n20_shaft_d, n20_shaft_d, 50]);
            }
            translate([0, 0, -flange - 2]) rotate([0, 90, 0]) cylinder(d = 1.8, h = 10);  // M2 grub screw
        } else {
            translate([0, 0, -10]) cylinder(d = 3.4, h = 50);
        }
        for (i = [0 : 5]) rotate([0, 0, i * 60 + 30]) translate([rp * 0.55, 0, -10]) cylinder(d = 7, h = 50);
    }
}

module road_wheel() {  // middle wheel: smooth, with a groove for the lugs
    difference() {
        wheel_body();
        translate([0, 0, track_w / 2 - (lug[1] + 1.5) / 2]) difference() {
            cylinder(r = rp + 1, h = lug[1] + 1.5);
            translate([0, 0, -1]) cylinder(r = rp - lug[2] - 0.6, h = lug[1] + 4);
        }
        translate([0, 0, -10]) cylinder(d = 3.4, h = 50);
        for (i = [0 : 5]) rotate([0, 0, i * 60 + 30]) translate([rp * 0.5, 0, -10]) cylinder(d = 6, h = 50);
    }
}

module spacer() {  // between the body wall and an idler / road wheel
    difference() {
        cylinder(d = 7, h = wheel_y0 - body_w / 2);
        translate([0, 0, -1]) cylinder(d = 3.4, h = 20);
    }
}

// --------------------------------------------------------- sensor mounts
scoop_len = cliff_reach + cliff_board[0] / 2 + 4;
pogo_z = 7;  // dock contact height above the body's underside
module scoop(pogo = false) {  // front scoop or rear lip, each with 2 cliff sensors near the corners; printed flat
    len = scoop_len;
    w = body_w * 0.9;
    difference() {
        union() {
            translate([0, -w / 2, 0]) cube([len, w, 8]);
            translate([-0.01, -w / 2, 0]) cube([3, w, 16]);  // flange against the body wall
            if (pogo) translate([len - 8, -12, 0]) cube([8, 24, 14]);  // dock contact block
        }
        if (pogo) {  // the spring-pin half of the pogo connector, facing forward, and its wire channel
            translate([len - 6, 0, pogo_z]) cube([14, pogo_cut[0] + 2 * fit, pogo_cut[1] + 2 * fit], center = true);
            translate([-1, -2, 2]) cube([len - 4, 4, 20]);
        }
        for (fy = [-0.75, 0.75]) translate([cliff_reach, fy * body_w / 2, 2]) {
            board_pocket(cliff_board, 10, 6);
            // wire channel back to the body
            translate([-cliff_reach, -2, 0]) cube([cliff_reach, 4, 10]);
        }
        for (dy = [-20, 20]) translate([-1, dy, 9]) rotate([0, 90, 0]) cylinder(d = 3.4, h = 10);
        translate([-1, 0, 9]) rotate([0, 90, 0]) cylinder(d = 6, h = 10);
    }
}

module hand() {  // side ToF holder; its face looks side_tof_yaw out from straight ahead. Mirror for the right.
    face = [6, 10, 1];
    module face_frame() { translate(face) rotate([0, 0, side_tof_yaw - 90]) children(); }
    difference() {
        hull() {
            translate([-12, 0, -10]) cube([24, 3, 22]);  // plate against the body side
            face_frame() cube([side_board[0] + 6, 4, 22], center = true);
        }
        for (dx = [-6, 6]) translate([dx, -1, 0]) rotate([-90, 0, 0]) cylinder(d = 3.4, h = 30);
        hull() {  // wire channel from the body into the board recess
            translate([0, -1, 7]) rotate([-90, 0, 0]) cylinder(d = 5, h = 2);
            face_frame() sphere(d = 5);
        }
        face_frame() translate([0, 2, 0])  // board recess in the outer face
            cube([side_board[0] + 2 * fit, 6, side_board[1] + 2 * fit], center = true);
    }
}

// ------------------------------------------------------------- neck & head
blk = [sg90_tab_len + 4, sg90[2] + 2, sg90[1] + 4];  // tilt servo block: x, y, z
blk_x0 = -sg90_shaft_from_end - (sg90_tab_len - sg90[0]) / 2 - 2;
blk_y1 = sg90[2] / 2;  // the servo's shaft face is flush with the block's +y face

module neck() {  // sits on the pan servo horn; holds the tilt servo at the top
    col = [14, 22];
    base_h = 3;
    top = pivot_h - blk[2] / 2;  // underside of the servo block, above the lid
    difference() {
        union() {
            cylinder(d = 26, h = base_h);
            translate([-col[0] / 2, -col[1] / 2, 0]) cube([col[0], col[1], top]);
            translate([blk_x0, blk_y1 - blk[1], top]) cube([blk[0], blk[1], blk[2]]);
            // pivot boss for the yoke's other arm
            translate([0, blk_y1 - blk[1], pivot_h]) rotate([90, 0, 0]) cylinder(d = 8, h = 5);
        }
        // servo horn screw + horn screws
        translate([0, 0, -1]) cylinder(d = 2.5, h = base_h + 2);
        for (a = [0, 180]) rotate([0, 0, a]) translate([7, 0, -1]) cylinder(d = 1.5, h = base_h + 2);
        // cable channel: up the column, out the back under the servo block
        translate([-5, -9, base_h]) cube([5, 18, top - base_h + 0.01]);
        translate([-col[0], -9, top - 8]) cube([col[0], 18, 7]);
        translate([-col[0], -9, base_h]) cube([col[0], 18, 7]);
        // tilt servo pocket: drops in from the top, shaft towards +y
        translate([0, 0, pivot_h - sg90[1] / 2]) {
            translate([-sg90_shaft_from_end - fit, blk_y1 - sg90[2], 0]) cube([sg90[0] + 2 * fit, sg90[2] + 1, 30]);
            translate([-sg90_shaft_from_end + sg90[0] / 2 - sg90_tab_len / 2 - fit, blk_y1 - sg90[2] + sg90_tab_z - 0.3, 0])
                cube([sg90_tab_len + 2 * fit, sg90_tab_t + 0.6, 30]);
            for (sx = [-1, 1])  // tab screws, driven in from the +y face
                translate([-sg90_shaft_from_end + sg90[0] / 2 + sx * sg90_tab_hole / 2, -3, sg90[1] / 2])
                    rotate([-90, 0, 0]) cylinder(d = 1.8, h = 20);
        }
        // pivot screw (M3 self-tapping)
        translate([0, blk_y1 - blk[1] + 2, pivot_h]) rotate([90, 0, 0]) cylinder(d = 2.5, h = 8);
    }
}

module head() {  // yoke + plate that carries the eyes; printed plate-down
    arm_t = 3;
    inner_pos = blk_y1 + 4 + 0.5;          // past the servo shaft and horn
    inner_neg = blk_y1 - blk[1] - 5 - 0.5; // past the pivot boss
    difference() {
        union() {
            translate([eye_x - 15, -eye_y - eye_r + 6, plate_z]) cube([30, 2 * (eye_y + eye_r - 6), 3]);
            for (y = [inner_pos, inner_neg - arm_t]) hull() {
                translate([-6, y, plate_z]) cube([12, arm_t, 1]);
                translate([0, y, 0]) rotate([-90, 0, 0]) cylinder(r = 7, h = arm_t);
            }
        }
        // horn screws (servo side) and pivot screw (other side)
        for (dz = [0, 7]) translate([0, inner_pos - 1, dz]) rotate([-90, 0, 0]) cylinder(d = 1.5, h = 10);
        translate([0, inner_neg - arm_t - 1, 0]) rotate([-90, 0, 0]) cylinder(d = 3.4, h = 10);
        // eye screws
        for (sy = [-1, 1], dx = [-7, 7]) translate([eye_x + dx, sy * eye_y, plate_z - 1]) cylinder(d = 2.4, h = 10);
    }
}

module eye(camera) {  // printed standing on its back end; camera eye = left
    t = 2;
    difference() {
        union() {
            rotate([0, 90, 0]) cylinder(r = eye_r, h = eye_len, center = true);
            translate([-eye_len / 2, -8, -eye_r]) cube([eye_len, 16, 3]);  // flat foot on the head plate
        }
        rotate([0, 90, 0]) cylinder(r = eye_r - t, h = eye_len - 2 * t, center = true);
        translate([-eye_len / 2 - 1, 0, 0]) rotate([0, 90, 0]) cylinder(r = eye_r - t, h = 4);  // open back
        // lens recess on the front, Wall-E style
        translate([eye_len / 2 - 0.8, 0, 0]) rotate([0, 90, 0]) cylinder(r = eye_r - 4, h = 2);
        if (camera) {
            translate([eye_len / 2, 0, cam_lens_offset]) rotate([0, 90, 0]) cylinder(d = 14, h = 10, center = true);
            for (sy = [-1, 1], sz = [-1, 1])  // blind holes for the board's M2 screws
                translate([eye_len / 2 - t - 4, sy * cam_holes[0] / 2, sz * cam_holes[1] / 2])
                    rotate([0, 90, 0]) cylinder(d = 1.8, h = 4.5);
        } else {
            translate([eye_len / 2, 0, 0]) rotate([0, 90, 0]) cylinder(d = 5.2, h = 10, center = true);  // status LED
        }
        for (dx = [-7, 7]) translate([dx, 0, -eye_r - 1]) cylinder(d = 1.8, h = 8);
    }
    if (camera)  // standoffs for the camera board, behind the front face
        for (sy = [-1, 1], sz = [-1, 1])
            translate([eye_len / 2 - t - 3, sy * cam_holes[0] / 2, sz * cam_holes[1] / 2]) rotate([0, 90, 0])
                difference() { cylinder(d = 4.5, h = 3); cylinder(d = 1.8, h = 4); }
}

module eye_cap() {  // push-fit back cover with a cable slot
    difference() {
        union() {
            cylinder(r = eye_r, h = 1.6);
            cylinder(r = eye_r - 2 - fit, h = 5);
        }
        translate([0, 0, 1.6]) cylinder(r = eye_r - 3.6, h = 10);
        translate([-9, -eye_r * 0.4, -1]) cube([18, 3, 10]);
    }
}

// ------------------------------------------------------------------- dock
// Wall-E drives in forwards between the guide arms until the pogo pins on its
// scoop snap onto the matching half in the contact block. The wall behind it
// carries a printed ArUco marker the camera uses to find the dock.
dock_plate_t = 3;
dock_len = 170;                                  // entry to contact block, x
dock_gap = 2 * (track_y + track_w / 2) + 6;      // between the arms at the narrow end
dock_mouth = dock_gap + 30;                      // between the arms at the entry
arm_t = 4;
dock_w = dock_mouth + 2 * arm_t;
block = [12, dock_gap + 2 * arm_t, 28];          // contact block at the front of the dock
marker = 80;                                     // ArUco marker size

module dock_base() {
    difference() {
        union() {
            // floor plate with a ramp at the entry
            hull() {
                translate([-dock_len, -dock_w / 2, 0]) cube([dock_len, dock_w, 0.6]);
                translate([-dock_len + 15, -dock_w / 2, 0]) cube([dock_len - 15, dock_w, dock_plate_t]);
            }
            // funnel arms
            for (sy = [-1, 1]) hull() {
                translate([-dock_len + 20, sy * (dock_mouth / 2 + arm_t / 2), 0]) cylinder(d = arm_t, h = 22);
                translate([-block[0] + 1, sy * (dock_gap / 2 + arm_t / 2), 0]) cylinder(d = arm_t, h = 22);
            }
            translate([-block[0], -block[1] / 2, 0]) cube(block);
        }
        // the socket half of the pogo connector, at the robot's contact height
        translate([-block[0] - 1, 0, dock_plate_t + clearance + pogo_z])
            cube([20, pogo_cut[0] + 2 * fit, pogo_cut[1] + 2 * fit], center = true);
        // wire channel down the back of the block
        translate([-4, -2, -1]) cube([5, 4, block[2] + 2]);
        // screws holding the wall
        for (sy = [-1, 1]) translate([-6, sy * block[1] / 3, block[2] - 12]) rotate([0, 90, 0]) cylinder(d = 2.6, h = 20);
        // anti-slip pads underneath
        for (sx = [-dock_len + 25, -25], sy = [-1, 1]) translate([sx, sy * (dock_w / 2 - 20), -1]) cylinder(d = 12.5, h = 1.6);
    }
}

module dock_wall() {  // screws to the back of the contact block; printed flat
    h = 200;
    difference() {
        translate([0, -block[1] / 2, 0]) cube([4, block[1], h]);
        // marker recess on the face Wall-E sees, about where the camera looks when approaching
        translate([-1, -marker / 2 - 1, 150 - marker / 2 - 1]) cube([1.6, marker + 2, marker + 2]);
        for (sy = [-1, 1]) translate([-1, sy * block[1] / 3, block[2] - 12]) rotate([0, 90, 0]) {
            cylinder(d = 3.4, h = 10);
            translate([0, 0, 3.5]) cylinder(d = 6.6, h = 3);  // screw heads at the back
        }
        // 12 V barrel jack for the adapter, and the wire path to the contacts
        translate([-1, block[1] / 2 - 25, 40]) rotate([0, 90, 0]) cylinder(d = dc_jack_d, h = 10);
        translate([-1, -2, 0]) cube([2, 4, 45]);
    }
}

// --------------------------------------------------------------- assembly
module sg90_ghost() {  // stand-in for a bought servo, shaft at the origin pointing +z
    color("#3060c0", 0.8) translate([-sg90_shaft_from_end, -sg90[1] / 2, -sg90[2]]) {
        cube(sg90);
        translate([sg90[0] / 2 - sg90_tab_len / 2, 0, sg90_tab_z]) cube([sg90_tab_len, sg90[1], sg90_tab_t]);
    }
}

module place_wheel(x, side) {
    translate([x, side * track_y, axle_z]) rotate([side > 0 ? -90 : 90, 0, 0]) translate([0, 0, -track_w / 2]) children();
}

module assembly() {
    color("gold") body();
    color("gold") translate([0, 0, shell_h]) lid();
    for (side = [-1, 1]) {
        color("dimgray") place_wheel(-spacing, side) sprocket(true);
        color("dimgray") place_wheel(spacing, side) sprocket(false);
        color("dimgray") place_wheel(0, side) road_wheel();
        color("#333") translate([0, side * track_y - track_w / 2, axle_z]) rotate([90, 0, 0])
            translate([0, 0, -track_w]) belt();
        color("gray") translate([body_l / 2 - 14, side * body_w / 2, side_tof_z])
            mirror([0, side < 0 ? 1 : 0, 0]) hand();
    }
    color("gray") translate([body_l / 2, 0, 0]) scoop(pogo = true);
    color("gray") translate([-body_l / 2, 0, 0]) mirror([1, 0, 0]) scoop();
    translate([pan_x, 0, body_h]) {
        translate([0, 0, sg90[2] - sg90_tab_z]) sg90_ghost();  // tabs resting on the lid
        color("gray") translate([0, 0, neck_base_z]) neck();
        translate([0, 0, neck_base_z + pivot_h]) {
            translate([0, blk_y1, 0]) rotate([-90, 0, 0]) rotate([0, 0, 0]) sg90_ghost();
            color("gold") head();
            for (sy = [-1, 1]) color("dimgray") translate([eye_x, sy * eye_y, plate_z + 3 + eye_r]) eye(sy > 0);
        }
    }
}

// ------------------------------------------------------------- part select
if (part == "assembly") assembly();
if (part == "body") body();
if (part == "lid") rotate([180, 0, 0]) lid();
if (part == "belt") belt();
if (part == "sprocket_drive") rotate([180, 0, 0]) sprocket(true);  // hub up: no supports
if (part == "sprocket_idler") sprocket(false);
if (part == "road_wheel") road_wheel();
if (part == "spacer") spacer();
if (part == "motor_strap") motor_strap();
if (part == "scoop_front") scoop(pogo = true);
if (part == "lip_rear") scoop();
if (part == "hand_left") rotate([90, 0, 0]) hand();
if (part == "hand_right") rotate([-90, 0, 0]) mirror([0, 1, 0]) hand();
if (part == "neck") neck();
if (part == "head") rotate([180, 0, 0]) head();
if (part == "eye_camera") rotate([0, 90, 0]) eye(true);  // front face down: no supports
if (part == "eye_led") rotate([0, 90, 0]) eye(false);
if (part == "eye_cap") eye_cap();
if (part == "dock_base") dock_base();
if (part == "dock_wall") rotate([0, 90, 0]) dock_wall();  // marker face up
if (part == "dock") { dock_base(); dock_wall(); }
