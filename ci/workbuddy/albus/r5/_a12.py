import sys, subprocess
sys.path.insert(0, "albus/r5")
from _rsh import sh, push
# 1) 先把生产配置恢复到 11 项（用 register 生成件）
print(push("deploy/params/generated/strata-huihui-ud-iq4_xs.json",
           "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
print(sh("python3 -c \"import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('env_n',len(d['env']),sorted(d['env']))\"", t=60))
print(push("albus/r5/ab_p15.sh", "/home/albus/strata166/tmp/ab_p15.sh"))
print(sh("cd /home/albus/strata166/tmp && chmod +x ab_p15.sh && sh -n ab_p15.sh && echo SYNTAX_OK", t=60))
try:
    print(sh("cd /home/albus/strata166/tmp && setsid nohup ./ab_p15.sh > /tmp/ab_p15.out 2>&1 </dev/null & echo LAUNCHED", t=18))
except subprocess.TimeoutExpired:
    print("LAUNCHED (held)")
