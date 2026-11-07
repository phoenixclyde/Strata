#!/bin/bash
# W709 calibrate window: exclusive-GPU run of tools/calibrate.py on the 0.1.40.2 image.
# Fail-safe: the production container is restored unconditionally at the end.
set -u
D=/home/albus/strata166/w709
OUT=$D/calib_out.json
RUN=$D/calib_run.log
PROD=strata166-402
TMP=strata-calib
IMG=strata-gfx906:0.1.40.2

mkdir -p "$D"
: > "$RUN"
log() { echo "[$(date -Is)] $*" >> "$RUN"; }

log "WINDOW_START"

# 0) 清理残留临时容器
docker rm -f "$TMP" >/dev/null 2>&1 || true

# 1) 停生产（graceful）
log "stopping $PROD"
docker stop -t 60 "$PROD" >> "$RUN" 2>&1
log "stop_rc=$?"
sleep 6
docker ps --format '{{.Names}}|{{.Status}}' >> "$RUN" 2>&1

# 2) 起临时容器（同镜像 / 同挂载 / 同设备 / 无 restart policy）
log "starting $TMP"
docker run -d --name "$TMP" \
  --device=/dev/kfd --device=/dev/dri \
  --ipc=host --ulimit memlock=-1 \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  -e STRATA_SRC=/src \
  -v /home/albus/strata166/data:/data \
  -v /home/albus/strata166/weights:/weights:ro \
  "$IMG" sleep infinity >> "$RUN" 2>&1
log "run_rc=$?"
sleep 4
if docker ps --format '{{.Names}}' | grep -qx "$TMP"; then log "TMP_UP=1"; else log "TMP_UP=0"; fi

# 3) 跑校准（独占 GPU）
log "calibrate start"
timeout 3300 docker exec "$TMP" bash -lc \
  'cd /src && python3 -u tools/calibrate.py /data/strata-calib.json' > "$OUT" 2>&1
log "CALIB_RC=$?"
log "calib_out_bytes=$(stat -c %s "$OUT" 2>/dev/null || echo 0)"

# 4) 无条件恢复生产
log "restoring $PROD"
docker rm -f "$TMP" >> "$RUN" 2>&1 || true
docker start "$PROD" >> "$RUN" 2>&1
log "start_rc=$?"
sleep 25
if docker ps --format '{{.Names}}' | grep -qx "$PROD"; then log "PROD_UP=1"; else log "PROD_UP=0"; fi
log "WINDOW_END"
