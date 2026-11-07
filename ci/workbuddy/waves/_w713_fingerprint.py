# 0.1.41 镜像指纹：构建日志的 PATCH_SURFACE 标记 + 复核 grep + 引擎 binary + --version
import subprocess, base64

REMOTE = """set -u
echo '== 构建日志关键行（PATCH_SURFACE + 六处复核 grep + 版本）=='
grep -nE 'PATCH_SURFACE|^[0-9]+:.*(cudaFuncSetAttribute|cudaEventBlockingSync|STRATA_GR_SPLIT read|STRATA_HIP_GFX906|STRATA_Q6K_EXPERTS OR)|project\\(strata VERSION|patched=|verified=' /home/albus/strata166/build-ctx-411/build-411.log | tail -30
echo '== 镜像/引擎指纹 =='
docker images --format '{{.Repository}}:{{.Tag}} | {{.ID}} | {{.Size}} | {{.CreatedAt}}' | grep -i strata
docker run --rm --entrypoint bash strata-gfx906:0.1.41 -lc 'ls -l /src/build-906/strata; md5sum /src/build-906/strata; /src/build-906/strata --version 2>&1 | head -2; grep -n "project(strata VERSION" /src/CMakeLists.txt'
echo '== 构建耗时（日志首尾时间戳）=='
head -n 2 /home/albus/strata166/build-ctx-411/build-411.log
tail -n 3 /home/albus/strata166/build-ctx-411/build-411.log
"""

p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n",
                   capture_output=True, timeout=300)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-500:])
