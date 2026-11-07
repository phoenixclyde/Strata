set +e
C=strata166-407
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "===== [A] 生产快照 ====="
docker ps --format '{{.Names}} {{.Status}}' | head -2
docker inspect "$C" --format 'started={{.State.StartedAt}} restarts={{.RestartCount}} image={{.Image}}'
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe=',d['exe'],'args=',len(d['args']),'env=',len(d.get('env') or {}))"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots=%d vram_free=%d pcie=%s gen=%s width=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac'),e.get('gpu_pcie_gen'),e.get('gpu_pcie_width')))" 2>&1
echo "===== [B] 版本拼接：引擎/镜像/serve ====="
docker exec "$C" bash -lc "/data/bin/strata-0.1.55g --version 2>&1 | head -2; echo -n 'container serve/server.py: '; md5sum /src/serve/server.py | cut -c1-12; echo -n 'container /src 里有无 0.2.9 标记: '; grep -c 'COALESCE_PREFILL' /src/serve/server.py"
echo "===== [C] 新引擎对 33 个 args 有无不认/弃用告警 ====="
docker exec "$C" bash -lc "grep -aiE 'unknown|unrecognis|unrecogniz|ignoring|deprecat|not supported' $L | tail -8"
echo "--- 启动横幅里的 arch 行:"
docker exec "$C" bash -lc "grep -aE 'MI50-class|exact speed switches|rounding recipe' $L | tail -4"
echo "===== [D] 门禁 ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -4
echo "===== [E] 分支最终态 ====="
git -C /home/albus/strata166/gfx029 log --oneline --decorate -2
git -C /home/albus/strata166/gfx029 status --porcelain | head -3
echo -n "is-shallow(gfx029)="; git -C /home/albus/strata166/gfx029 rev-parse --is-shallow-repository
