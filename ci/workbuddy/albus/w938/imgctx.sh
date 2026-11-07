#!/bin/bash
set -u
CTX=/home/albus/strata166/build-ctx-210
R=/home/albus/strata166/work/rebase-trial
mkdir -p "$CTX"

echo "=== 1) 源码树打包（排除 .git / build 产物） ==="
tar czf "$CTX/strata-src-0.2.10.tar.gz" -C "$R" --exclude=.git --exclude=build-906 --exclude=build . 2>/dev/null
ls -lh "$CTX/strata-src-0.2.10.tar.gz" | awk '{print $5, $9}'

echo
echo "=== 2) llama.cpp 复用现有包 ==="
cp -f /home/albus/strata166/transfer/llama.cpp-3cf0325.tar.gz "$CTX"/ && ls -lh "$CTX/llama.cpp-3cf0325.tar.gz" | awk '{print $5, $9}'

echo
echo "=== 3) 写 Dockerfile ==="
cat > "$CTX/Dockerfile-0.2.10" <<'EOF'
# Strata on AMD gfx906 (Instinct MI50/MI60, Radeon VII) -- v0.2.10, engine 0.1.56
#
# 与 0.2.9-101 的差异：/src 换成 rebase 到 upstream v0.2.10 的树（37 条 gfx906 提交重放）；
# 不再带本地补丁树：0.2.10 已原生包含 PLE 提限(5a13c34f)、fatal GPU 自退(e1b27d54)、
# PF_GROUP_SCRATCH(fbf6e1c7)、penalty 窗口(ed76b12f)、stop bound(243fdb21)、dispatch counters(af6ba4c6)。
# 引擎二进制不放进镜像（/data 是 bind，引擎走 /data/bin 的版本文件 + ci 账本）。
FROM docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete

ENV DEBIAN_FRONTEND=noninteractive
ENV HSA_OVERRIDE_GFX_VERSION=9.0.6
ENV PATH=/opt/rocm/llvm/bin:/opt/rocm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV STRATA_SRC=/src
ENV PORT=8090

# 底座自带的 gfx906 apt 源已 403，必须删掉，否则 apt-get update 整体失败
RUN set -eux; \
    rm -f /etc/apt/sources.list.d/gfx906.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build ca-certificates unzip \
        python3-pip python3-venv python3-dev pkg-config; \
    rm -rf /var/lib/apt/lists/*; \
    cmake --version | head -1; ninja --version; clang++ --version | head -1

WORKDIR /src

COPY strata-src-0.2.10.tar.gz /tmp/
COPY llama.cpp-3cf0325.tar.gz /tmp/

RUN set -eux; \
    tar xzf /tmp/strata-src-0.2.10.tar.gz -C /src; \
    mkdir -p /src/third_party; \
    tar xzf /tmp/llama.cpp-3cf0325.tar.gz -C /src/third_party; \
    inner=$(find /src/third_party -maxdepth 1 -mindepth 1 -type d -name 'llama.cpp*' | head -1); \
    if [ "$inner" != "/src/third_party/llama.cpp" ]; then mv "$inner" /src/third_party/llama.cpp; fi; \
    rm -f /tmp/strata-src-0.2.10.tar.gz /tmp/llama.cpp-3cf0325.tar.gz; \
    grep -n 'project(strata VERSION' /src/CMakeLists.txt; \
    test -f /src/serve/server.py; \
    test -f /src/third_party/llama.cpp/ggml/CMakeLists.txt; \
    du -sh /src

# 运行期 python 依赖（serve/ 与 monitor）；源用国内镜像，失败即构建失败
RUN set -eux; \
    python3 -m pip install --no-cache-dir --break-system-packages \
      --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
      numpy jinja2 regex pyyaml tqdm requests pillow psutil; \
    python3 -c "import numpy,jinja2,psutil; print('py deps ok')"

# 记录本镜像对应的源码状态（可追溯）
RUN set -eux; \
    echo "{\"source\": \"rebase onto upstream v0.2.10 (ffa80d73) from gfx906/mi50 d963c791\", \"commits_on_top\": 37, \"engine\": \"0.1.56\", \"rebase_date\": \"2026-11-04\"}" > /src/BUILD-IMAGE.json

CMD ["/bin/bash"]
EOF
ls -l "$CTX"/*.tar.gz "$CTX/Dockerfile-0.2.10" | awk '{print $5, $9}'
echo
echo "=== 4) 构建进度 ==="
grep -E "^\[[0-9]+/165\]" ~/strata166/build-r28/_build.log | tail -1
grep -c "error:" ~/strata166/build-r28/_build.log
