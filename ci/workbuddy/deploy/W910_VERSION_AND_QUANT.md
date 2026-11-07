# W910 · 版本口径与量化口径：两处更正（附证据与复现）

> 2026-11-03 03:2x。零停服，只读探测。
> 机主质疑两点：①"不应该是 ROCm 10.1 吗？"②"不应该是 kq4 吗？"
> **两条质疑都成立。** 我上一轮把 ROCm 说成 7.14、把模型说成 iq4，都是只看了最外层的一个字符串。

---

## 0 结论

| 项 | 我上一轮的说法 | 实际 | 判定 |
|---|---|---|---|
| ROCm | "正确说法是 7.14"（撤回 10.1） | **Core SDK 10.1.0**；`7.14` 是**打包轨道**的名字 | **我错，你对** |
| 量化 | 沿用配置文件名 → iq4 | 主体 **K-quant**：专家 gate/up **Q4_K**、down **Q5_1**；IQ4_NL 只占 PLE 一张表 | **我错，你对** |
| KQ 库缺失（我上一轮的怀疑） | "Q4_K 专家可能退回 FP16" | **不成立**：`mmq-instance-*.cu` 直接编进 `strata_mmq` 静态库；`libstrata_kq.so` 是可选拆分 | 我的怀疑作废 |

---

## 1 ROCm 为什么有两个号：10.1 与 7.14 是**两条并行轨道**

官方 release history（`rocm.docs.amd.com/en/develop/release/versions.html`）逐字：

```
10.1.0   October 5, 2026
10.0.0   August 26, 2026
7.14.1   September 2, 2026
7.14.0   July 15, 2026
```

并且 10.1.0 的 release notes 写明：**"Since ROCm 7.14, ROCm uses TheRock as its build and release system."**
⇒ 7.14 是**发行/打包体系的版本**（TheRock 的包基线），10.x 是 **Core SDK 的版本**。同一套代码两个号，不是矛盾。

### 我们这台的证据链（全部可复现）

| 层 | 值 | 命令 |
|---|---|---|
| **源码树** | `git describe` = **`therock-10.1`**，commit `39d8d603`（2026-09-16） | `cd ~/strata166/rocm-libs && git describe --tags` |
| **安装标记** | `/opt/rocm/.info/version` = **`10.1.0`** | `cat /opt/rocm/.info/version` |
| **HIP 运行时** | `hipconfig --version` = **`7.16.26323-0000000`** | `hipconfig --version` |
| **HIP CMake** | `PACKAGE_VERSION "7.16.26323"` | `grep PACKAGE_VERSION /opt/rocm/lib/cmake/hip/hip-config-version.cmake` |
| **编译器** | AMD clang **24.0.0git**（ROCm/llvm-project `e3dd2f54`） | `clang --version` |
| **deb 包** | `amdrocm-core7.14-gfx906` **`7.14.0-gfx906+20260802001858`** | `dpkg -l | grep amdrocm-core` |
| rocBLAS | `5.7.0.962d0059` | `strings librocblas.so.5` |

**交叉验证**：AMD 自己的性能页写 "Container **ROCm 10.1.0** (HIP **7.16.26385**-0000000)"。
我们是 **HIP 7.16.26323** —— 与 10.1.0 的 7.16 线**同一条**，只差几十个 commit（自建于 2026-08~09 的 develop 快照）。

⇒ **正确口径**：`ROCm 10.1.0（Core SDK；HIP 7.16.26323；TheRock 打包轨道 7.14；自建 gfx906 包）`。
"7.14" 只适合用来描述 **deb 包名/打包基线**，不能用来描述这套栈的版本；反过来，"10.1" 也解释不了为什么包名是 7.14。
**我上一轮只看了 deb 名就下结论，方向错了，撤回。**

---

## 2 量化：主体是 K-quant，不是 IQ4

### 2.1 专家（真正吃 prefill 的那 71.7 GiB）

`/data/packs/ud-q4_k_xl/native_experts.txt` 头部自述：

```
# strata native experts v4: layer gu_type d_type offset blob_bytes gate_off up_off down_off [shard | ...]
#   (n_expert 512, total 77017907200; ...)
```

48 层 × 512 专家 = 24,576 对（与启动日志 `profile: 24576 ranked pairs` 一致）。类型分布：

```
48 层： 43 × (gu=12, d=7)   4 × (gu=12, d=8)   1 × (gu=13, d=8)
```

类型号是 **ggml_type**，不是我猜的 pack 私有枚举 —— 源码里 `include/strata/core/expert_nibble.hpp:96-98` 给了同族常量
`kIQ3_XXS=18 / kIQ3_S=21 / kIQ2_S=22`，与 ggml 编号完全一致。所以：

| 列 | 值 | ggml 类型 | 占比 |
|---|---|---|---|
| `gu_type`（gate/up） | 12（43 层）/ 13（1 层） | **Q4_K** / Q5_K | 48/48 层是 K-quant |
| `d_type`（down） | 7（43 层）/ 8（5 层） | **Q5_1** / Q8_0 | 无 IQ |

⇒ **专家侧一个 IQ 类型都没有。**

### 2.2 主 GGUF（4 分片，1224 张量，直方图来自文件本身）

`albus/w910/gguf_types.py` 解析每个张量的 `ggml_type` 与维度后按块大小折算字节：

| 类型 | 张量数 | GiB | 占比 |
|---|---|---|---|
| **Q4_K** | 94 | 41.31 | **39.8%** |
| **IQ4_NL** | **1** | 26.82 | **25.9%** |
| **Q5_1** | 43 | 25.20 | 24.3% |
| Q8_0 | 503 | 8.95 | 8.6% |
| Q5_K | 2 | 1.07 | 1.0% |
| F32 | 557 | 0.29 | 0.3% |
| BF16 | 24 | 0.04 | 0.0% |

