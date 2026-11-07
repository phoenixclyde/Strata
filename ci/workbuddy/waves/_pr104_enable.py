import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
set -u
echo "===== [1] 安装 unit ====="
sudo -n cp /tmp/strata166.service /etc/systemd/system/strata166.service
sudo -n chmod 644 /etc/systemd/system/strata166.service
ls -l /etc/systemd/system/strata166.service
sudo -n systemctl daemon-reload
echo "--- systemd-analyze verify ---"
sudo -n systemd-analyze verify /etc/systemd/system/strata166.service 2>&1 | head -20
echo "verify_rc=$?"

echo
echo "===== [2] unit 关键字段回读 ====="
sudo -n systemctl cat strata166 --no-pager 2>&1 | head -30

echo
echo "===== [3] 停旧容器 strata166-401 ====="
date -Is
docker stop -t 180 strata166-401 2>&1
echo "stop_rc=$?"
sleep 8
docker ps -a --format '{{.Names}} | {{.Status}}' | grep -i strata || echo "无 strata 容器"
echo "--- VRAM（应回地板）---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1

echo
echo "===== [4] enable --now ====="
sudo -n systemctl enable --now strata166 2>&1
sleep 25
date -Is
echo "--- systemctl status ---"
systemctl status strata166 --no-pager 2>&1 | head -22
echo "--- docker ps ---"
docker ps --format '{{.Names}} | {{.Status}} | {{.Ports}}' | grep -i strata || echo "无运行中 strata"
''', timeout=560, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
