# W718 ---- P23 `STRATA_PREFILL_CPU_SHARE`：上游 banner 误开 + 本机零收益

- 日期：2026-10-09 19:2x - 19:3x（本机时间）
- 缘起：W717 重启 `-407` 时，启动块里出现
  `prefill: the CPU share is ON by default for prompt chunks below 1024 tokens (the idle CPU takes some of the
  experts the GPU would stream; answers can differ slightly from 0.1.40.3, mean KL ~0.004). STRATA_PREFILL_CPU_SHARE=0
  turns it off.` ---- 而官方 release note 明说 "**AMD are as before**"、源码注释明说
  "the layer split, batch slots and **HIP stay off**"。三处互相矛盾，遂立项。
- **结论先说**：① 这行 banner 在本机构建上**确实是误开**（上游用错了宏）；
  ② 它**真的在动**（实测 **197 个专家由 CPU 承担**）---- 官方"AMD are as before"与源码"HIP stay off"**被证伪**；
  ③ 但**零性能收益**（prefill 928.3 vs 929.5 ms、输出逐 token 相同）；
  ④ 已按"官方本意"**显式设 0** 并复验。

---

## 1 源码级判定：根因是「宏选择缺陷」

| 环节 | 源码 / 证据 | 值 |
|---|---|---|
| 判据（错在这里） | `src/prefill/prefill.cpp:1839` `#if !defined(STRATA_USE_HIP)` | 用它当"是不是 AMD" |
| 本机构建的真实标记 | `CMakeLists.txt:134` `add_compile_definitions(STRATA_HIP_GFX906=1)`；`CMakeLists.txt:64-67` 明说 gfx906 与 `STRATA_ENABLE_HIP` 是 **"separate backends; enable only one"** | `STRATA_HIP_GFX906` |
| 编译命令实证 | `build-906/compile_commands.json` 里 `STRATA_USE_HIP` **计数 = 0**；`-DSTRATA_HIP_GFX906` **26 处** | 该宏**未定义** |
| 后果 | `prefill.cpp:1840-1848` 走 **CUDA 分支** => `g_share_default = true`（`prefill.cpp:162`）+ 打印 banner | 误开 |
| 二进制旁证 | `strings build-906/strata` 命中 banner 串（若走 `#else` 分支，该串不会进二进制） | 一致 |
| 运行日志 | `-407` 日志 banner 出现 **3 次**（行 47 / 190 / 598），每次引擎启动都打 | 一致 |
| 调用点 | `generate.cpp:11131` `arm_cpu_share(!multi_gpu && !no_pool, !multi_gpu && !no_pool && o.batch <= 0)` | 我机 = `true, true` |
| 执行点 | `prefill.cpp:2202` `cpu_pool_ != nullptr && cpu_share_on() && !stream_all`，其中 `stream_all = ... && T >= stream_all_min()`（`=1024`） | `T < 1024` 时生效 |

> 对照：P30（`STRATA_MMVQ_IL`）用的是 **`__HIPCC__`** ---- HIP 编译器**内置**宏（不在 `-D` 里，所以
> `compile_commands.json` 查不到它属正常），因此那一条在 gfx906 上**正确地**走了 HIP 分支。
> **两处用了不同的宏，一处对、一处错** ---- 这就是根因。

`STRATA_USE_HIP` 的真身：`cmake/hip_backend.cmake:89`
`target_compile_definitions(strata_hip_runtime INTERFACE STRATA_USE_HIP=1 ...)` ---- 它只挂在
`strata_hip_runtime` 这个 INTERFACE 库上，gfx906 兼容构建不走它。

---

## 2 实测：两臂（只差该 env 一项）

**方式**：CLI 模式直接跑引擎（`strata --tokens ... --pack ... --native ... --spec 4 --mtp ... --prefill 8192
--resident-budget-gib 76 --expert-profile ... --expert-cache auto --max-context 262144 --kv k8v4`），
prompt = `657 799 1829 13`（**4 token** => prefill 的 `T` 远小于 1024 => **触发 share**）。
独立临时容器窗口（与生产同设备同挂载），**跑前停 `-407`、跑后立即拉回**。Z0=off。

