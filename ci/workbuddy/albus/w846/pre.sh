set +e
C=strata166-407
echo "===== [1] 容器完整创建参数（重建依据） ====="
docker inspect "$C" --format '
image={{.Config.Image}}
cmd={{json .Config.Cmd}}
entrypoint={{json .Config.Entrypoint}}
env={{json .Config.Env}}
workdir={{.Config.WorkingDir}}
user={{.Config.User}}
hostname={{.Config.Hostname}}
restart={{.HostConfig.RestartPolicy.Name}}:{{.HostConfig.RestartPolicy.MaximumRetryCount}}
network={{.HostConfig.NetworkMode}}
portbindings={{json .HostConfig.PortBindings}}
binds={{json .HostConfig.Binds}}
devices={{json .HostConfig.Devices}}
devicerequests={{json .HostConfig.DeviceRequests}}
groupadd={{json .HostConfig.GroupAdd}}
privileged={{.HostConfig.Privileged}}
ipc={{.HostConfig.IpcMode}}
shm={{.HostConfig.ShmSize}}
ulimits={{json .HostConfig.Ulimits}}
securityopt={{json .HostConfig.SecurityOpt}}
capadd={{json .HostConfig.CapAdd}}
pid={{.HostConfig.PidMode}}
'
echo "===== [2] 有没有 compose 文件 ====="
ls -l /home/albus/strata166/*.yml /home/albus/strata166/*.yaml /home/albus/strata166/docker-compose* 2>/dev/null
grep -rl "strata166-407" /home/albus/strata166 --include=*.yml --include=*.yaml --include=*.sh 2>/dev/null | head -5
echo "===== [3] 镜像 /src 与 gfx029/serve 的文件差 ====="
docker exec "$C" bash -lc "cd /src/serve && find . -type f -name '*.py' | sort" > /tmp/img_serve.txt
(cd /home/albus/strata166/gfx029/serve && find . -type f -name '*.py' | sort) > /tmp/tree_serve.txt
echo "--- 镜像有、树里没有（0.2.8 独有）:"; comm -23 /tmp/img_serve.txt /tmp/tree_serve.txt | head
echo "--- 树里有、镜像没有（0.2.9 新增）:"; comm -13 /tmp/img_serve.txt /tmp/tree_serve.txt | head -12
echo -n "--- 文件数 镜像/树: "; echo "$(wc -l < /tmp/img_serve.txt) / $(wc -l < /tmp/tree_serve.txt)"
echo "===== [4] 0.2.9 serve 的 import 是否都能在镜像里满足 ====="
docker exec "$C" bash -lc "cd /src && python3 - <<'PY'
import ast,os,sys
roots=set()
for d in ('serve',):
    for r,_,fs in os.walk(d):
        for f in fs:
            if f.endswith('.py'):
                try: t=ast.parse(open(os.path.join(r,f),encoding='utf-8',errors='replace').read())
                except Exception: continue
                for n in ast.walk(t):
                    if isinstance(n,ast.Import):
                        for a in n.names: roots.add(a.name.split('.')[0])
                    elif isinstance(n,ast.ImportFrom):
                        if n.level==0 and n.module: roots.add(n.module.split('.')[0])
print('IMPORTS:', ' '.join(sorted(roots)))
PY"
echo "===== [5] 这些顶层模块在镜像里能不能 import ====="
docker exec "$C" bash -lc "cd /src && python3 - <<'PY'
import importlib,sys
mods=['psutil','yaml','numpy','torch','PIL','aiohttp','fastapi','uvicorn','starlette','httpx','requests','tiktoken','regex','mlx','httptools','websockets']
ok=[];bad=[]
for m in mods:
    try:
        importlib.import_module(m); ok.append(m)
    except Exception: bad.append(m)
print('OK  :', ' '.join(ok))
print('MISS:', ' '.join(bad))
PY"
echo "===== [6] serve 是否会 import strata_cli（版本耦合） ====="
docker exec "$C" bash -lc "grep -rn 'strata_cli\|from strata' /src/serve/*.py | head -5"
echo "--- 树里 0.2.9 serve 的同类引用:"
grep -rn "strata_cli\|from strata" /home/albus/strata166/gfx029/serve/*.py | head -5
