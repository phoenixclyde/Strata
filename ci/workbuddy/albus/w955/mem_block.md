## W955 · R90-S1/S2：0.8.0 拿到手并编通（17:1x–17:4x）

- **S1 DONE**：`ref/llama_b12099`（sparse clone 只取 `ggml/`，28 MB）。ggml-cuda 我们 161 文件 → 0.8.0 168：
  新增 `gated-delta-net-mma`/`top-k-mask`/`conv3d`/`batch-get`，删除 `fattn-swizzle.cuh`；`GGML_VERSION` 0.24.0→**0.28.0**。
- **关键**：**`mmq-config-gcn.cuh` 与 0.4.1 逐字节相同（diff 0）** ⇒ tile 层结论（R60/R63）不因升级失效；
  mirror 钩子全在（process_tile 4、DECL_MMQ_CASE 23→**26**、load_tiles_q5_1 3、vec_dot_q4_K 1）；文本差 585/322/93/189 行。
- **S2 PASS，但发现"静默降级"**：configure RC=0，overlay 因锚点 `GGML_TYPE_COUNT = 43`（0.8.0 是 **44**）**整体跳过并只打一行日志**
  ⇒ 少 trellis 实例（我们不用 trellis，无害），但任何人看"配置成功"都会以为 overlay 生效。S3 要改成 FATAL_ERROR。
- **编译实测**：q4_k + q5_1 两个 MMQ 实例 **24.1 s** 编过；对象 973,544→**1,128,104 B（+15.9%）**、
  fatbin 701,280→**777,960 B（+10.9%，md5 不同）** ⇒ 机器码变了，"编过"≠"等价"≠"更快"，逐位 + A/B 不能省。
- **顺手修 P1**：`ci/config.sh` 从 gfx029-build/0.2.9-101 改为 **build-r28/0.2.10-101**，commit **03381d82**，tag **mi50-0.2.10-r29**
  （末条 tag==HEAD）；主线变 **落后 0 / 领先 38**。
- 结案台账 `audit_closure.py`：**35/35 RESOLVED，FAIL 0**。账本 176 条 / 已结 101（57.4%）；R90 → **INFLIGHT**。本轮零停服零重启。
- 下一步 S3：修锚点（改成"抓最后一个 GGML_TYPE_* 再 +1"）→ 重建 mirror → 逐位（同 prompt 贪心 64 token argmax 相同）→ S4 六长度档 A/B。
