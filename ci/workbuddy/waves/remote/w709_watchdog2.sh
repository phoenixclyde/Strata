#!/bin/bash
# W709 watchdog v2 (corrected).
# v1 bug: it tested "is calibrate running" ~13 s into the window, before the docker exec had
# started, so it wrongly pulled the production container back up (two engines raced for the GPU).
# v2 judges by the WINDOW WRAPPER's presence instead: the wrapper is the window marker.
set -u
D=/home/albus/strata166/w709
W=$D/watchdog2.log
PROD=strata166-402
mkdir -p "$D"
: > "$W"
echo "[$(date -Is)] watchdog2 up" >> "$W"
for i in $(seq 1 300); do
  sleep 20
  if ! pgrep -f 'w709/run_calib\.sh' >/dev/null 2>&1; then
    echo "[$(date -Is)] window wrapper gone (i=$i)" >> "$W"
    sleep 15
    if docker ps --format '{{.Names}}' | grep -qx "$PROD"; then
      echo "[$(date -Is)] $PROD already running" >> "$W"
    else
      docker start "$PROD" >> "$W" 2>&1
      echo "[$(date -Is)] watchdog2 started $PROD rc=$?" >> "$W"
    fi
    exit 0
  fi
done
echo "[$(date -Is)] watchdog2 TIMEOUT - forcing $PROD up" >> "$W"
docker start "$PROD" >> "$W" 2>&1
echo "[$(date -Is)] watchdog2 exit" >> "$W"
