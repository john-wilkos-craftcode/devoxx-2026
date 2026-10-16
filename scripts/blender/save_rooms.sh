#!/usr/bin/env bash
# Save the old by-eye scene (build_scene.py) once per room, without rendering, so the photo-matched venue can take
# its auditoriums and the exact seat cameras of the published stills (cam-seat-<n> and its widened copy):
#   scripts/blender/save_rooms.sh [rooms...]      (default 3 4 5 6 7 8 9 10) -> kino-renders\rooms\kino-room-<n>.blend
set -u
cd "$(dirname "$0")/../.."
ROOTW=$(wslpath -w "$PWD")
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT="C:/Users/wilkojo/kino-renders/rooms"
mkdir -p "$(wslpath -u "$OUT")"
ROOMS=("$@"); [ ${#ROOMS[@]} -eq 0 ] && ROOMS=(3 4 5 6 7 8 9 10)
for n in "${ROOMS[@]}"; do
  t0=$(date +%s)
  ( cd /mnt/c/Users/wilkojo && "$BLENDER" -b --python "$ROOTW\\scripts\\blender\\build_scene.py" -- --root "$ROOTW" --room "$n" \
      --save "$OUT/kino-room-$n.blend" ) > "$(wslpath -u "$OUT")/save-$n.log" 2>&1
  echo "room $n: exit $? in $(( $(date +%s) - t0 ))s; $(grep -ci 'traceback\|error:' "$(wslpath -u "$OUT")/save-$n.log") error lines"
done
