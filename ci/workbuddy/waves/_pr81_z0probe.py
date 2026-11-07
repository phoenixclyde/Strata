import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

script = r'''
echo "===== [1] 当前 Z0 三件实值 ====="
echo -n "  GPU perflevel : "; cat /sys/class/drm/card0/device/power_dpm_force_performance_level 2>&1
echo -n "  CPU governor  : "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>&1
echo -n "  THP enabled   : "; cat /sys/kernel/mm/transparent_hugepage/enabled 2>&1
echo -n "  THP defrag    : "; cat /sys/kernel/mm/transparent_hugepage/defrag 2>&1
echo -n "  cur_freq_khz  : "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>&1

echo
echo "===== [2] _rk78_z0_state.sh 现状 ====="
ls -la /home/albus/routeK/run/_rk78_z0_state.sh 2>&1
md5sum /home/albus/routeK/run/_rk78_z0_state.sh 2>&1
echo "--- 全文 ---"
cat /home/albus/routeK/run/_rk78_z0_state.sh 2>&1

echo
echo "===== [3] 既有开机机制 ====="
echo "--- enabled systemd units (filtered) ---"
systemctl list-unit-files --state=enabled 2>/dev/null | grep -iE 'z0|routek|rk|thp|cpufreq|tuned' | head -20
echo "--- /etc/systemd/system 下自建 (非 *.wants) ---"
ls -la /etc/systemd/system/ 2>&1 | grep -viE '\.wants|\.requires|^total|^d' | head -30
echo "--- rc.local ---"
ls -la /etc/rc.local 2>&1
echo -n "  rc-local enabled: "; systemctl is-enabled rc-local 2>&1
echo "--- crontab albus ---"
crontab -l 2>&1 | head -20
echo "--- crontab root (sudo -n) ---"
sudo -n crontab -l 2>&1 | head -20
echo "--- udev rules ---"
ls /etc/udev/rules.d/ 2>&1 | head -20

echo
echo "===== [4] sudo -n 可用性 ====="
sudo -n true 2>&1 && echo "SUDO_NOPASSWD_OK" || echo "SUDO_NEEDS_PASSWORD"

echo
echo "===== [5] 内核 cmdline ====="
cat /proc/cmdline

echo
echo "===== [6] run/ 下 z0/zk5 相关脚本 ====="
ls -la /home/albus/routeK/run/ 2>/dev/null | grep -iE 'z0|zk5' | head -20

echo
echo "===== [7] boot id / uptime ====="
cat /proc/sys/kernel/random/boot_id; uptime -s; uptime
'''
rc, out, err = _sshutil.run_remote(script, timeout=180, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
