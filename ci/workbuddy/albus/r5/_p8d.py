import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("pkill -9 -f ab_p8c 2>/dev/null; sleep 2; pkill -9 -f mt_phase 2>/dev/null; sleep 2; ps -ef | grep -c '[a]b_p8c'"))
src=open("albus/r5/ab_p8c.sh","rb").read(); pl=base64.b64encode(src).decode("ascii")
print(sh("echo '%s' | base64 -d > /home/albus/strata166/tmp/ab_p8d.sh && chmod +x /home/albus/strata166/tmp/ab_p8d.sh && sh -n /home/albus/strata166/tmp/ab_p8d.sh && echo SYNTAX_OK" % pl))
print(sh("sed -i 's|w798c_phase|w798d_phase|g; s|w798c_done|w798d_done|g; s|bak_w798c_|bak_w798d_|g' /home/albus/strata166/tmp/ab_p8d.sh && grep -c w798d /home/albus/strata166/tmp/ab_p8d.sh"))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p8d.sh > /tmp/ab_p8d.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
