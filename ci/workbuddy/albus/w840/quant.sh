set +e
BIN=/home/albus/strata166/data/bin/strata-0.1.54n3
echo "=== [1] 部署二进制 ==="
ls -l /home/albus/strata166/data/bin/
md5sum $BIN
echo "=== [2] 镜像 ==="
docker inspect strata-gfx906:0.2.8p2 --format 'id={{.Id}} created={{.Created}} size={{.Size}}'
docker inspect strata166-407 --format 'image={{.Config.Image}} imgid={{.Image}} restart={{.HostConfig.RestartPolicy.Name}} started={{.State.StartedAt}}'
echo "=== [3] 构建树产物 md5 ==="
ls -l /home/albus/strata166/src028/build-028r/ 2>/dev/null | head -20
for f in $(find /home/albus/strata166/src028/build-028r -maxdepth 2 -type f -name 'strata*' -size +10M 2>/dev/null); do md5sum $f; done
echo "=== [4] 启动横幅 ==="
docker exec strata166-407 bash -lc "grep -a 'MI50-class' /data/strata-huihui-ud-iq4_xs.log | tail -6"
echo "=== [5] 关键分配行 ==="
docker exec strata166-407 bash -lc "grep -aiE 'expert cache [0-9]+ slots|prompt path borrows|pre-filled [0-9]+ of|vram reserve|context window|max_context|kv cache|slots of VRAM' /data/strata-huihui-ud-iq4_xs.log | tail -20"
echo "=== [6] 二进制版本串 ==="
docker exec strata166-407 bash -lc "strings /data/bin/strata-0.1.54n3 | grep -aE 'strata [0-9]+\.[0-9]+\.[0-9]+|exact speed switches|build [0-9]{4}' | sort -u | head -12"
echo "=== [7] 配置 md5 与备份件 ==="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json*
echo "=== [8] 分支状态 ==="
cd /home/albus/strata166/gfx906 && git rev-parse --short HEAD && git status --porcelain | head -20 && git log --oneline -3
echo "=== [9] 实时状态(采样) ==="
python3 - <<'PY'
import json,urllib.request
d=json.loads(urllib.request.urlopen("http://127.0.0.1:8090/metrics",timeout=8).read().decode())
print("live:", {k:d.get("live",{}).get(k) for k in ("state","queued","phase","prompt_tokens","prompt_read","prompt_total")})
print("hw:", {k:d.get("hardware",{}).get(k) for k in ("gpu_util","gpu_temp","gpu_power","gpu_pcie_rx_mb")})
PY
