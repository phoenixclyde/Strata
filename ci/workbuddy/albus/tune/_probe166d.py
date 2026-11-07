import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
echo "===GGUF==="
ls -l --block-size=1 /home/albus/strata166/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/*.gguf 2>/dev/null
echo "===PACKFILES==="
ls -l --block-size=1 /home/albus/strata166/data/packs/huihui-ud-iq4_xs/ 2>/dev/null | head -20
echo "===EXPERTS_LINES==="
sed -n '19655,19725p' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log 2>/dev/null | grep -i -E "expert|blob|layer|dense|kv|VRAM|arena|slot" | head -40
echo "===VRAMRESERVE==="
docker exec strata166-407 /src/build-906/strata --help 2>&1 | grep -i -E "vram-reserve|reserve-mib|max-context|kv-grow|shared-expert"
echo "===HEADER==="
docker exec strata166-407 /src/build-906/strata --help 2>&1 | sed -n '1,24p'
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8","replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_probe166d.out.txt","w",encoding="utf-8").write(out)
print("RC",p.returncode,"len",len(out)); print(out)
