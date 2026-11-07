import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
echo "===== [1] 构建进度 ====="
pgrep -af 'docker build' >/dev/null && echo "BUILD_RUNNING" || echo "BUILD_DONE_OR_DEAD"
tail -4 /home/albus/strata166/logs/build-402.log
echo -n "已完成的步骤标记: "; grep -c '^#[0-9]* DONE' /home/albus/strata166/logs/build-402.log
echo -n "当前编译进度: "; grep -oE '\[[0-9]+/[0-9]+\]' /home/albus/strata166/logs/build-402.log | tail -1

echo
echo "===== [2] strata166-401 容器配置 ====="
echo "--- Cmd / Entrypoint / WorkingDir / Env ---"
docker inspect strata166-401 --format 'Cm={{json .Config.Cmd}}
Ep={{json .Config.Entrypoint}}
Wd={{json .Config.WorkingDir}}
Vol={{json .Config.Volumes}}' 2>&1
docker inspect strata166-401 --format '{{range .Config.Env}}ENV {{.}}
{{end}}' 2>&1 | head -20
echo "--- HostConfig 关键项 ---"
docker inspect strata166-401 --format 'Binds={{json .HostConfig.Binds}}
Devices={{json .HostConfig.Devices}}
Priv={{.HostConfig.Privileged}}
GroupAdd={{json .HostConfig.GroupAdd}}
IpcMode={{.HostConfig.IpcMode}}
Ulimits={{json .HostConfig.Ulimits}}
PortBindings={{json .HostConfig.PortBindings}}
RestartPolicy={{json .HostConfig.RestartPolicy}}
ShmSize={{.HostConfig.ShmSize}}' 2>&1
echo "--- Mounts ---"
docker inspect strata166-401 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}})
{{end}}' 2>&1
echo "--- Image ---"
docker inspect strata166-401 --format '{{.Config.Image}}  created={{.Created}}' 2>&1

echo
echo "===== [3] 容器内的 serve 进程与配置 ====="
docker exec strata166-401 bash -lc 'ps -eo pid,ppid,etime,pcpu,rss,args --sort=-rss 2>/dev/null | head -8' 2>&1
echo "--- /data 下的配置与脚本 ---"
docker exec strata166-401 bash -lc 'ls -la /data 2>&1 | head -20' 2>&1
''', timeout=240, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
