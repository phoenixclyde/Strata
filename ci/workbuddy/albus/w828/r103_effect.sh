C=strata166-407
CFG=$(docker inspect "$C" --format '{{json .Config.Cmd}}' | tr ',' '\n' | grep -o '/data/[a-z0-9_.-]*\.json' | head -1)
LOG=$(docker exec "$C" bash -lc "python3 -c \"import json;print(json.load(open('$CFG')).get('log'))\"" 2>/dev/null | tr -d '\r')
echo "cfg=$CFG"
echo
echo "=== 1. effects in THIS boot's log (env -> what the engine said) ==="
for pat in "K-quant prompt kernels" "PROMPT_F16" "prompt chunk" "expert cache" "rocBLAS" "resident" "reduce12\|REDUCE12" "swizzle\|SWIZZLE" "GDN" "HC_Q8\|hyper" "SIMT" "tail skip\|TAIL_SKIP" "MMQ"; do
  line=$(docker exec "$C" bash -lc "grep -ai '$pat' '$LOG' 2>/dev/null | tail -1 | cut -c1-190")
  [ -n "$line" ] && echo "  [$pat] $line"
done
echo
echo "=== 2. binary provenance ==="
md5sum /home/albus/strata166/data/bin/strata-0.1.54n
for f in /home/albus/strata166/src028/build-028/strata /home/albus/strata166/src028/build-028/bin/strata /home/albus/strata166/src028/build-028*/strata; do
  [ -f "$f" ] && md5sum "$f" && ls -la "$f" | awk '{print "   ", $5, $9}'
done
echo
echo "=== 3. image + serve layer provenance ==="
docker inspect "$C" --format '  image={{.Config.Image}} id={{.Image}}'
docker exec "$C" bash -lc "md5sum /src/serve/server.py /src/serve/frontend.py 2>/dev/null"
md5sum /home/albus/strata166/src028/serve/server.py /home/albus/strata166/src028/serve/frontend.py
echo
echo "=== 4. does the serve layer have the 0.2.8 tool-call recovery? ==="
docker exec "$C" bash -lc "grep -c 'tool_call_recovery' /src/serve/*.py /src/serve/strata_control/*.py 2>/dev/null | grep -v ':0' | head"
