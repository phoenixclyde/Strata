import io

P = ".workbuddy/memory/2026-11-07.md"
ADD = """
### W1039（08:5x–09:3x）按 b12180 配方重编 port-all：pa3/pa4，DP4A 慢 7%、DPP 中性

- **pa3 配方**：`/out` 从 `build-port2` 整目录拷贝（继承 flags）、`/llama.cpp`=`tmp/w1037/llama-master`（b12180 的树，`mmq.cuh` 627c4c62）、**必须重 configure**。两个坑：① port-all 的 `cmake/strata_ggml_tq_overlay.cmake` 还是旧探测（按 get_nthreads 推断），要搬 pr/k10 的 W1037 修；② 还要补 b12110 API 差——`mul_mat_q_case` 加 `GGML_PREC_Q8` **26 处**（比 k10 多 port-all 独有 `mmq_nvfp4_w4a4.cu` 一处）、`get_config` 5 处、`new_pool_for_device` 1 处。
- **可复现**：拷一份 build dir + `ninja -t clean` 全量重编，md5 与增量件**完全一致** `b2ba6304…` ⇒ 既排除旧树残留目标，也证明可重建。
- **第一窗口零效果的真因（第三次同族）**：生产 `STRATA_GFX906_TUNED=1` 把 `GFX906_ATTN_QUERY_SWIZZLE` 打开（日志 `:146006` 横幅），而 W1037 接的 OPT 分支条件是 `!use_query_swizzle` ⇒ 永不成立。生产跑 `attn_chunk_kernel<3,false,true,true>`，OPT 版是 `<M,false,false,false,OPT>`，不是同一实例化。**判据补充：判断开关在不在热路径，除看调用链，还要看生产配方本身打开了哪些实例化。**
- **第二窗口（pa4 把派发搬进 swizzle 分支，用 `<M,false,true,true,O>`）**：DP4A 让 8K `qsa attn` 2234→**2387（+6.84%）**、16K 4727→**5074（+7.35%）**，整条 prefill +1.07%/+1.44%（2×CV 0.10/0.51）⇒ **显著变慢**；DPP 8K/16K attn −0.76%/−0.47%、整条 +0.10%/+0.14% ⇒ 中性。**B1/B2 判 DONE_NEG。**
- **机制推测**：dp4a 每题要把 q 量化成 int8（`sq8`/`sq8s`，`qsa_decode_attn.cu:199-200`）且 `SQ_HEADS` 从 G 降到 1，量化+LDS 搬运超过 dot 省的；V 累加仍 fp32 `fmaf` 未被覆盖。
- **静默正确性洞**：`STRATA_ATTN_OPT_DISPATCH` 只有 case 1/2/4，`default: break;` 后直接 `return` ⇒ 组合开关（如 DPP|LDS_PAD=5）**一个内核都不发**、调用方照常 merge ⇒ 输出残留数据且不报错。已扩到 1..7。
- **窗口**：两窗口合计**重启 6 次、停机 264 s**（129+135），config 逐字节还原 `5e9b81e2…`，在产仍 `b12180`。pa3=`b2ba6304`/43,306,640、pa4=`49937458`/43,569,792，均已进 REBUILD_RECIPE。
"""
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD)
print("mem appended", len(ADD))
