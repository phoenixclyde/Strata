import io
import re

P = "deploy/W832_OPT_PLAN_V2.md"

BLOCK = """### 回写 · W1039（2026-11-07 08:5x–09:3x）按 b12180 配方重编 port-all：pa3/pa4 两次窗口，DP4A 慢 7%，DPP 中性

> 生产 **重启 6 次 / 停机 264 s（129 + 135）/ 装机 0（pa3、pa4 只做候选，AB 后已还原 b12180）**。
> config md5 回到 `5e9b81e2f66ca48999766d2ae0201fb6`，在产仍是 `strata-0.1.57-b12180`。账本 `P445`–`P448`。

**一、pa3 怎么来的，以及它凭什么可信（`P445`）。**
配方三件事：① `/out` 从 `build-port2` 整目录拷贝（继承全部 cmake flags，不手抄）；② `/llama.cpp` 换成
`tmp/w1037/llama-master`（就是 b12180 用的那棵树，`mmq.cuh` = `627c4c62`）；③ 重跑 `cmake -S /src -B /out -DSTRATA_MMQ_TQ_OVERLAY=ON`。
两条必踩的坑：**overlay 生成器在 port-all 里还是旧探测**（按 `get_nthreads` 推断 write-back 的第 5 个模板实参），对 b12180 必挂
⇒ 搬 pr/k10 的 W1037 修；**光换树不够，还要补 b12110 的 API 差**（`mul_mat_q_case` 加 `GGML_PREC_Q8` 26 处、
`ggml_cuda_mmq_get_config` 加精度参 5 处、`new_pool_for_device` 加 ctx 形参 1 处）。
**可复现性**：把 `build-pa3` 再拷一份、`ninja -t clean` 全量重编，得到**同一个 md5 `b2ba6304ddc848100ba72140e49ef9a9` / 43,306,640 B**
⇒ 既排除旧树残留目标文件，也证明该件可由配方重建（`REBUILD_RECIPE.tsv` 已登记，`recipe_check --live` PASS）。

**二、第一窗口：又是一次「改到死代码」（`P446`）。**
三臂 ctl(b12180) / pa3+`ATTN_DP4A` / pa3+`DPP`+`LDS_PAD`+`ROUTE_DPP`，每臂 2.5K×2 + 8K×2 + 16K×2。
`qsa attn` 8K **2238 → 2235 / 2232 ms**、16K **4731 → 4718 / 4750 ms**，整条 prefill 偏差 ≤0.15%（2×CV 0.19%）——逐毫秒不动。
根因：引擎启动横幅（日志 `:146006`）写着 *"the rounding-level recipe is on … GFX906_ATTN_QUERY_SWIZZLE …"*，
`use_query_swizzle` 为真；而 W1037 接的那段条件含 `!use_query_swizzle` ⇒ 永不成立。
生产实际跑 `attn_chunk_kernel<3,false,true,true>`，OPT 版是 `<M,false,false,false,OPT>`，**不是同一条实例化**。

**三、第二窗口：开关真的在跑了，结论是负的（`P447`）。**
pa4 把派发放进 `if (use_query_swizzle)` 内，改用 `attn_chunk_kernel<M,false,true,true,O>`（保留 swizzle+reduce12，只换内层）。

| 臂 | 8K `qsa attn` | 16K `qsa attn` | 8K 整条 prefill | 16K 整条 prefill | decode |
|---|---|---|---|---|---|
| ctl | 2234 ms | 4727 ms | 1253.0 µs/tok | 1278.9 µs/tok | 62.35 tok/s |
| **+DP4A** | **2387（+6.84%）** | **5074（+7.35%）** | **+1.07%**（2×CV 0.10%） | **+1.44%**（2×CV 0.51%） | 62.42 |
| +DPP | 2217（−0.76%） | 4705（−0.47%） | +0.10%（2×CV 0.86%） | +0.14%（2×CV 0.13%） | 60.75 |

**DP4A 显著变慢**（8K 白给 153 ms、16K 白给 347 ms）；DPP 中性偏负。机制推测：dp4a 分支每题要把 q 量化成 int8
（`sq8`/`sq8s`，`qsa_decode_attn.cu:199-200`）并把 `SQ_HEADS` 从 G 降到 1，量化 + LDS 搬运超过 dot 省下的；
V 累加仍是 fp32 `fmaf`，没被覆盖。**判决：B1(DPP) / B2(DP4A) 均不采用**，R103 的 attn 一支收口。

**四、顺带修掉一个静默正确性洞（`P448`）。**
`STRATA_ATTN_OPT_DISPATCH` 只有 `case 1/2/4`，`default: break;` 之后直接 `return;` ⇒ 同时开两个开关（如 `DPP|LDS_PAD` = 5）
会**一个 kernel 都不发就返回**，调用方照常 merge，输出是残留数据，**不报错**。已扩到 `case 1..7`。
第一窗口恰好被 swizzle 挡住，否则 c 臂测到的会是「零成本」的假象。
"""

def main():
    s = io.open(P, encoding="utf-8").read()
    if "### 回写 · W1039" not in s:
        if not s.endswith("\n"):
            s += "\n"
        s += "\n" + BLOCK + "\n"
        print("block appended")

    # directory row
    anchor = "| `回写 · W1038（2026-11-07 08:3x）"
    i = s.find(anchor)
    if i >= 0 and "回写 · W1039（2026-11-07 08:5x" not in s.split("### 6.5.0")[1][:8000]:
        j = s.find("\n", i)
        row = ("\n| `回写 · W1039（2026-11-07 08:5x–09:3x）按 b12180 配方重编 port-all：pa3/pa4 两次窗口，DP4A 慢 7%，DPP 中性`"
               " | pa3 用 b12180 的 llama 树重编并 clean-rebuild 位相同；第一窗口三臂零效果是因为生产开着 QUERY_SWIZZLE、"
               "W1037 的 OPT 分支被 `!use_query_swizzle` 挡住；pa4 搬进 swizzle 分支后 DP4A 让 attn 慢 6.8%/7.35% |")
        s = s[:j] + row + s[j:]
        print("directory row inserted")
        m = re.search(r"共 \*\*(\d+)\*\* 块", s)
        if m and int(m.group(1)) == 27:
            s = s.replace("共 **27** 块", "共 **28** 块", 1)
            print("directory count -> 28")

    # denominator
    s2 = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1038 校正",
                "**391 条 / 已结 306 / 78.3%**（W1039 校正", s, count=1)
    print("denom:", "ok" if s2 != s else "MISS")
    s = s2

    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("len", len(s))


if __name__ == "__main__":
    main()
