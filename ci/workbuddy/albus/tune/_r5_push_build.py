# -*- coding: utf-8 -*-
"""推送 R5-A 的补丁与 Dockerfile，构建 strata-gfx906:0.2.4r5。"""
import base64, hashlib, subprocess, sys

HOST = "albus@192.168.50.166"
TAG = "0.2.4r5"
FILES = [
    (r"D:/workbuddy_space/strata_ws/deploy/docker/patch_gr_tilev.py",
     "/home/albus/strata166/build024/patches/patch_gr_tilev.py"),
    (r"D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.2.4",
     "/home/albus/strata166/build024/Dockerfile-0.2.4"),
]

def run(script, timeout=600):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")

for local, remote in FILES:
    data = open(local, "rb").read()
    want = hashlib.md5(data).hexdigest()
    b = base64.b64encode(data).decode("ascii")
    o = run("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (b, remote, remote, remote, remote))
    ok = want in o
    print("[push] %-26s %s" % (remote.rsplit("/", 1)[-1], "OK" if ok else "MISMATCH"))
    if not ok:
        print(o[-300:]); sys.exit(2)

if len(sys.argv) > 1 and sys.argv[1] == "pushonly":
    sys.exit(0)

o = run(r'''cd /home/albus/strata166/build024
rm -f build_r5.log
nohup sh -c 'docker build -f Dockerfile-0.2.4 -t strata-gfx906:%s . > build_r5.log 2>&1; echo RC=$? >> build_r5.log' >/dev/null 2>&1 &
sleep 10
echo "=== patch step ==="; grep -E "STRATA_GR_TILEV|small_tile|W788 R5-A|\[OK\]|error" build_r5.log | head -12
echo "=== tail ==="; tail -3 build_r5.log''' % TAG)
print(o[-2000:])
