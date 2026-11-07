import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
echo "等待冷启动（最多 300s）..."
for i in $(seq 1 60); do
  R=$(curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/v1/models 2>/dev/null)
  if [ "$R" = "200" ]; then echo "READY after ${i}0s (http=$R)"; break; fi
  sleep 5
done
echo
echo "===== [1] /v1/models ====="
curl -s -m 10 http://127.0.0.1:8090/v1/models
echo
echo
echo "===== [2] 一次真实推理（关思考，短）====="
curl -s -m 120 http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":32,"reasoning_effort":"none","temperature":0}' \
  2>&1 | head -c 700
echo
echo
echo "===== [3] 工具调用能力 ====="
curl -s -m 120 http://127.0.0.1:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"What is the weather in Shanghai?"}],"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],"max_tokens":128,"temperature":0}' \
  2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); c=d['choices'][0]; print('finish_reason =', c['finish_reason']); print('tool_calls =', json.dumps(c['message'].get('tool_calls'), ensure_ascii=False)[:300])" 2>&1

echo
echo "===== [4] 容器内确认引擎是 0.1.40.2 ====="
docker exec strata166-402 bash -lc 'ls -l /src/build-906/strata; md5sum /src/build-906/strata; grep -m1 "project(strata VERSION" /src/CMakeLists.txt' 2>&1
echo "--- 引擎进程命令行 ---"
docker exec strata166-402 bash -lc "ps -eo pid,etime,args 2>/dev/null | grep -E '[s]trata --serve|[s]erve/server.py' | head -3" 2>&1

echo
echo "===== [5] 终态 ====="
docker inspect strata166-402 --format 'status={{.State.Status}}  restart={{.HostConfig.RestartPolicy.Name}}  started={{.State.StartedAt}}' 2>&1
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1
free -g 2>/dev/null | head -2
date -Is
''', timeout=560, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