| 项 | 臂 A（默认，share armed） | 臂 B（`STRATA_PREFILL_CPU_SHARE=0`） |
|---|---|---|
| 引擎原话 | `prefill 3 tokens in 1 chunks, 928.3 ms (3.2 tok/s); experts streamed 309 (295 by DMA, host 174.0 ms), resident 607, **on the CPU 197 (share 0.90)**; PLE 10.3 ms` | `prefill 3 tokens in 1 chunks, 929.5 ms (3.2 tok/s); experts streamed 506 (492 by DMA, host 177.3 ms), resident 606, **on the CPU 0 (share 0.00)**; PLE 8.5 ms` |
| **CPU 承担专家数** | **197**（分担比 0.90） | **0** |
| 流式专家数 | 309 | 506 |
| PCIe 专家 | 1.83 distinct/layer | 1.81 distinct/layer |
| 预填（引擎内部） | **928.3 ms** | **929.5 ms**（差 **0.13%**） |
| 输出 tokens | `271 248068 198 760` | `271 248068 198 760`（**逐 token 相同**） |
| MTP | 4.112 ms/round，接受 2/9 | 4.038 ms/round，接受 2/9 |

**读法**：
- `on the CPU 197` => **机制确实生效**，不是"打印了 banner 但没做事" => **证伪 "AMD are as before"**。
- 预填耗时差 0.13% ---- **远低于预填分辨力 1.2-1.7%** => **零性能收益**。
- **机理**：专家已近 100% 在 page cache / resident RAM（`pcie experts 1.83 distinct/layer`），
  **PCIe 流式根本不是瓶颈** => 把专家从 GPU 挪到 CPU 算，只是"换个地方算"，不省时间。
  这与 W716 的 **P98（`STRATA_STAGER_SSD`）三臂无差**是同一类结论：**我们的瓶颈不在数据搬运**。

---

## 3 采纳：显式关闭（value = 0）

| 步骤 | 结果 |
|---|---|
| register | P23：value `auto` -> **`0`**、status `CANDIDATE` -> **`ADOPTED`**；evidence 重写（含宏缺陷全套证据 + 两臂实测） |
| register 现状 | **41 行（含表头）/ 数据行 40**；分布 **ADOPTED 22 / REJECTED 14 / CANDIDATE 4**；md5 `9353e5e8dadbf1508ff27be3956c7ac7` |
| config | `gen_config.py --write` -> `env` 段新增 `"STRATA_PREFILL_CPU_SHARE": "0"`（1316 B，md5 `115bcee9b63635f5de10ffebbfdc8b9e`） |
| 推 166 | register + config 双推，**两侧 md5 一致** |
| 生效 | `docker restart -t 60 strata166-407` |
| 复验 | `verify_config.py` -> **PASS=19 FAIL=0**；banner 在重启后**不再出现** |

**为什么是"关"而不是"留默认"**（即便实测零收益）：
1. **官方设计上 AMD 应关**（源码注释原文 "HIP stay off"）---- 当前是误开，显式 0 是**修回预期行为**；
2. 官方实测它**会改答案**（CUDA 上 KL ~0.004，原话 "answers can differ slightly from 0.1.40.3"）
   ---- 本样本输出相同，但那是 4-token 的特例，不能证明全场景；
3. 实测**零收益** => 关掉**没有任何性能损失**，只换来"回到官方字节 / 行为可复现"的确定性；
4. 设 0 后 `cpu_share_explicit()` 返回 0.0（非 -2.0）=> 连 banner 也不再打印，账更干净。

---

## 4 影响面（关掉之前它影响了什么）

- share 只作用于 **chunk 内 `T < 1024`** 的段（`stream_all_min()` = 1024）。
- => 受影响的是：**极短 prompt**（agent 的 tool result、单句追问），或**任何 prompt 的最后一段余数 < 1024**。
- **W716 的三档基线不受影响**：5,485 / 11,785 / 27,985 token 的末段余数分别为 5,485（单 chunk）、
  3,593、3,409 ---- **均 >= 1024**。故 W716 读数无需重取。
