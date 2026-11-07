set +e
D=/home/albus/strata166/gfx029
C=strata166-407
echo "===== [1] 缺失依赖到底被谁 import（文件:行） ====="
for m in jsonschema referencing anthropic strata_tokenizer web_i18n; do
  echo "--- $m:"
  grep -rn "^import $m\|^from $m\|[^a-zA-Z_.]$m" "$D/serve" --include=*.py 2>/dev/null | grep -E "import|from" | head -5
done
echo
echo "===== [2] web_i18n / strata_tokenizer 是什么（在树里是不是本地模块） ====="
ls -l "$D/serve/web_i18n.py" "$D/web_i18n" 2>/dev/null
find "$D" -maxdepth 2 -name "web_i18n*" -o -maxdepth 2 -name "strata_tokenizer*" 2>/dev/null | head -6
docker exec "$C" bash -lc "ls -d /src/web_i18n* /src/serve/web_i18n* /src/strata_tokenizer* 2>/dev/null"
echo
echo "===== [3] requirements 差异 ====="
echo "--- 镜像 /src/requirements.txt:"; docker exec "$C" bash -lc "cat /src/requirements.txt 2>/dev/null | head -20"
echo "--- 树 requirements.txt:"; head -20 "$D/requirements.txt" 2>/dev/null
echo "--- 树 requirements-monitor.txt:"; head -12 "$D/requirements-monitor.txt" 2>/dev/null
echo
echo "===== [4] server.py 的启动期 import 链是否触碰这些模块 ====="
docker exec "$C" bash -lc "python3 - <<'PY'
import ast,os,sys
base='/src'
seen=set(); stack=['serve.server']
def finds(mod):
    p=mod.replace('.','/')
    for cand in (os.path.join(base,p+'.py'), os.path.join(base,p,'__init__.py')):
        if os.path.exists(cand): return cand
    return None
risky={'jsonschema','referencing','anthropic','strata_tokenizer','web_i18n'}
hit=[]
while stack:
    m=stack.pop()
    if m in seen: continue
    seen.add(m)
    f=finds(m)
    if not f: continue
    try: t=ast.parse(open(f,encoding='utf-8',errors='replace').read())
    except Exception: continue
    for n in ast.walk(t):
        mods=[]
        if isinstance(n,ast.Import): mods=[a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom) and n.level==0 and n.module: mods=[n.module]
        for mm in mods:
            root=mm.split('.')[0]
            if root in risky: hit.append((m,mm,n.lineno))
            elif root in ('serve','strata_control','strata_cli') and mm not in seen: stack.append(mm)
print('静态可达模块数:', len(seen))
print('启动链里触碰风险模块:', hit if hit else '无')
PY"
