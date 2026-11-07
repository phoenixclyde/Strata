#!/usr/bin/env bash
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== 1. docs ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
marker = "两个测量陷阱，写在文件头注释里，因为都真的踩过："
add = """### 专家块的粒度（R26）

探针还带一个 3.13 MB 的形状：模型的每个 (layer, expert) 槽位就是这么大（21.79 GiB / 7463 槽），
一层读 8 个做样本。同一批字节：

| S | 只读 | 反量化+FMA | dp4a |
|---:|---:|---:|---:|
| 2 | 700 | 410 | 427 |
| 4 | 726 | 377 | 378 |
| 8 | 712 | 487 | 490 |

对比 HC 的形状（同样算术只剩 37% 的只读），这个粒度能保住 68% —— 因为一块要遍历九万个 Q8 块，
流水线填得满。所以"专家读慢"不是粒度问题。

账目：48 层 x top-10 x 3.13 MB x 96.5% 命中 = 1.45 GB/token、2.60 GB/窗口（dense 的 61%），
8.85 ms 对应 295 GB/s = 屋顶的 33%。生产比同算术的探针低 1.65x，那部分是内核结构，不是物理上限。

"""
if "专家块的粒度（R26）" not in s:
    assert s.count(marker) == 1
    s = s.replace(marker, add + marker, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("docs updated")
else:
    print("docs already updated")
PY

echo
echo "=== 2. gate ==="
python3 ci/gate.py --repo . --source-only 2>&1 | tail -3

echo
echo "=== 3. commit ==="
git add ci/probe docs/DOWNSTREAM.md
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
perf(decode): the expert read is 1.45 GB per token at 33% of the roof

R26 asked for the expert byte count, which nobody had ever worked out. Three sources, no guesses:

  * GGUF header (ci/r26_gguf_moe.py): 48 layers, 512 experts, top-10 used, N=2560, expert FFN 640
    -> 4.92M params per expert = 2.64 MiB at Q4_K; the cache slot measures 3.13 MB (21.79 GiB / 7463)
  * the engine already logs its own hit rate: "decode expert cache hit rate: 96.5%"
  * so 48 x 10 x 3.13 MB x 96.5% = 1.45 GB per token, 2.60 GB per window -- 61% of the dense
    weights (4.26 GB), for 2% of the experts.

At the measured 8.85 ms of "VRAM hits" that is 295 GB/s, 33% of the 884 GB/s read roof. Unlike the
hyper-connection read, this one is not arithmetic starved by its own shape: the probe's 3.13 MB
form reads at 712 GB/s and still does 487 with dequant+FMA on top (68%), because each block walks
ninety thousand Q8 blocks and keeps the pipeline full. Production is 1.65x below that, so the gap
is kernel structure -- grouped-GEMM launch and tail per expert, gather address generation, or the
M dimension wasted at ~10 tokens per expert -- not physics.

Worth ~3.5 ms per window (7.4%) if closed, and unlike dp4a it does not move the numbers.
MSG
git --no-pager log --oneline -1
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2

echo
echo "=== 4. tag r9 ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r9 -m 'MI50 drop r9: expert read accounted (1.45 GB/token, 295 GB/s = 33% of roof) and its 3.13 MB form measured in the probe. Engine binary unchanged.' HEAD
timeout 120 git push origin mi50-0.2.9-r9 2>&1 | tail -1
git describe --exact-match --tags HEAD
