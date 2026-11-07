#!/bin/bash
# 显存归零验证：停容器 -> 读 VRAM -> 启容器 -> 读 VRAM
echo "=== before"
echo "  used=$(cat /sys/class/drm/card0/device/mem_info_vram_used)"
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,+3p' | tail -2 | sed 's/^/  /'

echo "=== docker stop"
docker stop strata166-407 >/dev/null 2>&1
sleep 5
echo "  used=$(cat /sys/class/drm/card0/device/mem_info_vram_used)"
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,+3p' | tail -2 | sed 's/^/  /'
echo "  gtt=$(cat /sys/class/drm/card0/device/mem_info_gtt_used 2>/dev/null)"

echo "=== docker start"
docker start strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  ready=${i}s"; break; }; sleep 1; done
echo "  used=$(cat /sys/class/drm/card0/device/mem_info_vram_used)"
rocm-smi --showpids 2>/dev/null | sed -n '/KFD process/,+3p' | tail -2 | sed 's/^/  /'

echo "=== config"
python3 - <<'PY'
import json
p="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d=json.load(open(p))
e=d.get("env") or {}; a=d.get("args") or []
print("  env_n=%d args_n=%d ple_args=%s prefill=%s timing=%s"
      % (len(e), len(a), [k for k in a if "ple" in k] or "NONE",
         a[a.index("--prefill")+1], [k for k in e if "TIMING" in k or "TRACE" in k] or "NONE"))
PY
