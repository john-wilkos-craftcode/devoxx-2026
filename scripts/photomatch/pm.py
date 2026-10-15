"""Shared photo-match maths: a calibrated photo camera (calib.py's json plus a position) and measuring with it.

Camera: R_cw (camera -> world, camera axes x right, y down, z forward), f in pixels, principal point = image
centre + shift_px, position C in world metres (z up).
"""
import json
import math

import numpy as np


class Cam:
    def __init__(self, cal, C=(0.0, 0.0, 1.6), yaw_turns=0):
        if isinstance(cal, str):
            cal = json.load(open(cal))
        self.cal = cal
        self.W, self.H = cal["size"]
        self.f = cal["f_px"]
        self.c = np.array([self.W / 2, self.H / 2]) + np.array(cal.get("shift_px", [0, 0]))
        R = np.array(cal["R_cw"])
        q = yaw_turns * math.pi / 2                       # yaw is only known modulo 90 degrees: pick the walls
        Rz = np.array([[math.cos(q), -math.sin(q), 0], [math.sin(q), math.cos(q), 0], [0, 0, 1]])
        self.R = Rz @ R
        self.C = np.array(C, float)

    def project(self, X):
        X = np.atleast_2d(np.asarray(X, float))
        p = (X - self.C) @ self.R                         # world -> camera: R^T (X - C), row-vector form
        return np.stack([self.f * p[:, 0] / p[:, 2] + self.c[0], self.f * p[:, 1] / p[:, 2] + self.c[1]], 1)

    def ray(self, u, v):
        d = self.R @ np.array([(u - self.c[0]) / self.f, (v - self.c[1]) / self.f, 1.0])
        return d / np.linalg.norm(d)

    def on_plane(self, u, v, axis, value):
        """where the pixel's ray meets the plane world[axis] = value (axis 0 x, 1 y, 2 z)"""
        d = self.ray(u, v)
        t = (value - self.C[axis]) / d[axis]
        return self.C + t * d

    def floor(self, u, v, z=0.0):
        return self.on_plane(u, v, 2, z)

    def height_at(self, base, u, v):
        """z of the point straight above/below the world point base that shows at pixel (u, v): least squares
        over both image coordinates"""
        d = self.ray(u, v)
        # closest point between the vertical line through base and the ray
        a = np.array([0, 0, 1.0])
        w0 = self.C - np.asarray(base, float)
        b, dd, e = a @ d, d @ w0, a @ w0
        s = (e - b * dd) / (1 - b * b)
        return base[2] + s

    def blender(self):
        """Blender camera: matrix_world rows, lens in mm on a 36 mm horizontal sensor, shift_x/y"""
        M = np.eye(4)
        M[:3, :3] = self.R @ np.diag([1, -1, -1])
        M[:3, 3] = self.C
        big = max(self.W, self.H)
        sh = np.array(self.cal.get("shift_px", [0, 0]))
        return {"matrix": M.tolist(), "lens": self.f * 36 / self.W, "sensor_width": 36,
                "shift_x": -sh[0] / big, "shift_y": sh[1] / big, "size": [self.W, self.H]}
