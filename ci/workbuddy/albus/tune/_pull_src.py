import subprocess, base64, hashlib, os
HOST = "albus@192.168.50.166"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_tpatch"
for remote, name in (("/home/albus/strata166/build023/src/serve/web/app.js", "app.js.upstream023"),
                     ("/home/albus/strata166/build023/src/serve/telemetry.py", "telemetry.py.upstream023"),
                     ("/home/albus/strata166/build022/src/serve/web/app.js", "app.js.upstream022")):
    s = "base64 -w0 %s" % remote
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(s.encode("ascii")), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = base64.b64decode(b"".join(p.stdout.split()))
    path = os.path.join(OUT, name)
    open(path, "wb").write(data)
    print(name, len(data), hashlib.md5(data).hexdigest()[:8])
