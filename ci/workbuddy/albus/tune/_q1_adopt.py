# -*- coding: utf-8 -*-
"""Q1 定案：采纳「去 --resident-experts」（P66 -> REJECTED，新增 P89 记录三档 A/B），随后推送重启。"""
import io, os, sys, time, shutil, subprocess

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py"
PUSH = r"D:/workbuddy_space/strata_ws/albus/tune/_c1_push.py"
PY = sys.executable

EV = ("【W785-Q1 2026-10-25 定案：去 --resident-experts 胜】交错 A/B（base/nores/base/nores，每臂 2 轮 x 5 runs，"
      "同一 M 档 21,827 token，greedy）：decode 逐次 base 46.4,55.3,57.6,61.9,62.8 / 46.2,55.9,61.2,62.8,61.7（中位 61.2）；"
      "nores 54.9,64.4,67.6,70.5,68.9 / 54.4,66.0,67.0,67.6,65.7（中位 67.6）= **+10.5%**。"
      "**混淆因子已排除**：spec 接受率 base 95.8/95.9% vs nores 96.4/95.8%（差 <=0.6 点），prompt_tps 488.2 vs 488.8（+0.1%）。"
      "三档复核：S 408.8/62.6 -> **429.5/70.0**（prompt +5.1%, decode +11.8%）；M 488.2/61.2 -> 488.8/67.6（+0.1%/+10.5%）；"
      "L 464.9/33.8 -> 468.1/42.6（+0.7%/+26%，该档仅 32 token，分辨率低）。三档同向，prompt 不减。"
      "**机理**：`--resident-experts` = `--mmap-experts --resident-cpu-experts --resident-pin --resident-soft`，"
      "会把 36.93 GiB 专家副本 mlock 成常驻（`generate.cpp:2482-2492`）；去掉后专家落 page cache：实测 RAM used 46.9 -> 64.9 GB、"
      "MemAvailable 83.7 -> 65.2 GB，页缓存能覆盖更多 55.4 GiB 专家集，CPU 侧（`waitCPU` 4.01 ms/window，P87）读专家更少打到磁盘。"
      "**代价**：arena_mib 37495 -> 56762（虚拟地址，非物理）；冷读路径少了 pinned 副本（W28D 曾测 prefill 冷读 -2.5%），"
      "但本次 S 档 prompt 反而 +5.1%，说明在新版（0.1.49.2）上该代价已不成立。"
      "**风险控制**：SwapFree 16777200 kB（未换出）；slots 9901 不变；verify PASS=29 FAIL=0。回退 = 把 P66 改回 ADOPTED 并重启。")

rows = io.open(REG, encoding="utf-8-sig").read().splitlines()
shutil.copy2(REG, REG + ".bak_q1adopt_" + time.strftime("%Y%m%d_%H%M%S"))
out = []
for ln in rows:
    if ln.startswith("P66\t"):
        f = ln.split("\t")
        f[5] = "REJECTED"
        f[10] = "否决：去 resident 后 decode 三档 +10.5~11.8%，prompt 不减（详见 P89）"
        ln = "\t".join(f)
    out.append(ln)
out = [ln for ln in out if not ln.startswith("P89\t")]
out.append("\t".join(["P89", "REF", "--resident-experts 三档 A/B", "去 resident 胜", "vram", "REFERENCE",
                      "-", "-", "-", EV, "采纳去 resident：S +5.1%/+11.8%、M +0.1%/+10.5%、L +0.7%/+26%"]))
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("register updated, rows:", len(out))

subprocess.run([PY, GEN, "--write"], cwd=os.path.dirname(GEN), check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("gen_config written")
r = subprocess.run([PY, PUSH], capture_output=True, text=True, timeout=1200)
print(r.stdout[-1200:])
