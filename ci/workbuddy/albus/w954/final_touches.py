# -*- coding: utf-8 -*-
"""Final touches: R90 note (mapping done), AUDIT_INDEX pointer to the closure ledger."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
old = "**S1 必须先建立 pin→上游 tag 映射**（`~/strata166/llama.cpp` 不是 git 仓库）。"
new = ("**S1 必须先建立 pin→上游 tag 映射**（`~/strata166/llama.cpp` 不是 git 仓库）。"
       "**【W953 已完成映射】** 我们 = **upstream `e6ab7c1a4`（LLAMA_VERSION 0.4.1，2026-09-22）**，"
       "证据是 `mmq.cuh` 与上游该 tag **逐字节相同（diff 0，71,851 B）**；mx 0.6.0 / exabit 0.7.0 **比我们新**，上游 b12099 **0.8.0** "
       "⇒ **落后 4 个 minor**。S1 余下只剩「下 0.8.0 的 `ggml/src/ggml-cuda/` 全目录」。")
if "W953 已完成映射" not in s and old in s:
    s = s.replace(old, new, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("R90 note ok")
else:
    print("R90 note skip")

Q = "D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md"
t = io.open(Q, encoding="utf-8").read()
add = """
## 结案台账（AUDIT24 起，机器可验）

- `AUDIT_LEDGER_A24.tsv` —— 每条发现一行：`id / 级别 / 文件 / 标志串 / 状态 / 处置 / md5`。
- `tools/audit_closure.py` —— 逐条校验"标志串是否还在文档里"：**任何一条撤回被后来的编辑删掉，脚本立刻 FAIL**。
  本轮：**33 行 / RESOLVED 33 / FAIL 0 / WARN 0**。
- 相关纪律：㉑ 账本行可机械验（`tools/ledger_lint.py`）· ㉒ 改表必体检 · ㉓ 引用方案给 `md5+行号` ·
  **㉔ 撤回必须带结论动词**（只改数字不算）· **㉕ 版本先后只能用正确 tag 的来源文件证明**。
"""
if "AUDIT_LEDGER_A24" not in t:
    t = t.rstrip() + "\n" + add
    io.open(Q, "w", encoding="utf-8", newline="").write(t)
    print("index ok")
else:
    print("index skip")
