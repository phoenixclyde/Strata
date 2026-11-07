# 第二轮侦察：strata-vision 是否已编出、PLE shard 从哪来、iq_pack --base 语义、setup.py 的权威用法
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-406
echo "===== A) /src/build-906 内容 ====="
docker exec $C ls -l /src/build-906/ 2>&1 | head -40
echo
echo "===== B) 全镜像找 vision 产物 ====="
docker exec $C sh -c "find /src -maxdepth 3 -iname '*vision*' 2>/dev/null | head -20"
echo
echo "===== C) setup.py 里 vision / ple 的权威写法 ====="
docker exec $C sh -c "grep -nE 'vision|ple-gguf|ple_gguf|suffix-draft|lookup-chain|ple-io' /src/setup.py | head -50"
echo
echo "===== D) 哪些文档提到 --vision / ple-gguf ====="
docker exec $C sh -c "grep -rlnE 'ple-gguf|strata-vision|--vision' /src/docs /src/README.md /src/*.md 2>/dev/null | head -20"
echo
echo "===== E) /src/data 内容（看有无 ple/vision 产物）====="
docker exec $C sh -c "ls -l /src/data/ 2>/dev/null | head -30"
echo
echo "===== F) 找 ple 相关文件 ====="
docker exec $C sh -c "find /src /data -maxdepth 4 -iname '*ple*' 2>/dev/null | head -25"
echo
echo "===== G) iq_pack.py 源码关键段（--base 语义）====="
docker exec $C sh -c "sed -n '1,60p' /src/tools/iq_pack.py"
echo
echo "===== H) ple_fp8_pack.py 用法 ====="
docker exec $C python3 /src/tools/ple_fp8_pack.py --help 2>&1 | head -30
echo
echo "===== I) mtp_fetch.py 用法（MTP 来源）====="
docker exec $C python3 /src/tools/mtp_fetch.py --help 2>&1 | head -30
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_recon2.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
