#!/bin/bash
# Phase A: bulk copy /home/albus and /models to the new NVMe while production keeps running.
# rate-limited so the model's page cache is not evicted wholesale.
set -u
LOG=/home/albus/nvme_bulk.log
: > "$LOG"
echo "start $(date -Is)" >> "$LOG"

sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --bwlimit=350M \
  --info=progress2 --no-inc-recursive \
  /home/albus/ /nvme/home_albus/ >> "$LOG" 2>&1
echo "home rc=$? $(date -Is)" >> "$LOG"

sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --bwlimit=350M \
  --info=progress2 --no-inc-recursive \
  /models/ /nvme/models/ >> "$LOG" 2>&1
echo "models rc=$? $(date -Is)" >> "$LOG"

echo "done $(date -Is)" >> "$LOG"
df -h /nvme >> "$LOG"