元数据：`general.architecture=qwen4exp`、`general.name=Qwen3.8 Flash Next`、`general.quantization_version=2`、`split.count=4`。

**`general.file_type=15` = `MOSTLY_Q4_K_M`**（gguf-py `LlamaFileType`：0 ALL_F32、1 F16、2 Q4_0、3 Q4_1、7 Q8_0、8 Q5_0、**9 Q5_1**、10 Q2_K、11–13 Q3_K_S/M/L、14 Q4_K_S、**15 Q4_K_M**、16 Q5_K_S、17 Q5_K_M、18 Q6_K）。
这是**文件自己声明的配方**，与手算的 39.8% Q4_K 相互印证。注意两个枚举撞号：`file_type=15` 是 Q4_K_M，而**张量类型** 15 是 Q8_K —— 用 ggml_type 表去解释 file_type，从 2 往上就全错。

**关键：那 25.9% 的 IQ4_NL 是"一张张量"** —— 26.82 GiB 的 PLE 表（启动日志 `PLE on, table 320001536 rows`）。
它不是矩阵乘的权重，是查表用的嵌入；所以它既不进 MMQ、也不进 dp4a 主路径。

### 2.3 所以"iq4"这个印象从哪来

1. **配置文件名**：`/data/strata-huihui-ud-iq4_xs.json` —— 遗留名；同一文件里 `model_name` 写的是
   `qwen3.8-flash-next-ud-q4_k_xl-abliterated`，`--native` 和 `--pack` 都指向 `UD-Q4_K_XL`。
2. **PLE 表**确实是 IQ4_NL（25.9% 字节），容易以偏概全。
3. **KV cache**是 `--kv k8v4`（K=Q8_0、V=4-bit），又一处"4-bit"但不是权重格式。

⇒ 一句话：**模型是 unsloth 的动态量化 UD-Q4_K_XL —— 密度方向 Q4_K/Q5_1/Q8_0 混排，专家 gate/up Q4_K、down Q5_1，只有 PLE 表是 IQ4_NL。叫它 "iq4" 只对 26.8 GiB 那一张表；叫它 "kq4" 才描述的是矩阵乘主体。**

---

## 3 顺带否掉我自己上一轮的一个怀疑（重要）

上一轮我看见 `/data/bin` 里没有 `libstrata_kq.so`、日志里也只打印了 `MMQ tile: type 20/21/23/8`（没有 12/7），
就推测"Q4_K 专家可能退回了 FP16"。**这个推测不成立**，证据：

- `CMakeLists.txt:2192`：`target_sources(strata_mmq PRIVATE ${_strata_mmq}/template-instances/mmq-instance-${_t}.cu)`
  ⇒ **llama.cpp 的 `mmq-instance-*.cu` 是直接编进 `strata_mmq` 静态库再链进引擎的**，不依赖那个 `.so`。
- `libstrata_kq.so` 是 **MODEL-UPDATE Phase 1 的可选拆分**（`mmq_kq_lib.cu` 头注释：把四个实例搬出引擎以省 VRAM，
  "load only when moe_mmq.cu opens this library"）。镜像里没有它 = **没有启用拆分**，不是缺件。
- `MMQ tile: type N` 是**我们自己的 `mmq_tab` Context**（9 个 IQ/Q 类型）在初始化时打印的；
  llama.cpp 的 `mmq-instance-*` 不打印这一行 ⇒ 日志里没有 12/7 不能推出"Q4_K 没走 MMQ"。

这也解释了 W909 那 130,808 条 `v_dot4_i32_i8` 落在哪：`mmq-instance-q4_k.cu` / `-q5_1.cu` / `-q6_k.cu` 这些实例
＋ `iq_kernels.cu` 的 mmvq ＋ `s2_*`。**类型与指令是对得上的。**

---

## 4 对上一轮 dot 结论的影响：结论不变，措辞要改

| W909 的说法 | 是否仍成立 |
|---|---|
| 生产在用 `v_dot4_i32_i8`（130,808 条）、没有 `v_dot8_i32_i4` | **成立** |
| "tiled dp4a 已现役" | **成立**，但要写清是两条：K-quant 走 llama.cpp 的 `mmq-instance-*`（编进引擎的 `strata_mmq`）；IQ 类型走我们自己的 `mmq_tab` |
| `v_dot8` 在 W4A8 下负收益、IQ 码本更不可用 | **成立**；且现在更硬：**本模型专家一个 IQ 类型都没有**，所以"IQ 码本"这条对它连边都不沾；真正相关的是 W4A8（Q4_K/Q5_1 权重 × Q8_1 激活） |
| 差距是 4.55/21.52 = 21% 的 VALU 供给率 | **成立**，前提（专家 = Q4_K/Q5_1，走 dp4a）已验证 |

---

## 5 复现

```bash
# ROCm 到底哪个号
cd ~/strata166/rocm-libs && git describe --tags        # therock-10.1
docker exec strata166-407 cat /opt/rocm/.info/version   # 10.1.0
docker exec strata166-407 hipconfig --version           # 7.16.26323-0000000
docker exec strata166-407 dpkg -l | grep amdrocm-core   # 7.14.0-gfx906+20260802001858

# 模型到底什么类型（不信文件名，直接读 GGUF 张量表）
docker cp gguf_types.py strata166-407:/tmp/
docker exec strata166-407 python3 /tmp/gguf_types.py \
  /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/*.gguf

# 专家类型
docker exec strata166-407 head -2 /data/packs/ud-q4_k_xl/native_experts.txt
docker exec strata166-407 sh -c 'grep -v "^#" /data/packs/ud-q4_k_xl/native_experts.txt | cut -d" " -f2,3 | sort | uniq -c'
```
