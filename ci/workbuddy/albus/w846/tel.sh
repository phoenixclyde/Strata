set +e
echo "===== [1] /metrics 顶层段 ====="
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;d=json.load(sys.stdin)
print('top-level:', sorted(d.keys()))
for k in d:
    if isinstance(d[k],dict): print('  %-12s keys(前12): %s' % (k, sorted(d[k].keys())[:12]))
"
echo
echo "===== [2] 原始 JSON 里的 pcie / fru 字样 ====="
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json,re;raw=sys.stdin.read()
for kw in ('pcie','fru','bw_','vram'):
    hits=[m.start() for m in re.finditer(kw,raw)]
    print('  %-6s 命中 %d' % (kw,len(hits)))
d=json.loads(raw)
def walk(o,p=''):
    if isinstance(o,dict):
        for k,v in o.items(): walk(v,p+'/'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o[:3]): walk(v,p+'[%d]'%i)
    else:
        if any(t in p.lower() for t in ('pcie','fru')): print('   ',p,'=',o)
walk(d)
"
echo
echo "===== [3] 遥测补丁是否还在（telemetry.py 内容特征） ====="
docker exec strata166-407 bash -lc "grep -c 'pcie' /src/serve/telemetry.py; grep -n 'gpu_pcie\|FRU\|fru' /src/serve/telemetry.py | head -6"
