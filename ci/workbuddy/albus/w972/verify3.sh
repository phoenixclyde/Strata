#!/bin/bash
# Phase C (v2): compare the OLD trees (visible under the non-recursive bind /mnt/rootraw) with the
# NVMe copies, by content checksum. Empty itemised diff = identical bytes. Read-only on both sides.
set -u
LOG=/tmp/verify_nvme.log
: > "$LOG"
echo "start $(date -Is)" >> "$LOG"

for pair in "models models" "home/albus home_albus"; do
  set -- $pair
  src="/mnt/rootraw/$1"
  dst="/nvme/$2"
  echo "== $src -> $dst  $(date +%H:%M:%S)" >> "$LOG"
  sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --checksum --dry-run --itemize-changes \
       "$src/" "$dst/" > "/tmp/diff_$2.txt" 2>>"$LOG"
  echo "diff lines: $(wc -l < /tmp/diff_$2.txt)   $(date +%H:%M:%S)" >> "$LOG"
done

echo "done $(date -Is)" >> "$LOG"
