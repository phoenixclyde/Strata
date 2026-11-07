import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R86":
        c[6] = "0"
        c[7] = "OPEN"
        c[8] = (c[8] or "") + (
            " 【W1000 撤回 W999 判否 %s】机主质疑「混搭 bench 不等于完整移植」，核实**成立**。W999 A/B 有两个实质缺陷："
            "①**用错 kernel**：mx `mul-mat-id.cu:216` 的 `use_w32 = n_assign < 2*BN_ID*ne02`（BN_ID=128、ne02=16 ⇒ 阈值 4096）；"
            "rows=32/128 时 n_assign=512/2048，真实实现走 `mmq_gemm_repacked_w32`（32-wide/TN=1/block 32×8）或窄 mat-vec，"
            "而 W999 全程强制 64-wide ⇒ 这两档（尤其「慢 2.28×」）无效。"
            "②**激活布局错**：mx GEMM 吃 `block_q8_1_mmq_h`（`QK8_1_MMQ=4*QK8_1=128`、f32 d4[4]，由 `quantize_mmq_q8_1_cuda` 生成），"
            "W999 填的是标准 `block_q8_1`（32 值/块）全零 ⇒ stride 与 LDS 读取模式都不对。"
            "⇒ **W999 的四档数字不能作为判否依据，R86 回到 OPEN，P278 结论作废**。"
            "补齐 A/B 的前置：按 use_w32 分派 + 用 grouped MMQ 激活布局（应复用我们自己的 `mmq::quantize` 输出而非手填）。" % TS)
        l = "\t".join(c)
    if len(c) > 8 and c[1] == "P278":
        c[7] = "CORRECTION"
        c[8] = "**W1000 作废**：实验缺陷见 R86 的 W1000 撤回说明；数字保留仅作过程留痕，不得引用为判据。"
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B4上游移植", "P279", "完整生产移植 repack 的三条接入通道与我们的差距", "W1000", "count", "1", "0", "OPEN",
               "**W1000 立（%s）** 按 mx README：①**权重上传**＝repack buffer type 注册给 loader、`set_tensor` 上传时转换；"
               "我们没有 ggml extra buft，专家权重在 host arena(71.7GiB)、prefill 每 chunk 借 2606 槽上传 ⇒ 需在上传路径加 GPU 侧 repack kernel。"
               "②**compute dispatch**＝`ggml_cuda_mul_mat{,_id}` 按 should_fire 路由；我们是自有 `mmq::Context::run` ⇒ 需加格式/形状路由"
               "（w32/64-wide/窄 matvec 三选一）、移植 `repack_tile_off` 生成 tile_meta、expert_stride 改 `repack_gcn_nbytes`。"
               "③**fused FFN**＝`ggml_cuda_try_fuse` 的 GLU 分支，但 README 明说**仅单 token**（`ne[2]==1`），"
               "多 token prefill 落回 GEMM ⇒ **prefill 场景拿不到融合红利**。④激活格式需与 `block_q8_1_mmq_h` 逐字节核对。"
               "工程量不是「接进来」，是在自有 prefill 路径里重写一套 repack 支持 + 逐位/六档/2×CV/质量门验证。" % TS]),
    "\t".join(["B4上游移植", "P280", "外网核对：repack/融合类优化的公开收益量级", "W1000", "count", "1", "1", "DONE",
               "**W1000（%s）** PR #29948（fused FFN gate/up+GLU，已合并）：DGX Spark Q4_K_M pp 840.1→899.9 t/s（**+7.1%%**）、"
               "全格式 +4.6~7.4%%；RTX 5090 **+1.9~4.1%%**。PR #28702 贡献者 pp16K +10.5~14.7%%（DGX Spark）/+4.1%%（5090）。"
               "PR #31188（MoE 版）宣称 +17.2%% 但**原文明确无对照数据、不能归因**。"
               "⇒ 这类优化公开量级是个位数到十几个百分点，**强依赖硬件/形状**，不是 +84%%；收益来自「省 launch 与中间搬运」，"
               "当未融合 kernel 已很高效时收益会缩水。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R86 回 OPEN / P278 作废 / +P279,P280")
