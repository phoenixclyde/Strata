import io

p = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / R104（13:0x–13:5x）`--kv-grow` 的前置条件被一行源码推翻

- **队列第一条不是「零代码」**：`generate.cpp:6704` 的 `on` 是十一项与关系，生产 37 args / 9 env 逐项对完，**唯一为假的是 `vmm_available()`**；而它恒 false 的原因是 `vmm.cpp:167` 的 `!defined(STRATA_HIP_GFX906)`（注释自称 "gfx906: no virtual memory"）。
- **探针实测（1 s GPU、零停机、不启引擎）**：本卡 `hipDeviceAttributeVirtualMemoryManagementSupported = 1`、最小粒度 4096 B、reserve/create/map/setaccess 全 `hipSuccess`；两 chunk 分别 map 到同 range 不同偏移后写读全对；**unmap+release 一个 chunk 后另一个仍完整**——正是 kv-grow 要的归还语义。⇒ 那行排除是撰写时的假设。
- **同族第四次「改没编进去」（`P473`）**：v1 只去掉 gfx906 排除 → 重编 BLD=0 / FAILED=0 而 **md5 不变**（`d24f8293`）。根因：该 TU 的 `DEFINES` **没有 `-DSTRATA_USE_HIP`**，只有 `-DSTRATA_HIP_GFX906=1`；条件仍为假，stub 又编一遍。v2 用 `(STRATA_USE_HIP || STRATA_HIP_GFX906)` 才换掉实现。**条件编译类改动的判据 = 二进制变了**（`nm -D | grep hipMemAddressReserve`：新件 1、在产 0）。
- **候选 `strata-0.1.57-kvg`** = `a85743d7f554159e8ac1e2d432d2e5ea` / 43,214,976 B，源 = `pr/k10 @ fa8e6761`（= b12180 的树）+ 该补丁，构建口径完全同 b12180。
- **预期**：k8v4 全额 2.391 GiB → 起机只 map ≈160 MiB（`STRATA_KV_GROW_INIT` 默认 16384 cells），让出 ≈2.23 GiB ÷ 2.99 MiB/槽 ⇒ **+746 槽，7463 → ≈8209（+10.0%）**。**代价面**：长请求从专家缓存借 chunk ⇒ 短上下文更快、长上下文回落到现值；20K 点专门触发一次增长。
- **窗口已备未开**：两次重启 ≈90–100 s，`window_kvg.sh` + `ab_kvg.py`（含 20K 点）已在 166 过语法检查，config 有逐字节备份（`5e9b81e2`），还原件 `b12180`。
"""
s = io.open(p, encoding="utf-8").read()
io.open(p, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended", len(add))
