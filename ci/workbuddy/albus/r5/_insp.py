import subprocess, base64, json
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("docker inspect strata166-407 --format '{{json .Config.Entrypoint}}|{{json .Config.Cmd}}|{{json .HostConfig.Binds}}|{{json .HostConfig.Devices}}|{{.HostConfig.IpcMode}}|{{json .HostConfig.GroupAdd}}|{{.HostConfig.NetworkMode}}|{{json .HostConfig.PortBindings}}|{{.HostConfig.RestartPolicy.Name}}'"))
