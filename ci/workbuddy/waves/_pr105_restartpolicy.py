import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
echo "===== [1] 全部容器的 restart policy ====="
docker ps -a --format '{{.Names}}' | while read c; do
  printf '  %-20s %-18s %-22s %s\n' "$c" \
    "$(docker inspect "$c" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)" \
    "$(docker inspect "$c" --format '{{.Config.Image}}' 2>/dev/null | cut -c1-22)" \
    "$(docker inspect "$c" --format '{{.State.Status}}' 2>/dev/null)"
done

echo
echo "===== [2] 有没有 systemd unit 管 docker 容器 ====="
grep -l 'docker' /etc/systemd/system/*.service 2>/dev/null || echo "  (没有任何 unit 提到 docker)"
echo "--- 现有自建 unit 全列 ---"
ls /etc/systemd/system/*.service 2>/dev/null | grep -v snap | head -10
echo
echo "--- docker.service 自身 ---"
systemctl is-enabled docker 2>&1
systemctl is-active docker 2>&1

echo
echo "===== [3] 5 个常驻容器的完整启动参数（取一个样本详看）====="
docker inspect open-webui --format '{{json .HostConfig.RestartPolicy}}
Image={{.Config.Image}}
Cmd={{json .Config.Cmd}}
Binds={{json .HostConfig.Binds}}
Ports={{json .HostConfig.PortBindings}}
Devices={{json .HostConfig.Devices}}' 2>&1
echo "--- netdata / comfyui / portainer / searxng 的 restart policy ---"
for c in netdata comfyui-cu130 portainer searxng; do
  printf '  %-16s %s\n' "$c" "$(docker inspect "$c" --format '{{.HostConfig.RestartPolicy.Name}}' 2>&1)"
done

echo
echo "===== [4] 新服务状态（systemd 起的）====="
systemctl is-active strata166 2>&1
docker ps --format '{{.Names}} | {{.Status}} | {{.Ports}}' | grep strata || echo "no strata"
echo "--- 8090 是否已 ready ---"
curl -s -m 5 http://127.0.0.1:8090/v1/models 2>&1 | head -c 260
echo
echo "--- VRAM ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1
''', timeout=300, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
