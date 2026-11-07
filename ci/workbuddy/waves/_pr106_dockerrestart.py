import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
set -u
echo "===== [1] 撤掉 systemd 方案（回退我自己的多余动作）====="
sudo -n systemctl disable --now strata166 2>&1 | head -5
sudo -n rm -f /etc/systemd/system/strata166.service
sudo -n systemctl daemon-reload
sudo -n systemctl reset-failed strata166.service 2>/dev/null || true
echo -n "unit 还在吗: "; ls /etc/systemd/system/strata166.service 2>&1
echo -n "multi-user.target.wants 软链还在吗: "; ls /etc/systemd/system/multi-user.target.wants/strata166.service 2>&1
echo "--- 现在还有哪些 unit 提到 docker ---"
grep -l docker /etc/systemd/system/*.service 2>/dev/null || echo "  (无：与另 5 个容器一致)"

echo
echo "===== [2] 清掉 --rm 的临时容器 ====="
docker rm -f strata166-402 2>&1
sleep 6
docker ps -a --format '{{.Names}} | {{.Status}}' | grep strata || echo "无 strata 容器"
echo "--- VRAM 回地板确认 ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1

echo
echo "===== [3] 用 Docker restart policy 重建（与另 5 个同机制）====="
docker run -d --restart unless-stopped --name strata166-402 \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 \
  -p 8090:8090 \
  -v /home/albus/strata166/data:/data \
  -v /home/albus/strata166/weights:/weights:ro \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  -e STRATA_SRC=/src \
  strata-gfx906:0.1.40.2 \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-ud-iq4_xs.json --port 8090'
echo "run_rc=$?"
sleep 10

echo
echo "===== [4] 复核 restart policy 已生效 ====="
docker inspect strata166-402 --format 'name={{.Name}}  image={{.Config.Image}}
restart={{json .HostConfig.RestartPolicy}}
status={{.State.Status}}' 2>&1
docker ps --format '{{.Names}} | {{.Status}} | {{.Ports}}' | grep strata

echo
echo "===== [5] 重启自动拉起 —— 机制自证（不做真重启）====="
echo -n "  docker.service enabled : "; systemctl is-enabled docker
echo -n "  docker.service active  : "; systemctl is-active docker
echo "  带 restart policy 的容器（daemon 重启后会自拉起）:"
docker ps --format '{{.Names}}' | while read c; do
  p=$(docker inspect "$c" --format '{{.HostConfig.RestartPolicy.Name}}')
  [ "$p" != "no" ] && printf '    %-20s %s\n' "$c" "$p"
done
''', timeout=420, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
