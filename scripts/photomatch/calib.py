"""Camera matching from one photo, the way fSpy does it, but automatic: find the building's three vanishing
directions in the photo's straight edges and solve the lens (focal length) and the camera's orientation from them.

Conventions: image u right, v down, principal point at the image centre (no shift). Camera frame x right, y down,
z forward (OpenCV). World: metres, z up, x/y along the building's walls (Manhattan world). The camera's yaw is only
known modulo 90 degrees from the lines alone; the area's set-up file picks which wall is which.

  python3 scripts/photomatch/calib.py <photo> <out.json> [--mask x0,y0,x1,y1 ...] [--fov 40:110] [--debug out.jpg]
"""
import argparse
import json
import math

import cv2
import numpy as np
from scipy.optimize import least_squares

R_CW0 = np.array([[1.0, 0, 0], [0, 0, 1], [0, -1, 0]])     # columns: camera x, y, z in world, looking along +y


def rot(axis, a):
    c, s = math.cos(a), math.sin(a)
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def r_cw(yaw, pitch, roll):
    """camera -> world rotation: yaw about world z, pitch about the camera's right axis, roll about its view axis"""
    return rot("z", yaw) @ rot("x", pitch) @ R_CW0 @ rot("z", roll)


def segments(img, masks, min_len):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 1600 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    s = scale if scale < 1 else 1.0
    lines = cv2.createLineSegmentDetector().detect(small)[0]
    if lines is None:
        return np.zeros((0, 4))
    L = lines.reshape(-1, 4) / s
    keep = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1]) >= min_len
    for x0, y0, x1, y1 in masks:
        mx, my = (L[:, 0] + L[:, 2]) / 2, (L[:, 1] + L[:, 3]) / 2
        keep &= ~((mx >= x0) & (mx <= x1) & (my >= y0) & (my <= y1))
    return L[keep]


def sin_residual(L, vps, c):
    """sin of the angle between each segment and the line from its midpoint to each vanishing point: (n, k)"""
    m = np.stack([(L[:, 0] + L[:, 2]) / 2 - c[0], (L[:, 1] + L[:, 3]) / 2 - c[1]], 1)
    s = np.stack([L[:, 2] - L[:, 0], L[:, 3] - L[:, 1]], 1)
    s = s / np.linalg.norm(s, axis=1, keepdims=True)
    # vp homogeneous (x, y, w) relative to the centre; direction from m towards vp = vp.xy - m * vp.w
    d = vps[None, :, :2] - m[:, None, :] * vps[None, :, 2:3]
    d = d / (np.linalg.norm(d, axis=2, keepdims=True) + 1e-12)
    return np.abs(s[:, None, 0] * d[..., 1] - s[:, None, 1] * d[..., 0])


def vps_for(f, R_cw):
    """vanishing points (homogeneous, relative to the image centre) of the world x, y, z axes"""
    R_wc = R_cw.T
    K = np.diag([f, f, 1.0])
    return (K @ R_wc).T                                   # row k = K R_wc e_k


def search(L, c, fov_range, W):
    lens = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    t0 = math.sin(math.radians(1.5))
    best = (-1, None)
    for fov in np.arange(fov_range[0], fov_range[1] + 0.1, 3):
        f = (W / 2) / math.tan(math.radians(fov) / 2)
        for yaw in np.radians(np.arange(0, 90, 2)):
            for pitch in np.radians(np.arange(-40, 41, 2.5)):
                for roll in np.radians(np.arange(-8, 8.1, 2)):
                    r = sin_residual(L, vps_for(f, r_cw(yaw, pitch, roll)), c).min(1)
                    score = (lens * np.clip(1 - (r / t0) ** 2, 0, None)).sum()
                    if score > best[0]:
                        best = (score, (f, yaw, pitch, roll))
    return best[1]


