# W970 · R90 上线：生产切到 llama.cpp **0.8.0**（21:4x–21:5x）

> 机主问"什么情况，怎么起了又 down"——**是我在切换基线**：一次冒烟 + 一次正式切换，每次都要重新装载（约 4 分钟）。
> 现在已起来并在跑新版，health OK。回滚只改一个字段。

---

## 1 做了什么

| 步骤 | 内容 |
|---|---|
| 合并 | `gfx906/mi50` ← `exp/R90-080`，merge commit **`645d3d6a`**（35 行 API 适配） |
| overlay 移植 | commit **`304bd3be`**，tag **`mi50-0.2.10-r31`**：`x_gate` 参数 + `write_back_mma` 的 `has_fusion` |
| 构建 | `build-r29`，生产同款 flags，**overlay=ON**，**44,908,992 B，0 error** |
| 冒烟 | 生产原样配置（含 `--mtp --vision --spec 4 --kv k8v4`），health OK，2,354 tok / 4,732 ms = **497.4 tok/s** |
| 切换 | `/data/bin/strata-0.1.56-080`（md5 `209d8f50a77d9d45803c9cbbe3e70dde`），config `exe` 已改，restart |
| 验证 | health OK；真实请求 5.20 s / 2,353 prompt / 16 out；引擎侧 **503–535 tok/s**；`expert cache 7463 slots / 21.79 GiB` 与旧版一致 |

## 2 机主看到"起了又 down"的解释

- 21:4x 第一次：冒烟（停生产 → 起候选 → 出结果 → 停候选 → 起生产），**约 2×4.5 分钟不可用**；
- 21:5x 第二次：正式切换（改 exe → restart），**约 4 分钟装载**。
- 两次都按计划，不是崩溃；每次 health 都回到 `loaded: true`。

## 3 关键：overlay 是 **ON**，不是关掉

机主指出"overlay 不是 on 吗"——对。上一轮我为了绕开编译错误把它关了，那是缩水。真正的原因是 0.8.0 两处签名变化：

```cpp
// mmq.cuh (0.8.0)
typedef void (*ggml_cuda_mmq_load_tiles_t)(const char * __restrict__ x,
                                           const char * __restrict__ x_gate,   // <- 新增（fusion 的 gate）
                                           int * __restrict__ x_tile, const int kbx0, const int i_max, const int stride);
ggml_cuda_mmq_write_back_mma<type, J, fallback, prec_src1, false>                 // <- 新增 has_fusion
```

`cmake/strata_ggml_tq_overlay.cmake` 现在按目标树自动补这两处（`x_gate` 接收但不用；`has_fusion=false`），
于是 **dp4a 与 MMA 两条 trellis 分支、连 NVFP4 那个 TU 都编得过**。

## 4 回滚（一条命令）

```bash
# 方式一：改回旧 exe
python3 - <<'PY'
import json; p='/data/strata-huihui-ud-iq4_xs.json'
c=json.load(open(p)); c['exe']='/data/bin/strata-0.1.56'; json.dump(c, open(p,'w'), indent=1)
PY
docker restart strata166-407
# 方式二：整份配置回滚（切换前的备份）
cp /data/strata-huihui-ud-iq4_xs.json.bak_w970 /data/strata-huihui-ud-iq4_xs.json && docker restart strata166-407
```

旧引擎仍在盘上：`/data/bin/strata-0.1.56`，md5 `ae085365441381c438b56bcabcccf450`。

## 5 已知差异 / 待办

1. 新二进制更大（44.9 MB vs 42.9 MB）：0.8.0 的 ggml + overlay 的 trellis 实例都在里面，属预期。
2. 尚未做的验收（下一步）：六长度档 A/B（2K/8K/16K/32K/64K/130K，真实文本），判据 `|Δ| ≥ 2×CV`；
   `W969` 的模型 `t ≈ 1.7 s + n/822` 可直接当基线。
3. **`#29953` 的越界 padding 仍未摘**（`ids_dst` 补 `J-1`、`src1_q8_1` 按 `nthreads` 上取整）——
   我们自己的 `moe_mmq` 尾部余量也要核。这是正确性项，下一轮做。
4. 生产日志里确认 0.8.0 的启动行、cache 槽位与旧版一致，无告警。

## 6 复现

```bash
bash albus/w970/build_full.sh on build-r29     # 构建（overlay ON）
bash albus/w970/smoke_candidate.sh             # 生产配置试跑
bash albus/w970/deploy.sh                      # 切换 + 验证
```
