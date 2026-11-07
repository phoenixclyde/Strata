# W775delta 发现 ---- `STRATA_ROUTE_TAIL_SKIP` 在我方 gfx906 生产上**是开着的**（且在实际动作）

> 触发：机主 2026-10-11 12:2x「有些开关虽然没说支持 gfx906，但机理上可以支持」。本条正是该类，
> 而且**不是"能不能支持"，是"早就在跑"**。证据全部现取：生产日志 + 0.1.42 镜像源码 + 构建 CMake。**未发车。**

## 0 结论（先行）

1. **`STRATA_ROUTE_TAIL_SKIP=7` 在我方生产上 ON（default）**：生产日志 **12/12 次**启动都打
   `strata serve: STRATA_ROUTE_TAIL_SKIP=7 is ON (default): ... a missed expert ... is skipped (+10..20% decode ...); STRATA_ROUTE_TAIL_SKIP=0 turns it off`。
2. **它不只是"生效"，而在"动作"**：日志有
   `strata serve: route tail skip: <N> missed experts skipped (<M> entries) since the start`，
   N 递增到 **672,855**（M 697,204）=> **累计跳过 67 万次**。
3. => **`P57` 的 F-1 判定**（「x 不适用 / ▲ 改答案 ..... off on AMD and Intel；且 off when every expert is in VRAM」）
   **两条理由都不成立**。

## 1 为什么（机制，逐字）

`src/program/generate.cpp:8074-8080`：
```cpp
const char* tse = std::getenv("STRATA_ROUTE_TAIL_SKIP");
#if !defined(STRATA_USE_HIP)
    const bool tail_default_ok = tse == nullptr && !all_experts_resident && o.batch == 0 && o.peer_device < 0;
#else
    const bool tail_default_ok = false;   // HIP and SYCL stay as they were
#endif
if (tail_default_ok) strata::core::set_tail_skip_rank(7);
```
- 运行时打出 `(default)` => `tse == nullptr`；打出 rank=7 => `set_tail_skip_rank(7)` 被执行 => **`tail_default_ok == true`**
  => **`generate.cpp` 编译时 `STRATA_USE_HIP` 未定义** => 走 **CUDA 分支**。（**反证，逻辑闭合**）
- 构建面：
  - `CMakeLists.txt:64` = `option(STRATA_HIP_GFX906 "Build the **CUDA targets** for AMD gfx906 through HIP (wave64 compat layer)" OFF)`
  - `CMakeLists.txt:137` = `add_compile_definitions(STRATA_HIP_GFX906=1)`（**全局**）
  - `cmake/hip_backend.cmake:86-89` = `add_library(strata_hip_runtime INTERFACE)` + `target_compile_definitions(strata_hip_runtime INTERFACE STRATA_USE_HIP=1 ...)`
  - `target_link_libraries(... strata_hip_runtime)`（CMakeLists:404-1475）的名单**多为 bench / test 目标**
    （`hip_*_parity` / `qsa_select_bench` / `hip_prefill_fused_moe` 等），**主引擎目标不在其中**。
- => **主引擎没有 `STRATA_USE_HIP`** => 主引擎里 `#if !defined(STRATA_USE_HIP)` 的段**是活的**（= CUDA 分支）。

> 这与我们 Dockerfile 自己的注释一致：*"`STRATA_HIP_GFX906=ON` 会强制 `STRATA_ENABLE_CUDA=ON` => 走 CUDA 分支"*。

## 2 连带更正（三处）

| 件 | 原说法 | 更正（据 §0/§1） |
|---|---|---|
| `PARAM_REGISTER` `P57`（含 F-1 行） | `STRATA_ROUTE_TAIL_SKIP` = x 不适用 / ▲ 改答案 | **判错**：本机 **ON (default)** 且**在动作**（>=67 万次 skipped）。**待机主签字后改 register** |
| `W775delta_REL0142_LEDGER` `A-1` / `U-1` | 「精确 0.1.41 答案条件 = `ROUTE_TAIL_SKIP=0` + `PREFILL_CPU_SHARE=0`；我们已显式 PREFILL=0 => 天然满足」 | **只满足一半**：`PREFILL_CPU_SHARE=0` OK；但 **`ROUTE_TAIL_SKIP` 未设 0、默认 7 且在动作** => **我们的答案相对 0.1.41 有偏移**（源码注释 KL ~0.003-0.006，`docs/DETAILS.md`） |
| `W775delta_R4_P41_SCREEN` §2 | 「`STRATA_USE_HIP=1` 是定义的」（易读成普遍生效） | **收窄**：它只在链接 `strata_hip_runtime` 的目标上生效；**主引擎不拿它** => 主引擎的 CUDA 分支是活的 |

## 3 新的高价值实验（建议**插到 §4 族其余项之前**）

**A/B：默认(`=7`) vs `STRATA_ROUTE_TAIL_SKIP=0`**（同一 harness `_w4x_rc.sh` 即可，无需新写）
- 量化这条开关买到的 **decode**（上游自述 +10..20%，限定"miss experts 的卡"；我们实测 skipped 量级 41-67 万）
- 同时量化**答案差**（属"改答案"类 => **必须配质量门**；我们已有 `P51` 的 teacher-forced `STRATA_LOGPOS` 门，self=0）
- 价值：这是**唯一一条"已在生产上跑、量级已知、却从未被本机量化"**的开关

## 4 待核（不擅断）

- 生产日志的 `prefill: the CPU share is ON by default ...`（行 47/190/598）**可能是 0.1.41 会话的残留**
  （该日志跨版本未轮转）。若属 0.1.42，则 `W15`「banner 零打印」需复核。**待按 session 时间戳/版本行核。**
- `PcieAuto`（`generate.cpp:8090`）与 tail-skip 同一段，条件含 `o.pcie_frac_auto`；我们显式给 `--pcie-frac 0.20`
  => 预期 `pcie_frac_auto=false`，但**未逐字核该 flag 是否真的关掉 auto**。若没关，则"自适应 PCIe share"可能同样活着。

## 5 局限

- **本条未发车**：全部是「日志 + 源码 + CMake」证据。
- `skipped` 是**自本次启动的累计值**，不是速率 => **不能直接换算 tok/s 收益**。
- "12 次 ON 行是否全属 0.1.42 会话"：由 `runtime` 版本行（引擎 md5 `5efa1d45...`）旁证，**未逐行对时间戳**。
- 结论只针对 `ROUTE_TAIL_SKIP`；**不代表 P57 其它项**（多卡 / Intel / gfx12 专属仍需逐条按机理复核）。
