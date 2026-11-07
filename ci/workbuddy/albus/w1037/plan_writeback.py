import io, re, shutil, sys

PLAN = "deploy/W832_OPT_PLAN_V2.md"
BLOCK_TITLE = "### 回写 · W1037（2026-11-07 06:4x–07:2x）R103：A5 是死代码；J 上限与「还有 5.4× 空间」两支判否；开窗清单就位"
DIR_ROW = ("| `回写 · W1037（R103：A5 是死代码；J 上限与「还有 5.4× 空间」两支判否；开窗清单就位）` | "
           "开窗前先点开关：pa0 里五个 gfx906 开关只有四个在二进制里，A5 的派发仍包在 STRATA_EXPERIMENTAL_SM60 内 |")

BLOCK = """
### 回写 · W1037（2026-11-07 06:4x–07:2x）R103：A5 是死代码；J 上限与「还有 5.4× 空间」两支判否；开窗清单就位

> 生产 **0 重启 / 0 停机 / 0 装机**（pa1 只在 `build-port2`，`/data/bin` 仍是 `-001` 与上一轮的 `pa0`）。
> 账本 `P425` / `P426` / `P427`。分支 `gfx906/port-all` 多一个提交 `8b44f3d1`。

**一、A5 的开关根本没进二进制（`P425`）。** 开窗前先做了一件零成本的事：`strings <bin> | grep -c <VAR>`。
`pa0`（W1036 构建，md5 `e99455a0`）里五个 gfx906 开关只找到 **4 个**——`STRATA_GFX906_Q8_GATHER8` = 0。
根因在 `kv_q8.cu:221`：8-wide gather 的**派发**仍在 `#if defined(STRATA_EXPERIMENTAL_SM60)` 内，W1036 只把内核定义与
`pre75_q8_gather()` 放进了 `STRATA_HIP_GFX906` 分支 ⇒ 无人调用、链接时整个丢掉。**这一臂要是直接开窗，会被记成「零收益」**，
而不是「没跑」。派发处补 `|| defined(STRATA_HIP_GFX906)`（默认仍由 env 关着），重建 **pa1 = `36bc1be7` / 43,043,424 B**，
五开关 **5/5 在册**；`build-port2/strata` 与候选件同 md5（D1 身份）。
**新增门**：凡是「一分支一编译、逐项开关」的 A/B，开窗前必须点开关，成本 0。

**二、两支判否，都不开窗。**

| 支 | 结论 | 证据 |
|---|---|---|
| 「Q4_K 只到 J=64，MoE 白算」 | **判否** | 生产日志 **12,268 行** `pick_J` 统计 `ceil(ncols/J)*J/ncols`：中位数 **7.9%**、均值 **12.4%**，尾部全在 `ncols=1` 这类退化样本；gate/up 的 ncols≈3000–4000 ⇒ **≤1.8%**（3144→3200 列）。且 `ref/llama_3cf0325`（pin b11062）与 `ref/llama_b12169` 的 `mmq-config-gcn.cuh` **diff 为空** ⇒ 上游没有可移植的表改进；J 加倍只减块数/权重重读（−26% 流量），**不改 FLOPs** |
| 「预填内核还有 5.4× 空间」（`P423` 的表述） | **下修到 ≤1.69×** | `vecdotq.cuh:542-556` 的 Q4_K×Q8_1 内环每 **4 个 MAC 至少 3 条 lane 指令**（`v_lshrrev` / `v_and` / `v_dot4`），外加 v/u 取数。峰值 26.5 TMAC/s 按「1 条 dot4 = 4 MAC」算，3 条指令给的上限 = **8.8 TMAC/s**；2.5K gate/up 实测 3.93 TMAC / 754 ms = **5.21 TMAC/s** ⇒ 等价 **≈5.1 条指令 / 4 MAC**。要吃这 1.69× 只能让激活也变 4-bit（`v_dot8_i32_i4`），`P38` 已判否 |

**三、`P427` 不否掉 B1/B2，理由同一条尺子。** attn 分数内环现在是 **2.0 条指令 / MAC**（256 次 `(float)c*sc` 反量化 + 256 次 FMA，
一个 MAC 一条半），离 0.75 的下限还有 2.7×；换 dp4a 后 ≈0.27 条/MAC。**GEMM 侧已经贴顶，attn 侧没有**——这就是窗口只测 attn 的原因。

**四、为窗口定判据的相位账（同一批请求，n=2 同形状，`本机实测`）。**

| 形状 | GPU | `qsa attn` | `gemm gate/up` | `gemm down` | `dequant` |
|---|---|---|---|---|---|
| 3403 tok | 5358 ms | **575（10.7%）** | 1126（21.0%） | 691（12.9%） | 570（10.6%） |
| 10773 tok | 13543 ms | **2231（16.5%）** | 2651（19.6%） | 1677（12.4%） | 539（4.0%） |

⇒ attn 份额随长度从 10.7% 涨到 16.5%，B1/B2 的收益上限**随长度上升**，所以判据取 8K/10.8K 而不是 2K。

**五、上游（llama.cpp 最新）再核查。** 本地已存 pin `3cf0325`(b11062) 与 `b12169` 两棵树：`mmq-config-gcn.cuh` 逐字节相同；
Q4_K 表已有 `I=128` 行但 `J` 只到 64，Q8_0 到 128——**这是上游全局现状，不是我们落后**。
外网同卡实测（skyne98 `gfx906-dot4-dot8`，60CU@1725MHz）：`sdot4` 依赖链 21.7–22.3 TOPS、ILP4 43.0–44.4 TOPS
（= 10.9–22.2 TMAC/s，理论 26.5），`sdot8` 恰为 2×；且「热循环里做 QDQ」比纯 fp32 慢 3×，只有**摊薄转换**才有收益。
⇒ 与 `P427` 同向：**dot4 速率本身不是瓶颈，指令条数与摊薄方式才是**。

**六、开窗清单（等机主点头后执行，脚本已在 `/home/albus/strata166/tmp/w1037/`）。**

| 臂 | 二进制 | 开关 | 目的 |
|---|---|---|---|
| `ctl` | `strata-0.1.57-001` | 无（**不重启**，就在当前生产上测） | 当次基线 |
| `b` | `pa1` `36bc1be7` | `ATTN_DP4A=1` | B1+B2（decode + prefill 的分数相位） |
| `c` | `pa1` | `+ATTN_DPP +ATTN_LDS_PAD +ROUTE_DPP` | A1/A2/A3（bitwise，只判不劣化） |

每臂 5 条预填（2.5K×3 / 8K×2）+ 3 条 decode；**三次重启**（装机、加开关、还原）⇒ 预计 **5–8 min 不可用**。
安全：config 备份 + md5 校验还原（失败重试 sudo 后中止）、TERM 立即 `exit 130`、`exe` 只写容器路径、
单引擎断言、每臂预热 + 3 次重试 + 一次性盐值。配置改写已在副本上验过：只多一个 env 键，`args`/`model`/`port` 不变，还原后与原文语义相等。

**七、仍欠。** D2（`rocprofv3` 每 CU `SQ_INSTS` 方差、最忙/平均比）与 D3（rocBLAS 表 fallback 覆盖）都要独占窗口；
B3 前提已被 `P421` 否掉；C1（V 侧 fp16 累加）与 A4（逐文件 max-ilp）仍 defer。
"""


