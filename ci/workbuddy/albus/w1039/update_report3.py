#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: section 四, the ISA finding as body item 16, and the downgrade note on item 14."""
import io

P = "albus/w1039/reply.md"
s = io.open(P, encoding="utf-8").read()

old4 = "**四、进度** — **405 条 / 已结 318 / 78.5%**（本轮 +18：`P445`–`P462`）。"
new4 = "**四、进度** — **406 条 / 已结 319 / 78.6%**（本轮 +19：`P445`–`P463`）。"
assert old4 in s
s = s.replace(old4, new4, 1)

# item 14 gains the downgrade pointer
old14 = "速度面不受影响——`P451` 的 −11% 是墙钟。"
new14 = ("速度面不受影响——`P451` 的 −11% 是墙钟。**但下面第 16 条把这一步的前提打掉了**："
         "C16 那段分支被编译器展平了 8 倍，「只差结合次序」并不成立。")
assert old14 in s
s = s.replace(old14, new14, 1)

anchor = "**产物**：`albus/w1039/reply.md`（本件）"
assert anchor in s
add = """**16. 零窗口拿到设备汇编：`<..,16>` 被展平成 7087 条，是 `<..,0>` 的 8 倍（`P463`）**

设备码不在 `.o` 的普通节里，也不在 `.hip_fatbin` 的原样字节里——后者是 clang 的 **offload bundle**：

```
clang-offload-bundler -list     -type=o -input=fat.bin   →  hip-amdgcn-amd-amdhsa--gfx906
clang-offload-bundler -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=fat.bin -output=code906.o
llvm-objdump -d --mcpu=gfx906 code906.o                  →  85,393 行
```

同一份 pa7 目标文件里五个实例：

| 实例 | 指令数 | `global_load_dwordx2` 载入点 | 标志性指令 |
|---|---|---|---|
| `<3,false,true,true,0>` 基线 | **886** | **1** | `ds_read_b128` 24、`s_waitcnt` 94 |
| `<..,2>` int8 dot4 | 879 | 2 | `v_dot4_i32_i8` 24 |
| `<..,8>` fp16 dot2 | 824 | 1 | `v_dot2_f32_f16` 48 |
| `<..,32>` F16Q | 860 | 1 | — |
| `<..,16>` CTLREAD | **7,087** | **408** | `s_waitcnt` **761**、`s_mul_i32` 158 |

**⇒ 「源码等价」不能当作「生成的代码等价」。** 我那条 bit-16 分支让整个内核展平了约 8 倍，
所以「它与基线只差 `pp*ks` 与 `(c*sc)*q` 的结合次序（O(1e-7)）」这个前提**不成立**，
第 14 条里「C16 证明 OPT 分支读法有问题」这一步**降级为未定**。

**但真正要解释的一致事实反而更清楚了**：DP4A / F16D / F16Q 三个臂规模都正常（824–879 条），
KL 却分别是 **0.0413 / 0.0380 / 0.0448** —— 几乎同一个数。这不是「某个分支写错了」的样子，
更像这三条路共享了同一处与指令无关的差异。

**下一个判别臂只需要一次臂（约 5 min）**：`ATTN_DPP=1`（bit 1）——它只把 `warp_sum` 换成 DPP 归约、
**不碰任何算术**，设计上必须与基线逐位相同。它若也给 0.04 ⇒「任何 OPT 臂都偏」，与开关无关；
它若给 0 ⇒ 只有读 K 的臂偏，回到读法。

"""
s = s.replace(anchor, add + anchor, 1)

olda = "`error_structure.py` / `arm_matrix.py` / `isa2.py`。"
newa = "`error_structure.py` / `arm_matrix.py` / `isa2.py` / `isa3.py` / `dump_fatbin.sh` / `unbundle.sh`。"
assert olda in s
s = s.replace(olda, newa, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("report: %d chars" % len(s))

# plan §0.1 denominator
Q = "deploy/W832_OPT_PLAN_V2.md"
q = io.open(Q, encoding="utf-8").read()
a = "**405 条 / 已结 318 / 78.5%**（W1039 校正；值由"
b = "**406 条 / 已结 319 / 78.6%**（W1039 校正；值由"
assert a in q
io.open(Q, "w", encoding="utf-8", newline="\n").write(q.replace(a, b, 1))
print("plan denom -> 406/319")
