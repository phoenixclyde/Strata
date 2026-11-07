#!/bin/bash
# 污染审计：进程 / 配置 / 显存 / 页缓存 / 我这几轮留下的文件
echo "########## 1 进程"
echo "-- ab_p4x 与客户端"
pgrep -af "ab_p4|mt_read|mt_gen|mt_hash|mt_chat|kl_gate|dec_gate|sweep.py" | grep -v pgrep || echo "  (none besides below)"
echo "-- 引擎进程（容器内）"
docker exec strata166-407 bash -lc 'pgrep -af "build-906/strata" || echo "  NO ENGINE"' 2>/dev/null
echo "-- 宿主机上任何 python/strata 长时间进程"
ps -eo pid,etimes,pcpu,rss,comm,args --sort=-rss | awk 'NR==1 || ($5 ~ /python|strata|ninja|cmake/)' | head -8

echo
echo "########## 2 配置（应当 = 生产：env 12 / args 33 / 无 --ple-io / 无 TIMING）"
python3 - <<'PY'
import json
p="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d=json.load(open(p))
e=d.get("env") or {}; a=d.get("args") or []
print("  env_n=%d args_n=%d" % (len(e), len(a)))
print("  env:", " ".join("%s=%s" % kv for kv in sorted(e.items())))
bad=[k for k in ("--ple-io","--no-ple-prefetch","--ple-row-cache") if k in a]
print("  ple args:", bad or "NONE")
print("  prefill:", a[a.index("--prefill")+1] if "--prefill" in a else "?")
print("  timing env:", [k for k in e if "TIMING" in k or "TRACE" in k] or "NONE")
PY

echo
echo "########## 3 显存"
for d in /sys/class/drm/card*/device; do [ -e $d/mem_info_vram_used ] && echo "  used=$(cat $d/mem_info_vram_used) total=$(cat $d/mem_info_vram_total)"; done
rocm-smi --showpids 2>/dev/null | head -12

echo
echo "########## 4 页缓存 / 内存"
grep -E "^(MemTotal|MemFree|MemAvailable|Cached|AnonPages|Mlocked)" /proc/meminfo | sed 's/^/  /'
echo "  26.8GiB 的 PLE 分片在页缓存里占多少："
grep -c . /proc/self/maps >/dev/null; python3 - <<'PY'
import os,struct
# 用 /proc/<pid>/smaps 太慢；这里只报告总 Cached，分片常驻在 PLEMAP 里单列
print("  (分片常驻见 maptop/plemap)")
PY

echo
echo "########## 5 我这轮留下的文件"
ls -la /home/albus/strata166/data/w81*_*.txt 2>/dev/null | tail -10
echo "-- 备份"
ls -la /home/albus/strata166/data/*.bak_w81* 2>/dev/null | tail -5
