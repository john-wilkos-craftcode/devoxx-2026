#!/usr/bin/env bash
# Render the cinema page's media for every room with talks, from WSL against Windows Blender, then publish.
#   scripts/blender/render_rooms.sh [rooms...]        (default: 3 4 5 6 7 8 9 10)
# Per room: the room's half of the walk (walk-b, 1280x720, 24 samples, motion blur), the seat still and its
# cut-out layer, and the phone door still (1080p-class, 256 samples). The shared halves (walk-a-east/-west)
# and the hall stills are rendered once, if missing. Renders go to C:\Users\<you>\kino-renders\final.
# A room that's already done is skipped, so the script can be stopped and restarted. Waits for any running
# Blender to finish first, so it can be queued behind another render.
set -u
cd "$(dirname "$0")/../.."
ROOTW=$(wslpath -w "$PWD")
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUTW="C:/Users/wilkojo/kino-renders/final"
OUT=$(wslpath -u "$OUTW")
ROOMS=("$@"); [ ${#ROOMS[@]} -eq 0 ] && ROOMS=(3 4 5 6 7 8 9 10)
LOG="$OUT/render_rooms.log"
mkdir -p "$OUT"

while /mnt/c/Windows/System32/tasklist.exe | grep -qi blender.exe; do sleep 30; done

run() {   # run <room> <what>
  ( cd /mnt/c/Users/wilkojo && "$BLENDER" -b --python "$ROOTW\\scripts\\blender\\build_scene.py" -- --root "$ROOTW" --room "$1" \
      --render "$2" --out "$OUTW" --samples 256 --walk-samples 24 ) 2>&1 | grep -i "error\|traceback\|saved\|^done" | grep -v "Shadow\|HIPEW" >> "$LOG"
}
frames() { ls "$OUT/$1" 2>/dev/null | wc -l; }

echo "== $(date '+%d/%m %H:%M') rooms ${ROOMS[*]}" >> "$LOG"
[ -f "$OUT/hall.png" ] && [ -f "$OUT/hall-phone.png" ] || run 8 "hall,hall-phone"
for side_room in "east 8" "west 5"; do
  set -- $side_room
  [ "$(frames walk-a-$1)" -ge 100 ] || run "$2" walk-a
done
for n in "${ROOMS[@]}"; do
  if [ -f "$OUT/seat-$n.png" ] && [ -f "$OUT/door-phone-$n.png" ] && [ "$(frames walk-b-$n)" -ge 60 ]; then
    echo "room $n: done already" >> "$LOG"; continue
  fi
  echo "== $(date '+%H:%M') room $n" >> "$LOG"
  run "$n" "seat,door-phone,walk-b"
done
echo "== $(date '+%d/%m %H:%M') publishing" >> "$LOG"
python3 scripts/blender/publish_renders.py "$OUT" >> "$LOG" 2>&1
echo "== $(date '+%d/%m %H:%M') finished" >> "$LOG"
