import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
echo "===CONFIG==="
cat /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
echo ""
echo "===HELP_PREFILL==="
docker exec strata166-407 /src/build-906/strata --help 2>&1 | grep -i -E "prefill|chunk|cpu-share|pipe|stage|stream" | head -60
echo "===HELP_CACHE==="
docker exec strata166-407 /src/build-906/strata --help 2>&1 | grep -i -E "expert|resident|cache|ple|mmap|vram|arena" | head -60
echo "===HELP_PCIE==="
docker exec strata166-407 /src/build-906/strata --help 2>&1 | grep -i -E "pcie|spec|mtp|draft|kv|context" | head -60
echo "===LOGTAIL==="
docker logs --tail 120 strata166-407 2>&1 | grep -v "^\s*$" | tail -80
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8","replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_probe166b.out.txt","w",encoding="utf-8").write(out)
print("RC",p.returncode,"len",len(out)); print(out)
