import io, os, sys, hashlib
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/albus/netdata_v37")
from sshrun import run, push

W = r"D:/workbuddy_space/strata_ws/albus/netdata_v37"
ASSETS = "/home/albus/netdata/ops/image/assets"
CTX = "/home/albus/netdata/ops/image"
BAK = "/home/albus/netdata/ops/_bak/assets_v37b_20261105"

cmd = ("mkdir -p " + BAK + " && cp -a " + ASSETS + "/gpu.html " + BAK + "/gpu.v37a.html && "
       "cp -a " + CTX + "/rk-health-collect.sh " + BAK + "/rk-health-collect.v37a.sh && "
       "ls -l " + BAK + " && md5sum " + ASSETS + "/gpu.html " + CTX + "/rk-health-collect.sh")
rc, out, err = run(cmd)
print("BACKUP rc=%d\n%s\n%s" % (rc, out, err))
if rc != 0:
    raise SystemExit(2)

for local, remote in [
    (os.path.join(W, "gpu.html"), ASSETS + "/gpu.html"),
    (os.path.join(W, "rk-health-collect.sh"), CTX + "/rk-health-collect.sh"),
]:
    push(local, remote)
    lm = hashlib.md5(io.open(local, "rb").read()).hexdigest()
    rc, out, _ = run("md5sum " + remote + " | cut -d' ' -f1")
    rm = out.strip()
    print("%-22s local=%s remote=%s %s" % (os.path.basename(local), lm, rm, "OK" if lm == rm else "MISMATCH"))
    if lm != rm:
        raise SystemExit("GATE_CTX 失败：" + remote)

rc, out, err = run("sh -n " + CTX + "/rk-health-collect.sh && echo SH_OK; chmod 755 " + CTX
                   + "/rk-health-collect.sh; ls -l " + CTX + "/rk-health-collect.sh " + ASSETS + "/gpu.html")
print("SH_CHECK rc=%d\n%s%s" % (rc, out, err))
