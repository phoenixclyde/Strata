# -*- coding: utf-8 -*-
"""为「新建独立 Strata-gfx906 镜像」准备构建上下文：源码 zip + llama.cpp 源码 + Dockerfile。"""
import os, shutil, tarfile, time

NEW = r'D:\strata166'
TR = os.path.join(NEW, 'transfer')
DK = os.path.join(NEW, 'docker')
os.makedirs(TR, exist_ok=True)
os.makedirs(DK, exist_ok=True)

# 1) Strata 源码 zip
src_zip = r'D:\Strata\strata-src.zip'
dst_zip = os.path.join(TR, 'strata-src-0.1.39.zip')
if os.path.exists(src_zip):
    shutil.copy2(src_zip, dst_zip)
    print('copy  %-46s %8.2f MB' % ('strata-src-0.1.39.zip', os.path.getsize(dst_zip) / 1048576))
else:
    print('MISSING', src_zip)

# 2) llama.cpp 源码（已解压出来的那份，原 zip 被 safe-delete shim 删了 —— 直接打包目录）
ll = r'D:\Strata\src\Strata-0.1.39\third_party\llama.cpp'
tg = os.path.join(TR, 'llama.cpp-3cf0325.tar.gz')
if os.path.isdir(ll):
    t0 = time.time()
    n = 0
    with tarfile.open(tg, 'w:gz') as tf:
        for root, dirs, files in os.walk(ll):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
            for f in files:
                p = os.path.join(root, f)
                try:
                    tf.add(p, arcname=os.path.join('llama.cpp', os.path.relpath(p, ll)))
                    n += 1
                except OSError:
                    pass
    print('pack  %-46s %8.2f MB  (%d files, %.1fs)'
          % ('llama.cpp-3cf0325.tar.gz', os.path.getsize(tg) / 1048576, n, time.time() - t0))
else:
    print('MISSING', ll)

# 3) 校验关键路径存在（构建时要用）
for k in [os.path.join(ll, 'ggml', 'CMakeLists.txt'), os.path.join(ll, 'gguf-py')]:
    print('  check %-58s %s' % (k.replace(ll, 'llama.cpp'), os.path.exists(k)))

# 4) Dockerfile —— 专用镜像，独立于 routek-base
DOCKERFILE = r'''# Strata on AMD gfx906 (Instinct MI50 / MI60, Radeon VII) — 专用镜像
#
# 为什么不复用现成镜像：routek-base / routek-vllm 是 RouteB 的 layer-0 资产（org.routek.* 标签），
# 不动它们；本镜像自带 Strata v0.1.39 + pinned llama.cpp + 已编译好的 gfx906 引擎。
#
# 底座：mixa3607/rocm-gfx906:7.14-complete
#   —— Strata docs/AMD_HIP.md#gfx906 指定的 gfx906 构建环境（HIP 7.14，含 gfx906 的 rocBLAS/hipBLAS 内核）。
#   166 上 registry-1.docker.io 不通，走本地已验证可达的镜像源 docker.1ms.run（manifest 探测通过）。
FROM docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete

ENV DEBIAN_FRONTEND=noninteractive
# 有些主板上 gfx906 要这一步运行时才认卡（文档原话）；不想要就 docker run -e HSA_OVERRIDE_GFX_VERSION=
ENV HSA_OVERRIDE_GFX_VERSION=9.0.6

# 构建工具（镜像里已有 hipcc/clang/gcc/git/python3；缺 cmake/ninja）
RUN set -eux; \
    (apt-get update && apt-get install -y --no-install-recommends \
        cmake ninja-build ca-certificates python3-venv python3-pip unzip \
     && rm -rf /var/lib/apt/lists/*) \
    || (pip3 install --no-cache-dir --break-system-packages cmake ninja); \
    cmake --version | head -1; ninja --version

WORKDIR /src
# Strata 源码（v0.1.39）+ pinned llama.cpp（ggml / gguf-py / mtmd 来源）
COPY transfer/strata-src-0.1.39.zip /tmp/
COPY transfer/llama.cpp-3cf0325.tar.gz /tmp/
RUN set -eux; \
    unzip -q /tmp/strata-src-0.1.39.zip -d /tmp/srcx; \
    inner=$(find /tmp/srcx -maxdepth 1 -mindepth 1 -type d | head -1); \
    cp -a "$inner"/. /src/; \
    mkdir -p /src/third_party; \
    tar -xzf /tmp/llama.cpp-3cf0325.tar.gz -C /src/third_party; \
    ls -d /src/third_party/llama.cpp/ggml/CMakeLists.txt /src/third_party/llama.cpp/gguf-py

# gfx906 引擎：文档配方 + STRATA_MMQ_KQUANTS=ON
#   前者来自 docs/AMD_HIP.md#gfx906（STRATA_HIP_GFX906 会强制打开 CUDA 目标并拒绝 STRATA_ENABLE_HIP）
#   后者编译 Q4_K / Q5_K / Q5_1 的 MMQ 预填实例 —— 正是 Unsloth UD-Q4_K_XL 的专家格式
#   （CMakeLists.txt:1056-1062 的注释原文点名 UD-Q4_K_XL）。默认开，方便直接验证「AMD 上到底行不行」；
#   若它导致配置失败，用 --build-arg SMMQ_KQUANTS=OFF 重来（回退档）。
ARG SMMQ_KQUANTS=ON
RUN set -eux; \
    cmake -S /src -B /src/build-906 -G Ninja \
      -DSTRATA_HIP_GFX906=ON \
      -DCMAKE_HIP_ARCHITECTURES=gfx906 \
      -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
      -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
      -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
      -DSTRATA_MMQ_KQUANTS=${SMMQ_KQUANTS}; \
    ninja -C /src/build-906 strata; \
    /src/build-906/strata --help >/dev/null 2>&1 || true; \
    ls -l /src/build-906/strata

# 运行时需要的 python 依赖（serve/ 用）
RUN pip3 install --no-cache-dir --break-system-packages numpy jinja2 regex pyyaml tqdm requests pillow psutil \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 数据/权重的挂载点
ENV STRATA_SRC=/src
WORKDIR /src
CMD ["/bin/bash"]
'''
p = os.path.join(DK, 'Dockerfile')
open(p, 'w', encoding='utf-8', newline='\n').write(DOCKERFILE)
print('write %-46s %8.2f KB' % ('docker/Dockerfile', os.path.getsize(p) / 1024))

print()
print('=== D:\\strata166\\transfer ===')
for f in sorted(os.listdir(TR)):
    print('  %-46s %8.2f MB' % (f, os.path.getsize(os.path.join(TR, f)) / 1048576))
