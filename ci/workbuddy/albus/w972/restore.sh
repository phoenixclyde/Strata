#!/bin/bash
# Restore the 49 files that the accidentally-started legacy build containers rewrote at 23:24-23:26,
# taking them from the frozen pre-cutover snapshot (/mnt/rootraw = the old root LV view).
# The live production log is deliberately skipped (it grew legitimately since the switch).
set -u
cd /

LIST=/tmp/restore_list.txt
awk '/^>/{ $1=""; sub(/^ /,""); print }' /tmp/diff_home_albus.txt \
  | grep -v '^strata166/data/strata-huihui-ud-iq4_xs.log$' > "$LIST"
echo "to restore: $(wc -l < "$LIST")"

sudo rsync -aHAX --numeric-ids --files-from="$LIST" /mnt/rootraw/home/albus/ /nvme/home_albus/
echo "restore rc=$?"

# neutralise the legacy containers so a reboot cannot repeat this
for c in buildrun028 buildrun028w r51diag rk312_rpt2_kept_czW312 srv_research w863build strata-ci-build strata-ci; do
  docker update --restart=no "$c" >/dev/null 2>&1 && echo "policy=no $c"
  docker stop "$c" >/dev/null 2>&1
done

echo "== re-check the restored paths =="
sudo rsync -aHAX --numeric-ids --checksum --dry-run --itemize-changes \
     --files-from="$LIST" /mnt/rootraw/home/albus/ /nvme/home_albus/ | head -10
echo "remaining lines: $(sudo rsync -aHAX --numeric-ids --checksum --dry-run --itemize-changes --files-from="$LIST" /mnt/rootraw/home/albus/ /nvme/home_albus/ | wc -l)"
