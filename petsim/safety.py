"""Safety reflex between any controller and the motors.

Learned policies are good but never guaranteed, so, like a Roomba's firmware,
the cliff sensors and the IMU override whatever the controller asks for. On the real robot
this runs on the microcontroller, independent of the Pi.
"""

import numpy as np

CLIFF_TRIGGER = 0.5  # normalized cliff reading meaning "the floor is gone"
TILT_TRIGGER = 0.25  # rad (~14 deg): the tracks are climbing something


def safety_filter(cliff, tilt, action):
    """cliff: the 5 normalized cliff readings (3 front, 2 rear); tilt: body tilt
    from the IMU's gravity reading, in rad; action: track speeds."""
    # Cliffs come first: when tipping over an edge, keep driving away from it.
    front = cliff[:3].max() > CLIFF_TRIGGER
    rear = cliff[3:].max() > CLIFF_TRIGGER
    if front and rear:
        return np.zeros(2)
    if front:
        return np.array([-0.5, -0.5])  # back straight away from the edge
    if rear:
        return np.array([0.5, 0.5])
    if tilt > TILT_TRIGGER:
        return np.zeros(2)  # stop and let it settle rather than climb on and tip over
    return action
