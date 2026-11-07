#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1045 close-out: ledger, plan write-back, snapshot, memory."""
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
HAND = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")

ROWS = [
    ["B4上游移植", "P517", "R103 移植面盘点：全量方案只落 B1 一条，B2/B3/A1/A5 未移植，A2/A3 与诊断位移植了没开",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 分支 diff 实测**：`port-all@91a7c5a4` 相对 `e181bda5` 改 **10 文件**（483+/93−），"
     "在产 `gfx906/attn-opt@deb41e12` 相对 `gfx906/lcpp-k10` **只改 1 文件** `qsa_decode_attn.cu`（219+/23−）。"
     "A1（`native_router.cu` 144 行）、A5（`kv_q8.cu` 15 行）在 k10 树 `git diff` 为空 ⇒ **未移植**；"
     "A2(bit2)/A3(bit0) 在 `qsa_decode_attn.cu:1066-1068` 但生产只开 bit1 ⇒ **移植了没落生产**；"
     "port-all 的 F16D/CTLREAD/F16Q（`:1143-1145`）未进生产；dot8 核心 0 调用点被 DCE。"
     "**最重结论**：B2（`qsa_pattn.cu:146-181`）与 B3（`fused_gr.cu:114-121` `dot8q` 仍是 8 次 `fmaf`）"
     "在 k10 与 port-all **两棵树都没改过**；`P435` 早已更正预填吃的是 `qsa_prompt_attn_batch`"
     "（`qsa_prompt_attn.cu:353-356` fp32 `fmaf`）⇒ B2 是落点没开工，不是差一步。"
     "**可挖排序**：B2 > B3 > A1 > A5 > A2/A3 单开关 A/B > A4。",
     "P420;P435", "KW:qsa_pattn.cu|fused_gr.cu|未移植"],

    ["B6判定探针", "P518", "dot4 硬件/软件现状逐 TU 实测：硬件 8 万余条、软件痕迹 <0.5%、dot8 全树 0 条、fused_gr 真空",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 ISA 实测**（单 TU 拆 `.hip_fatbin` 才是正确取样面；整机 28 MB fatbin 用 `llvm-objdump` 只出 235 行是假的）："
     "`qsa_decode_attn.cu.o` `v_dot4_i32_i8`=**384**、`iq_kernels.cu.o`=**44,746**、`native_mmvq.cu.o`=**37,464**；"
     "`v_dot8_i32_i4` 全树 **0**；`v_mad_i32_i24` 仅 34/195/87；`fused_gr.cu.o` `v_dot4`=**0**、`v_fmac_f32`=**81,240**。"
     "生效层 `include/strata/platform/hip_compat/strata_hip.h:237-251`：`strata_dp4a(int,…)` 在 `__gfx906__` 走 "
     "`__builtin_amdgcn_sdot4`（硬件），`strata_dp4a(unsigned int,…)` 在 `:246-250` 是 4 次逐字节乘加（**软件回退**）"
     "⇒ **两者同时存在、按符号分流**，不是非此即彼。`hip_compat/intrinsics.hpp:18` 仍是死文件（W1042 已纠错）。"
     "真正待办不是硬件/软件之争，而是 `fused_gr` 一条 dot4 都没有（=B3 真空）。",
     "P500;P501", "KW:v_dot4_i32_i8|软件回退|81,240"],

    ["B6判定探针", "P519", "dot8 该试：外证 2× 吞吐，但队列早有 R91/R74，且需先过 roofline 与 W4A4 离线门",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 上网核**：skyne98 gfx906 实测 `sdot8`≈44 TOPS vs `sdot4`≈22 TOPS（**2×**），ILP4 下 86 vs 43 TOPS；"
     "ROCm `AMDGPUAsmGFX906.html` 确认 `v_dot8_i32_i4` 可用、`dot4c/dot8c` 不可用、`gfx9-generic` 排除这些指令；"
     "LLVM 明确 32 位累加器可溢出、`clamp=false` 回绕。外证强调「**仅当布局支持 4-bit 打包**」。"
     "**队列纠错**：dot8 接入早有 `R91`（六子任务）与前置 `R74`（W4A4 精度门），我 W1042 又立 `R108` 属**重复**，"
     "本轮只标注建议合并、未改队列行。**两条路线**：(a) Q4_K 权重 MMQ（权重本就 4-bit，激活 Q8_1→int4）= R91；"
     "(b) k8v4 的 V 侧 4-bit 需 `p→int4`（softmax 概率是 float），新增误差源 ⇒ 不先做。"
     "**零停机三步预注册**：① 微基准 roofline（`GFX906_OPT_INVENTORY §8` 已记 gather 型 kernel 上 ALU 换指令无效、dp4a 已满速，"
     "若 memory-bound 直接判否）；② 离线 W4A4 精度门 `R74`（KL/top-1，不动内核）；③ 才做 `R91` P1–P6 单变量 A/B。",
     "R91;R74;P501", "KW:44 TOPS|W4A4|R108"],

    ["B10环境与版本", "P520", "K10 的 mmq 溯源：不是移植算法，是 llama.cpp 升 pin 的 API 对齐；现在是落后 5 提交的混合树",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 源码+GitHub API 双证**。`fa8e6761` 提交 message 逐字：`mul_mat_q_case<type> → <type,GGML_PREC_Q8>`"
     "（llama.cpp **#30168**）25 处、`ggml_cuda_mmq_get_config(..,cc) → (..,cc,GGML_PREC_Q8)` 5 处、"
     "`new_pool_for_device` 加 ctx 1 处、cmake overlay 改探测签名；共 6 文件 39+/33−，`moe_mmq.cu` 的 25/25 行全是签名。"
     "`mmq*` 来自上游 **`4c1004c49221…`（2026-10-19）**，API 核实为 **#30553 `cap MMQ Stream-K blocks at available work`**，"
     "只改 `ggml/src/ggml-cuda/mmq.cuh` 一个文件。生产主体已升 **b12180 = master `bcb01528`（2026-11-06）** ⇒ **混合树**。"
     "**更好的移植确实存在**：API 列 4c1004c 之后 `mmq.cuh` 还有 5 提交 —— `1a24df16`(10-23 **#30837 DP4A tile height 与 warp size，"
     "wave64 的 gfx906 直接相关**)、`c49edf09`(#29948)、`eb4e244b`(#31373 RDNA4 不适用)、`5ce06fc7`(#31296)、`69ee2ecc`(#31047)。"
     "本树口子：`src/prefill/moe_mmq.cu:386` 的 `pick_J()` 自遍历 J=8..128，上游已有 `ggml_cuda_mmq_get_J_best()`；"
     "`GGML_CUDA_MMQ_PREC` 的 q4 激活需 Blackwell MMA，gfx906 走不了。**换 mmq 要重编+数值门+A/B，不能盲跟**。",
     "P430;R90", "KW:4c1004c|#30553|混合树"],

    ["B8工程", "P521", "CI/CD 覆盖审计：本轮装机分支无 CI run、gh_gate 未走、脚本未版本化、pre-push 缺位",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 实测**（对照 `strata-ci-cd` 技能 13 节点）。`downstream-gate.yml` 白名单分支 `main`/`gfx906/mi50`/`ci/**`，"
     "paths `src/**` `include/**` `CMakeLists.txt` `ci/**` + workflow 自身 ⇒ **`tools/**` 不在 paths**。"
     "GitHub API 最近 20 次 run 全是 11-05/11-06、最新 sha `e181bda5`；`af797b90`(kvg)/`deb41e12`(attn)/`e0ce7c96`(dot48) "
     "**一次 run 都没有** ⇒ 今天 CI 零触发（三个分支已推 origin，但都不在白名单）。"
     "`pr/strata-fork` 有 pre-push 钩子，**`pr/k10/.git/hooks/pre-push` 不存在** ⇒ 这些 push 连 `round_gate.py --ci` 都没跑。"
     "`ci/deploy.sh:41` 的 `0/8 gh_gate` 与 `:96` 的 `3.5/8 evidence gate` 都在，但 W1040/W1044 走**手工停/起**，"
     "六条门是本机 `tools/deploy_gate.py` 手工补跑的。`deploy/`、`albus/`、本机 `tools/` **都不是 git 仓库**；"
     "`window_w1044.sh`/`finish_install.sh`/`judge.py`/`kl_extract.py`/`longctx_needle.py` 的 `git ls-files` 计数全为 0，"
     "只有 `gfx906/dot48` 的 5 个文件进了 git；权威件靠 `mirror_check.py --sync` 7 件同步（是同步不是版本化）。"
     "⇒ **五条缺口** + 第六个实证见 `P522`：没有任何门拦住对在产二进制的写操作。",
     "P491", "KW:白名单|gh_gate|ls-files"],

    ["B8工程", "P522", "【事故+恢复】审计时 llvm-objcopy 原地改写在产二进制，已恢复并新增 binary_integrity 机械门",
     "W1045", "count", "1", "1", "DONE",
     "**W1045 18:20 实测事故（我自己造成）**：拆 ISA 时 `llvm-objcopy --dump-section .hip_fatbin=… <file>` "
     "**没给输出文件** ⇒ 原地改写输入并移除该 section（W940 同款根因）。在产 `/data/bin/strata-0.1.57-attn` "
     "从 43,452,008 B / `3b758f88…` 变成 43,425,632 B / `2d2b7490…`；运行进程持旧 inode "
     "(`/proc/20/exe -> …attn (deleted)`，md5 仍 `3b758f88…`)，服务正常但**下次重启会加载缺设备代码的坏件**。"
     "**处置（零停机）**：用逐字节相同的 `dot48`（`3b758f88…`/43,452,008 B）按 `cp → .new → mv` 原子替换恢复，"
     "复核 disk = running = SNAPSHOT 三方 md5 全等、health ok；坏件留证 `tmp/attn_objcopy_damaged.bin`；"
     "同命令改写的 **6 个构建 `.o`** 移到 `tmp/w1045/damaged_objects/`，让 ninja 下次重编。"
     "**防再犯（机械）**：新增 `tools/binary_integrity.py`（`--live` 比对 disk/running/SNAPSHOT md5，`--self-test` **5/5**，"
     "`(deleted)` 且内容一致只 WARN 不 FAIL，因铁律判 md5 非 inode）；`albus/w1045/isa_audit.sh` 加双保险"
     "（拒绝 `/data/bin/*`、先复制副本、给 objcopy 显式输出文件）；`/data/bin` 挂载一律 `:ro`。"
     "**这正是 `P521` 的第六个实证**：当时没有任何一道门拦住对在产二进制的写操作，靠人工事后发现。",
     "P521", "KW:llvm-objcopy|binary_integrity|零停机"],
]


