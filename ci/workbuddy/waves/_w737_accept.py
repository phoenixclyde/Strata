# W709 步22：实机验收（现役 config 下的多轮复用）+ 资源代价核查
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
echo "=== 现役 LIVE ==="
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--prompt-cache-every [0-9]*' || echo "(未生效?)"
echo
echo "=== 实机验收：~10,000-token prompt 的多轮复用 ==="
docker exec strata166-402 python3 -u /data/bench_prefix.py ACCEPT 220
echo
echo "=== 引擎日志同口径自证（最近 4 条 prompt 行）==="
grep -E 'strata serve: prompt' /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -4
echo
echo "=== 资源代价（RAM/VRAM）==="
docker exec strata166-402 bash -lc 'grep -E "resident RAM|expert cache hit" /data/strata-ud-iq4_xs.log | tail -2'
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
free -g | head -2
'''
rc, out, err = _sshutil.run_remote(sc, timeout=900, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
