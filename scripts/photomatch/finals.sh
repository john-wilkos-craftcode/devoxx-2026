#!/usr/bin/env bash
# The full-quality finals, one Blender job at a time, resumable (John 18/10: "render everything"; 19/10: the PC goes off
# around 08:00 to go to work). Each job writes a marker in final/done/ when its renders are in; a rerun skips those, so
# after a restart just run it again. A job only starts if its estimate fits before --until HH:MM (default: none); the
# rest wait for the next run. Extra render flags (e.g. adopted A/B settings) come from final/extra-flags if present.
#   scripts/photomatch/finals.sh [--until 07:45]
# One build per room and variant (--both: walk there + walk back + stills, 18/10 optimisation review); encodes run in
# the background while the next build goes. A clip is done when its anim/.complete exists, so a job stopped by a
# shutdown resumes with what's missing (the walk back, then the stills from their own build). Phone walks get a clearance check first (< 0.45 m: skipped and reported).
set -u
cd "$(dirname "$0")/../.." || exit 1
F=/mnt/c/Users/wilkojo/kino-renders/photomatch/final; LG=/mnt/c/Users/wilkojo/kino-renders/photomatch/logs
W=$(wslpath -w $F); mkdir -p $F/done
Q="--engine eevee --samples 48 --tex-limit 1024 --shadow-scale 0.5"
X=$(cat $F/extra-flags 2>/dev/null || true)
UNTIL=""; [ "${1:-}" = "--until" ] && UNTIL=$2
END=""                                     # the deadline, fixed at the start: the next HH:MM from now
if [ -n "$UNTIL" ]; then END=$(date -d "$UNTIL" +%s); [ "$END" -lt "$(date +%s)" ] && END=$(date -d "tomorrow $UNTIL" +%s); fi
lastlog() { echo $LG/$(ls -t $LG | head -1); }
fits() {   # minutes: does a job that long finish before --until?
  [ -z "$END" ] && return 0
  [ $(( $(date +%s) + $1 * 60 )) -le "$END" ]
}
clip_done() { [ -e "$F/venue/$1/anim/.complete" ]; }   # photomatch_scene writes it when a whole clip is in
done_() { [ -e "$F/done/$1" ] && ! grep -qs hold "$F/done/$1"; }   # (a "hold" marker only parks a job for a queue
                                                                    # already running: not done)
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
run() {   # job name, estimate (min), render.sh args, mp4 pairs "dir:name ..."; resumes a job stopped half way
  local job=$1 est=$2 args=$3 outs=$4 L todo="" o stills=""
  done_ $job && return
  for o in $outs; do clip_done "${o%%:*}" || todo="$todo $o"; done
  case "$args" in *--stills*) stills=$(echo "$args" | sed 's/ --both//; s/ --walk anim//; s/ --width [0-9]*//');; esac
  if [ -z "$todo" ]; then                  # every clip in (the PC went off before the stills): only those
    args=""; est=15
  elif [ "$(echo $todo | wc -w)" -lt "$(echo $outs | wc -w)" ]; then   # the walk there is in: the walk back alone
    args=$(echo "$args" | sed 's/--both/--back/; s/ --stills//'); est=$((est / 2 + 10))
  else
    stills=""                              # --both --stills renders the stills itself
  fi
  fits $est || { echo "WAIT $job (~$est min, past $UNTIL)"; return; }
  echo "start $job $(date +%H:%M)${todo:+ (clips:$todo)}"
  for o in $todo; do rm -rf "${F:?}/venue/${o%%:*}/anim"; done
  if [ -n "$args" ]; then
    scripts/photomatch/render.sh venue $args $Q $X --out "$W" >/dev/null 2>&1
    L=$(lastlog); grep -E "RENDERED anim|Traceback|CROWD timing" "$L" | sed "s/^/  /"
    grep -q "RENDERED still" "$L" && echo "  stills: $(grep -c 'RENDERED still' "$L")"
    grep -q Traceback "$L" && { echo "FAILED $job: $L"; return; }
  fi
  for o in $todo; do clip_done "${o%%:*}" || { echo "FAILED $job: ${o%%:*} incomplete"; return; }; done
  if [ -n "$stills" ]; then                # the stills from their own build (the walk back's build can't)
    scripts/photomatch/render.sh venue $stills $Q $X --out "$W" >/dev/null 2>&1
    L=$(lastlog); echo "  stills: $(grep -c 'RENDERED still' "$L")"
    grep -q Traceback "$L" && { echo "FAILED $job stills: $L"; return; }
  fi
  echo done > $F/done/$job
  (for o in $todo; do encode "$F/venue/${o%%:*}/anim" "${o##*:}"; done) &
}

