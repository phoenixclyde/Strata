# -*- coding: utf-8 -*-
"""给 flashnext-engine-selection 技能追加 §7：gfx906 单卡路线（全实测）"""
import os

p = r'C:\Users\clyde\.workbuddy\skills\flashnext-engine-selection\SKILL.md'
TXT = r'''

## 7 gfx906（MI50/MI60/Radeon VII）单卡路线：官方无先例，**已实测跑通**（2026-10-06）

### 7.0 为什么值得先试单卡
官方 `docs/AMD_HIP.md#gfx906` 只给 **2×MI50 16GB** 的参考机，**单卡 32GB 明确写"未做"**。
实测：**单卡不仅能跑，还更快** —— 因为单卡机器（本机 166 = 1×MI50 32GB + 128 GB RAM）能让
**24576 个专家全部常驻内存，稳态零读盘**，而官方那台只有 32 GB RAM。
⇒ 判据顺序：先算「专家总量 vs RAM」，够全常驻就别急着凑多卡。

### 7.1 镜像构建（底座、配方、三个底座坑）
- 底座 = 官方文档指定的 **`docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete`**（HIP 7.14）
- 底座实测构成：**有** clang++/hipcc（只在 `/opt/rocm/llvm/bin`，**不在 PATH**）、ROCm 库；
  **无** cmake/ninja/gcc/g++/unzip/pip ⇒ 必须 apt 装 `build-essential cmake ninja-build unzip python3-pip python3-venv python3-dev`
- **[!] 先剔掉镜像自带的 `s3.arkprojects.space/apt-gfx906` 源**（已 403 失效）：它会让 `apt-get update` **整体失败**，
  而 pip 兜底又因**底座没有 pip3** 直接 exit 127 —— 这是第一次构建失败的真因
- 构建配方：`-DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 -DSTRATA_GGML_DIR=<llama.cpp>`
  `-DSTRATA_MMQ_KQUANTS=ON`（**K-quant 专家档如 UD-Q4_K_XL 默认带上**，这个开关就是为它而设；失败可 `--build-arg SMMQ_KQUANTS=OFF` 回退）
- apt 走 `archive.ubuntu.com` 实测只有 ~504 kB/s（对比 pip 清华 52 MB/s）⇒ 装工具链这步会慢，别以为卡死

### 7.2 [!] 必打补丁：hip_compat 的函数式宏吃不了模板逗号
- 症状：`ninja strata` 在 `src/kernels/cuda/fused_gr.cu:1089` 报
  `too many arguments provided to function-like macro invocation` +
  `use of undeclared identifier 'cudaFuncSetAttribute'`
- 根因：**gfx906 专用**那套 `include/strata/platform/hip_compat/strata_hip.h` 把 `cudaFuncSetAttribute`
  定义成**函数式宏**；调用点传的是**带逗号的模板实参**（`kern<1, kFusedGrMaxT, false>`）⇒
  预处理器不认 `<>`，按逗号切成 5 个实参 ⇒ 宏不展开。**全仓 16 处**（fused_gr / qsa_prompt_attn / moe_fused / moe_fused_iq）
- 修法（照搬同仓库 **wave32** 那套 `include/strata/hip_compat/cuda_runtime.h` 的已验证写法）：
```cpp
template <typename Kernel>
inline hipError_t cudaFuncSetAttribute(Kernel kernel, hipFuncAttribute attribute, int value) {
    return hipFuncSetAttribute(reinterpret_cast<const void*>(kernel), attribute, value);
}
```
  并补该头**缺失**的 `#define cudaFuncAttributePreferredSharedMemoryCarveout hipFuncAttributePreferredSharedMemoryCarveout`
- 补丁脚本必须**带锚点断言、找不到就 fail-closed 退出**，别做静默替换
- 通用教训：**跨后端移植时"函数式宏"接不了模板实参**，能用内联函数就别用宏

### 7.3 [!] MTP draft 层的两个坑
- **`--mtp` 是 serve 模式的硬要求**：缺了引擎会把模型**全载完**（十几分钟）、打印
  `strata serve: needs --spec T, --mtp DIR and --prefill CHUNK` 然后退出 ⇒ 别省它
- **清单反斜杠**：`mtp_pack.py` 读 `mtp-manifest.json` 的 `file` 字段。若清单由 Windows 侧生成，
  会写成 `tensors\x.bin` ⇒ Linux 下 `Path(src)/'tensors\x.bin'` 成了**带反斜杠的字面文件名**，
  报 `FileNotFoundError`（文件其实就在旁边）。修法：json 读出后 `f.replace('\\','/')` 写回
- 官方口径：draft **固定 `--experts q2_0`**（`setup.py` 里无条件这么调），产物
  `experts.bin 707.8MB / dense.bin 116MB / dense.txt 29 行 / draft_vocab.bin`，共约 6 GB

### 7.4 [!] 重启的两条自伤（现象与真因完全不像）
1. **`pkill -f` 匹配到自身**：`bash -lc 'pkill -f "build-906/strata"; ...'` —— shell 自己的 cmdline 就含这串字
   ⇒ 自杀 ⇒ **后面所有清理命令一条都没执行**，且 `docker exec` 输出为空（极易误判为"已清干净"）。
   自免写法：`pkill -f "build-906/[s]trata"`（自身含字面 `[s]`，不匹配该正则），或直接按 PID 杀。
2. **硬杀引擎后 server 变僵尸占端口**：`-9` 杀掉引擎 → `serve/server.py` **不自己退**，
   留 `[strata] <defunct>` 僵尸子进程，端口一直被攥 ⇒ 新实例报 `port 8090 is already in use`。
   **定式：先杀 server、再杀引擎**；启动前用 `ps -eo pid,ppid,etime,pcpu,args` 确认无残留
   （容器里**没有 `ss`/`fuser`**，只有 pkill/pgrep）。
3. **判活别信 curl**：引擎死后旧 server 仍会回 `/v1/models` 200。要看：引擎进程存在 + VRAM 占用 + 新日志三者同时成立。

### 7.5 资源与耗时（1×MI50 32GB + Xeon E5-2696v4 22C，UD-Q4_K_XL 111 GB）
- 首启 **240 s**；`--resident-budget-gib 76` 会被引擎**自己 clamp**成"显存装不下的那部分"
  （实测 46.94 / 48.74 GiB），不是给多少用多少
- 专家两层：GPU 缓存 + RAM 页锁定，**两者相加 = 24576 = 全部专家 ⇒ 稳态零文件读**
- ctx 8192 → 131072 的代价仅：GPU 缓存 24.79→22.99 GiB、RAM 46.94→48.74 GiB（**专家仍全常驻**）
  ⇒ **长上下文几乎不要钱，别照抄官方 UD 示例的 8192**（那是给 12 GB 卡的）

### 7.6 实测读数（ctx 131072，KV int8，`--spec 4 --spec-min-p 0.5`）
| 指标 | gfx906 单卡（MI50 32G） | 同机另一台 9070XT 16G |
|---|---|---|
| 量化 | **UD-Q4_K_XL（4-bit）** | IQ2_XS（2-bit） |
| 预填 | **467~470 tok/s**（21.6k 与 71.8k 冷 prompt 同值 ⇒ 线性无衰减） | 622 tok/s |
| 解码（稳态） | **42.2 t/s**（冷启动首请求 25~27） | 34~36 t/s |
| MTP 接受率 | **71~76%（有效）** | 8.5%（被否决） |
| 前缀复用 | 21584/21589 命中 ⇒ TTFT **0.31 s** | — |
| 解码专家缓存命中 | 94% | — |

- 71787 token 冷预填 **152.6 s**（=468.5 tok/s）⇒ 131072 上下文完全可用
- **反直觉但可解释**：gfx906 用**更高位宽**反而解码更快（128 GB 内存让专家全常驻、不挤 PCIe）；
  **预填慢约 1.5×**，与源码判据吻合（**K-quant 的 prompt kernel 是 CUDA-only**，AMD 走退化路径）
- `--suffix-draft` 多数不命中（2/5、0/3），偶尔 15/15；**主要收益全在 MTP**
'''
old = open(p, encoding='utf-8').read()
assert '## 7 gfx906' not in old, '已存在 §7，勿重复追加'
open(p, 'w', encoding='utf-8').write(old + TXT)
b = open(p, 'rb').read()
print('skill bytes', len(b), 'chars', len(b.decode('utf-8')))
