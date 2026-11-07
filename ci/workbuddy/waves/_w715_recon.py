# 侦察 166/容器：iq_pack 用法、strata 参数面（vision / ngram / mtp / draft）、vision 产物
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-406
echo "===== A) iq_pack.py 用法 ====="
docker exec $C python3 /src/tools/iq_pack.py --help 2>&1 | head -70
echo
echo "===== B) strata 参数面（关键字过滤）====="
docker exec $C /src/build-906/strata --help 2>&1 | grep -iE 'vision|ngram|n-gram|suffix|draft|mtp|spec|image|mmproj' | head -50
echo
echo "===== C) tools 里 vision / ngram / draft 相关文件 ====="
docker exec $C sh -c "ls /src/tools/ | grep -iE 'vision|ngram|suffix|spec|draft|mmproj'"
echo "--- tools/vision 目录 ---"
docker exec $C ls -l /src/tools/vision/ 2>&1 | head -25
echo
echo "===== D) 源码里 ngram / vision 的落点 ====="
docker exec $C sh -c "grep -rilE 'ngram|n-gram' /src/src /src/serve 2>/dev/null | head -10"
echo "--- vision ---"
docker exec $C sh -c "grep -rilE 'vision|mmproj' /src/src /src/serve 2>/dev/null | head -10"
echo
echo "===== E) serve 目录 ====="
docker exec $C ls /src/serve/ 2>&1 | head -25
echo
echo "===== F) 现役 config 全文 ====="
cat /home/albus/strata166/data/strata-ud-iq4_xs.json
echo
echo "===== G) 现有 packs / data 目录 ====="
ls -l /home/albus/strata166/data/packs/
echo "--- data 顶层 ---"
ls -l /home/albus/strata166/data/ | head -25
echo
echo "===== H) mtp 工具用法 ====="
docker exec $C python3 /src/tools/mtp_rt.py --help 2>&1 | head -25
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_recon.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
