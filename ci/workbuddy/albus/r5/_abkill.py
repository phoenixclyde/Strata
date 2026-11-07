import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh("pkill -f ab_p3.sh; sleep 2; pkill -f w776_bench.py; sleep 1; ps -ef | grep -c '[a]b_p3'; echo KILLED"))
