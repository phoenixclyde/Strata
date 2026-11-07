import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    "\t".join(["B10环境与版本", "P269", "TAB=ON 重编实证：gfx906 结构上编不出 pointer-table MMQ", "W994", "count", "1", "1", "DONE_NEG",
               "**W994（%s，机主令「重编」）**：按 W974 权威 flags + `/ref=llama_b12110`(ggml 0.29) 全量重编，"
               "产物 md5 **`eea5ea3749ad54b124330386605a18bc` 与生产逐字节相同**；而 `build.ninja` 里 `STRATA_MMQ_TAB=1` 定义数 **0**、mmq-tab 目标 **0**。"
               "根因 `CMakeLists.txt:2378` 的 `AND NOT STRATA_HIP_GFX906`，且 TAB 只覆盖 9 种 IQ 类型（不含 Q4_K/Q5_1）。"
               "⇒ **C 无法通过重编启用**，需源码级移植。" % TS]),
    "\t".join(["B4上游移植", "P270", "`kq_bench` 按 build-r32 同款 flags 重编并复测（R86 第一步）", "W994", "count", "1", "1", "DONE",
               "**W994（%s）**：`hipcc -O3 -DNDEBUG -std=c++20` + `hip_compat` 头 + `libstrata_mmq.a`（先编对象再链接，避免 -x hip 吃 .a）；"
               "运行需 `STRATA_MMQ_KQ=1`（`kq_ok()` 要求）。**Q5_1 down [640,2560] 16×320**: 1.243/1.262/1.246 ms ⇒ **1.246 ms / 6.73 TMAC/s**"
               "（W944 旧构建 1.53 ms / 5.47 ⇒ **+23%%**）；**Q4_K gate/up [1280,2560]**: 2.292–2.574 ms / 6.52–7.32 TMAC/s，与旧构建持平。"
               "Q5_1 仍是供给率最低者，R86 repack 仍有空间。" % TS]),
    "\t".join(["B8工程", "P271", "构建链纪律：一切重编先读 `ci/build.sh` 与 r32 CMakeCache，不自行摸索 configure", "W994", "count", "1", "1", "DONE",
               "**W994（%s，机主质疑）**：本轮自行 configure 连撞 6 坑（无 GPU 设备、缺 KQUANTS/NATIVE/Q6K、错 /ref 版本、缺 hip_compat、-x hip 吃 .a、kq_ok 需 env）。"
               "权威路径 = `ci/build.sh` 的 `ninja -t commands strata` 三条逐字命令；全量构建 = W974 §38 的 flags。"
               "**自证**：按权威参数重编产物与生产 md5 逐字节相同。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(lines + rows) + "\n")
print("PROGRESS: +P269/P270/P271")
