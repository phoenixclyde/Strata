import subprocess, base64, sys, os

HOST = "albus@192.168.50.166"
LOCAL = r"D:/workbuddy_space/strata_ws/albus/tune/_bench166.py"
REMOTE = "/home/albus/strata166/tmp/w776_bench.py"


def run(script, timeout=1800):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15", HOST,
                        "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


payload = base64.b64encode(open(LOCAL, "rb").read()).decode("ascii")
print(run("mkdir -p /home/albus/strata166/tmp && echo '%s' | base64 -d > %s && python3 -c 'import ast;ast.parse(open(\"%s\").read())' && echo PUSHED_OK"
          % (payload, REMOTE, REMOTE)))

for tag in sys.argv[1:]:
    print("===== TIER %s =====" % tag, flush=True)
    print(run("cd /home/albus/strata166/tmp && python3 w776_bench.py %s 2>&1" % tag), flush=True)
