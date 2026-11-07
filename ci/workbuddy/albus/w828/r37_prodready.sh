R=""
for i in $(seq 1 420); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
date +%H:%M:%S
echo "PROD_READY=$R"
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 160; echo
grep -a -E "filling the GPU" <(docker logs strata166-407 2>&1) | head -2