def main():
    s = io.open(PLAN, encoding="utf-8").read()
    if "回写 · W1037" in s:
        print("W1037 block already present")
        return 0
    shutil.copyfile(PLAN, PLAN + ".bak_w1037")
    lines = s.split("\n")
    # 1) append the block at the very end
    body = BLOCK.rstrip("\n").split("\n")
    lines = lines + [""] + body
    # 2) directory row after the last directory row
    last = max(i for i, l in enumerate(lines) if re.match(r"\| `回写 · ", l))
    lines[last + 1:last + 1] = [DIR_ROW]
    out = "\n".join(lines) + "\n"
    assert "回写 · W1037" in out and out != s
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(out)
    print("appended W1037 block + directory row after dir line", last + 1)

    # 3) §0.1 分母 + 队列
    s = io.open(PLAN, encoding="utf-8").read()
    a = "**366 条 / 已结 283 / 77.3%**（W1036 校正"
    b = "**369 条 / 已结 286 / 77.5%**（W1037 校正"
    if a in s:
        s = s.replace(a, b, 1)
    c = "就是本方案的一个 R）**"
    d = ("就是本方案的一个 R）**；**W1037**：pa1 `36bc1be7` 已构建、五开关 5/5 在册，"
         "J 上限（`P426`）与「5.4× 空间」（`P427`）两支**判否**，**待点头开窗**（三臂 / 三次重启 / 约 5–8 min）")
    if c in s and d not in s:
        s = s.replace(c, d, 1)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("§0.1 denominator + queue updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
