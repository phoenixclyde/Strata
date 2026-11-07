C=strata166-407
CFG=$(docker inspect "$C" --format '{{json .Config.Cmd}}' | tr ',' '\n' | grep -o '/data/[a-z0-9_.-]*\.json' | head -1)
echo "cfg=$CFG"
LOG=$(docker exec "$C" bash -lc "python3 -c \"import json;print(json.load(open('$CFG')).get('log'))\"" 2>/dev/null | tr -d '\r')
echo "log=$LOG"
docker exec "$C" bash -lc "ls -la '$LOG' 2>/dev/null || echo MISSING"
echo "--- startup parameters ---"
docker exec "$C" bash -lc "grep -a 'prefill_cap' '$LOG' 2>/dev/null | tail -2 | cut -c1-260"
echo "--- chunk / prefill lines ---"
docker exec "$C" bash -lc "grep -aE 'prefill|chunk' '$LOG' 2>/dev/null | tail -6 | cut -c1-200"
