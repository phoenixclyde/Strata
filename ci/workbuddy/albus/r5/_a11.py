import sys, subprocess
sys.path.insert(0, "albus/r5")
from _rsh import sh, push
for f in ("mt_chat.py", "lib_a9.sh", "ab_p14.sh"):
    print(push("albus/r5/" + f, "/home/albus/strata166/tmp/" + f))
print(sh("cd /home/albus/strata166/tmp && chmod +x lib_a9.sh ab_p14.sh && sh -n ab_p14.sh && echo SYNTAX_OK", t=60))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p14.sh > /tmp/ab_p14.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
