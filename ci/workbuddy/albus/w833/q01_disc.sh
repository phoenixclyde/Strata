#!/bin/bash
L=/data/strata-huihui-ud-iq4_xs.log
C=strata166-407
echo "=== [1] 引擎日志里能量化的行（末 3 条） ==="
for pat in "expert cache" "arena" "slots" "resident" "GiB" "swapped"; do
  echo "--- $pat ---"
  docker exec $C bash -lc "grep -aiE '$pat' $L 2>/dev/null | tail -3 | cut -c1-170" 2>&1
done
echo
echo "=== [2] /metrics 顶层键 ==="
curl -s --max-time 8 http://127.0.0.1:8090/metrics > /tmp/m.json 2>/dev/null
python3 - <<'PY'
import json
try:
    d=json.load(open('/tmp/m.json'))
    print("top keys:", list(d.keys())[:20])
    h=d.get("hardware") or {}
    print("hardware keys:", sorted(h.keys())[:24])
    for k in ("gpu_vram_used_mb","gpu_vram_total_mb","gpu_pcie_rx_mb","gpu_power","gpu_temp","cpu"):
        if k in h: print("  ", k, "=", h[k])
    s=d.get("stats") or {}
    print("stats keys:", sorted(s.keys())[:20] if isinstance(s,dict) else type(s))
except Exception as e:
    print("ERR", e)
PY
echo
echo "=== [3] rocm-smi 显存 ==="
docker exec $C bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | tail -8' 2>&1 | head -12
