"""The auditoriums the room walks end in, appended from the old by-eye scene so every walk ends exactly in the seat of
its published still (data/photomatch/seats.json). Each room is cut out of a saved old-scene file by
scripts/blender/extract_auditorium.py into kino-renders/rooms/aud-<n>.blend (save_rooms.sh, then the extraction);
this module appends whichever of them exist. Same coordinates as the venue (venue.json's frame), no transform.
"""
from pathlib import Path

import bpy

ROOMS = (3, 4, 5, 6, 7, 8, 9, 10)
SRC = Path("C:/Users/wilkojo/kino-renders/rooms")


def build(root, unified=True):
    coll = bpy.data.collections.new("auditoriums")
    bpy.context.scene.collection.children.link(coll)
    import pm_areas.venue as V
    got = []
    for n in ((V.ROOM,) if V.ROOM else ()):        # only the room walk's own room: every other door is shut
        f = SRC / f"aud-{n}.blend"
        if not f.exists():
            continue
        with bpy.data.libraries.load(str(f), link=False) as (src, dst):
            dst.objects = list(src.objects)
        for ob in dst.objects:
            if ob is not None:
                coll.objects.link(ob)
        got.append(n)
    print(f"AUDITORIUMS appended: {got or 'none (run save_rooms.sh and extract_auditorium.py)'}", flush=True)
