#!/bin/bash
# W709 watchdog: independent safety net. If no calibrate run is alive and the production
# container is down, start the production container. Exits once handled or after ~65 min.
set -u
D=/home/albus/strata166/w709
W=$D/watchdog.log
PROD=strata166-402
mkdir -p "$D"
: > "$W"
echo "[$(date -Is)] watchdog up" >> "$W"
for i in $(seq 1 260); do
  sleep 15
  if ! pgrep -f 'calibrate\.py /data/strata-calib\.json' >/dev/null 2>&1; then
    echo "[$(date -Is)] no calibrate alive (i=$i)" >> "$W"
    sleep 12
    if docker ps --format '{{.Names}}' | grep -qx "$PROD"; then
      echo "[$(date -Is)] $PROD already running" >> "$W"
    else
      docker start "$PROD" >> "$W" 2>&1
      echo "[$(date -Is)] watchdog started $PROD rc=$?" >> "$W"
    fi
    break
  fi
done
echo "[$(date -Is)] watchdog exit" >> "$W"
