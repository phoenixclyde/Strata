import sys, hashlib
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/albus/netdata_v37")
from sshrun import run, push

p = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/upgrade_netdata_image.sh"
push(p, "/home/albus/netdata/ops/upgrade_netdata_image.sh")
rc, out, err = run("md5sum /home/albus/netdata/ops/upgrade_netdata_image.sh; bash -n /home/albus/netdata/ops/upgrade_netdata_image.sh && echo BASH_OK")
print(out, err, "| local", hashlib.md5(open(p, "rb").read()).hexdigest())

rc, out, err = run("docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | grep -E 'rk-netdata' | head -8")
print(out)
