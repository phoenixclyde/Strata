# -*- coding: utf-8 -*-
"""R90 progress note + two new closure rows (config.sh fix, S1/S2 feasibility)."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
hit = 0
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W955" not in r[8]:
        r[8] += ("\n**【W955 · 2026-11-04 17:3x】S1/S2 已完成**：0.8.0 的 `ggml/` 已 sparse-clone 到 `ref/llama_b12099`（28 MB，"
                 "ggml-cuda 168 文件 vs 我们 161）；**`mmq-config-gcn.cuh` 与 0.4.1 逐字节相同（diff 0）** ⇒ tile 层结论不因升级失效；"
                 "mirror 钩子全在（`mul_mat_q_process_tile` 4、`DECL_MMQ_CASE` 23→26、`load_tiles_q5_1` 3、`vec_dot_q4_K` 1）。"
                 "**configure RC=0，但 overlay 静默关闭**（锚点 `GGML_TYPE_COUNT = 43` 在 0.8.0 里是 44）⇒ 只缺 trellis 类型，"
                 "我们不用 trellis，可接受但必须修；**q4_k + q5_1 两个实例 24 s 编通**，对象 973,544→1,128,104 B（+15.9%）、"
                 "fatbin 701,280→777,960 B（+10.9%）⇒ 机器码确实变了，**性能只能 A/B**。下一步 S3（修锚点 + mirror + 逐位测试）。")
        hit += 1
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")
print("R90 note updated:", hit)

# extend the closure ledger
G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
s = io.open(G, encoding="utf-8").read()
add = (' ("C-1",   "P1", "W955_R90_S1S2_FEASIBILITY.md",          "build-r28",                         "RESOLVED", "ci/config.sh -> build-r28 + 0.2.10-101 (commit 03381d82, tag r29)"),\n'
       ' ("V-3",   "P1", "W955_R90_S1S2_FEASIBILITY.md",          "S2",                                "RESOLVED", "R90-S1/S2 完成: 0.8.0 编通, overlay 静默 off 已记"),\n')
if "C-1" not in s:
    s = s.replace(' ("V-1",', add + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(s)
    print("generator extended")
print(subprocess.run(["C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe", G],
                     capture_output=True, text=True).stdout.strip())
print(subprocess.run(["C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe",
                      "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
                     capture_output=True, text=True).stdout.strip())
