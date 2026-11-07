#!/bin/bash
W=/home/albus/strata166/src028/serve/web
echo "=== .monitor-row / grid in app.css (lines 80-115) ==="
sed -n "80,115p" $W/app.css
echo
echo "=== tail of app.css (append point) ==="
tail -6 $W/app.css
echo
echo "=== container run config (for an exact recreate) ==="
docker inspect strata166-407 --format 'IMAGE={{.Config.Image}}
RESTART={{.HostConfig.RestartPolicy.Name}}
NET={{.HostConfig.NetworkMode}}
BINDS={{range .HostConfig.Binds}}{{.}} {{end}}
DEVICES={{range .HostConfig.Devices}}{{.PathOnHost}}:{{.PathInContainer}} {{end}}
PORTS={{range $p,$v := .HostConfig.PortBindings}}{{$p}}->{{range $v}}{{.HostIp}}:{{.HostPort}}{{end}} {{end}}
SHM={{.HostConfig.ShmSize}}
CAPADD={{range .HostConfig.CapAdd}}{{.}} {{end}}
GROUPADD={{range .HostConfig.GroupAdd}}{{.}} {{end}}
PRIV={{.HostConfig.Privileged}}
ENVN={{len .Config.Env}}' 2>&1
echo
echo "=== is prod busy right now? ==="
curl -s --max-time 6 http://127.0.0.1:8090/status 2>/dev/null | head -c 300
echo
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 200
