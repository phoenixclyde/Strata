# -*- coding: utf-8 -*-
"""把 P83（STRATA_SH_STREAM）以 REJECTED 记入 register（--drop 会把行整条删掉，需重建）。"""
import io, time, shutil

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_p83_" + time.strftime("%Y%m%d_%H%M%S"))

EV = ("【W783 2026-10-25 实测否决】来源：上游自带的 tools/calibrate.py 在 166 上跑完（rc=0，1292 s），"
      "它自己的 sweep 里 STRATA_SH_STREAM=1 两次样本 41.63/38.35 tok/s，对比 =0 的 40.67/37.46，**两次都 +2.4%**，"
      "但未达它自己的 MIN_GAIN=0.03。我方同口径复核（唯一 nonce、reused=0、5 runs/档）："
      "M 档 prompt 486.8 / decode 60.1，对比基线 485.6 / 60.1 => **+0.25% / 0.00%**；"
      "S 档 prompt 413.9 / decode 65.7 对比 408.7 / 59.4 => +1.27% / +10.6%（S 档只出 320 token，decode 受首字开销污染，分辨率不足）。"
      "=> 在我们自己的三档 fixture 上不成立，判噪声。机理侧：该开关只把 shared expert 放到独立流，"
      "而 shared expert 在 gfx906 上本来就走 GPU、与专家流并行度有限，收益上限低。"
      "维持不设（AMD 默认：主流程）。回退位：删掉即恢复。")
NOTE = "否决：自测 M 档 +0.25%（噪声），校准器的 +2.4% 未复现"

rows = io.open(REG, encoding="utf-8-sig").read().splitlines()
new = "\t".join(["P83", "ENV", "STRATA_SH_STREAM", "1", "decode", "REJECTED", "-", "-", "-", EV, NOTE])
out = [ln for ln in rows if not ln.startswith("P83\t")]
# 插在 P82 之后（若存在），否则追加
idx = None
for i, ln in enumerate(out):
    if ln.startswith("P82\t"):
        idx = i
if idx is None:
    out.append(new)
else:
    out.insert(idx + 1, new)
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P83 written as REJECTED, rows:", len(out))
