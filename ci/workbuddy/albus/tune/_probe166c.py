import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
echo "===LOGSTART==="
grep -n -E "pool worker|expert cache|arena|ple|PLE|resident|prefill chunk|prompt chunk|adaptive|kv |KV |vram|VRAM|head |spec|mtp|ready:" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log 2>/dev/null | tail -70
echo "===PACKSIZE==="
du -sb /home/albus/strata166/data/packs/huihui-ud-iq4_xs 2>/dev/null
du -sh /home/albus/strata166/data/packs/huihui-ud-iq4_xs 2>/dev/null
echo "===PROFILE==="
ls -la /home/albus/strata166/data/profiles/ 2>/dev/null
echo "===SSD==="
lsblk -d -o NAME,SIZE,ROTA,SCHED,MODEL 2>/dev/null
echo "---sched---"
for d in /sys/block/sd*/queue/scheduler /sys/block/nvme*/queue/scheduler; do echo -n "$d: "; cat $d 2>/dev/null; done
echo "===KVGROW_SRC==="
grep -rn "kv_grow\|kv-grow" /src/generate.cpp 2>/dev/null | head -5
echo "===POOLW_SRC==="
grep -rn "pool_workers\|pool-workers" /src/generate.cpp 2>/dev/null | head -8
echo "===MEMLOCK==="
docker exec strata166-407 sh -c 'ulimit -l' 2>&1
echo "===CONTAINER_MEM==="
docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}' strata166-407 2>&1
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8","replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_probe166c.out.txt","w",encoding="utf-8").write(out)
print("RC",p.returncode,"len",len(out)); print(out)
