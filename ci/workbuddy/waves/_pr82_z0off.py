import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

script = r'''
RUN=/home/albus/routeK/run

echo "===== [0] 现有 z0-off 工具 ====="
ls -la $RUN/_zk5_z0off.sh 2>&1
md5sum $RUN/_zk5_z0off.sh 2>&1
echo "--- run/ 下所有 z0* / *z0off* ---"
ls -la $RUN/ 2>/dev/null | grep -iE 'z0off|z0_state|z0_on' 2>&1

show() {
  echo -n "  GPU perflevel : "; rocm-smi -d 0 --showperflevel --json 2>/dev/null \
     | sed -n 's/.*"Performance Level"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
  echo -n "  CPU governor  : "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>&1
  echo -n "  THP enabled   : "; cat /sys/kernel/mm/transparent_hugepage/enabled 2>&1
  echo -n "  THP defrag    : "; cat /sys/kernel/mm/transparent_hugepage/defrag 2>&1
  echo -n "  cur_freq_khz  : "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>&1
}

echo
echo "===== [1] BEFORE（执行前）====="
show

echo
echo "===== [2] 执行 z0-off ====="
if [ -f "$RUN/_zk5_z0off.sh" ]; then
  echo "--- via _zk5_z0off.sh ---"
  bash "$RUN/_zk5_z0off.sh" 2>&1
  echo "z0off_rc=$?"
else
  echo "--- 工具缺失，手工三条 ---"
  sudo -n rocm-smi -d 0 --setperflevel auto 2>&1 | tail -n2
  sudo -n cpupower frequency-set -g schedutil 2>&1 | tail -n3
  echo madvise | sudo -n tee /sys/kernel/mm/transparent_hugepage/enabled >/dev/null 2>&1
  echo "manual_done"
fi

sleep 3
echo
echo "===== [3] AFTER（执行后）====="
show

echo
echo "===== [4] 判定 ====="
P=$(rocm-smi -d 0 --showperflevel --json 2>/dev/null | sed -n 's/.*"Performance Level"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
G=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null | tr -d ' \t')
T=$(head -n1 /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null | sed 's/.*\[\([a-z]*\)\].*/\1/')
echo "Z0OFF_FINAL perflevel=$P governor=$G thp=$T"
if [ "$P" = "auto" ] && [ "$G" = "schedutil" ] && [ "$T" = "madvise" ]; then
  echo "Z0_OFF_VERIFY_OK=1 (三件均已清到省电档)"
else
  echo "Z0_OFF_VERIFY_FAIL=1"
fi
'''
rc, out, err = _sshutil.run_remote(script, timeout=240, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
