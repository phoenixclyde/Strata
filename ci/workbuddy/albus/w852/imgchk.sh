set +e
IMG=strata-gfx906:0.2.9r1
echo "===== [1] 10.1 候选镜像五件套是否齐 ====="
docker run --rm --entrypoint bash "$IMG" -lc '
  echo -n "  /src 文件数: "; find /src -type f | wc -l
  echo -n "  engine 组件: "; ls /opt/strata/components/engine/ 2>/dev/null
  echo -n "  terminal: "; ls -d /opt/strata/terminal 2>/dev/null && /opt/strata/terminal/bin/strata --version 2>&1 | head -1
  echo -n "  seed: "; du -sh /opt/strata/seed 2>/dev/null | cut -f1
  echo -n "  wrapper: "; head -1 /usr/local/bin/strata 2>/dev/null
  echo -n "  PORT: "; echo $PORT
'
echo
echo "===== [2] 与生产 0.2.9t2 的差异（除 /opt/rocm） ====="
docker run --rm --entrypoint bash "$IMG" -lc 'md5sum /src/serve/server.py /src/serve/telemetry.py /usr/local/bin/strata 2>/dev/null' | sed 's/^/  10.1 /'
docker run --rm --entrypoint bash strata-gfx906:0.2.9t2 -lc 'md5sum /src/serve/server.py /src/serve/telemetry.py /usr/local/bin/strata 2>/dev/null' | sed 's/^/  7.14 /'
echo
echo "===== [3] 10.1 下 terminal / wrapper 能不能跑（它们依赖 hip/rocblas） ====="
docker run --rm --entrypoint bash "$IMG" -lc '
  echo -n "  terminal strata --version: "; /opt/strata/terminal/bin/strata --version 2>&1 | head -1
  echo -n "  python 有没有坏: "; /opt/strata/terminal/bin/python3 -c "import sys;print(sys.version.split()[0])" 2>&1 | head -1
  echo -n "  ldd terminal 缺失库数: "; ldd /opt/strata/terminal/bin/python3 2>/dev/null | grep -c "not found"
'
