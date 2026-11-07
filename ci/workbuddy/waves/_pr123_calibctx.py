# W709 步2：校准窗口的前置情报（只读）
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

sc = r'''
echo "=== 1) 生产 config 全文 ==="
cat /home/albus/strata166/data/strata-ud-iq4_xs.json
echo
echo "=== 2) 容器 402 的 Mounts / Devices / Env / Cmd / Restart ==="
docker inspect strata166-402 --format '{{json .HostConfig.RestartPolicy}}'
docker inspect strata166-402 --format '{{json .HostConfig.Privileged}} {{json .HostConfig.IpcMode}}'
docker inspect strata166-402 --format '{{json .HostConfig.Devices}}'
docker inspect strata166-402 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} (rw={{.RW}}){{println}}{{end}}'
docker inspect strata166-402 --format '{{range .Config.Env}}{{println .}}{{end}}'
docker inspect strata166-402 --format '{{json .Config.Cmd}}'
docker inspect strata166-402 --format '{{json .HostConfig.Ulimits}}'
echo
echo "=== 3) calibrate 需要的三件：exe / tokenizer / 目录 ==="
docker exec strata166-402 bash -lc 'ls -la /src/build-906/strata; echo ---; cat /proc/1/cmdline | tr "\0" " "; echo; echo ---; python3 -c "import sys;sys.path.insert(0,\"/src\");import serve.server as s;print(\"server import OK\")" 2>&1 | tail -3'
echo "--- tokenizer 目录（从 config 推） ---"
docker exec strata166-402 bash -lc 'ls -la /data/tok 2>&1 | head -8; echo ---; find /data -maxdepth 3 -name vocab.json 2>/dev/null | head -5; find /weights -maxdepth 2 -name vocab.json 2>/dev/null | head -5'
echo
echo "=== 4) 还有谁在用 GPU ==="
docker ps --format '{{.Names}}|{{.Image}}' 
echo "--- rocm-smi 进程占用 ---"
rocm-smi --showpids 2>/dev/null | head -20
echo "--- VRAM ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -2
echo
echo "=== 5) calibrate 里 engine_args 的取法（serve/server.py） ==="
docker exec strata166-402 bash -lc 'grep -n "^def engine_args" -A 30 /src/serve/server.py | head -45'
'''
rc, out, err = _sshutil.run_remote(sc, timeout=400, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---')
    print(err[:800])
