## W970 · R90 已上线：生产切到 llama.cpp 0.8.0（21:5x）

- 分支：`gfx906/mi50` 合并 `exp/R90-080`（`645d3d6a`）+ overlay 移植（`304bd3be`，tag **r31**）。
- **overlay 移植**（机主指出不能偷偷关掉）：0.8.0 给 `ggml_cuda_mmq_load_tiles_t` 加了第 2 个权重指针 `x_gate`、
  给 `ggml_cuda_mmq_write_back_mma` 加了第 5 个模板参数 `has_fusion`；overlay 生成器现在补这两个 ⇒ **`STRATA_MMQ_TQ_OVERLAY=ON` 全通**。
- 构建：`build-r29`，生产同款 flags，**44,908,992 B，0 error**。
- 试跑（生产原样配置含 `--mtp/--vision`）：health OK，2354 token / 4732 ms = **497.4 tok/s**。
- 切换：`/data/bin/strata-0.1.56-080`（md5 `209d8f50a77d9d45803c9cbbe3e70dde`），config exe 已改，restart 后 health OK，
  真实请求 5.20 s / 2353 prompt / 16 out；引擎侧 503–535 tok/s；expert cache 7463 slots / 21.79 GiB（与旧版一致）。
- **回滚**：`cp /data/strata-huihui-ud-iq4_xs.json.bak_w970 …` 或把 exe 改回 `/data/bin/strata-0.1.56`（md5 `ae085365…`）+ restart。
- 停服原因（机主看到"起了又 down"）：冒烟一次 + 切换一次，各约 4 分钟装载。
