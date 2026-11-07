# -*- coding: utf-8 -*-
"""W987 整改：default-on 口径、R84/P2 状态、补 3 行轮次账。"""
import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

Q = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
rl = io.open(Q, encoding="utf-8").read().splitlines()
head, body = rl[0], rl[1:]
DEFAULT_ON = {"P55", "P56", "P78", "P103", "P109", "P110", "P115", "P116", "P127", "P149", "P245"}
out = []
for l in body:
    c = l.split("\t")
    if c[0] in DEFAULT_ON:
        note = c[10] if len(c) > 10 else ""
        if "default-on" not in note:
            c[10] = note + (" 【W987 口径 %s】ADOPTED 记录的是**生效值**，不是「env 必须出现」："
                            "该项由二进制默认打开（gfx906），生产 env 不设也生效。" % TS)
        l = "\t".join(c)
    out.append(l)
io.open(Q, "w", encoding="utf-8", newline="").write("\n".join([head] + out) + "\n")
print("REGISTER: %d 条 default-on 口径已标注" % len(DEFAULT_ON))

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
touched = []
for l in lines:
    cols = l.split("\t")
    if len(cols) > 7:
        if cols[1] == "R84" and cols[7] == "INFLIGHT":
            cols[7] = "BLOCKED"
            cols[8] = (cols[8] if len(cols) > 8 else "") + \
                " 【W987 状态修正 %s】自 W951 起无实验、无数据，INFLIGHT 属陈旧；改 BLOCKED，解除条件=dot8 微基准出数（R91 同时推进）。" % TS
            touched.append("R84")
        if cols[1] == "P2" and cols[7] == "BLOCKED":
            cols[8] = (cols[8] if len(cols) > 8 else "") + \
                " 【W987 解除条件 %s】并发轴已关（W829）⇒ 需重启该项必须同时打开 `--parallel`-等价路径，否则无对照；暂不排期。" % TS
            touched.append("P2")
    out.append("\t".join(cols))

rows = [
    "\t".join(["B10环境与版本", "P260", "NVMe 迁移 + 数据分层再评估（W972/W975）", "W987", "count", "1", "1", "DONE_NEG",
               "**W975（%s）**：arena 71.73 GiB + PLE 26.8 GiB 是正确分层；`--mmap-experts` decode −19%%/prefill −60%%/磁盘重读 400 GB；"
               "稳态 0 磁盘读。结论：NVMe 不替换 RAM，只加速加载（3.43 GiB/s）。" % TS]),
    "\t".join(["B10环境与版本", "P261", "v0.9.0 升级后的六档基线与 decode/TTFT 复测（W978/W981/W982）", "W987", "count", "1", "1", "DONE",
               "**W982（%s）**：2K 531 / 8K 704 / 16K 780 / 32K 775 / 60K 786 / 130K 784；decode 43.1（CV 3.3%%）；TTFT 2K 4.05 s；"
               "与 11-04 同条件持平。8K「凹陷」经 W987 复测证实为固定成本摊销，非 chunk 缺陷。" % TS]),
    "\t".join(["B8工程", "P262", "门的三次加固（restart-baseline / 三分判定 / unset + 多长度）", "W987", "count", "1", "1", "DONE",
               "**W983–W987（%s）**：提交 7ee33b02、e0b975d8、2a74afbd、33bddcfd；负向自测通过（env=list、未知 flag、重复 flag 均 FAIL）。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: 状态修正 %s；+3 行" % touched)
