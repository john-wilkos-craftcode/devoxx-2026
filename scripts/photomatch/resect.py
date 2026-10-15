"""Camera resection: solve a photo's camera from points whose world position is known (corners of the model) and
whose pixel position you read in the photo. Use it to place a second photo of an area in the model built from the
first, or to pin the focal length of a one-point-perspective photo that the vanishing lines leave open.

  python3 scripts/photomatch/resect.py <points.json> <cal_in.json> <cal_out.json> [--C x,y,z] [--turns 0]
      [--free f,shift] [--level]

points.json: {"points": [{"uv": [u, v], "X": [x, y, z], "name": "..."}, ...]} in full-resolution photo pixels.
Starts from cal_in (calib.py output) at --C/--turns; solves position and orientation always, the focal length
and the principal point's shift when listed in --free (--level keeps the camera level: pitch 0, verticals
parallel, the horizon carried by a vertical shift). Writes a calib-style json whose R_cw already includes the
turns (so use "turns": 0 with it) and prints the camera position and each point's error in pixels.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).parent))
from pm import Cam  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("points")
    ap.add_argument("cal_in")
    ap.add_argument("cal_out")
    ap.add_argument("--C", default="0,0,1.6")
    ap.add_argument("--turns", type=int, default=0)
    ap.add_argument("--free", default="", help="comma list of f, shift (shift = both axes), shift_y")
    ap.add_argument("--level", action="store_true")
    a = ap.parse_args()
    pts = json.load(open(a.points))["points"]
    uv = np.array([p["uv"] for p in pts], float)
    X = np.array([p["X"] for p in pts], float)
    cal = json.load(open(a.cal_in))
    cam = Cam(cal, [float(v) for v in a.C.split(",")], a.turns)
    free = set(filter(None, a.free.split(",")))
    W, H = cam.W, cam.H
    c0 = np.array([W / 2, H / 2])
    if a.level:
        # level camera: R_cw = Rz(yaw) @ R0 @ Rz(roll); start from the current yaw
        fwd = cam.R[:, 2]
        yaw0 = math.atan2(-fwd[0], fwd[1])
        p0 = [yaw0, 0.0]
    else:
        p0 = list(Rotation.from_matrix(cam.R).as_rotvec())
    p0 += list(cam.C) + [math.log(cam.f)] + list(cam.c - c0)

    def unpack(p):
        if a.level:
            yaw, roll = p[0], p[1]
            Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
            R0 = np.array([[1.0, 0, 0], [0, 0, 1], [0, -1, 0]])
            Rr = np.array([[math.cos(roll), -math.sin(roll), 0], [math.sin(roll), math.cos(roll), 0], [0, 0, 1]])
            R, rest = Rz @ R0 @ Rr, p[2:]
        else:
            R, rest = Rotation.from_rotvec(p[:3]).as_matrix(), p[3:]
        C, f, sh = rest[:3], math.exp(rest[3]), np.array(rest[4:6])
        return R, C, f, sh

    mask = np.ones(len(p0), bool)
    n_rot = 2 if a.level else 3
    if "f" not in free:
        mask[n_rot + 3] = False
    if "shift" not in free:
        mask[n_rot + 4] = False
        if "shift_y" not in free and not a.level:
            mask[n_rot + 5] = False
        elif "shift_y" not in free and a.level:
            mask[n_rot + 5] = True                      # level: the horizon must be free to move
    p0 = np.array(p0, float)

    def fun(q):
        p = p0.copy()
        p[mask] = q
        R, C, f, sh = unpack(p)
        rel = (X - C) @ R
        proj = np.stack([f * rel[:, 0] / rel[:, 2], f * rel[:, 1] / rel[:, 2]], 1) + c0 + sh
        return (proj - uv).ravel()
    sol = least_squares(fun, p0[mask], loss="soft_l1", f_scale=3.0)
    p = p0.copy()
    p[mask] = sol.x
    R, C, f, sh = unpack(p)
    err = np.linalg.norm(fun(sol.x).reshape(-1, 2), axis=1)
    out = dict(cal)
    out.update({"f_px": f, "fov_h": math.degrees(2 * math.atan(W / 2 / f)), "R_cw": R.tolist(),
                "shift_px": sh.tolist(), "resected_from": a.points, "C": C.tolist()})
    json.dump(out, open(a.cal_out, "w"), indent=1)
    print(f"C = [{C[0]:.3f}, {C[1]:.3f}, {C[2]:.3f}]  fov_h {out['fov_h']:.1f}  shift {sh[0]:.0f},{sh[1]:.0f}px  "
          f"rms {np.sqrt((err ** 2).mean()):.1f}px  (use turns 0)")
    for pnt, e in zip(pts, err):
        print(f"  {pnt.get('name', ''):24} {e:6.1f}px")


if __name__ == "__main__":
    main()
