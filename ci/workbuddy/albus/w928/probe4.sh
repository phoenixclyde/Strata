#!/bin/bash
set -u
P=~/strata166/pr/strata-fork
F=$P/src/kernels/cuda/qsa_prompt_attn.cu
echo "########## A. KV_MODE 1（int8 K/V）里 p.v 怎么算 ##########"
grep -n "KV_MODE == 1\|KV_MODE == 4\|VElem\|p\.v\|__hfma2\|__half2float\|dp4a" $F 2>/dev/null | sed -n '1,40p'

echo
echo "########## B. mode1 的 V 点积具体几行 ##########"
sed -n '/KV_MODE == 1/,/^$/p' $F 2>/dev/null | grep -nE "dot|sum|v_|acc" | head -12
echo "--- 找 v 的累加循环 ---"
grep -n "for (int d = 0" -A 12 $F 2>/dev/null | head -30

echo
echo "########## C. 816 B/cell 的出处（k8v4 vs int8 显存） ##########"
grep -rn "816\|B/cell\|bytes_per_cell\|cell_bytes" --include=*.hpp --include=*.cpp --include=*.cuh $P/include $P/src/core 2>/dev/null | head -10

echo
echo "########## D. P 记录里 kv 相关的已有结论 ##########"
cd "D:/workbuddy_space/strata_ws/deploy" 2>/dev/null
python3 - <<'PY'
import io
rows = io.open("params/PARAM_REGISTER.tsv", encoding="utf-8").read().split("\n")
for r in rows:
    f = r.split("\t")
    if len(f) > 8 and ("kv" in f[2].lower() or "KV" in f[2]):
        print("%-8s %-34s %-12s %s" % (f[0], f[2][:34], f[3][:12], f[7] if len(f)>7 else ""))
PY
