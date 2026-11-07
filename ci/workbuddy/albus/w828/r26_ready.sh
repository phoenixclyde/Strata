R=""
for i in $(seq 1 480); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
date +%H:%M:%S
echo "READY_AT=$R"
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
echo "--- models ---"
curl -s --max-time 5 http://127.0.0.1:8090/v1/models | head -c 300; echo
echo "--- startup markers ---"
docker logs strata166-407 2>&1 | grep -a -E "filling the GPU|expert cache auto|allocated after the cache|tool_call_recovery|0\.1\.54" | head -6 | cut -c1-190
