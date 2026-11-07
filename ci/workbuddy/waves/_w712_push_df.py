# 把清洗过禁用码位的 Dockerfile-0.1.40.4 重新推到 166（保持本机/远端逐字节一致），只读校验
import subprocess, base64, hashlib

p = r"D:/workbuddy_space/strata_ws/deploy/docker/Dockerfile-0.1.40.4"
raw = open(p, "rb").read()
assert b"\r" not in raw
md5 = hashlib.md5(raw).hexdigest()
b64 = base64.b64encode(raw).decode("ascii")

script = r"""
set -u
D=/home/albus/strata166/build-ctx-404
cp -n "$D/Dockerfile-0.1.40.4" "$D/Dockerfile-0.1.40.4.preclean" 2>/dev/null || true
base64 -d > "$D/Dockerfile-0.1.40.4" <<'__DF_EOF__'
%(b64)s
__DF_EOF__
echo "remote md5: $(md5sum $D/Dockerfile-0.1.40.4 | cut -d' ' -f1)"
echo "remote CR : $(tr -cd '\r' < $D/Dockerfile-0.1.40.4 | wc -c)"
echo "-- 与 preclean 版的差异（应只有注释里的码位）--"
diff "$D/Dockerfile-0.1.40.4.preclean" "$D/Dockerfile-0.1.40.4" || true
echo "PUSH_DONE"
""" % {"b64": b64}

pr = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "albus@192.168.50.166", "base64 -d | bash"],
    input=(base64.b64encode(script.encode("utf-8")) + b"\n"), capture_output=True, timeout=120)
print("local md5", md5)
print("ssh rc", pr.returncode)
print(pr.stdout.decode("utf-8", "replace"))
print("STDERR:", pr.stderr.decode("utf-8", "replace")[-300:])
