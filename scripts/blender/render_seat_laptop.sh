#!/usr/bin/env bash
# Render the cinema seat for laptops, from WSL against Windows Blender, then publish:
#   scripts/blender/render_seat_laptop.sh [laptop] [rooms...]     (default: laptop 3 4 5 6 7 8 9 10)
# - the laptop on your lap (build_laptop.py): open, closed and the opening frames, into kino-renders\laptop
# - each room's seat still and its cut-out layer, wider and taller than the walk (build_scene.py --render seat), into
#   kino-renders\seat-wide
# Waits for any running Blender to finish first.
set -u
cd "$(dirname "$0")/../.."
ROOTW=$(wslpath -w "$PWD")
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
BASE="C:/Users/wilkojo/kino-renders"
LOG="$(wslpath -u "$BASE")/render_seat_laptop.log"
ARGS=("$@"); [ ${#ARGS[@]} -eq 0 ] && ARGS=(laptop 3 4 5 6 7 8 9 10)
while /mnt/c/Windows/System32/tasklist.exe | grep -qi blender.exe; do sleep 30; done
echo "== $(date '+%d/%m %H:%M') ${ARGS[*]}" >> "$LOG"
for a in "${ARGS[@]}"; do
  if [ "$a" = laptop ]; then
    ( cd /mnt/c/Users/wilkojo && "$BLENDER" -b --python "$ROOTW\\scripts\\blender\\build_laptop.py" -- --root "$ROOTW" --out "$BASE/laptop" ${SAMPLES:+--samples $SAMPLES} ) 2>&1 \
      | grep -i "error\|traceback\|saved\|^done\|laptop frame" | grep -v "HIPEW" >> "$LOG"
  else
    echo "== $(date '+%H:%M') room $a" >> "$LOG"
    ( cd /mnt/c/Users/wilkojo && "$BLENDER" -b --python "$ROOTW\\scripts\\blender\\build_scene.py" -- --root "$ROOTW" --room "$a" \
        --render seat --out "$BASE/seat-wide" --samples ${SAMPLES:-256} ) 2>&1 | grep -i "error\|traceback\|saved\|^done" | grep -v "Shadow\|HIPEW" >> "$LOG"
  fi
done
echo "== $(date '+%d/%m %H:%M') publishing" >> "$LOG"
python3 scripts/blender/publish_renders.py "$(wslpath -u "$BASE")/seat-wide" "$(wslpath -u "$BASE")/laptop" >> "$LOG" 2>&1
echo "== $(date '+%d/%m %H:%M') finished" >> "$LOG"
