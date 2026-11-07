set +e
C=strata166-407
D=/home/albus/strata166/gfx029
echo "===== [1] 0.2.9 的 serve 依赖哪些 /src 子系统（import 顶层） ====="
docker exec "$C" bash -lc "python3 - <<'PY'
import ast,os
roots=set()
for r,_,fs in os.walk('/src/serve'):
    for f in fs:
        if not f.endswith('.py'): continue
        p=os.path.join(r,f)
        try: t=ast.parse(open(p,encoding='utf-8',errors='replace').read())
        except Exception: continue
        for n in ast.walk(t):
            if isinstance(n,ast.Import):
                for a in n.names: roots.add(a.name.split('.')[0])
            elif isinstance(n,ast.ImportFrom):
                if n.level==0 and n.module: roots.add(n.module.split('.')[0])
local={'serve','strata_control','strata_cli','strata_tokenizer','tools','apps','bench'}
print('LOCAL-ISH:', sorted(roots & local))
print('THIRD-PARTY:', sorted(roots - local - {'__future__'}))
PY"
echo
echo "===== [2] 关键第三方依赖在镜像里是否可 import ====="
docker exec "$C" bash -lc "cd /src && python3 - <<'PY'
import importlib
for m in ['jinja2','jsonschema','referencing','anthropic','psutil','yaml','numpy','PIL','regex','strata_tokenizer','strata_control','strata_cli','web_i18n']:
    try:
        importlib.import_module(m); print('  OK   ',m)
    except Exception as e: print('  MISS ',m,type(e).__name__,str(e)[:60])
PY"
echo
echo "===== [3] 镜像 /src 顶层 与 0.2.9 树的对应目录 ====="
docker exec "$C" bash -lc "ls /src"
echo "--- 树:"
ls "$D" | head -20
echo
echo "===== [4] 逐文件差（serve / strata_control / strata_cli） ====="
docker exec "$C" bash -lc "cd /src && for d in serve strata_control strata_cli; do find \$d -type f \( -name '*.py' -o -name '*.js' -o -name '*.css' -o -name '*.html' -o -name '*.jinja' \) -exec md5sum {} \; ; done" | sort -k2 > /tmp/img_md5.txt
(cd "$D" && for d in serve strata_control strata_cli; do find $d -type f \( -name '*.py' -o -name '*.js' -o -name '*.css' -o -name '*.html' -o -name '*.jinja' \) -exec md5sum {} \; ; done) | sort -k2 > /tmp/tree_md5.txt
echo -n "  镜像文件数 = "; wc -l < /tmp/img_md5.txt
echo -n "  树文件数   = "; wc -l < /tmp/tree_md5.txt
echo "  内容不同的文件:"; join -j2 /tmp/img_md5.txt /tmp/tree_md5.txt 2>/dev/null | awk '$2!=$3{print "    "$1}' | head -20
echo "  只在树里的（新增）:"; comm -13 <(cut -d' ' -f3 /tmp/img_md5.txt | sort) <(cut -d' ' -f3 /tmp/tree_md5.txt | sort) | head -12
echo
echo "===== [5] 0.2.9 新增的 strata_control/replica_profile.py 是否存在 ====="
ls -l "$D/strata_control/replica_profile.py" 2>/dev/null || echo "  树里没有 replica_profile.py"
docker exec "$C" bash -lc "ls /src/strata_control/replica_profile.py 2>/dev/null || echo '  镜像里没有 replica_profile.py'"
