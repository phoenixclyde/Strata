set +e
cd /home/albus/strata166/gfx906
echo "=== generate.cpp 11175-11250 ==="
sed -n '11175,11250p' src/program/generate.cpp
echo
echo "=== 日志完整行（policy / all_cached） ==="
docker exec strata166-407 bash -lc "grep -a -A3 'expert cache 7463 slots' /data/strata-huihui-ud-iq4_xs.log | tail -12"
echo
echo "=== metrics 里 decode 窗口相关字段 ==="
python3 - <<'PY'
import json,urllib.request
d=json.loads(urllib.request.urlopen("http://127.0.0.1:8090/metrics",timeout=8).read().decode())
def walk(o,p=""):
    if isinstance(o,dict):
        for k,v in o.items():
            walk(v,p+"/"+k)
    else:
        low=p.lower()
        if any(s in low for s in ("pcie","miss","ms_","window","expert","decode")):
            print(p,"=",o)
walk(d)
PY
