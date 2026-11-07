# W709 步19：前缀复用判别（容器内跑）+ 取 --prompt-cache 族 help 原文
import sys, ast
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

lp = r'D:/strata166/data/bench_reuse.py'
b = open(lp, 'rb').read()
ast.parse(b.decode('utf-8'))
assert b.count(b'\r') == 0
ok, size, md5, det = _sshutil.push_b64(lp, '/home/albus/strata166/data/bench_reuse.py')
print('push bench_reuse ok=%s size=%s md5=%s' % (ok, size, md5))

sc = r'''
echo "=== 前缀复用判别 ==="
docker exec strata166-402 python3 -u /data/bench_reuse.py
echo
echo "=== --prompt-cache 族 help 原文 ==="
docker exec strata166-402 bash -lc '/src/build-906/strata --help 2>&1' | grep -B1 -A4 -E '^\s+--prompt-cache' | head -40
echo
echo "=== 现役启动行里的 prompt-cache 相关 ==="
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--prompt-cache[a-z-]* [^ ]*\|--prompt-cache-tail' || echo "(启动行未显式给出 => 走引擎默认)"
echo
echo "=== 引擎日志里的 cache 命中行（最近）==="
grep -iE 'cached|prompt cache|reuse|prefix' /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -8
'''
rc, out, err = _sshutil.run_remote(sc, timeout=900, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
