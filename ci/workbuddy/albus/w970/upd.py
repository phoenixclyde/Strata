# -*- coding: utf-8 -*-
"""W970: R90 deployed -> DONE; closure V-11; memory block."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90":
        r[8] += (" **【W970 · 21:58 已上线】紧跟上游落地**：trellis overlay 移植到 0.8.0（loader 加 `x_gate`、"
                 "`write_back_mma` 加 `has_fusion=false`）⇒ **overlay=ON 全量构建通过 44,908,992 B**（commit `304bd3be`，tag r31）。"
                 "用**生产原样配置**（含 `--mtp --vision --spec 4 --kv k8v4`）试跑：health OK、2354 token 读 4732 ms = 497.4 tok/s。"
                 "已切换：`exe=/data/bin/strata-0.1.56-080`（md5 `209d8f50a77d9d45803c9cbbe3e70dde`），restart 后 health OK、"
                 "真实请求 5.20 s / 2353 prompt / 16 out、引擎侧 503–535 tok/s。回滚：config 指回 `strata-0.1.56`（md5 `ae085365…`）。")
        if r[5] != "DONE":
            r[5] = "DONE"
        print("R90 ->", r[5])
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-11",  "P0", "W970_R90_DEPLOY.md",                    "209d8f50",                          "RESOLVED", "0.8.0 已上生产; overlay ON; 回滚到 ae085365"),\n')
if "V-11" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")

mem = """## W970 · R90 已上线：生产切到 llama.cpp 0.8.0（21:5x）

- 分支：`gfx906/mi50` 合并 `exp/R90-080`（`645d3d6a`）+ overlay 移植（`304bd3be`，tag **r31**）。
- **overlay 移植**（机主指出不能偷偷关掉）：0.8.0 给 `ggml_cuda_mmq_load_tiles_t` 加了第 2 个权重指针 `x_gate`、
  给 `ggml_cuda_mmq_write_back_mma` 加了第 5 个模板参数 `has_fusion`；overlay 生成器现在补这两个 ⇒ **`STRATA_MMQ_TQ_OVERLAY=ON` 全通**。
- 构建：`build-r29`，生产同款 flags，**44,908,992 B，0 error**。
- 试跑（生产原样配置含 `--mtp/--vision`）：health OK，2354 token / 4732 ms = **497.4 tok/s**。
- 切换：`/data/bin/strata-0.1.56-080`（md5 `209d8f50a77d9d45803c9cbbe3e70dde`），config exe 已改，restart 后 health OK，
  真实请求 5.20 s / 2353 prompt / 16 out；引擎侧 503–535 tok/s；expert cache 7463 slots / 21.79 GiB（与旧版一致）。
- **回滚**：`cp /data/strata-huihui-ud-iq4_xs.json.bak_w970 …` 或把 exe 改回 `/data/bin/strata-0.1.56`（md5 `ae085365…`）+ restart。
- 停服原因（机主看到"起了又 down"）：冒烟一次 + 切换一次，各约 4 分钟装载。
"""
io.open("D:/workbuddy_space/strata_ws/albus/w970/mem_block.md", "w", encoding="utf-8", newline="").write(mem)
print("mem written")
