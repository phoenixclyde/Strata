# W709 步16：确认驱动已停 + 恢复 166 现场
import sys, subprocess
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

# 1) 本机残留驱动（用 PowerShell 落文件再读，避开输出被吞）
ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
      "Where-Object { $_.CommandLine -like '*_w726_ab.py*' } | "
      "ForEach-Object { $_.ProcessId } | Out-File -Encoding ascii "
      r"D:/workbuddy/_z_rk81/_resid.txt")
subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
try:
    r = open(r'D:/workbuddy/_z_rk81/_resid.txt').read().strip()
except FileNotFoundError:
    r = '(file missing)'
print('[1] 残留驱动 PID =', r or '(none)')

# 2) 恢复 166
sc = r'''
set -u
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
echo "--- 现在 LIVE ---"; md5sum $LIVE
cp -f $GEN $LIVE; echo "cp_rc=$?"
echo "--- 恢复后 LIVE（应 8847728605528012c65cebe5048172ce）---"; md5sum $LIVE
docker restart -t 30 strata166-402 >/dev/null 2>&1; echo "restart_rc=$?"
echo "--- 等就绪 ---"
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  sleep 10
  c=$(docker exec strata166-402 bash -lc 'curl -s -m 6 -o /dev/null -w "%{http_code}" http://127.0.0.1:8090/v1/models' 2>/dev/null)
  echo "  [$((i*10))s] http=$c"
  [ "$c" = "200" ] && break
done
echo "--- 最后一次 engine started ---"
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--pcie-frac [0-9.]*\|--spec-min-p [0-9.]*\|--prompt-cache-tail' || echo "(无新旋钮)"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=600, host='192.168.50.166')
print(out)
if err.strip():
    print('err:', err[:400])
