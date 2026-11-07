# -*- coding: utf-8 -*-
"""追加日志：[W-Strata-06] 镜像建成（含 hip_compat 补丁血证）+ 权重校验全过 + pack 中。"""
import os

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
ANCHOR = '## [W-Strata-06]'
os.makedirs(os.path.dirname(P), exist_ok=True)

ADD = """
## [W-Strata-06] 166 上的 gfx906 镜像建成 —— 关键卡点是 hip_compat 的「函数式宏吃模板逗号」

### 一、最终产物
- 镜像 **`strata-gfx906:0.1.39`**（6.52 GB），底座 `docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete`
- 容器 **`strata166`** 已起：`--device=/dev/kfd --device=/dev/dri --group-add video --ipc=host --ulimit memlock=-1`，
  只读挂 `/weights`、可写挂 `/data`、端口 **8090**
- 容器内 `rocminfo` 认到 **gfx906 / 60 CU / wave64 / `gfx906:sramecc+:xnack-`**，rocm-smi 看到 31.98 GiB VRAM 全空
- 引擎 `/src/build-906/strata`（19,443,712 B）可执行、`--help` 正常

### 二、**[!] 血证：gfx906 的 hip_compat 用函数式宏映射 cudaFuncSetAttribute，被模板逗号拆坏**
**症状**：`ninja strata` 在 `src/kernels/cuda/fused_gr.cu:1089` 报
`error: too many arguments provided to function-like macro invocation` +
`use of undeclared identifier 'cudaFuncSetAttribute'; did you mean 'hipFuncSetAttribute'?`
（共 12 errors）

**根因**：`include/strata/platform/hip_compat/strata_hip.h`（**gfx906 专用**那套）写的是
`#define cudaFuncSetAttribute(fn, attr, val) hipFuncSetAttribute(reinterpret_cast<const void*>(fn), attr, val)`；
而调用点传的是**带逗号的模板实参**：`cudaFuncSetAttribute(gr_down_v3_kernel<1, kFusedGrMaxT, false>, …)`。
**预处理器不认 `<>`**，按逗号切成 5 个实参 → 宏不展开 → 标识符未声明。
全仓共 **16 处**这种调用：`fused_gr.cu`(8) · `qsa_prompt_attn.cu`(2) · `moe_fused.cu`(2) · `moe_fused_iq.cu`(1) 等。

**修法（最小补丁，已写进 Dockerfile 的构建步骤）**：照搬**同仓库 wave32 那套**已验证写法
（`include/strata/hip_compat/cuda_runtime.h`）—— 把宏换成**模板内联函数**（函数实参按 C++ 语法解析，模板逗号无碍）：
```cpp
template <typename Kernel>
inline hipError_t cudaFuncSetAttribute(Kernel kernel, hipFuncAttribute attribute, int value) {
    return hipFuncSetAttribute(reinterpret_cast<const void*>(kernel), attribute, value);
}
```
并补上该头缺失的 `#define cudaFuncAttributePreferredSharedMemoryCarveout hipFuncAttributePreferredSharedMemoryCarveout`
（wave32 那套有，gfx906 那套漏了）。
补丁脚本：`D:\\strata166\\docker\\patch_hipcompat.py`（内含断言，锚点找不到就 fail-closed 退出）。
⇒ 通用教训：**跨后端移植时，"函数式宏"接不了模板实参**；能用内联函数就别用宏。

### 三、底座镜像的三个坑（都已处理）
1. 自带 apt 源 `/etc/apt/sources.list.d/gfx906.sources` → `s3.arkprojects.space` **403 失效**，
   会让 `apt-get update` 整体失败 ⇒ 构建时先 `rm -f` 它（镜像里已烘进 gfx906 的 ROCm 库，不依赖该源）
2. **没有 pip/pip3、没有 cmake/ninja/gcc/g++/unzip** ⇒ 必须 apt 装（apt 走 archive.ubuntu.com，实测只有 ~504 kB/s）
3. **clang++ 只在 `/opt/rocm/llvm/bin`，不在 PATH** ⇒ Dockerfile 里显式把它放到 PATH 最前

### 四、权重与传输（本波收口）
- 本机下载 111.33 GB（4 片），32 分钟内；**sha256 四片全部 match**（比对 `setup.py` 的 `UNSLOTH_SHARDS` 钉死值）
- 内网传 166：4 片并行裸流 **22.2 分钟 / 79.8 MB/s**；传后远端 size 逐片核对 OK；**远端 sha256 四片也全部 match**
- 结论：**「下载 → 传输 → 落盘」三道都逐字节可信**（Content-Range 硬校验 + size + sha256）

### 五、UD-Q4_K_XL 的官方启动要点（`docs/UNSLOTH_Q4.md`，照抄而非猜）
- `--native` 指 **shard 1**；**不需要 `--ple-gguf`** —— 引擎按名字自己找 `per_layer_token_embd.weight`（本仓在 **shard 2**）
- ⚠ **shard 1 是 0 张量的元数据片**（10,946,624 B），PLE 表在 shard 2（形状 `[160, 320001536]` = 28.8 GB）
- `--resident-budget-gib N` **会启用 mapped 模式**（蕴含 `--mmap-experts`）；N = 你的 RAM − 20~24 GB。
  166 有 125 GB ⇒ 给 76（引擎自己 clamp，最多全部 71 GiB 专家常驻，即**不读 SSD**）
- pack 必须带 `--compat-bf16`（195 个 Q8_0 小投影要降到 BF16），且**不要** `--experts-bin`
- `--expert-profile data/expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5`
"""

P_ = os.path.join(r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory', '2026-10-06.md')
b0 = open(P_, 'rb').read() if os.path.exists(P_) else b''
if ANCHOR.encode('utf-8') in b0:
    print('锚已存在，跳过')
else:
    data = ADD.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
    with open(P_, 'ab') as f:
        f.write(data)
    b1 = open(P_, 'rb').read()
    assert b1.startswith(b0) and b0.count(b'\r') == b1.count(b'\r'), '自证失败'
    print('APPEND OK 2026-10-06.md  %d -> %d B  (+%d)' % (len(b0), len(b1), len(b1) - len(b0)))
