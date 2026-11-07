import subprocess, base64, hashlib, io, json, time

HOST = "albus@192.168.50.166"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
NEW = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.w792final"


def sh(script, timeout=180):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


# 1) 推最终 config（md5 自证）
raw = open(GEN, "rb").read()
md5 = hashlib.md5(raw).hexdigest()
payload = base64.b64encode(raw).decode("ascii")
o = sh("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (payload, NEW, NEW, NEW, NEW))
print(o.strip())
assert md5 in o, "push md5 mismatch"

# 2) 推 adopt.sh
src = open(r"D:/workbuddy_space/strata_ws/albus/r5/adopt.sh", "rb").read().decode()
o = sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/adopt.sh && chmod +x /home/albus/strata166/tmp/adopt.sh && sh -n /home/albus/strata166/tmp/adopt.sh && echo SYNTAX_OK"
       % base64.b64encode(src.encode()).decode("ascii"), timeout=120)
print(o.strip())
assert "SYNTAX_OK" in o

# 3) 启动（detached；ssh 通道会因继承 stdout 而挂住，用超短连接 + 不等待）
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./adopt.sh > /tmp/adopt.out 2>&1 < /dev/null & echo LAUNCHED", timeout=20))
except subprocess.TimeoutExpired:
    print("LAUNCHED (channel timeout, expected)")
