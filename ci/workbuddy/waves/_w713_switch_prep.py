# W1: 推两个脚本 -> 建容器 strata166-405（0.1.41）-> 执行通用切换（带自动回滚）
import base64, hashlib, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166", "base64 -d | bash"]


def sh(script, timeout=600):
    for pth in ["deploy/scripts/switch_strata.sh", "deploy/scripts/upgrade_gate.sh"]:
        pass
    p = subprocess.run(SSH, input=base64.b64encode(script.encode("utf-8")) + b"\n",
                       capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def load(rel):
    raw = open(os.path.join(WS, rel), "rb").read()
    t = raw.decode("utf-8")
    nb = sum(1 for c in t if ord(c) in BAN)
    assert b"\r" not in raw, "%s 有 CR" % rel
    assert nb == 0, "%s BAN=%d" % (rel, nb)
    print("%-40s md5=%s bytes=%d CR=0 BAN=0" % (rel, hashlib.md5(raw).hexdigest(), len(raw)))
    return base64.b64encode(raw).decode("ascii")


sw = load("deploy/scripts/switch_strata.sh")
gt = load("deploy/scripts/upgrade_gate.sh")

script = r"""
set -u
D=/home/albus/strata166/w712
base64 -d > "$D/switch_strata.sh" <<'__SW_EOF__'
%(sw)s
__SW_EOF__
base64 -d > "$D/upgrade_gate.sh" <<'__GT_EOF__'
%(gt)s
__GT_EOF__
chmod +x "$D/switch_strata.sh" "$D/upgrade_gate.sh"
echo "md5 remote: $(md5sum $D/switch_strata.sh | cut -d' ' -f1) $(md5sum $D/upgrade_gate.sh | cut -d' ' -f1)"
echo "CR remote : $(tr -cd '\r' < $D/switch_strata.sh | wc -c) $(tr -cd '\r' < $D/upgrade_gate.sh | wc -c)"
echo "bash -n   : $(bash -n $D/switch_strata.sh && echo SW_OK || echo SW_FAIL) $(bash -n $D/upgrade_gate.sh && echo GT_OK || echo GT_FAIL)"
echo "=== 建容器 strata166-405（0.1.41，参数逐项抄 -404）==="
if docker inspect strata166-405 >/dev/null 2>&1; then
  docker inspect -f 'exists: status={{.State.Status}} image={{.Config.Image}}' strata166-405
else
  docker create --name strata166-405 \
    --restart unless-stopped \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --ulimit memlock=-1 \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -p 8090:8090 \
    -v /home/albus/strata166/data:/data \
    -v /home/albus/strata166/weights:/weights:ro \
    strata-gfx906:0.1.41 \
    bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-ud-iq4_xs.json --port 8090'
  docker inspect strata166-405 --format 'created: status={{.State.Status}} image={{.Config.Image}} Binds={{json .HostConfig.Binds}} Ports={{json .HostConfig.PortBindings}} RAS={{json .HostConfig.RestartPolicy}}'
fi
""" % {"sw": sw, "gt": gt}

rc, out, err = sh(script, timeout=300)
print("rc=%d" % rc)
print(out)
if err.strip():
    print("STDERR:", err[-400:])
