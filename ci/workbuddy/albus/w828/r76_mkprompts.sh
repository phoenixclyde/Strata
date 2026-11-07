set -e
cd /home/albus/strata166
python3 - <<'PY'
import json, random
pool=json.load(open('/home/albus/strata166/tmp/kl_pool.json'))
texts=[t for t in pool if isinstance(t,str)]
texts=sorted(texts, key=len, reverse=True)
target=3600          # chars per prompt (~1.0k tokens); 8 of them accumulate the scored positions
prompts=[]
used=0
for i in range(8):
    parts=[]; n=0
    while n < target and used < len(texts):
        t=texts[used % len(texts)]; used+=1
        parts.append(t); n+=len(t)+1
    prompts.append(' '.join(parts))
json.dump({'prompts': prompts}, open('/home/albus/strata166/tmp/kl_multi.json','w'))
print('prompts', len(prompts), 'chars', [len(p) for p in prompts])
PY
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run --rm -v /home/albus/strata166/data:/data strata-gfx906:0.2.8 rm -f /data/w828kl/*.tsv
echo "dir now:"; ls -la /home/albus/strata166/data/w828kl/ 2>/dev/null
