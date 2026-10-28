"""Regenerate hardware/params.scad from RobotSpec and export every printable part.

    python scripts/build_hardware.py            # STLs into hardware/stl/
    python scripts/build_hardware.py --previews # also PNGs into hardware/preview/ (needs a display or xvfb-run)

Needs OpenSCAD (https://openscad.org) on your PATH.
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "hardware")

# part name -> (quantity, material, colour)
PARTS = {
    "body": (1, "PETG or PLA", "yellow"),
    "lid": (1, "PETG or PLA", "yellow"),
    "belt": (2, "TPU 95A", "black"),
    "sprocket_drive": (2, "PETG", "grey"),
    "sprocket_idler": (2, "PETG", "grey"),
    "road_wheel": (2, "PETG", "grey"),
    "spacer": (4, "PETG or PLA", "any"),
    "motor_strap": (2, "PETG or PLA", "any"),
    "scoop_front": (1, "PETG or PLA", "grey"),
    "lip_rear": (1, "PETG or PLA", "grey"),
    "hand_left": (1, "PETG or PLA", "grey"),
    "hand_right": (1, "PETG or PLA", "grey"),
    "neck": (1, "PETG or PLA", "grey"),
    "head": (1, "PETG or PLA", "yellow"),
    "eye_camera": (1, "PLA", "grey"),
    "eye_led": (1, "PLA", "grey"),
    "eye_cap": (2, "PLA", "grey"),
}


def openscad(args, display=False):
    cmd = ["openscad", *args]
    if display and shutil.which("xvfb-run") and not os.environ.get("DISPLAY"):
        cmd = ["xvfb-run", "-a", *cmd]
    result = subprocess.run(cmd, cwd=HW, capture_output=True, text=True)
    if result.returncode != 0 or "ERROR" in result.stderr or "WARNING" in result.stderr:
        sys.exit(f"openscad failed for {args}:\n{result.stderr}")
    return result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--previews", action="store_true")
    parser.add_argument("parts", nargs="*", help="only these parts (default: all)")
    args = parser.parse_args()
    if not shutil.which("openscad"):
        sys.exit("OpenSCAD not found: install it from https://openscad.org")

    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_scad_params.py")], check=True)
    os.makedirs(os.path.join(HW, "stl"), exist_ok=True)
    os.makedirs(os.path.join(HW, "preview"), exist_ok=True)
    for name in args.parts or PARTS:
        stl = os.path.join("stl", f"{name}.stl")
        openscad(["-D", f'part="{name}"', "-o", stl, "walle.scad"])
        print(f"{stl:30s} x{PARTS[name][0]}  {PARTS[name][1]}")
        if args.previews:
            openscad(["-D", f'part="{name}"', "-o", os.path.join("preview", f"{name}.png"), "--imgsize=600,600",
                      "--viewall", "--autocenter", "--colorscheme=Tomorrow", "walle.scad"], display=True)
    if args.previews and not args.parts:
        for view, cam in {"assembly_front": "0,0,100,70,0,35,650", "assembly_side": "0,0,100,90,0,0,650",
                          "assembly_back": "0,0,100,60,0,215,650"}.items():
            openscad(["-o", os.path.join("preview", f"{view}.png"), "--imgsize=1000,1000", f"--camera={cam}",
                      "--colorscheme=Tomorrow", "walle.scad"], display=True)
        print("previews in hardware/preview/")


if __name__ == "__main__":
    main()
