#!/bin/bash
C=strata166-407
echo "=== entrypoint / cmd / env ==="
docker inspect $C --format 'ENTRYPOINT={{json .Config.Entrypoint}}
CMD={{json .Config.Cmd}}
WORKDIR={{.Config.WorkingDir}}
RESTART={{.HostConfig.RestartPolicy.Name}}
NET={{.HostConfig.NetworkMode}}
PORTS={{json .HostConfig.PortBindings}}'
echo "--- Env ---"
docker inspect $C --format '{{range .Config.Env}}{{println .}}{{end}}'
echo "=== launcher scripts on host ==="
ls -la /home/albus/strata166/*.sh 2>/dev/null | head -20
grep -ln "strata166-407" /home/albus/strata166/*.sh /home/albus/*.sh 2>/dev/null | head -10
echo "=== the wrapper inside the image ==="
docker run --rm strata-gfx906:0.2.9-101 cat /usr/local/bin/strata 2>/dev/null | head -40
