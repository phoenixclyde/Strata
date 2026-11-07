set -eu
D=/home/albus/strata166/gfx029
CTX=/home/albus/strata166/img029s
TAG=strata-gfx906:0.2.9s1
rm -rf "$CTX"; mkdir -p "$CTX"
cd "$CTX"

echo "===== [1] 组装上下文（仅运行时需要的 4 处） ====="
cp -a "$D/serve" serve
cp -a "$D/strata_cli" strata_cli
cp -a "$D/strata_control" strata_control
mkdir -p tools
cp -a "$D/tools/strata_tokenizer.py" "$D/tools/web_i18n.py" tools/ 2>/dev/null || true
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
du -sh serve strata_cli strata_control tools | sed 's/^/  /'

cat > Dockerfile <<'DOCKER'
# W846: serve 层叠到 0.2.9（引擎 0.1.55 已跑 0.2.9 树构建产物；此层只补 Python 侧）
# 目的：让 /src/serve 与源码树 gfx029 一致，解锁 COALESCE_PREFILL / PAR_COUNTERS / replicas。
FROM strata-gfx906:0.2.8p2
COPY serve /src/serve
COPY strata_cli /src/strata_cli
COPY strata_control /src/strata_control
COPY tools/strata_tokenizer.py /src/tools/strata_tokenizer.py
COPY tools/web_i18n.py /src/tools/web_i18n.py
DOCKER

cat > .dockerignore <<'IGN'
**/__pycache__
**/*.pyc
IGN

echo "===== [2] 构建 ====="
docker build -t "$TAG" . 2>&1 | tail -8
docker images "$TAG" --format '  {{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}'

echo "===== [3] 叠加验证：镜像里的 serve 是否 = 树里（逐文件 md5） ====="
docker run --rm --entrypoint bash "$TAG" -lc 'cd /src && md5sum serve/server.py serve/replicas.py strata_control/replica_profile.py serve/telemetry.py serve/web/app.js serve/web/app.css tools/strata_tokenizer.py' | sed 's/^/  IMG  /'
( cd "$D" && md5sum serve/server.py serve/replicas.py strata_control/replica_profile.py serve/telemetry.py serve/web/app.js serve/web/app.css tools/strata_tokenizer.py ) | sed 's/^/  TREE /'

echo "===== [4] 导入自检（不起引擎、不占显存） ====="
docker run --rm --entrypoint python3 "$TAG" -c "
import sys, importlib, traceback
sys.path.insert(0,'/src')
mods=['serve.server','serve.replicas','serve.frontend','serve.telemetry','serve.structured','serve.lifeline','serve.runconfig','strata_control.replica_profile','strata_control.gpu_pick','strata_cli','strata_tokenizer','web_i18n']
bad=[]
for m in mods:
    try:
        importlib.import_module(m); print('  OK   ',m)
    except Exception as e:
        bad.append((m,type(e).__name__,str(e)[:90])); print('  FAIL ',m,type(e).__name__,str(e)[:90])
print('IMPORT-FAIL:',len(bad))
sys.exit(1 if bad else 0)
"
echo "IMG-OK"
