import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
src=open(r"D:/workbuddy_space/strata_ws/albus/r5/ab_p7.sh","rb").read().decode()
pl=base64.b64encode(src.encode()).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/ab_p7.sh && chmod +x /home/albus/strata166/tmp/ab_p7.sh && sh -n /home/albus/strata166/tmp/ab_p7.sh && echo SYNTAX_OK" % pl))
# 确认生产基线正常再开跑
print(sh("curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 60; echo; docker inspect -f '{{.Config.Image}}' strata166-407; ps -ef | grep -c '[a]b_p'"))
