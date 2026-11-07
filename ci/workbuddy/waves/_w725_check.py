# W709 步15：正确探针复核部署结果 + 复验
import sys, json
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
echo "=== 容器 ==="
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata
echo "=== HTTP（正确写法）==="
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo "=== LIVE config md5 ==="
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
echo "=== 最后一次 engine started ==="
grep "engine started" /data/strata-ud-iq4_xs.log | tail -1 | cut -c1-800
echo "=== 有没有报错 ==="
grep -iE "error|fail|out of memory|abort|ERR " /data/strata-ud-iq4_xs.log | tail -8
echo "=== 真实推理自检 ==="
docker exec strata166-402 bash -lc 'curl -s -m 120 http://127.0.0.1:8090/v1/chat/completions -H "Content-Type: application/json" -d @- <<JSON
{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"Reply with the single word OK."}],"max_tokens":16,"temperature":0}
JSON'
echo
'''
rc, out, err = _sshutil.run_remote(sc, timeout=400, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:500])
