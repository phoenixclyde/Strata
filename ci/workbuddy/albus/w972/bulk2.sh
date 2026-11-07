#!/bin/bash
# Phase A (clean): bulk copy both trees to the NVMe, quiet log, rate-limited.
set -u
LOG=/nvme/bulk.log
: > "$LOG"
echo "start $(date -Is)" >> "$LOG"

sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --bwlimit=350M \
  --info=stats2 /home/albus/ /nvme/home_albus/ >> "$LOG" 2>&1
echo "home rc=$? $(date -Is)" >> "$LOG"

sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --bwlimit=350M \
  --info=stats2 /models/ /nvme/models/ >> "$LOG" 2>&1
echo "models rc=$? $(date -Is)" >> "$LOG"

echo "done $(date -Is)" >> "$LOG"
df -h /nvme >> "$LOG"
