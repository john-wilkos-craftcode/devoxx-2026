#!/usr/bin/env bash
# Build one photo-matched area in Windows Blender (from WSL), render its reference cameras, and lay each render
# over its photo (scripts/photomatch/compare.py).
#   scripts/photomatch/render.sh <area> [blender args, e.g. --cams upstairs_hall --engine workbench --samples 32]
# Renders and comparisons land in C:\Users\wilkojo\kino-renders\photomatch\<area>\.
set -u
area=$1; shift
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
REPO=$(cd "$(dirname "$0")/../.." && pwd)
OUT=/mnt/c/Users/wilkojo/kino-renders/photomatch
mkdir -p "$OUT/logs"
log="$OUT/logs/$area-$(date +%m%d-%H%M%S).log"
win=$(wslpath -w "$REPO")
cd /mnt/c/Users/wilkojo || exit 1
"$BLENDER" -b --python-exit-code 1 --python "$win\\scripts\\blender\\photomatch_scene.py" -- --root "$win" \
    --area "$area" --out "$(wslpath -w "$OUT")" "$@" > "$log" 2>&1
code=$?
grep -E "BUILT|RENDERED|SANITY|CROWD|BLUR|WALK|Error|Traceback|^  File|^[A-Za-z]*Error|^done" "$log" | tail -n 40
echo "exit $code, log: $log"
[ $code -eq 0 ] && python3 "$REPO/scripts/photomatch/compare.py" "$area"
exit $code
