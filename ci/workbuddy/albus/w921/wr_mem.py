import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 00:3x（11-04）W921 · R66：0.2.10 三个 opt-in prefill 开关 = 全部生效、零收益
- **移植成功且路径断言齐全**：`fbf6e1c7`(PF_GROUP_SCRATCH) 12 hunk 全过、`5273fb66`(PREFILL_ROUTED_STREAM) 6 hunk 全过、`3cc47f02`(PF_HC_REGION) **在 p1 之后** 5 hunk 全过（W918 说的"1 处手解"是因为当时没上前置，实际不需要）。产物 `2fa104e5`（40,782,104 B）。
- **决定性路径断言**：`prompt path borrows` **1578 slots (4.62 GiB) → 1226 slots (3.59 GiB)**，少借 **352 slots / 1.03 GiB（−22.3%）**。日志另有 ROUTED_STREAM 完整提示。三条不是空开关。
- **A/B**（同脚本、去冷启、rep2-9 median）：prefill **8.819 → 8.799 s = −0.23%**（CV 1.6/1.0%）、decode 79.24 → 78.19（cache 槽数与 VRAM free 均相同 ⇒ 噪声）⇒ **DONE_NEG，不采纳**。
- **副产物 1（方法价值）**：三开关关掉、只换二进制时 borrows **回到 1578 slots**，与基线逐字相同 ⇒ **补丁关闭时 bitwise 等价**，自述获实测印证。
- **副产物 2（立 R72）**：省下 1.03 GiB 借用；`expert cache 7463 slots / 21.79 GiB` 与 `VRAM free 920 MiB` 都被 `--vram-reserve-mib 832` 卡住 ⇒ 1.03 GiB ÷ 3 MiB/槽 ≈ **+350 槽（+4.7%）**。R72 = 三开关常开 + reserve 832→~600，看 decode；**红线：最终 VRAM free ≥ 300 MiB**（源码注释：<256 MiB 会让驱动 page、verify 图自旋不返回）。
- **编译三坑（都踩过）**：①**不能跑全量 `ninja`**——它会 `Re-running CMake`，而 `STRATA_GGML_DIR=/llama.cpp` 是缓存里的值、镜像内不存在 ⇒ `add_subdirectory ... /llama.cpp/ggml` 失败；正确做法是 `ninja -t commands` 抽**单条编译行 + 归档行 + 链接行**逐条 `bash -e`（`strata-ci-build` 就是这个套路）。②`ninja -n` 同样会先跑 cmake，不能用来 dry-run。③**换二进制必须 `mv`**（`cp` 报 `Text file busy`，正在运行的 inode 不能覆盖），mv 换 inode 后重启才生效。
- **构建树建法**：`rsync -a --exclude=.git` 复制（**保留 mtime**，否则 ninja 全量重编，97M 几秒完成）；`git worktree` 会让所有 mtime 变新 ⇒ 不可用。
- **生产已恢复**：`mv` 换回 `a97f4479`、config 回 `51ef8837`（env 9）、health ok、restarts=0、`ulimits` 保留 `memlock=-1`。
- 进度 **87/156 = 55.8%**，主线 **87/128 = 68.0%**。队列 `~~R59~~ → ~~R67~~ → ~~R66~~ → **R68** → R72 → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3`。
- 产物：`deploy/W921_R66_OPTIN_AB.md`；`PROGRESS.tsv` R66(DONE_NEG)+R72；`W832` 队列与表行；实验树 `~/strata166/work/r66`。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
