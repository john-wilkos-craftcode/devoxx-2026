#!/usr/bin/env bash
# Run by Claude/owner outside Codex's sandbox. Never runs final animations.
# Usage: bash scripts/blender/phase1_review.sh check|preview|benchmark [rooms ...]
set -uo pipefail
cd "$(dirname "$0")/../.."
repo_linux=$PWD
repo_windows=$(wslpath -w "$repo_linux")
blender='/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe'
mode=${1:-check}; shift || true
rooms=("$@"); ((${#rooms[@]})) || rooms=(3 8)
out_linux=/mnt/c/Users/wilkojo/kino-renders/preview
out_windows=C:/Users/wilkojo/kino-renders/preview
mkdir -p "$out_linux"
status=0
for room in "${rooms[@]}"; do
  case "$mode" in
    check) flags=(--check --plans) ;;
    preview) flags=(--preview-clips all --plans) ;;
    benchmark)
      side=east; ((room<=6)) && side=west
      flags=(--benchmark "intro,intro-phone,walk-a-$side,walk-b-$room,walk-phone-a-$side,walk-phone-b-$room,back-b-$room,back-phone-b-$room") ;;
    *) echo 'Usage: phase1_review.sh check|preview|benchmark [rooms...]' >&2; exit 2 ;;
  esac
  log="$out_linux/$mode-$room.log"
  # Serial, blocking launch. Do not run this script alongside another Blender job.
  (cd /mnt/c/Users/wilkojo && "$blender" -b --python-exit-code 1 \
    --python "$repo_windows/scripts/blender/build_scene.py" -- \
    --root "$repo_windows" --room "$room" --out "$out_windows" "${flags[@]}") > "$log" 2>&1 || status=1
  rg '^(CHECK|FAIL)|Traceback|Error:|Exception|NameError|TypeError|AttributeError' "$log" || true
  # Blender may swallow SystemExit; the machine-readable report is authoritative.
  if [[ "$mode" == check && -f "$out_linux/check-$room.json" ]]; then
    python3 - "$out_linux/check-$room.json" <<'PY' || status=1
import json,sys
sys.exit(0 if json.load(open(sys.argv[1]))['status']=='PASS' else 1)
PY
  fi
done
if [[ "$mode" == check || "$mode" == preview ]]; then
  python3 "$repo_linux/scripts/blender/path_artifacts.py" "$out_linux" || status=1
fi
exit "$status"
