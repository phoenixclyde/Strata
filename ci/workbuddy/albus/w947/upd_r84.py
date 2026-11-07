# -*- coding: utf-8 -*-
import io
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
ADD = (" 【W947 进度 2026-11-04 16:1x｜A 级，未结题】产物 `~/strata166/w947/q4k_dot8.cu`（M=1）与 `q4k_gemm_dot8.cu`（M=64）。"
       "①`sdot8` 在 `--offload-arch=gfx906` 下编译并运行 no error，语义同 W909（0xFF nibble = -1）；"
       "②数学恒等式已证：u4 经 `^0x88888888` 按 s4 解释即 q-8，`sum((q-8)a) + 8 sum(a) == sum(q a)`，20000 组随机 **0 违反**"
       "（首版脚本写成 `((q^8)-8)` 得 19433/20000 违反，那是脚本错）；"
       "③M=64 GEMM 两臂 rel_l2 = **0.99481（dp4a）/ 0.99590（dot8）** ⇒ **两臂都错**，说明问题在共用路径（pack8_u4 / `_Float16 d,dmin` 的 host 读取 / 参考实现），"
       "**不是 dot 指令**；下一版改 `uint16_t` 位模式 + 显式 `__half2float`；"
       "④吞吐 0.55 / 0.30 TMAC/s **不可用**（朴素 8 值标量循环主导，生产 MMQ 是 7.7 TMAC/s）⇒ 不能据此判收益或判负。"
       "结题条件不变：数值 rel_l2 <= 0.01 → KL(R74) → MMQ tile 的 x_qs 改 int4（LDS 减半）→ A/B。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")
out = []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R84":
            f8[8] += ADD; ln = "\t".join(f8)
    out.append(ln)
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("R84 updated")
