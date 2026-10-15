"""WSL Python: plot evaluated Blender footprints and routes. No Blender invocation.
Usage: python3 scripts/blender/path_artifacts.py /mnt/c/Users/wilkojo/kino-renders/preview
"""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def plot(path):
    data = json.loads(path.read_text())
    fig,axes = plt.subplots(2,2,figsize=(18,16))
    for ax,key in zip(axes.flat,('ground','upstairs','west-stair','east-stair')):
        segments = data.get('geometry_slices',{}).get(key,[])
        if segments: ax.add_collection(LineCollection(segments,colors='#aaa',linewidths=.45))
        side = key.endswith('stair')
        for name,clip in data['clips'].items():
            p = np.array([v['location'] for v in clip['poses']])
            if side:
                x = -6 if key.startswith('west') else 11.4
                mask = (abs(p[:,0]-x)<1.5)&(p[:,1]>-5)&(p[:,1]<13)
                xy = p[:,[1,2]]
            else:
                mask = p[:,2]<5 if key=='ground' else p[:,2]>=5
                xy = p[:,:2]
            if not np.any(mask): continue
            shown = xy.copy(); shown[~mask] = np.nan
            line, = ax.plot(shown[:,0],shown[:,1],linewidth=1.,label=name)
            ids = np.arange(0,len(p),10); ids=ids[mask[ids]]
            yaw = np.array([v['yaw'] for v in clip['poses']])[ids]
            pitch = np.array([v['pitch'] for v in clip['poses']])[ids]
            dx,dy = (np.sin(yaw)*np.cos(pitch),np.sin(pitch)) if side else (np.cos(yaw),np.sin(yaw))
            ax.quiver(xy[ids,0],xy[ids,1],dx,dy,color=line.get_color(),angles='xy',scale_units='xy',scale=1.4,width=.002)
        if side: ax.set_xlim(-5,13); ax.set_ylim(-.5,10)
        else: ax.set_xlim(-40,45); ax.set_ylim(-68,22)
        ax.set_aspect('equal'); ax.set_title(key); ax.grid(alpha=.2)
        ax.set_xlabel('y (m)' if side else 'x (m)'); ax.set_ylabel('z (m)' if side else 'y (m)')
        ax.legend(fontsize=6,loc='upper left')
    fig.suptitle(f'Room {data["room"]}: evaluated geometry slices; heading every 10 frames')
    fig.tight_layout()
    dest=path.with_name(f'plan-{data["room"]}.png'); fig.savefig(dest,dpi=130); plt.close(fig)
    print(f'CHECK PLAN PNG {dest}')


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('folder',type=Path); args=ap.parse_args()
    for path in sorted(args.folder.glob('paths-*.json')): plot(path)
