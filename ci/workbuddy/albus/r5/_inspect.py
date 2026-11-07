import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker inspect strata166-407 --format '{{json .HostConfig.Binds}}|{{json .Config.Cmd}}|{{json .Config.Entrypoint}}|{{json .HostConfig.Devices}}|{{json .HostConfig.PortBindings}}|{{.HostConfig.NetworkMode}}|{{json .Config.Env}}|{{.HostConfig.RestartPolicy.Name}}|{{.HostConfig.IpcMode}}|{{json .HostConfig.GroupAdd}}'
'''))
