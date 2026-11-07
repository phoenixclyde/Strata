# W775delta W18 / W19 ---- 两条只读观察项的据实结论

日期 2026-10-11 13:52 ｜ 全部 166 现场现取（ssh 只读 + `docker exec` 只读）｜ 工作区 `D:/workbuddy_space/strata_ws/`

## W18 ---- 生产日志里那条 CPU-share banner 是不是残留？（= `W15` 的独立复核）

**判据（客观，非推断）**：数它出现的位置，与"最后一次引擎启动"比。

| 项 | 实测 |
|---|---|
| 日志 | `/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log`（4,204,421 B / 3,619 行） |
| banner 出现行号 | **47 / 190 / 598**（共 **3** 次） |
| 首次 / 末次 `engine started` | 第 **7** 行 / 第 **3570** 行（2026-10-11 05:35:23） |
| **最后一次引擎启动之后的出现次数** | **0** |

**2 处 0.1.42 会话实测行**：第 3514 行（2026-10-11 03:47:28）、第 3570 行（05:35:23）---- 两者之后均 **0** 次。

### 结论

**是残留 ---- 且不是 0.1.42 打的。** 该 banner 的 3 次全部落在日志早期（第 47/190/598 行），**早于全部 0.1.42 会话区间**；
最后一次引擎启动之后出现 **0** 次。

=> **`W15` 的「banner 零打印」结论独立复核成立**（此前 W15 是从 `/proc` 的 environ + 启动日志取证的，本件换了判据：**按出现行号对会话分段**）。

**限定（必须随行）**：本件只证「**0.1.42 不打印**」+「当前会话不打印」；**未**逐条回读第 47/190/598 三个会话的引擎版本串。

## W19 ---- `--pcie-frac 0.20` 是否真关掉了 `PcieAuto`？（0.1.42 `generate.cpp` 实读）

**结论：是，真关了。** 三处源码逐条闭合：

| 位置 | 原文（逐字） | 作用 |
|---|---|---|
| `generate.cpp:572` | `bool pcie_frac_auto = false;` | 默认**假** |
| `:2672` | `if (o.pcie_frac < 0.0) { ... }` | **只有未给 `--pcie-frac` 才进这块** |
| `:2684` | `o.pcie_frac_auto = o.layer_split.empty() && ...;` | **全文件唯一把它置真处**，在 `:2672` 块**内部** |
| `:8090` | `if (o.pcie_frac_auto && native_pack && !all_experts_resident && o.batch == 0 && o.peer_device < 0 && n_stages == 1) {` | 消费点 |
| `:8094` | `pcie_auto.on = true;` | 就在 `:8090` 块内 |
| `:11670` | `if (pcie_auto.on) { ... }` | 运行期精化（每窗口改 `pcie_frac`） |

=> 我们显式给 `--pcie-frac 0.20` ==> `o.pcie_frac = 0.20 >= 0` ==> **`:2672` 整块被跳过** ==> `pcie_frac_auto` 保持字面默认 **false**
==> `:8090` 不成立 ==> `pcie_auto.on` **永不置真** ==> `:11670` 的运行期精化**从不执行**。
（全文件对 `pcie_frac_auto` 的写点只有 `:2684` 一处、对 `pcie_auto.on` 的写点只有 `:8094` 一处 ---- 已 grep 全文件确认。）

### 附带发现（记入 `W17` 的机理复核清单）

`:2683` 那两行赋值还在 **`#if !defined(STRATA_USE_HIP)`** 内：

```cpp
#if !defined(STRATA_USE_HIP)
            const char* pfd = std::getenv("STRATA_PCIE_FRAC_DEFAULT");
            o.pcie_frac_auto = o.layer_split.empty() && !(pfd != nullptr && std::strcmp(pfd, "old") == 0);
            o.pcie_probe_gbps = bw;
#endif
```

=> **与 `STRATA_ROUTE_TAIL_SKIP` 同型的宏判据**（`#if !defined(STRATA_USE_HIP)`）。本机主引擎不链接 `strata_hip_runtime`，
该分支**是活的** ==> `W17` 逐条复核时，凡此类守卫都**不能按「文档说 AMD 不适用」排除**。
（本条对我们的**当前**行为无影响：外层 `if (o.pcie_frac < 0.0)` 已先排除。）

## 产物

- `deploy/tmp/_w18_w19.py` / `_w18_w19b.py`（探针）；原始输出 `deploy/tmp/_w18_w19.out.txt` · `_w18_w19b.out.txt`
