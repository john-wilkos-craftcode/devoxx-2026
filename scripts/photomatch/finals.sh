#!/usr/bin/env bash
# The full-quality finals, one Blender job at a time, resumable (John 18/10: "render everything"; 19/10: the PC goes off
# around 08:00 to go to work). Each job writes a marker in final/done/ when its renders are in; a rerun skips those, so
# after a restart just run it again. A job only starts if its estimate fits before --until HH:MM (default: none); the
# rest wait for the next run. Extra render flags (e.g. adopted A/B settings) come from final/extra-flags if present.
#   scripts/photomatch/finals.sh [--until 07:45]
# One build per room and variant (--both: walk there + walk back + stills, 18/10 optimisation review); encodes run in
# the background while the next build goes. Phone walks get a clearance check first (< 0.45 m: skipped and reported).
set -u
cd "$(dirname "$0")/../.." || exit 1
F=/mnt/c/Users/wilkojo/kino-renders/photomatch/final; LG=/mnt/c/Users/wilkojo/kino-renders/photomatch/logs
W=$(wslpath -w $F); mkdir -p $F/done
Q="--engine eevee --samples 48 --tex-limit 1024 --shadow-scale 0.5"
X=$(cat $F/extra-flags 2>/dev/null || true)
UNTIL=""; [ "${1:-}" = "--until" ] && UNTIL=$2
lastlog() { echo $LG/$(ls -t $LG | head -1); }
fits() {   # minutes: does a job that long finish before --until?
  [ -z "$UNTIL" ] && return 0
  local end now
  end=$(date -d "$UNTIL" +%s); [ "$end" -lt "$(date +%s)" ] && end=$(date -d "tomorrow $UNTIL" +%s)
  now=$(date +%s); [ $((now + $1 * 60)) -le "$end" ]
}
encode() {   # frames dir, mp4 name
  local s
  s=$(ls "$1" 2>/dev/null | head -1 | tr -dc 0-9 | sed 's/^0*//')
  [ -z "$s" ] && { echo "  NO FRAMES in $1"; return; }
  ffmpeg -y -loglevel error -framerate 24 -start_number "$s" -i "$1/f_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 16 "$F/$2" \
    && echo "  encoded $2 $(date +%H:%M) $(python3 scripts/photomatch/qc.py "$1" | grep -E '^QC (PASS|FAIL)')"
}
clear_ok() {   # room, variant flags: both directions clear >= 0.45 m (a cheap build without the crowd)
  local b m
  for b in "" "--back"; do
    scripts/photomatch/render.sh venue --room $1 $2 $b --engine eevee --walk 1 --samples 4 --width 320 >/dev/null 2>&1
    m=$(grep "ROOMWALK clearance" "$(lastlog)" | tail -1 | sed -n 's/.*min \([0-9.]*\) m.*/\1/p')
    python3 -c "import sys; sys.exit(0 if '$m' and float('$m') >= 0.45 else 1)" || { echo "SKIPPED room $1 $2 ${b:-there}: clearance ${m:-none} m"; return 1; }
  done
}
run() {   # job name, estimate (min), render.sh args, mp4 pairs "dir:name ..."
  local job=$1 est=$2 args=$3 outs=$4 L n_ok
  [ -e $F/done/$job ] && return
  fits $est || { echo "WAIT $job (~$est min, past $UNTIL)"; return; }
  echo "start $job $(date +%H:%M)"
  for o in $outs; do rm -rf "${F:?}/venue/${o%%:*}/anim"; done
  scripts/photomatch/render.sh venue $args $Q $X --out "$W" >/dev/null 2>&1
  L=$(lastlog); grep -E "RENDERED anim|Traceback|CROWD timing" "$L" | sed "s/^/  /"
  n_ok=$(grep -c "RENDERED anim" "$L")
  grep -q "RENDERED still" "$L" && echo "  stills: $(grep -c 'RENDERED still' "$L")"
  if grep -q Traceback "$L" || [ "$n_ok" -lt "$(echo $outs | wc -w)" ]; then echo "FAILED $job: $L"; return; fi
  touch $F/done/$job
  (for o in $outs; do encode "$F/venue/${o%%:*}/anim" "${o##*:}"; done) &
}

# laptops (the fly-through and room 8's walks are done): rooms 3-10, one build each (~140 min)
for n in 3 4 5 6 7 9 10; do
  run laptop-$n 150 "--room $n --crowd --both --stills --walk anim --width 1600" \
    "walk-room$n:final-room$n-laptop.mp4 walk-room$n-back:final-room$n-back-laptop.mp4"
done
if [ ! -e $F/done/stills-8-laptop ] && fits 15; then
  scripts/photomatch/render.sh venue --room 8 --crowd --stills $Q $X --out "$W" >/dev/null 2>&1
  grep -q "RENDERED still seat-8-front" "$(lastlog)" && touch $F/done/stills-8-laptop && echo "stills 8 laptop done $(date +%H:%M)"
fi
# phones: the fly-through (~165 min), then one build per room (~95 min) after a clearance check
run phone-fly 165 "--variant phone --crowd --walk anim --width 810" "walk-phone:final-flythrough-phone.mp4"
for n in 3 4 5 6 7 8 9 10; do
  [ -e $F/done/phone-$n ] && continue
  fits 100 || { echo "WAIT phone-$n (~100 min, past $UNTIL)"; continue; }
  clear_ok $n "--variant phone" || continue
  run phone-$n 95 "--room $n --variant phone --crowd --both --stills --walk anim --width 810" \
    "walk-phone-room$n:final-room$n-phone.mp4 walk-phone-room$n-back:final-room$n-back-phone.mp4"
done
wait
echo "queue done $(date +%H:%M): $(ls $F/done | wc -l) jobs finished, $(ls $F/done | tr '\n' ' ')"
