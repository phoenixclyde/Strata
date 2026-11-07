# -*- coding: utf-8 -*-
"""追加今日日志：[W-Strata-04] 166 搬迁专用路径 + 166 实测配置 + UD-Q4_K_XL 裁定 + 新镜像方案。"""
import os

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-05.md'
ANCHOR = '## [W-Strata-04]'

ADD = """

## [W-Strata-04] Strata 搬迁 166：新专用路径 + 目标机实测 + UD-Q4_K_XL 裁定 + 独立镜像方案

### 一、新建专用工作路径（机主要求「专门弄这个事」）
- **本机**：`D:\\strata166\\` —— `scripts\\`（探针/构建/下载器）· `logs\\` · `docker\\`（Dockerfile）· `configs\\` · `transfer\\`（构建上下文）· `weights\\`
- **166**：`/home/albus/strata166/` —— `docker/ src/ build/ weights/ data/ logs/ transfer/`（已建，只建目录）
- 权重仍落 `D:\\idm\\`（既有下载约定）：官方 IQ2_XS 在 `D:\\idm\\Strata-GGUF\\`；UD-Q4_K_XL 在 `D:\\idm\\Strata-UDQ4KXL\\`
- 本机 9070XT 侧的 Strata 脚本仍在 `D:\\workbuddy_space\\2026-10-04-13-25-07\\`（两件事分开）

### 二、166 实测配置（2026-10-05 23:13，只读探针）
| 维度 | 166（实测） | 官方 gfx906 参考机 | 本机 9070XT |
|---|---|---|---|
| GPU | **1× AMD Vega20 / MI50 32GB**（1002:66a1），gfx906，60 CU，wave64，`gfx906:sramecc+:xnack-` | 2× MI50 16GB | RX 9070 XT 16GB |
| VRAM | 34,342,961,152 B = **31.98 GiB**（BAR Region0 仅 **16GB**，非全 BAR） | 32 GB | 15.9 GiB |
| CPU | **Xeon E5-2696 v4，22C/44T，AVX2，无 AVX-512** | E5-2666v3 10C/20T | i7-12700K 12C/20T |
| RAM | **128.7 GB**（可用 121 GB）+ swap 16 GB | 32 GB | 64 GB |
| OS/内核 | Ubuntu 24.04.5，`7.0.0-34-generic` | Ubuntu 24.04 | Windows |
| 驱动 | amdgpu **dkms 6.19.14**；`vm_update_mode=0` + `noretry=1`（RouteB 绕 SDMA fence 死锁）+ `iommu=pt` | 内核 amdgpu | — |
| ROCm | 系统 `/opt/rocm-6.4.4`；容器里 ROCm 10.1/HIP 7.14 | HIP 7.14 | 预编译包内 |
| 磁盘 | 单块 Fanxiang S100Pro SSD（ROTA=0）935G，**余 272G** | SATA SSD | NVMe 余 389G |
| 其它 GPU | **RTX 2070 8GB** + ASPEED BMC | — | — |
⇒ **单卡 32GB ≈ 参考机的 2×16GB 总容量**，但官方明写「a single-card run 未做」⇒ **无先例**。
RAM 是参考机 4 倍、CPU 2.2 倍 —— 这两项正是 Strata 的结构性优势项（RAM 层＝第二计算层）。

**166 出网实测**：modelscope / huggingface / hf-mirror / github **全部不通**（8s 超时）；
**只有 pip（清华源 52MB/s）与 apt（archive.ubuntu.com / tuna / aliyun 均可）可达**。
⇒ **权重必须靠内网从本机传**；本机 ModelScope 8 连接 110MB/s。

**166 端口已被占**：8080(open-webui 映射) · 8081(searxng) · 8000/9443(portainer) · 8188(comfyui) · 19999/8125(netdata) · 4096(opencode) · 3000
⇒ **Strata 必须另选端口（定 8090）**，且**不许动这些容器**。

**166 已有 docker 资产**：`routek-base:gfx906-rocm101-hip716-torch215`（10.8GB，**RouteB 的 layer-0，标签 org.routek.*，不许碰**）；
`mixa3607/vllm-gfx906:0.20.1-rocm-7.2.1-aiinfos`（26.2GB，含 cmake/ninja/clang/hipcc）；
`docker.1ms.run/mixa3607/llama.cpp-gfx906:v0.5.0-rocm-7.14`（7.86GB，HIP **7.14**，但**无 cmake/ninja**）。

### 三、UD-Q4_K_XL 在 AMD 上「不是死路，但缺的正是预填」——源码裁定
- `setup.py` 对 `nvidia_only` 走 **`confirm_risk`（提示，不是拒绝）**，文档也写 `--model UD-Q4_K_XL --yes` 会试 ⇒ 机主判读正确
- `CMakeLists.txt` 选项原文：
  - `STRATA_MMQ_KQUANTS` "Build the **CUDA** MMQ prompt kernels for Q4_K / Q5_K / Q5_1 experts"（注释**点名 UD-Q4_K_XL**，`CMakeLists.txt:1056-1062`）
  - `STRATA_PREFILL_MMQ` "Build the optional GGML MMQ prefill path for **HIP**"，但 **requires `STRATA_ENABLE_HIP=ON`**
  - 而 `STRATA_HIP_GFX906` **强制 `STRATA_ENABLE_CUDA=ON` 并 FATAL 拒绝 `STRATA_ENABLE_HIP`**（「一次只能一个 HIP 构建」）
  ⇒ **gfx906 上装不了 HIP 的 MMQ 预填**；K-quant 的 MMQ 实例只有 CUDA 那条路
- `STRATA_NATIVE_EXPERTS` 默认 **ON**，但其描述是「Native (**IQ**) expert support」⇒ K-quant 专家不在其中
- `docs/AMD_HIP.md#gfx906` 的 mode 7 原文：「**the IQ formats only**（Unsloth's K-quant / Q5_1 / Q8_0 experts **take the CUDA layout**）」
⇒ 结论口径：**解码大概率能跑（走 CUDA 布局内核），长 prompt 会明显慢**；能否起得来要实测。
⇒ 因此新镜像**默认带上 `-DSTRATA_MMQ_KQUANTS=ON`**（低风险、正是为 UD-Q4_K_XL 而设；失败可 `--build-arg SMMQ_KQUANTS=OFF` 回退）。

### 四、新独立镜像方案（不碰 routek-base）
- 底座：**`docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete`** —— Strata 官方 gfx906 文档指定的那个环境（HIP 7.14），
  且 166 上 **manifest 探测 rc=0（668B）⇒ 可拉**；直连 `registry-1.docker.io` 不通、daocloud 未白名单。
- Dockerfile 已写在 `D:\\strata166\\docker\\Dockerfile`：底座 → apt 装 cmake/ninja-build（apt 可达）→ 解源码与 llama.cpp →
  `cmake -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 -DSTRATA_GGML_DIR=... -DCMAKE_C/CXX_COMPILER=/opt/rocm/llvm/bin/clang++` + `-DSTRATA_MMQ_KQUANTS=ON` → `ninja strata` → 装 serve 的 py 依赖（tuna 源）
- 构建上下文（很小，47.67 MB）：`transfer/strata-src-0.1.39.zip`（14.68MB）+ `transfer/llama.cpp-3cf0325.tar.gz`（32.99MB，2824 文件）
  ⚠ llama.cpp 的**原 zip 已被本机 safe-delete shim 删掉**，是重新打包已解压目录得到的
- 起容器需 `--device=/dev/kfd --device=/dev/dri --group-add video --ipc=host --ulimit memlock=-1`
- 权重（UD-Q4_K_XL 111.34GB，4 片：0.01+49.86+49.38+12.09）本机下到 `D:\\idm\\Strata-UDQ4KXL\\`，下完移入 `D:\\strata166\\weights\\`

### 五、本轮新增文件
- `D:\\strata166\\scripts\\`：`_probe166.py`（首轮全采）· `_probe166b.py`（构建环境/gguf/pip/磁盘）· `_probe166_base.py`（镜像底座盘点）·
  `_mk166dir.py`（建 166 目录）· `_mk_buildctx.py`（构建上下文）· `_buildcheck166.py`（已停）· `_ms_dl_udq4k.py` · `_udq4k_probe.py`
- `D:\\strata166\\docker\\Dockerfile` · `D:\\strata166\\logs\\_166_probe*.txt`
"""

b0 = open(P, 'rb').read()
assert ANCHOR.encode('utf-8') not in b0, '锚已存在'
data = ADD.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
with open(P, 'ab') as f:
    f.write(data)
b1 = open(P, 'rb').read()
assert b1.startswith(b0) and b0.count(b'\r') == b1.count(b'\r'), '自证失败'
print('APPEND OK  %d -> %d B  (+%d)' % (len(b0), len(b1), len(b1) - len(b0)))
