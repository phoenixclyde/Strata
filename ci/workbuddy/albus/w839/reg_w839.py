#!/usr/bin/env python3
# W839-40 登记 P226 / P227，并把两条补丁写进 LOCAL_PATCHES.tsv
import io

REG = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
s = io.open(REG, encoding="utf-8").read()

rows = [
 ["P226", "MEASUREMENT",
  "gfx906 架构入口原本是死代码：arch_defaults.cpp 未被任何编译单元引用，链接器整块丢弃",
  "补上 STRATA_HIP_GFX906 下的调用点；生产 env 14→6（TUNED=1），实测等价",
  "measurement", "ADOPTED", "—", "—", "P224",
  ("证据：n2 与 W837 版 n3 里 nm 无 apply_arch_defaults、grep 无 MI50-class 字符串；"
   "generate.cpp.o 对 apply_arch_defaults 引用 0 处；编译宏只有 -DSTRATA_HIP_GFX906 与 -D__HIP_PLATFORM_AMD__，"
   "全 build.ninja 仅 1 处 -DSTRATA_USE_HIP（W776 给 dflash2.cpp），而调用点 generate.cpp:3355 在 #if defined(STRATA_USE_HIP) 内。"
   "改法：分支 commit 1309b1d，+23 行，在原 #1728 块前加一个 STRATA_HIP_GFX906 专属调用，同 CUDA 块同一套 all_igpu 判据，"
   "setenv(...,0) 保证用户设置优先，STRATA_GFX906_DEFAULTS=0 仍可整表关。"
   "验证：直接跑二进制出两行横幅（2 exact + 7 tuned）；三臂同镜像 0.2.8p2 各 8x128 decode + 3 档 read 中位——"
   "A(n3,14env) 51.60/4114/6045/9703；B(无调用点,5env) 50.35/7144(+74%)；B2(n3,6env含TUNED) 51.40/4065/6019/9704。"
   "B2 与 A 差 -0.4%/-1.2%/-0.4%/+0.0%（噪声内）⇒ 入口复现 9 条手工 env。"
   "落生产：exe n2→n3，env 14→6，args 33 不变，镜像不变；就绪后日志有 2 行横幅，"
   "显存 33.5/34.3GB(97.4%)、7463 槽/21.79GiB、借用 1578 槽/4.62GiB、预热 12820MB/s 与切换前逐项一致。"
   "方法教训两条：①/proc/pid/environ 不反映 setenv（是 exec 时快照），判据只能认横幅/行为；"
   "②部署物与构建产物必须当场核 md5——首轮 A/B 跑的是未含调用点的旧 n3。"),
  "已落生产。回滚：配置 .bak-w839 + 旧二进制 n2 均在。"],
 ["P227", "MEASUREMENT",
  "generate.cpp 里 28 个 STRATA_USE_HIP 条件块在 gfx906 构建中不生效（共 38 个块，仅 10 个含 STRATA_HIP_GFX906）",
  "不批量打开；候选仅 pcie_frac_auto / decode_defaults_arch_ok，需逐块加 || defined(STRATA_HIP_GFX906) 并单独 A/B",
  "measurement", "PROPOSED", "—", "—", "P226",
  ("静态清点（脚本对 src/program/generate.cpp 逐行匹配）：38 个 #if defined(STRATA_USE_HIP)，其中 28 个不含 STRATA_HIP_GFX906。"
   "对本机有意义的：2111/2124/2140/4948 的 decode_defaults_arch_ok() 与 2153 的 STRATA_PCIE_FRAC_DEFAULT=auto，"
   "以及 4208 的 pcie_frac_auto/pcie_probe_gbps——意味着单卡 pcie 分数自适应这条路在我们这套构建里从未存在，"
   "生产一直用固定 --pcie-frac 0.20（P209 判 UNRESOLVED）；另有 3713 的启动期架构校验（安全网）。"
   "风险已知：W717/P23 实测过全局 STRATA_USE_HIP 会切换 CUDA-only 路径，所以只能逐块放开。"
   "与 P222 同一条纪律：来自别的架构/别的构建形态的开关一律按未知处理，先单项测。"),
  "未打开任何一块；候选清单已记录。"],
]

for r in rows:
    assert len(r) == 11, (r[0], len(r))
    if ("\n" + r[0] + "\t") in ("\n" + s):
        print(r[0], "exists")
    else:
        s += "\t".join(r) + "\n"
        print(r[0], "added")
io.open(REG, "w", encoding="utf-8", newline="\n").write(s)
print("rows now:", len([l for l in s.split("\n") if l.strip()]) - 1)

# LOCAL_PATCHES.tsv 补两条
P = "D:/workbuddy_space/strata_ws/deploy/patches/LOCAL_PATCHES.tsv"
t = io.open(P, encoding="utf-8").read()
add = []
if "W837" not in t:
    add.append("W837\tsrc/core/arch_defaults.cpp\tMI50-class\tbranch+src028\t\"gfx906 精确表 2 项 + opt-in 配方 7 项 + gfx_arch_is_gfx906 谓词\"\t642de24f")
if "W839" not in t:
    add.append("W839\tsrc/program/generate.cpp\tW839 local\tbranch+patcher\t\"在 STRATA_HIP_GFX906 下调用 apply_arch_defaults；不复制整文件（main 与 v0.2.8 差数百行），由 patches/apply_w839_generate.py 锚点落\"\t1309b1d")
if add:
    if not t.endswith("\n"):
        t += "\n"
    t += "\n".join(add) + "\n"
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("LOCAL_PATCHES += %d rows" % len(add))
else:
    print("LOCAL_PATCHES already has both")
print("patch rows:", len([l for l in t.split("\n") if l.strip()]) - 1)