# every clip as soon as it's whole (anim/.complete), not when its room's job ends (John 19/10: the walk there sat
# unencoded while its walk back rendered): a background pass every minute, for as long as this queue runs
mp4_for() { case "$1" in
  walk) echo final-flythrough-laptop.mp4;; walk-phone) echo final-flythrough-phone.mp4;;
  walk-phone-room*-back) n=${1#walk-phone-room}; echo "final-room${n%-back}-back-phone.mp4";;
  walk-phone-room*) echo "final-room${1#walk-phone-room}-phone.mp4";;
  walk-room*-back) n=${1#walk-room}; echo "final-room${n%-back}-back-laptop.mp4";;
  walk-room*) echo "final-room${1#walk-room}-laptop.mp4";; esac; }
( while kill -0 $$ 2>/dev/null; do
    for c in $F/venue/*/anim/.complete; do
      [ -e "$c" ] || continue
      d=$(basename "$(dirname "$(dirname "$c")")"); m=$(mp4_for "$d"); [ -n "$m" ] || continue
      [ "$F/$m" -nt "$c" ] || encode "$F/venue/$d/anim" "$m"
    done
    # and onto the page as they come (John 19/10: commit and push as we go): a walk with the still it ends on
    p=$(python3 scripts/photomatch/publish.py 2>&1 | tail -1)
    if [ -n "$(git status --porcelain site/cinema/media)" ]; then
      git add site/cinema/media && git commit -qm "Cinema media: final ${p#published: }" -- site/cinema/media \
        && { git pull -q --rebase --autostash && git push -q; } && echo "  pushed ${p#published: } $(date +%H:%M)" \
        || echo "  PUBLISH: commit/push failed ($p)"
    fi
    sleep 60
  done ) &
# the laptop stills rendered before they were made wider (John 19/10: ultrawide windows) and room 8's, from their own
# builds (~12 min each); room 8 first, for the page preview
for n in 8 3 4 5; do
  done_ stills-$n-laptop && continue
  fits 15 || { echo "WAIT stills-$n-laptop"; continue; }
  scripts/photomatch/render.sh venue --room $n --crowd --stills $Q $X --out "$W" >/dev/null 2>&1
  grep -q "RENDERED still seat-$n-front" "$(lastlog)" && echo done > $F/done/stills-$n-laptop && echo "stills $n laptop done $(date +%H:%M)"
done
# laptops (the fly-through and room 8's walks are done): rooms 3-10, one build each (~140 min)
for n in 3 4 5 6 7 9 10; do
  run laptop-$n 150 "--room $n --crowd --both --stills --walk anim --width 1600" \
    "walk-room$n:final-room$n-laptop.mp4 walk-room$n-back:final-room$n-back-laptop.mp4"
done
# phones: the fly-through (~165 min), then one build per room (~95 min) after a clearance check
run phone-fly 165 "--variant phone --crowd --walk anim --width 810" "walk-phone:final-flythrough-phone.mp4"
for n in 3 4 5 6 7 8 9 10; do
  done_ phone-$n && continue
  fits 100 || { echo "WAIT phone-$n (~100 min, past $UNTIL)"; continue; }
  clear_ok $n "--variant phone" || continue
  run phone-$n 95 "--room $n --variant phone --crowd --both --stills --walk anim --width 810" \
    "walk-phone-room$n:final-room$n-phone.mp4 walk-phone-room$n-back:final-room$n-back-phone.mp4"
done
wait
echo "queue done $(date +%H:%M): $(ls $F/done | wc -l) jobs finished, $(ls $F/done | tr '\n' ' ')"
