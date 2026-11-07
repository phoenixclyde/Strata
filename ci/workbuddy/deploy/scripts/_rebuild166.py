# -*- coding: utf-8 -*-
"""修 Dockerfile 并在 166 重建：去掉失效的 gfx906 apt 源、装全工具链、PATH 带上 rocm llvm。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CTX = '/home/albus/strata166/build-ctx'
LOG = '/home/albus/strata166/logs/build-image.log'

DOCKERFILE = r'''# Strata on AMD gfx906 (Instinct MI50 / MI60, Radeon VII) — 专用镜像
#
# 独立于 RouteB 的 routek-* 资产（那些带 org.routek.* 标签，不碰）。
# 底座 mixa3607/rocm-gfx906:7.14-complete = Strata docs/AMD_HIP.md#gfx906 指定的 gfx906 环境（HIP 7.14）。
#
# 底座实测构成（2026-10-05）：Ubuntu 24.04.4 · python3.12(无 pip) · git/tar/sha256sum 有 ·
#   hipcc 有(/opt/rocm/bin) · **clang++ 只在 /opt/rocm/llvm/bin（不在 PATH）** ·
#   **cmake/ninja/gcc/g++/unzip/pip 全缺** ·
#   且自带 apt 源 /etc/apt/sources.list.d/gfx906.sources -> s3.arkprojects.space 已 403 失效，
#   会让 apt-get update 整体失败 —— 所以必须先删掉它（镜像内已烘进 gfx906 的 ROCm 库，不依赖该源）。
FROM docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete

ENV DEBIAN_FRONTEND=noninteractive
# 有些主板上 gfx906 要这一步运行时才认卡（文档原话）；不要就用 docker run -e HSA_OVERRIDE_GFX_VERSION=
ENV HSA_OVERRIDE_GFX_VERSION=9.0.6
# 让 clang/clang++（ROCm llvm）先被找到
ENV PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# ---- 构建工具链 ----
RUN set -eux; \
    rm -f /etc/apt/sources.list.d/gfx906.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build ca-certificates unzip \
        python3-pip python3-venv python3-dev pkg-config; \
    rm -rf /var/lib/apt/lists/*; \
    cmake --version | head -1; \
    ninja --version; \
    python3 -m pip --version; \
    clang++ --version | head -1

WORKDIR /src
# ---- Strata 源码(v0.1.39) + pinned llama.cpp（ggml / gguf-py / mtmd 来源）----
COPY transfer/strata-src-0.1.39.zip /tmp/
COPY transfer/llama.cpp-3cf0325.tar.gz /tmp/
RUN set -eux; \
    unzip -q /tmp/strata-src-0.1.39.zip -d /tmp/srcx; \
    inner=$(find /tmp/srcx -maxdepth 1 -mindepth 1 -type d | head -1); \
    cp -a "$inner"/. /src/; \
    mkdir -p /src/third_party; \
    tar -xzf /tmp/llama.cpp-3cf0325.tar.gz -C /src/third_party; \
    ls -d /src/third_party/llama.cpp/ggml/CMakeLists.txt /src/third_party/llama.cpp/gguf-py

# ---- gfx906 引擎 ----
#   主配方来自 docs/AMD_HIP.md#gfx906（STRATA_HIP_GFX906 会强制打开 CUDA 目标并拒绝 STRATA_ENABLE_HIP）
#   + STRATA_MMQ_KQUANTS=ON：编译 Q4_K / Q5_K / Q5_1 的 MMQ 预填实例，正是 Unsloth UD-Q4_K_XL 的专家格式
#     （CMakeLists.txt:1056 注释点名 UD-Q4_K_XL）。它本意是给 CUDA 用的，但 gfx906 分支
#     会把 CUDA 目标通过 hip_compat 用 HIP 编，故值得一试；失败可 --build-arg SMMQ_KQUANTS=OFF 回退。
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
    ls -l /src/build-906/strata; \
    /src/build-906/strata --help 2>&1 | head -3 || true

# ---- serve/ 的 python 依赖（清华源）----
RUN python3 -m pip install --no-cache-dir --break-system-packages \
      --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
      numpy jinja2 regex pyyaml tqdm requests pillow psutil \
    && python3 -c "import numpy,jinja2,psutil; print('py deps ok')"

ENV STRATA_SRC=/src
WORKDIR /src
CMD ["/bin/bash"]
'''
open(r'D:\strata166\docker\Dockerfile', 'w', encoding='utf-8', newline='\n').write(DOCKERFILE)
print('Dockerfile 本地已更新，%d 字节' % len(DOCKERFILE.encode('utf-8')))

script = '''set +e
CTX=%s
echo '%s' | base64 -d > $CTX/Dockerfile
echo "=== 语法检查（前 20 行）==="; head -20 $CTX/Dockerfile
echo
echo "=== 清掉上次失败的 build（只清 build cache，不动镜像/容器）==="
docker builder prune -f 2>&1 | tail -2
echo
echo "=== 磁盘 ==="; df -h / | tail -1
echo "=== 重新后台构建 ==="
cd /home/albus/strata166
setsid nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f $CTX/Dockerfile $CTX \\
  > %s 2>&1 < /dev/null &
echo "launched pid=$!"
sleep 25
echo "--- log tail ---"; tail -20 %s
''' % (CTX, base64.b64encode(DOCKERFILE.encode('utf-8')).decode('ascii'), LOG, LOG)

b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:600])
