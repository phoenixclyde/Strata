import sys, subprocess
sys.path.insert(0, "albus/r5")
from _rsh import sh, push
for f in ("ab_p16.sh", "ab_p17.sh"):
    print(push("albus/r5/" + f, "/home/albus/strata166/tmp/" + f))
print(sh("cd /home/albus/strata166/tmp && chmod +x ab_p16.sh ab_p17.sh && sh -n ab_p16.sh && sh -n ab_p17.sh && echo SYNTAX_OK && ls w776_bench.py", t=60))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup sh -c './ab_p16.sh; ./ab_p17.sh' > /tmp/ab_p16_17.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
