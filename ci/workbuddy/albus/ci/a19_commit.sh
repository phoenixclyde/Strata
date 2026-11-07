#!/usr/bin/env bash
# [W863 AUDIT19] Clean the tree, record the two debts, commit the roofline probe.
set -eu
REPO=/home/albus/strata166/pr/strata-fork
BAK=/home/albus/strata166/ci/state/backups
cd "$REPO"

echo "=== 1. move the src backup out of the tree (the gate forbids .bak under src/) ==="
mkdir -p "$BAK"
if [ -f src/kernels/cuda/fused_gr.cu.w863r28bak ]; then
  mv src/kernels/cuda/fused_gr.cu.w863r28bak "$BAK/fused_gr.cu.w863r28bak"
  echo "moved -> $BAK/fused_gr.cu.w863r28bak"
else
  echo "already clean"
fi

echo
echo "=== 2. record the two debts in docs/DOWNSTREAM.md ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
marker = "## 已知限制"
add = """## 两笔已知欠账（AUDIT19）

| # | 欠什么 | 影响 | 什么时候清 |
|---|---|---|---|
| **A11** | 镜像 `/src/serve/telemetry.py` 仍是旧版（缺 `self._thread` 的 CI 修复，提交 `c3574d42`） | 仅显示层的线程引用，**不影响推理** | 下次重建镜像（`0.2.9-102`）时随镜像带上；用 `docker exec strata166-407 md5sum /src/serve/telemetry.py` 与主线比对 |
| **A12** | `deploy/params/gen_config.py` 的 `META` 停在旧部署，跑 `--write` 会写坏生产 config | 改 config 只能手工定点改 + 双备份 | 修 `META` 之前不要用它生成 |

**为什么记在这里而不是只记在工作区文档**：这两条都是「clone 下来会踩到」的东西，
跟着代码走才有人看得到。

## 屋顶探针（R29 / AUDIT19）

`ci/probe/stream_roof.cpp` 测这张卡的**可达读屋顶**，是所有「带宽利用率」的分母。

实测（2026-11-01，gfx906，与生产同驻留）：**读 884 GB/s（86.3% 规格，1024）**、拷贝 752 GB/s；
并行度曲线：1 block/CU 55% → **4 blocks/CU 86%（峰）** → 8 blocks/CU 82%。

```bash
bash ci/probe/stream_roof_run.sh      # 容器内编译+运行，~40 s，只用 <=256 MiB 显存
```

换卡或换 ROCm 大版本后重跑一次即可刷新分母；不要再用「约 700」这种没有出处的数。

"""
if "## 两笔已知欠账（AUDIT19）" not in s:
    assert s.count(marker) == 1
    s = s.replace(marker, add + marker, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("docs/DOWNSTREAM.md updated")
else:
    print("docs already has the section")
PY

echo
echo "=== 3. gate must pass again (no .bak under src/) ==="
python3 ci/gate.py --repo . --source-only 2>&1 | tail -4

echo
echo "=== 4. commit + push ==="
git add src/kernels/cuda/fused_gr.cu ci/probe docs/DOWNSTREAM.md
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
perf(gr): record why a 34-byte Q8_0 block cannot take a 32-bit load; add the roofline probe

R28 asked whether the HC down kernel could replace its 32 scalar 2-byte loads with wide
loads. It cannot: a Q8_0 block is 2 + 32 = 34 bytes, so a block starts at 0 or 2 mod 4 and a
32-bit load of `q` is misaligned half the time (undefined on GCN). Widening would require
padding the pack format to 36 bytes, which is a format change, not a kernel change. The
arithmetic now lives next to the loads so nobody re-derives it wrongly.

ci/probe/stream_roof.cpp measures what every "% of peak" claim in the plan had been guessing
at: the achievable read roof on this card. Measured 884 GB/s (86.3% of the 1024 GB/s spec),
copy roof 752 GB/s, and a parallelism curve that peaks at 4 blocks/CU (1 block/CU only
reaches 55%). Decode reads and writes almost nothing, so 884 -- not 1024, and certainly not
the ~700 that was in use -- is the denominator.

Consequence: dense decode sits at 29.8% of the roof (was reported as 37%), and even the best
single kernel (native_mmvq at 2560x10240, ncols=2) only reaches 53%.
MSG
git --no-pager log --oneline -1
echo "--- clean? ---"
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2
