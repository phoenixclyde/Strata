# W2 升级闸门：166 侧 nohup 跑 gate（服务面 + 中性矩阵 100/220/530），本机同步跑 verify_config，然后轮询
import subprocess, base64, time, os

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w713_gate.out.txt"
PY = r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe"
f = open(OUT, "w", encoding="utf-8")


def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()


def ssh(script, timeout=300):
    p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                        "-o", "ServerAliveInterval=15", "albus@192.168.50.166", "base64 -d | bash"],
                       input=base64.b64encode(script.encode()) + b"\n", capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


# 启动闸门（后台）
rc, out, err = ssh("cd /home/albus/strata166/w712 && setsid nohup bash upgrade_gate.sh 0.1.41 >/dev/null 2>&1 </dev/null & sleep 4; "
                   "pgrep -af upgrade_gate | head -2; head -n 8 /home/albus/strata166/w712/gate.log", 120)
log("gate 启动 rc=%d" % rc)
f.write(out + "\n"); f.flush()

# 本机跑核验器（第 4 个服务面）
r = subprocess.run([PY, "-u", r"D:/workbuddy_space/strata_ws/deploy/params/verify_config.py"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
vl = [x for x in (r.stdout or "").splitlines() if "PASS=" in x or x.startswith("目标容器")]
log("verify_config rc=%d  %s" % (r.returncode, " | ".join(vl)))

# 轮询到收尾
done = False
for i in range(24):
    time.sleep(20)
    rc, out, err = ssh("pgrep -f upgrade_gate.sh >/dev/null && echo RUNNING || echo DONE; "
                       "grep -c 'UPGRADE GATE done' /home/albus/strata166/w712/gate.log || true", 90)
    if "DONE" in out or "1" == out.strip().splitlines()[-1]:
        done = True
        break
log("轮询结束 done=%s (第 %d 次)" % (done, i + 1))

rc, out, err = ssh("cat /home/albus/strata166/w712/gate.log", 120)
f.write("\n===== gate.log 全文 =====\n" + out + "\n")
f.close()
print(out[-4000:])
