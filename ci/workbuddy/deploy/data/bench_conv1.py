import hashlib, json, sys, time, urllib.request

# 单会话重复性 + parking 一致性探针（决定性设计）
#   一个会话、3 轮、**重复 R 次**（同一引擎实例内）：这样能分辨
#   (a) 引擎本身不确定（同臂内两次不同）  还是  (b) parking 改了答案（跨臂不同而同臂内相同）
#   用法: python3 bench_conv1.py <tag> [reps]
#   产出: /data/c1_<tag>_r<rep>_t<turn>.txt + 每轮 `C1 <tag> r<rep> t<turn> pt= ttft= len= md5=`
BASE = 'http://127.0.0.1:8090/v1'
TAG = sys.argv[1]
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
PARAS = 120
DOC = ("The principal advantage of the configuration under test is that its working set fits "
       "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
       "access at all and the throughput is limited by compute rather than by storage. ")
QS = ["In one sentence, what is the principal advantage?",
      "Name two consequences of it, one per line.",
      "Give one counter-example where it would not hold."]

mdl = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']


def post(messages, mt=48):
    body = json.dumps({'model': mdl, 'messages': messages, 'max_tokens': mt,
                       'temperature': 0.0, 'top_k': 1, 'stream': True,
                       'stream_options': {'include_usage': True}}).encode()
    req = urllib.request.Request(BASE + '/chat/completions', data=body,
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; buf = []; usage = None
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
                if tf is None and (dc.get('content') or dc.get('reasoning_content')):
                    tf = time.time()
    return ''.join(buf), (usage or {}), (tf - t0) if tf else -1


doc = "Read the following text and answer the question.\n\n[conv-single]\n" + DOC * PARAS
print('===== C1 ARM %s (reps=%d) =====' % (TAG, REPS), flush=True)
for rep in range(1, REPS + 1):
    hist = []
    for turn in range(3):
        msgs = [{'role': 'user', 'content': doc + "\n\nQuestion: " + QS[0]}]
        for t in range(1, turn + 1):
            msgs.append({'role': 'assistant', 'content': hist[t - 1]})
            msgs.append({'role': 'user', 'content': "Question: " + QS[t]})
        out, u, ttft = post(msgs)
        hist.append(out)
        p = '/data/c1_%s_r%d_t%d.txt' % (TAG, rep, turn)
        open(p, 'w', encoding='utf-8', newline='\n').write(out)
        print('C1 %s r%d t%d msgs=%d pt=%s ttft=%.3fs len=%d md5=%s'
              % (TAG, rep, turn, len(msgs), u.get('prompt_tokens'), ttft, len(out),
                 hashlib.md5(out.encode('utf-8')).hexdigest()[:12]), flush=True)
print('===== C1 ARM %s DONE =====' % TAG, flush=True)
