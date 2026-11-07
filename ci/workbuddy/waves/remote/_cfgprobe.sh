#!/bin/bash
C=strata166-402
F=/home/albus/strata166/data/strata-ud-iq4_xs.log

echo "===== [A] 容器全部环境变量 ====="
docker inspect "$C" --format '{{json .Config.Env}}' | tr ',' '\n' | sed 's/^\[//;s/\]$//' | sed 's/"//g'
echo

echo "===== [B] 服务配置 JSON ====="
cat /home/albus/strata166/data/strata-ud-iq4_xs.json
echo

echo "===== [C] 当前这次启动的启动块（最后一次 'engine started' 之后 60 行）====="
N=$(grep -n 'engine started' "$F" | tail -1 | cut -d: -f1)
echo "最后一次 engine started 在 L$N（共 $(wc -l < "$F") 行）"
sed -n "${N},$((N+55))p" "$F"
echo

echo "===== [D] 引擎完整 --help ====="
docker exec "$C" bash -lc '/src/build-906/strata --help 2>&1'
echo

echo "===== [E] docs 里 gfx906 相关的环境开关（AMD_HIP.md 全文里出现过的 STRATA_*）====="
docker exec "$C" bash -lc "grep -ohE 'STRATA_[A-Z0-9_]+' /src/docs/AMD_HIP.md | sort -u"
echo
echo "===== [F] docs/DETAILS.md 里的环境开关（去重）====="
docker exec "$C" bash -lc "grep -ohE 'STRATA_[A-Z0-9_]+' /src/docs/DETAILS.md | sort -u | head -80"
echo
echo "===== [G] /src/data 是否可写 + expert-profile.bin 信息 ====="
docker exec "$C" bash -lc 'ls -la /src/data/ | head -12; echo ---; touch /src/data/.wtest && echo "可写: yes" && rm -f /src/data/.wtest'
