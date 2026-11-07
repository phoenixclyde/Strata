import hashlib, json, sys, time, urllib.request

# 答案一致性探针：同一批固定 prompt、贪心（temperature 0 / top_k 1），把生成文本落盘 + 打指纹。
# 用法: python3 bench_answer.py <tag>
# 产出: /data/ans_<tag>_<i>.txt  +  stdout 行 `ANS <tag> <i> len=<n> md5=<h> head=<前 60 字>`
BASE = 'http://127.0.0.1:8090/v1'
TAG = sys.argv[1]
OUTDIR = '/data'

PARA = ("The principal advantage of the configuration under test is that its working set fits "
        "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
        "access at all and the throughput is limited by compute rather than by storage. ")

# 三段长度：30 段(~1.4k，短于 chunk 4096) / 150 段(~6.8k) / 400 段(~18k)
CASES = [(30, "In one short sentence, what is the principal advantage described?"),
         (150, "List three consequences of the advantage described, in one line each."),
         (400, "Summarise the passage in exactly two sentences.")]

mdl = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']


def gen(text, mt=64):
    body = json.dumps({'model': mdl, 'messages': [{'role': 'user', 'content': text}],
                       'max_tokens': mt, 'temperature': 0.0, 'top_k': 1,
                       'stream': True, 'stream_options': {'include_usage': True}}).encode()
    req = urllib.request.Request(BASE + '/chat/completions', data=body,
                                 headers={'Content-Type': 'application/json'})
    buf, usage, t0 = [], None, time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            ln = raw.decode('utf-8', 'replace').strip()
            if not ln.startswith('data:'):
                continue
            d = ln[5:].strip()
            if d == '[DONE]':
                break
            try:
                j = json.loads(d)
            except Exception:
                continue
            if j.get('usage'):
                usage = j['usage']
            for ch in (j.get('choices') or []):
                dc = ch.get('delta') or {}
                if dc.get('reasoning_content'):
                    buf.append(dc['reasoning_content'])
                if dc.get('content'):
                    buf.append(dc['content'])
    return ''.join(buf), (usage or {}), time.time() - t0


print('===== ANSWER ARM %s =====' % TAG, flush=True)
for i, (paras, q) in enumerate(CASES):
    text = ("Read the following text and answer the question.\n\n[x]\n" + PARA * paras +
            "\n\nQuestion: " + q)
    out, u, dt = gen(text)
    p = '%s/ans_%s_%d.txt' % (OUTDIR, TAG, i)
    open(p, 'w', encoding='utf-8', newline='\n').write(out)
    h = hashlib.md5(out.encode('utf-8')).hexdigest()
    print('ANS %s %d pt=%s ct=%s len=%d md5=%s dt=%.1fs head=%r'
          % (TAG, i, u.get('prompt_tokens'), u.get('completion_tokens'), len(out), h, dt, out[:60]),
          flush=True)
print('===== ANSWER ARM %s DONE =====' % TAG, flush=True)
