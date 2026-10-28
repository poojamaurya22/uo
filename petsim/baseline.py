"""Hand-written follow controller: the yardstick a trained policy has to beat.

It reads the same observation vector as the policy, so it can also run on the
real robot unchanged as a safe fallback.
"""

import math

import numpy as np

from petsim.env import OBS, PERSON_RANGE, TOF_ZONES

TOF_RANGE = 4.0  # must match RobotSpec.tof_range


def follow_controller(obs, follow_distance=1.0):
    tof = obs[OBS["tof"]].reshape(TOF_ZONES, TOF_ZONES) * TOF_RANGE
    cliff = obs[OBS["cliff"]]
    side_left, side_right = obs[OBS["side"]] * TOF_RANGE
    visible, s, c, dist, lost = obs[OBS["person"]]
    bearing = math.atan2(s, c)
    dist *= PERSON_RANGE

    # Cliff: drive away from it, nothing else matters.
    front, rear = cliff[:3], cliff[3:]
    if rear.max() > 0.5:
        return np.array([0.6, 0.6])
    if front.max() > 0.5:
        return np.array([-0.6, -0.2]) if front[0] > front[2] else np.array([-0.2, -0.6])

    if lost < 1.0:  # seen within the last few seconds
        turn = np.clip(1.5 * bearing, -1, 1)
        fwd = np.clip(0.9 * (dist - follow_distance), -0.4, 0.8) * max(0.0, math.cos(bearing))
    else:  # search: spin towards where the person was last seen
        turn, fwd = (0.5 if s >= 0 else -0.5), 0.0

    # Obstacles: rows 2-6 look at body height; columns split left/centre/right.
    band = tof[2:7]
    left = min(band[:, :3].min(), side_left)
    centre = band[:, 3:5].min()
    right = min(band[:, 5:].min(), side_right)
    if centre < 0.35 and fwd > 0:
        fwd = 0.0
        turn = 0.7 if left > right else -0.7
    elif min(left, right) < 0.2:
        turn += 0.4 if left > right else -0.4

    left_track = np.clip(fwd - turn, -1, 1)
    right_track = np.clip(fwd + turn, -1, 1)
    return np.array([left_track, right_track])
