#!/bin/bash
# Phase C: byte-for-byte verification. Mount the OLD root LV read-only (nouuid) as the reference and
# compare against the NVMe copies with content checksums. Empty diff = identical.
set -u
LOG=/tmp/verify_nvme.log
: > "$LOG"
echo "start $(date -Is)" >> "$LOG"

sudo mkdir -p /mnt/rootraw
sudo mount -o ro,nouuid /dev/mapper/ubuntu--vg-lv--0 /mnt/rootraw 2>>"$LOG" || {
  echo "MOUNT FAILED" >> "$LOG"; tail -3 "$LOG"; exit 1; }
findmnt -no SOURCE,TARGET,OPTIONS /mnt/rootraw >> "$LOG"

for pair in "home/albus home_albus" "models models"; do
  set -- $pair
  src="/mnt/rootraw/$1"
  dst="/nvme/$2"
  echo "== $src -> $dst" >> "$LOG"
  sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --checksum --dry-run --itemize-changes \
       "$src/" "$dst/" > "/tmp/diff_$2.txt" 2>>"$LOG"
  echo "diff lines: $(wc -l < /tmp/diff_$2.txt)" >> "$LOG"
done

echo "done $(date -Is)" >> "$LOG"
