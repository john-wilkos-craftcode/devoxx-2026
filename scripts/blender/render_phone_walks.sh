#!/usr/bin/env bash
# Render the phones' own portrait walks, from WSL against Windows Blender, then publish:
#   scripts/blender/render_phone_walks.sh [rooms...]        (default: 3 4 5 6 7 8 9 10)
# phone-a-<side>: from the hall totem still, turning away towards the room's stair (shared per side);
# phone-b-<n>: a push-in on room n's door totem, ending on its still. 540x1170, 24 samples, motion blur.
# Renders go to C:\Users\<you>\kino-renders\final beside the other renders; rooms already done are skipped.
set -u
cd "$(dirname "$0")/../.."
ROOTW=$(wslpath -w "$PWD")
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUTW="C:/Users/wilkojo/kino-renders/final"
OUT=$(wslpath -u "$OUTW")
ROOMS=("$@"); [ ${#ROOMS[@]} -eq 0 ] && ROOMS=(3 4 5 6 7 8 9 10)
LOG="$OUT/render_rooms.log"

while /mnt/c/Windows/System32/tasklist.exe | grep -qi blender.exe; do sleep 30; done

run() {   # run <room> <what>
  ( cd /mnt/c/Users/wilkojo && "$BLENDER" -b --python "$ROOTW\\scripts\\blender\\build_scene.py" -- --root "$ROOTW" --room "$1" \
      --render "$2" --out "$OUTW" --walk-samples 24 ) 2>&1 | grep -i "error\|traceback\|saved\|^done" | grep -v "Shadow\|HIPEW" >> "$LOG"
}
frames() { ls "$OUT/$1" 2>/dev/null | wc -l; }

echo "== $(date '+%d/%m %H:%M') phone walks, rooms ${ROOMS[*]}" >> "$LOG"
for n in "${ROOMS[@]}"; do
  side=$([ "$n" -le 6 ] && echo west || echo east)
  what=""
  [ "$(frames phone-a-$side)" -ge 40 ] || what="phone-a"
  [ "$(frames phone-b-$n)" -ge 61 ] || what="${what:+$what,}phone-b"
  [ -z "$what" ] && { echo "room $n: phone walk done already" >> "$LOG"; continue; }
  echo "== $(date '+%H:%M') room $n: $what" >> "$LOG"
  run "$n" "$what"
done
echo "== $(date '+%d/%m %H:%M') publishing" >> "$LOG"
python3 scripts/blender/publish_renders.py "$OUT" >> "$LOG" 2>&1
echo "== $(date '+%d/%m %H:%M') phone walks finished" >> "$LOG"
