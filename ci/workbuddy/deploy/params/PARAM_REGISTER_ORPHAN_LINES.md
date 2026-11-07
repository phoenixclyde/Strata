# PARAM_REGISTER.tsv 里的叙事行（不是数据行，2026-10-31 由 albus 移出）

这 4 行是 W823/W824 时期误写进 TSV 的叙述段落，各占 1 列，会让任何按 11 列解析的脚本出错。
内容原样保留在下面，未做任何编辑。

- (原第 145 行) 【W823 复核（10-29，换权重之后）】上游仍无 x86 Qwen 新引擎：最新 release 0.2.7（引擎 0.1.52）；tag v0.2.7.1 = 引擎 0.1.53，但其 127 提交/132 文件里引擎面 32 个文件全是 dsv41(DeepSeek)/Metal/nv_defaults/sm_121(DGX Spark)，零个 x86 Qwen HIP 改动；main 也停在 0.1.53，自 10-28 08:11 起无提交。**K-quant 路径两版几乎逐字节相同**（我们现在跑的就是这条路）：`mmq_kq_loader.cpp` 124->124 行 +-0；`moe_mmq.cu` 的 K-quant 分派未变，新增融合 swiglu 与 trellis 类型均在 `#if !defined(__HIPCC__)` 或 SM60 专用；`native_mmvq.cu` 673 行改动**全部在 `#if !defined(__HIPCC__)` 内**，HIP 只多一个空桩；`expert_cache.cpp` 95 行是 Windows/NVML + STRATA_EXPERT_NIBBLE；45 个引擎文件的补丁里含 HIP/gfx906 的新增行为 0。唯二实质项：`STRATA_PLE_AUTO_RAM`（0.2.7 默认开，准入需 表26.8+竞技场71.7+headroom≈105 GB 对分配前可用，本机常态 60 余 GB ⇒ 必拒，回落 direct，与今天一致）；#3602 PLE reader 挂死 / #1503 会话 KV 串用（正确性，非速度）。⇒ 维持不升级。"

- (原第 150 行) 【W824 追加】按机主要求**删除 aliases**，只保留新名。兼容性已核：/v1/chat/completions 不校验 model 名（只有 /v1/load、/v1/unload、/props 会 404）⇒ 旧名客户端聊天不受影响，走 /props 的工具要改填新名。"

- (原第 154 行) 【W824 第三测】V1 臂（同法、带 decode timing）：tok/s 中位 45.1，基线 N1 45.9/N1b 44.5，ms/window 38.1 对 38.2/37.7 ⇒ 第三次得到""无差异""。三测一致，定案。"

- (原第 158 行) 【W824 质量门结论（10-30 01:30）】用 teacher-forced LOGPOS 直接验：把 share 固定为 0（P158）后，K1（reduce12=1）/ K0（=0）/ K1b（=1 重跑）三份 `w803_logpos_*.tsv` **md5 完全相同**（38fa1653c08dba8eb7fb41f9be535674，各 66,045 B），配对 KL 0.0000、argmax 一致率 100%、top-10 重叠 1.00、mean|Δlp_tgt| 0.0000（60 个位置）。⇒ **该开关在受评路径上逐位等价**，""质量未验""这条已关闭。边界：这 60 个位置来自 verify 窗口的 teacher-forced 读，prefill 自身的数值没有直接被打分；但同一内核只换模板参数、且验证路径逐位相同，可认为不引入数值偏差。"