def refine(L, c, x0, tol_deg, fixed_f=None, level=False):
    """least squares on the inlier segments. level: the photo was perspective-corrected in post (verticals made
    parallel), which is a level camera (pitch 0) whose lens is shifted vertically: solve the shift instead"""
    lens = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    f, yaw, pitch, roll = x0
    p = np.array([f, yaw, 0.0 if level else pitch, roll, (f * math.tan(pitch)) if level else 0.0])
    t = math.sin(math.radians(tol_deg))

    def unpack(p):
        ff = fixed_f if fixed_f else p[0]
        return ff, r_cw(p[1], 0.0 if level else p[2], p[3]), c + np.array([0.0, p[4] if level else 0.0])
    for _ in range(4):
        ff, R, cc = unpack(p)
        res = sin_residual(L, vps_for(ff, R), cc)
        cls = res.argmin(1)
        inl = res.min(1) < t
        w = np.sqrt(lens[inl])

        def fun(q):
            ff, R, cc = unpack(q)
            return w * sin_residual(L[inl], vps_for(ff, R), cc)[np.arange(inl.sum()), cls[inl]]
        p = least_squares(fun, p, loss="soft_l1", f_scale=0.01).x
    ff, R, cc = unpack(p)
    res = sin_residual(L, vps_for(ff, R), cc)
    cls = np.where(res.min(1) < t, res.argmin(1), -1)
    return (ff, p[1], 0.0 if level else p[2], p[3]), (cc - c), cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("out")
    ap.add_argument("--mask", nargs="*", default=[], help="x0,y0,x1,y1 in pixels: ignore segments in here")
    ap.add_argument("--fov", default="35:110", help="horizontal field of view search range, degrees")
    ap.add_argument("--fix-fov", type=float, help="known horizontal field of view (one-point perspective)")
    ap.add_argument("--min-len", type=float, default=0.025, help="shortest segment, fraction of the image width")
    ap.add_argument("--level", action="store_true", help="verticals are parallel in the photo (corrected in post): "
                    "level camera with a vertical lens shift")
    ap.add_argument("--debug")
    a = ap.parse_args()
    img = cv2.imread(a.photo, cv2.IMREAD_COLOR)
    H, W = img.shape[:2]
    c = np.array([W / 2, H / 2])
    masks = [tuple(float(v) for v in m.split(",")) for m in a.mask]
    L = segments(img, masks, a.min_len * W)
    fov_range = [float(v) for v in a.fov.split(":")]
    if a.fix_fov:
        fov_range = [a.fix_fov, a.fix_fov]
    x0 = search(L, c, fov_range, W)
    fixed = (W / 2) / math.tan(math.radians(a.fix_fov) / 2) if a.fix_fov else None
    (f, yaw, pitch, roll), sh, cls = refine(L, c, x0, 1.2, fixed, a.level)
    fov_h = math.degrees(2 * math.atan(W / 2 / f))
    R = r_cw(yaw, pitch, roll)
    counts = [int((cls == k).sum()) for k in range(3)]
    out = {"photo": a.photo, "size": [W, H], "f_px": f, "fov_h": fov_h,
           "yaw_deg": math.degrees(yaw), "pitch_deg": math.degrees(pitch), "roll_deg": math.degrees(roll),
           "R_cw": R.tolist(), "shift_px": sh.tolist(), "level": a.level, "lines_per_axis": counts, "masks": masks}
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{a.photo}: fov_h {fov_h:.1f}, yaw {out['yaw_deg']:.1f}, pitch {out['pitch_deg']:.1f}, "
          f"roll {out['roll_deg']:.1f}, shift {sh[0]:.0f},{sh[1]:.0f} px, lines x/y/z {counts}, unassigned {(cls < 0).sum()}")
    if a.debug:
        dbg = (img * 0.55).astype(np.uint8)
        col = {0: (60, 60, 255), 1: (60, 255, 60), 2: (255, 120, 40), -1: (160, 160, 160)}
        for seg, k in zip(L, cls):
            cv2.line(dbg, (int(seg[0]), int(seg[1])), (int(seg[2]), int(seg[3])), col[int(k)],
                     2 if k >= 0 else 1, cv2.LINE_AA)
        for x0_, y0_, x1_, y1_ in masks:
            cv2.rectangle(dbg, (int(x0_), int(y0_)), (int(x1_), int(y1_)), (0, 0, 0), -1)
        cv2.imwrite(a.debug, dbg)


if __name__ == "__main__":
    main()
