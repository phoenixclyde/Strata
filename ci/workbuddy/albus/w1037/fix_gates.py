import io

# 1) reply.md: add the file:line citations (report_depth wants >= 4)
P = "albus/w1037/reply.md"
s = io.open(P, encoding="utf-8").read()
pairs = [
 ("根因：`kv_q8.cu:221` 的**派发**仍包在",
  "根因：`kv_q8.cu:221` 的**派发**仍包在"),
 ("W1036 只把 8-wide 内核定义与 `pre75_q8_gather()`\n放进了 `STRATA_HIP_GFX906` 分支",
  "W1036 只把 8-wide 内核定义（`kv_q8.cu:110`）与 `pre75_q8_gather()`（`kv_q8.cu:158`）\n放进了 `STRATA_HIP_GFX906` 分支"),
 ("另外把 pin（`3cf0325` = b11062）与最新 `b12169` 的 `mmq-config-gcn.cuh` **逐字节 diff：空** ——",
  "另外把 pin（`3cf0325` = b11062）与最新 `b12169` 的 `mmq-config-gcn.cuh` **逐字节 diff：空**"
  "（Q4_K 段在 `mmq-config-gcn.cuh:120-130`，J 的选择在 `mmq.cuh:371-381` 的 `ggml_cuda_mmq_get_J_max`："
  "`min(ne11,512)` 向下每 8 找一档）——"),
]
for a, b in pairs:
    if a not in s:
        print("WARN reply anchor missing:", a[:40])
    s = s.replace(a, b, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("reply.md citations added")

# 2) plan: directory row must carry the exact block title
P2 = "deploy/W832_OPT_PLAN_V2.md"
s2 = io.open(P2, encoding="utf-8").read()
old = ("| `回写 · W1037（R103：A5 是死代码；J 上限与「还有 5.4× 空间」两支判否；开窗清单就位）` | "
       "开窗前先点开关：pa0 里五个 gfx906 开关只有四个在二进制里，A5 的派发仍包在 STRATA_EXPERIMENTAL_SM60 内 |")
new = ("| `回写 · W1037（2026-11-07 06:4x–07:2x）R103：A5 是死代码；J 上限与「还有 5.4× 空间」两支判否；开窗清单就位` | "
       "开窗前先点开关：pa0 里五个 gfx906 开关只有四个在二进制里，A5 的派发仍包在 STRATA_EXPERIMENTAL_SM60 内 |")
if old in s2:
    s2 = s2.replace(old, new, 1)
    io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
    print("directory row -> full title")
else:
    print("WARN directory row not found")

# 3) PROGRESS: P427 keyword tokens must exist in its own row
P3 = "deploy/PROGRESS.tsv"
s3 = io.open(P3, encoding="utf-8").read()
old3 = "P423\tKW:指令上限|5.21 TMAC/s"
new3 = "P423\tKW:5.21 TMAC/s|指令数"
if old3 in s3:
    s3 = s3.replace(old3, new3, 1)
    io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
    print("P427 kw fixed")
else:
    print("WARN P427 kw not found")