- 关掉后：整条路径回到"所有专家都在 GPU 侧"的确定性行为。

---

## 5 给上游的建议（可提 issue）

`prefill.cpp` 用 `STRATA_USE_HIP` 判"是否 HIP 后端"，但 **gfx906 兼容构建（`STRATA_HIP_GFX906`）不定义它**
=> `arm_cpu_share()` 的 `#else`（`(void) by_default;`）在这个构建里**永不生效**，
表现为：CUDA 专属的默认开关在 AMD gfx906 上被打开、并打印"ON BY DEFAULT"的 banner。
**修法**：把该判据改成 `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`
（与 `device.cu:235`、`expert_cache.cpp:6` 的既有写法一致 ---- 那两处就是 `||` 两个宏并列判的）。

---

## 6 证据索引

| 件 | 位置 | 指纹 |
|---|---|---|
| 臂 A 原始日志 | `deploy/tmp/_w717_p23_armA.log` | 7097 B, md5 `1648c5ab7be6c463` |
| 臂 B 原始日志 | `deploy/tmp/_w717_p23_armB.log` | 6855 B, md5 `fa15879bd87c38a0` |
| 两臂驱动日志 | `deploy/tmp/_w717_p23_main.log` | 3310 B, md5 `d6a1b918687ab41a` |
| 驱动脚本（166 侧） | `/home/albus/strata166/w717/p23_arm.sh` | 1079 B, md5 `bc94c4ea72c82f06` |
| 复验输出 | 本报告 §3 | `verify_config.py` 现算 |

> 过程脚本（本机）：`_p23recon / _p23src / _p23macro / _p23macro2 / _p23field / _p23live / _p23line / _p23cli /
> _p23arg / _p23go{,2,3} / _p23poll / _p23err{,2} / _p23done / _p23reg / _p23verify.py`，均在
> `C:\Users\clyde\AppData\Local\Temp\`。

## 7 附带：核验器 ENV 面缺口（本轮发现并修复）

把 P23 设为 ADOPTED 后**首次复验得 `PASS=18 FAIL=1`**：
`P23  STRATA_PREFILL_CPU_SHARE  0  FAIL  env=None`。

**根因**：`verify_config.py` 的 **ENV 面只查容器 `Config.Env`**，漏了 **config JSON 的 `env` 段**
（serve 用 `child_env(cfg)` 把 config 的 env 注入**引擎子进程**）。
`HSA_OVERRIDE_GFX_VERSION` 恰好两个面都有（`docker run -e` 传了、config 里也写了），
所以此前一直 PASS ---- **这个缺口被它掩盖了**。

**修法**（已改；备份 `verify_config.py.bak_w718_*`，原 md5 `19ca25eb420bc3d9`）：
ENV 面改为**两个面任一命中即 PASS**，并报出命中面（`docker Config.Env` / `config JSON env 段`）。

**修后复验 `PASS=19 FAIL=0`**，P23 的依据显示为 `config JSON env 段（serve 注入引擎子进程）`。

**独立旁证（最硬，不经核验器）** ---- 直接读运行中进程的 environ：

```
engine pid=12 : HSA_OVERRIDE_GFX_VERSION=9.0.6 / STRATA_PREFILL_CPU_SHARE=0
serve  pid=1  : HSA_OVERRIDE_GFX_VERSION=9.0.6          （serve 自身不拿 config 的 env，符合设计）
vision pid=72 : HSA_OVERRIDE_GFX_VERSION=9.0.6
```

> 这类"核验器只覆盖一个数据面"的问题在本项目**已是第二次**（第一次是容器名硬编码，见
> `W713_AUDIT.md` P1）。教训：**判据的覆盖面本身要定期复核 ---- 一个恰好两处都满足的样本会把缺口罩住。**
