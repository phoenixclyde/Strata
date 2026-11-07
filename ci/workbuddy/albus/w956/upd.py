# -*- coding: utf-8 -*-
"""R90 S3 note + closure row V-4 + refresh."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W956" not in r[8]:
        r[8] += (" **【W956 · 17:5x】S3 全量链接成功**：加 **30 行**适配（`GGML_PREC_Q8` 透传到 28 个 "
                 "`mul_mat_q_case`/`get_config` 调用点 + `new_pool_for_device` 三参签名 + 两个 NVFP4 TU），"
                 "`ninja strata` 0 error，产出 **39,599,200 B** 的 `strata`，`--version` = 0.1.56、`serve --help` 286 行 RC=0。"
                 "overlay 的 trellis 段**未适配** ⇒ 本轮 A/B 用 `-DSTRATA_MMQ_TQ_OVERLAY=OFF` 显式关闭（trellis 不在我们模型里）。"
                 "余下：S4 逐位（贪心 64 token argmax）+ 六长度档 A/B，需 1 次停服。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
s = io.open(G, encoding="utf-8").read()
add = (' ("V-4",   "P1", "W956_R90_S3_MMQ_API_PORT.md",          "全量链接成功",                        "RESOLVED", "0.8.0 + 30 行适配 -> strata 39,599,200 B, 冒烟通过"),\n')
if "V-4" not in s:
    s = s.replace(' ("V-1",', add + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(s)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:4]))
    print("---")
