docker inspect strata166-407 --format '{{json .HostConfig}}' | python3 -c "
import json,sys
h=json.load(sys.stdin)
for k in ('Binds','PortBindings','IpcMode','SecurityOpt','Ulimits','Devices','RestartPolicy','NetworkMode','ShmSize','GroupAdd','Privileged','DeviceRequests','CapAdd','ExtraHosts'):
    v=h.get(k)
    if v not in (None,[],{},''): print(k,'=',v)
"
echo "--- env ---"
docker inspect strata166-407 --format '{{range .Config.Env}}{{.}}
{{end}}' | head -20
echo "--- cmd ---"
docker inspect strata166-407 --format '{{json .Config.Cmd}}'
