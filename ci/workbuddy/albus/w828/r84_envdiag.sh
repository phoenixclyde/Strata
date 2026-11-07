date +%H:%M:%S
C=$(docker ps --format '{{.Names}}' | grep w828 | head -1)
echo "container=$C"
if [ -n "$C" ]; then
  PID=$(docker exec "$C" bash -lc "pgrep -f strata-0.1.54n | head -1" 2>/dev/null | tr -d '\r')
  echo "engine_pid=$PID"
  if [ -n "$PID" ]; then
    echo "--- engine env (STRATA_*) ---"
    docker exec "$C" bash -lc "tr '\0' '\n' < /proc/$PID/environ 2>/dev/null | grep STRATA_ | sort | head -25"
  fi
fi
echo "--- server.py: how config env reaches the engine ---"
grep -n "environ\|cfg.get(.env\|\.env\b" /home/albus/strata166/src028/serve/server.py | head -20
echo "--- frontend.py ---"
grep -n "environ\|\.env\b" /home/albus/strata166/src028/serve/frontend.py | head -12
echo "--- strata_control ---"
grep -rn "environ\|\.env\b" /home/albus/strata166/src028/serve/strata_control/ 2>/dev/null | head -15