def main():
    lines = io.open(P, encoding="utf-8").read().splitlines()
    have = {l.split("\t")[1] for l in lines if l.count("\t") >= 9 and not l.startswith("#")}
    for r in ROWS:
        assert len(r) == 11 and all("\t" not in x for x in r), r[1]
        whole = " ".join(r)
        for kw in r[10].replace("KW:", "").split("|"):
            assert kw in whole, "%s KW %r missing" % (r[1], kw)
    todo = [r for r in ROWS if r[1] not in have]
    n107 = 0
    for i, l in enumerate(lines):
        f = l.split("\t")
        if len(f) >= 11 and f[1] == "R107":
            f[2] = f[2].replace("13 轮连续未审", "14 轮连续未审")
            f[8] = f[8].replace("`13 unaudited rounds in a row (> 8)`（W1032–W1044",
                                "`14 unaudited rounds in a row (> 8)`（W1032–W1045")
            f[8] = f[8].replace("W1040 W1041 W1042 W1043 W1044", "W1040 W1041 W1042 W1043 W1044 W1045")
            f[10] = "KW:AUDIT29|14 轮连续未审|audit_scope"
            lines[i] = "\t".join(f)
            n107 += 1
    assert n107 == 1, n107
    lines += ["\t".join(r) for r in todo]
    io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    tot = done = 0
    for l in io.open(P, encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
            try:
                tot += int(f[5]); done += int(f[6])
            except ValueError:
                pass
    pct = 100.0 * done / tot
    print("TOTALS %d / %d / %.1f%% (+%d rows)" % (tot, done, pct, len(todo)))

    s = io.open(PLAN, encoding="utf-8").read()
    s = re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1044；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1045；" % (tot, done, pct), s, count=1)
    title = "### 回写 · W1045（2026-11-07 18:1x–18:5x）五问审计：移植面 / dot4 / dot8 / mmq / CI-CD"
    if title not in s:
        block = """__TITLE__

- **生产零变更**：`attn`（`3b758f88…`）+ config `3dde8801…`；**重启 0 / 停机 0 / 装机 0 / 回滚 0**。唯一写操作是修复审计工具造成的资产损伤。
- **事故与恢复（`P522`）**：`llvm-objcopy --dump-section` 没给输出文件 ⇒ **原地改写在产二进制**（W940 同款），18:20 磁盘件 `3b758f88…`→`2d2b7490…`、少 26,376 B；运行进程持旧 inode 服务正常但重启会加载坏件。已用同 md5 的 `dot48` 副本 `cp→.new→mv` 恢复，disk=running=SNAPSHOT、health ok、**零停机**；6 个被改写的 `.o` 移出构建树。新增 `tools/binary_integrity.py`（5/5 自测，`--live` PASS），`isa_audit.sh` 加副本+显式输出+拒绝 `/data/bin` 三保险。**没有任何一道门事先拦住这次写操作**。
- **R103 移植面（`P517`）**：`port-all` 改 10 文件，在产 `attn-opt` 只取 1 个 ⇒ **只落 B1 一条**。A1/A5 未移植、A2/A3 与三个诊断位移植了没开；**B2（`qsa_pattn.cu`）与 B3（`fused_gr.cu`）两棵树都没改**，而 B2 是方案里「最值钱」的一条。可挖排序 B2 > B3 > A1 > A5 > A2/A3 > A4。
- **dot4（`P518`）**：逐 TU ISA 实测硬件 `v_dot4_i32_i8` 384 / 44,746 / 37,464 条，软件回退只在 `strata_hip.h:246-250` 的 unsigned 重载；**dot8 全树 0 条**；`fused_gr` 0 条 dot4、81,240 条 fp32 FMA = 最明确真空。
- **dot8（`P519`，机主判断「要试」成立）**：外证 gfx906 `sdot8` 2× `sdot4`（44 vs 22 TOPS），但 `R91`+前置 `R74` 早有、`R108` 重复待合并；先做零停机 roofline + 离线 W4A4 精度门，再谈内核接入。
- **mmq（`P520`）**：K10 = llama.cpp 升 pin 的 **API 对齐**（#30168 等 25+5+1 处），`mmq*` 来自上游 `4c1004c`(10-19 **#30553**)；主体 b12180(11-06) ⇒ **混合树**，`mmq.cuh` 落后 5 提交（含 #30837 DP4A tile height，wave64 相关）。
- **CI/CD（`P521`）**：本轮三个装机分支已推 origin 但都不在白名单 ⇒ 今天 CI 零触发；`0/8 gh_gate` 未走；`pr/k10` 无 pre-push；窗口/判据脚本 `git ls-files` 计数为 0；`deploy/`/`albus/`/`tools/` 非 git 仓库。五条缺口 + 事故为第六实证。
- **边界**：只读审计 + 资产修复，未编译/未提交/未停机；dot8 roofline 与 W4A4 门是建议不是结论；`audit_scope §A` = **14 轮连续未审**，仍 FAIL。
""".replace("__TITLE__", title)
        s = s.rstrip("\n") + "\n\n" + block
        t0 = s.index("| 小节 |")
        last = s.rfind("| `回写 ·", t0, s.index("> **【AUDIT27", t0) if "> **【AUDIT27" in s[t0:] else t0 + 90000)
        assert last > 0
        eol = s.index("\n", last) + 1
        row = ("| `回写 · W1045（2026-11-07 18:1x–18:5x）五问审计：移植面 / dot4 / dot8 / mmq / CI-CD` | "
               "objcopy 事故恢复；R103 只落 B1；dot4 硬件主力；dot8 先过 roofline；mmq 混合树；CI 五缺口 | W1045 |\n")
        s = s[:eol] + row + s[eol:]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("plan written")

    h = io.open(HAND, encoding="utf-8").read()
    h2, n = re.subn(r"(> SNAPSHOT: round=)W\d{4}", r"\g<1>W1045", h, count=1)
    assert n == 1
    io.open(HAND, "w", encoding="utf-8", newline="\n").write(h2)
    print("snapshot -> W1045")

    m = io.open(MEM, encoding="utf-8").read()
    if "### W1045（" not in m:
        add = """
### W1045（18:14–18:5x）五问审计（只读）+ objcopy 事故恢复

- **生产零变更**：`attn` `3b758f88` + config `3dde8801`；**重启 0 / 停机 0 / 装机 0 / 回滚 0**。
- **【事故】** 拆 ISA 时 `llvm-objcopy --dump-section` 无输出文件 ⇒ **原地改写在产二进制**（W940 同款）：18:20 `3b758f88…`→`2d2b7490…`（少 26,376 B），运行进程持 deleted inode 正常但重启会加载坏件。已用 `dot48`（同 md5）`cp→.new→mv` 恢复，disk=running=SNAPSHOT、health ok、**零停机**；6 个被改写 `.o` 移到 `tmp/w1045/damaged_objects/`。新增 `tools/binary_integrity.py`（5/5 + --live PASS），`isa_audit.sh` 改副本+显式输出+拒绝 `/data/bin`。**铁律**：ISA 拆解绝不碰 `/data/bin`，挂载必须 `:ro`。
- **Q1 R103**：`port-all` 改 10 文件、在产 `attn-opt` 只取 1 个 ⇒ **只落 B1**。A1/A5 未移植；A2/A3+三诊断位移植没开；**B2 `qsa_pattn.cu` / B3 `fused_gr.cu` 两树都没改**（B2 是方案最值钱项，P435 已指落点错）。可挖 B2>B3>A1>A5>A2/A3>A4。
- **Q2 dot4**：生效层 `strata_hip.h:237`(int→`sdot4` 硬件) 与 `:246`(unsigned→软件 4 次乘加) **并存按符号分流**。ISA：attn 384 / iq 44746 / mmvq 37464 条 `v_dot4_i32_i8`，`v_mad_i32_i24` <0.5%；**dot8 全树 0**；`fused_gr` 0 dot4 / 81240 `v_fmac_f32`。
- **Q3 dot8**：要试（外证 2× 吞吐 44 vs 22 TOPS、ILP4 86 vs 43、必须 `--offload-arch=gfx906`、`dot8c` 不可用、累加器回绕）。但 `R91`+`R74` 早有、`R108` 重复待合并；先零停机 roofline（gather 型可能 memory-bound）+ 离线 W4A4 精度门，再谈接入。
- **Q4 mmq**：K10 **不是移植算法**，是 llama.cpp 升 pin 的 API 对齐（#30168：`GGML_PREC_Q8` 25+5 处、new_pool ctx、cmake 签名）；`mmq*` 来自 `4c1004c`(10-19 **#30553 Stream-K cap**)，主体 b12180(11-06) ⇒ **混合树**，`mmq.cuh` 落后 5 提交（#30837 DP4A tile height 与 wave64 相关）。
- **Q5 CI/CD**：三个装机分支已推但不在白名单 ⇒ 今天 CI 零触发（最近 run 最新 sha `e181bda5`）；`0/8 gh_gate` 未走；`pr/k10` 无 pre-push；窗口脚本 `git ls-files`=0；`deploy/`/`albus/`/`tools/` 非 git。五缺口 + 事故是第六实证。
- 进度 **__TOT__ 条 / 已结 __DONE__ / __PCT__%**；`audit_scope §A` = **14 轮连续未审**。
""".replace("__TOT__", str(tot)).replace("__DONE__", str(done)).replace("__PCT__", "%.1f" % pct)
        io.open(MEM, "w", encoding="utf-8", newline="\n").write(m.rstrip("\n") + "\n" + add)
        print("memory appended")


if __name__ == "__main__":
    main()
