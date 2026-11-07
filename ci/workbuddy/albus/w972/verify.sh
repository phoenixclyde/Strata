#!/bin/bash
# Phase C: byte-level verification of the migration. Runs AFTER the cutover, in the background,
# against the frozen copies in /home/albus.old and /models.old (production already serves the new tree).
# rsync --checksum compares content hashes on both sides; ANY output line means a real difference.
set -u
LOG=/nvme/verify.log
: > "$LOG"
echo "verify start $(date -Is)" >> "$LOG"

for pair in "/home/albus.old /nvme/home_albus" "/models.old /nvme/models"; do
  set -- $pair
  echo "== $1 vs $2" >> "$LOG"
  sudo ionice -c2 -n7 nice -n19 rsync -aHAX --numeric-ids --checksum --dry-run --itemize-changes \
       "$1/" "$2/" > /nvme/diff_$(basename "$1").txt 2>>"$LOG"
  n=$(wc -l < /nvme/diff_$(basename "$1").txt)
  echo "diff lines: $n" >> "$LOG"
done

echo "verify done $(date -Is)" >> "$LOG"
