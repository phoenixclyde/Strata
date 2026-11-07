set +e
C=/home/albus/strata166/img029t
TAG=strata-gfx906:0.2.9t
rm -rf "$C"; mkdir -p "$C"
cp /home/albus/strata166/termout/strata-terminal-0.1.55-linux-x86_64.tar.gz "$C/term.tar.gz"
cat > "$C/Dockerfile" <<'DOCKER'
# W848: 把 0.2.9 的 Terminal + seed 装进镜像（此前 /opt/strata 里只有 components，terminal/seed 根本不存在）
# 步骤与上游 Dockerfile 的 terminal stage 一致：解包 → /opt/strata/terminal → 产出 seed → 装 strata wrapper
FROM strata-gfx906:0.2.9
COPY term.tar.gz /tmp/term.tar.gz
RUN set -e; \
    mkdir -p /opt/strata; \
    tar -xzf /tmp/term.tar.gz -C /opt/strata; \
    mv /opt/strata/strata-terminal-* /opt/strata/terminal; \
    rm -f /tmp/term.tar.gz; \
    /opt/strata/terminal/bin/strata --version
RUN set -e; \
    mkdir -p /opt/strata/seed; \
    cd /src && tar -cf - setup.py requirements.txt requirements-build.txt requirements-monitor.txt strata.py \
        strata_control strata_cli serve tools docs data ref CMakeLists.txt bin packaging conftest.py \
        | tar -xf - -C /opt/strata/seed; \
    mkdir -p /opt/strata/seed/third_party; \
    cp -a /src/third_party/llama.cpp /opt/strata/seed/third_party/; \
    cd /opt/strata/seed/third_party/llama.cpp; \
    find . -mindepth 1 -maxdepth 1 ! -name gguf-py ! -name ggml ! -name 'LICENSE*' -exec rm -rf {} + ; \
    find ggml -mindepth 1 -depth ! -type d ! -name CMakeLists.txt -delete; \
    find ggml -mindepth 1 -type d -empty -delete; \
    du -sh /opt/strata/seed
RUN cp /src/docker/strata-wrapper.sh /usr/local/bin/strata && chmod 0755 /usr/local/bin/strata && /usr/local/bin/strata --help 2>&1 | head -5
DOCKER
echo "===== [1] 构建 ====="
docker build -t "$TAG" "$C" 2>&1 | grep -E "^(#[0-9]+ (\[|DONE|ERROR))|stra[^ ]* |Size|naming|DONE|ERROR" | tail -14
docker image inspect "$TAG" --format '  id={{.Id}} size={{.Size}}'
echo
echo "===== [2] 自证 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  /opt/strata: "; ls /opt/strata | tr "\n" " "; echo
  echo -n "  terminal/bin/strata --version: "; /opt/strata/terminal/bin/strata --version 2>&1 | head -2
  echo -n "  seed 大小: "; du -sh /opt/strata/seed 2>/dev/null | cut -f1
  echo -n "  seed 里 llama.cpp 内容: "; ls /opt/strata/seed/third_party/llama.cpp 2>/dev/null | tr "\n" " "; echo
  echo -n "  wrapper: "; head -3 /usr/local/bin/strata 2>/dev/null | tr "\n" " "; echo
  echo -n "  /src 仍在: "; md5sum /src/serve/server.py | cut -d" " -f1
'
