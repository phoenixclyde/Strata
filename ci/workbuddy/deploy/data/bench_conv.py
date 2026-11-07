import hashlib, json, sys, time, urllib.request

# 双会话交替探针（conversation parking 的体验判据 + 答案一致性）
#   两个会话 A/B 各有 3 轮；每轮把"上一轮回答"接回历史（模拟真实 chat 客户端），交替发送：
#   A1 B1 A2 B2 A3 B3  => A/B 互相把对方挤进 parking 缓存，回来时看 TTFT 是否塌到亚秒
#   用法: python3 bench_conv.py <tag> [paras]
#   产出: 每轮 `CONV <tag> <conv> <turn> pt= ttft= dt= len= md5=` + 文本落盘 /data/conv_<tag>_<conv>_<turn>.txt
BASE = 'http://127.0.0.1:8090/v1'
TAG = sys.argv[1]
PARAS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
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
                if dc and tf is None and (dc.get('content') or dc.get('reasoning_content')):
                    tf = time.time()
    return ''.join(buf), (usage or {}), (tf - t0) if tf else -1, time.time() - t0


convs = {'A': 'conv-A-salt', 'B': 'conv-B-salt'}
# 真实 chat 结构：turn N 的 messages = [user(doc+Q1), assistant(A1), user(Q2), assistant(A2), ...]
# 这样服务端渲染出的前缀与上一轮**逐 token 一致**，引擎才可能认作同一会话（上一版用合成 "Answer:" 拼接 => 前缀分叉，测试域不成立）
hist = {k: [] for k in convs}
print('===== CONV ARM %s (paras=%d) =====' % (TAG, PARAS), flush=True)
for turn in range(3):
    for k in ('A', 'B'):
        doc = ("Read the following text and answer the question.\n\n[%s]\n" % convs[k]) + DOC * PARAS
        msgs = [{'role': 'user', 'content': doc + "\n\nQuestion: " + QS[0]}]
        for t in range(1, turn + 1):
            msgs.append({'role': 'assistant', 'content': hist[k][t - 1]})
            msgs.append({'role': 'user', 'content': "Question: " + QS[t]})
        out, u, ttft, dt = post(msgs)
        hist[k].append(out)
        p = '/data/conv_%s_%s_%d.txt' % (TAG, k, turn)
        open(p, 'w', encoding='utf-8', newline='\n').write(out)
        print('CONV %s %s %d msgs=%d pt=%s ttft=%.3fs dt=%.1fs len=%d md5=%s'
              % (TAG, k, turn, len(msgs), u.get('prompt_tokens'), ttft, dt, len(out),
                 hashlib.md5(out.encode('utf-8')).hexdigest()[:12]), flush=True)
print('===== CONV ARM %s DONE =====' % TAG, flush=True)
