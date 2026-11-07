# F1「载入暂存」的 ISA 证据（W1037）

> 机主 2026-11-07 07:0x：「你怎么拿手法。能拿你拿呀。」这是那一条的全部证据。
> **本文件是本机副本**：原始 `.s` 在 166 的 `tmp/w1037/`（重启/断电即丢，见 `P433`），
> 所以可复查的东西（md5、计数、命令、机制推导）逐字抄在这里。

## 1 结论（一句话）

Q4_K 的「载入暂存」**编译通过、逐项指令计数不变、只少 0.44% 的 `s_waitcnt`** ⇒ 期望收益 <1%，低于 2×CV，**不开窗**。
不是这套写法没用，是**在我们的固化配置上**没有可重叠的余量。

## 2 配方（可复现，零 GPU）

```
# 树：生产 llama 树（== ref/llama_3cf0325，diff 0）两份副本
cp -a .../llama.cpp  .../tmp/w1037/llama-plain        # base
cp -a .../llama.cpp  .../tmp/w1037/llama-stage        # staged（打补丁）
python3 mmq_stage_patch.py .../tmp/w1037/llama-stage   # albus/w1036/mmq_stage_patch.py

# 编译到汇编（只走设备端，不碰 GPU）
clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 -std=c++17 -DGGML_USE_HIP \
  -I/g/ggml/include -I/g/ggml/src -I/g/ggml/src/ggml-cuda \
  -S /g/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu -o /g/mmq_<tag>.s
# staged 必须加 -DSTRATA_GFX906_MMQ_STAGE，否则两边编出同一份（踩过）
```

## 3 计数（`本机实测`，2026-11-07 07:1x）

| 指标 | base | staged | Δ |
|---|---|---|---|
| `.s` 行数 | 120,870 | 120,857 | −13 |
| `.s` 字节 | 3,910,386 | 3,910,386 | 0 |
| `global_load` | 3,788 | 3,788 | **0** |
| `ds_write` | 289 | 289 | **0** |
| `v_dot4_i32_i8` | 5,184 | 5,184 | **0** |
| `s_waitcnt` | 6,192 | **6,165** | **−27（−0.44%）** |

`mmq-load-tiles.cuh` md5：base `3eafc1fc2a8c`（= 生产树原样）→ staged `30e13cb0b873`。

## 4 机制：为什么没有余量

`mmq-load-tiles.cuh:711` 的 `ggml_cuda_mmq_load_tiles_q4_K`：

- `threads_per_row = MMQ_ITER_K / (4*QR4_K)` = `256 / 16` = **16**
- `nrows = warp_size / threads_per_row` = `64 / 16` = **4**
- `nwarps = nthreads / warp_size` = `256 / 64` = **4**
- `STEP = nrows*nwarps` = **16**，`I = 128` ⇒ 环路 **8 轮**，且整段是 `#pragma unroll`
- 每轮只做「1 次 `get_int_b4` + 1 次 `x_qs[...] = qs0`」，编译器在展开后本就能把 8 次载入提前排布
  ⇒ 手工攒进寄存器数组 **不增加可并行的载入数**，只改了调度次序。落到 ISA 上就是那 27 条 `s_waitcnt`。

**该写法在 iacop 那里有用**，是因为他们的宿主是 Q8_0 且 tile 参数不同（载入的字节数/条数更多）。
这正好说明：**「这套写法在别人那儿有用」和「在我们这条固化配置上有用」是两个命题**。

## 5 两个踩过的坑（下一轮别再踩）

1. **编 `mmq.cu` 会得到 29 行空 `.s` 且 `rc=0`** —— 模板实例在 `template-instances/mmq-instance-*.cu`，
   必须编那个文件；否则看起来"编过了"，其实一个 kernel 都没生成。
2. **staged 忘了加 `-D`** —— 补丁用 `#if defined(__gfx906__) && defined(STRATA_GFX906_MMQ_STAGE)` 包着，
   不加 `-D` 两边编出同一份，对比结果"完全一致"，会被误读成"补丁无效"。
3. `mmq_stage_patch.py --revert` 的路径**有 bug**（`#endif` 定位找不到），已在 W1037 实测；
   要"还原"请用两份副本，别用 `--revert`。
