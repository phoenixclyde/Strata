import io, os, sys, shutil, hashlib, time
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/albus/netdata_v37")
from sshrun import run

W = r"D:/workbuddy_space/strata_ws/albus/netdata_v37"
D = r"D:/workbuddy/netdata-dashboard"
stamp = time.strftime("%Y%m%d_%H%M%S")

shutil.copyfile(D + "/gpu.html", D + "/_bak_gpu_v37c_%s.html" % stamp)
shutil.copyfile(W + "/gpu.html", D + "/gpu.html")
h = hashlib.md5(io.open(D + "/gpu.html", "rb").read()).hexdigest()
print("canonical gpu.html", h, os.path.getsize(D + "/gpu.html"))

rc, out, _ = run("curl -s http://127.0.0.1:19999/custom/gpu.html | md5sum; docker inspect netdata --format '{{.Image}}'")
print(out)
rc, out, _ = run("grep -c '' /home/albus/netdata/ops/recreate_netdata.sh; grep '^IMG=' /home/albus/netdata/ops/recreate_netdata.sh")
print(out)
