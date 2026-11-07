# -*- coding: utf-8 -*-
"""把 R1 的补丁脚本与 Dockerfile 推到 166 的 build024 构建上下文，然后启动 docker build。"""
import base64, hashlib, subprocess, sys

HOST = "albus@192.168.50.166"
FILES = [
    (r"D:/workbuddy_space/strata_ws/deploy/docker/patch_final_ckpt.py", "/home/albus/strata166/build024/patches/patch_final_ckpt.py"),
    (r"D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.2.4", "/home/albus/strata166/build024/Dockerfile-0.2.4"),
]

def run(script, timeout=300):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace")

rc, o = run("mkdir -p /home/albus/strata166/build024/patches && echo ok")
print("[mkdir]", rc, o.strip())

for local, remote in FILES:
    data = open(local, "rb").read()
    want = hashlib.md5(data).hexdigest()
    b = base64.b64encode(data).decode("ascii")
    script = ("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s && wc -c %s"
              % (b, remote, remote, remote, remote, remote))
    rc, o = run(script)
    ok = want in o
    print("[push] %-28s rc=%d md5=%s %s" % (remote.rsplit("/", 1)[-1], rc, want[:8], "OK" if ok else "MISMATCH"))
    if not ok:
        print(o[-400:])
        sys.exit(2)

if len(sys.argv) > 1 and sys.argv[1] == "pushonly":
    sys.exit(0)

# 启动构建（后台），日志落 build_r1.log
script = r'''cd /home/albus/strata166/build024
rm -f build_r1.log
nohup sh -c 'docker build -f Dockerfile-0.2.4 -t strata-gfx906:0.2.4r1 . > build_r1.log 2>&1; echo RC=$? >> build_r1.log' >/dev/null 2>&1 &
sleep 8
echo "=== head ==="; head -4 build_r1.log 2>/dev/null
echo "=== tail ==="; tail -6 build_r1.log 2>/dev/null'''
rc, o = run(script)
print("[build] rc=%d" % rc)
print(o[:2000])
