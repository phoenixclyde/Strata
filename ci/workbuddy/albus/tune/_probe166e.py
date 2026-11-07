import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
echo "===MOUNTS==="
docker inspect strata166-407 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
echo "===INDEX_HEAD==="
head -6 /home/albus/strata166/data/packs/huihui-ud-iq4_xs/index.txt 2>/dev/null
echo "===INDEX_SHARDCOUNT==="
awk '{for(i=1;i<=NF;i++) if($i ~ /gguf/) print $i}' /home/albus/strata166/data/packs/huihui-ud-iq4_xs/index.txt 2>/dev/null | sed 's/.*-0000//' | sort | uniq -c | head
echo "===NATIVE_EXPERTS==="
head -8 /home/albus/strata166/data/packs/huihui-ud-iq4_xs/native_experts.txt 2>/dev/null
wc -l /home/albus/strata166/data/packs/huihui-ud-iq4_xs/native_experts.txt 2>/dev/null
echo "===GGUF_SIZE==="
for f in $(docker inspect strata166-407 --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}'); do :; done
ls -l --block-size=1 /home/albus/strata166/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/ 2>/dev/null
echo "===PLE_SHARD_IN_PACK==="
grep -c "00002-of-00003" /home/albus/strata166/data/packs/huihui-ud-iq4_xs/index.txt 2>/dev/null
grep -c "00002-of-00003" /home/albus/strata166/data/packs/huihui-ud-iq4_xs/native_experts.txt 2>/dev/null
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8","replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_probe166e.out.txt","w",encoding="utf-8").write(out)
print("RC",p.returncode,"len",len(out)); print(out)
