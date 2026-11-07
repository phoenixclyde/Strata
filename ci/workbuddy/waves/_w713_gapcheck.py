# 补三处证据缺口：① 0.1.41 引擎 binary md5（审计称"仅有自陈"）② _w727 真实位置 ③ 根目录 0 字节残留清单
import subprocess, base64, os, glob

print("=== ① 0.1.41 镜像内引擎 binary 指纹（只读 docker run）===")
R1 = """docker run --rm --entrypoint bash strata-gfx906:0.1.41 -lc 'ls -l /src/build-906/strata; md5sum /src/build-906/strata'"""
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(R1.encode()) + b"\n", capture_output=True, timeout=180)
print(p.stdout.decode("utf-8", "replace").strip() or "(空)")

print()
print("=== ② _w727 的真实位置 ===")
for pat in [r"D:/workbuddy_space/strata_ws/waves/_w727*", r"D:/workbuddy_space/strata_ws/deploy/logs/_w727*",
            r"D:/workbuddy_space/strata_ws/**/_w727*"]:
    hits = glob.glob(pat, recursive=True)
    print("  %-58s -> %s" % (pat.split('strata_ws/')[-1], hits[:3] if hits else "无"))

print()
print("=== ③ 工作区根目录 0 字节残留 ===")
root = r"D:/workbuddy_space/strata_ws"
for n in sorted(os.listdir(root)):
    fp = os.path.join(root, n)
    if os.path.isfile(fp) and os.path.getsize(fp) == 0:
        print("  [0B] %-40s mtime=%s" % (n, __import__("time").strftime("%H:%M:%S", __import__("time").localtime(os.path.getmtime(fp)))))
    elif os.path.isfile(fp):
        print("  [ok] %-40s %d B" % (n, os.path.getsize(fp)))
    else:
        print("  [dir] %s" % n)
