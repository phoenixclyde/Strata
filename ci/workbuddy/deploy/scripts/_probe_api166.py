# -*- coding: utf-8 -*-
"""对 166 的 Strata 服务做字段级实测：思考强度取值域 / 工具调用 / 图片 / 输出上限。
用本机直连 http://192.168.50.166:8090/v1（绕开代理）。"""
import json, sys, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://192.168.50.166:8090/v1'
OFF = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MODEL = 'qwen3.8-flash-next-ud-iq4_xs'


def post(path, payload, timeout=300):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time()
    try:
        with OFF.open(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', 'replace')
            return r.status, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace'), time.time() - t0
    except Exception as e:
        return -1, str(e)[:200], time.time() - t0


print('=== /v1/models ===')
s, b, dt = post('/models', {}) if False else (None, None, None)
try:
    with OFF.open(urllib.request.Request(BASE + '/models'), timeout=20) as r:
        print(r.status, r.read().decode()[:300])
except Exception as e:
    print('FAIL', e)

print()
print('=== 思考强度取值域（reasoning_effort）===')
for eff in ['(不传)', 'none', 'low', 'medium', 'high', 'xhigh', 'minimal']:
    p = {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Reply with the single word OK.'}],
         'max_tokens': 48, 'temperature': 0}
    if eff != '(不传)':
        p['reasoning_effort'] = eff
    s, b, dt = post('/chat/completions', p)
    tag = ''
    if s == 200:
        try:
            j = json.loads(b)
            msg = (j.get('choices') or [{}])[0].get('message') or {}
            rc = msg.get('reasoning_content')
            tag = 'reasoning_content=%s  content=%r  usage=%s' % (
                '有(%d字)' % len(rc) if rc else '无', (msg.get('content') or '')[:40], j.get('usage'))
        except Exception as e:
            tag = 'parse err ' + str(e)[:60]
    else:
        tag = b[:200].replace('\n', ' ')
    print('  %-8s -> HTTP %-4s %.1fs  %s' % (eff, s, dt, tag))

print()
print('=== 工具调用 ===')
tools = [{'type': 'function', 'function': {
    'name': 'get_weather', 'description': 'Get the weather for a city',
    'parameters': {'type': 'object', 'properties': {'city': {'type': 'string'}},
                   'required': ['city']}}}]
s, b, dt = post('/chat/completions', {
    'model': MODEL, 'messages': [{'role': 'user', 'content': 'What is the weather in Shanghai? Use the tool.'}],
    'tools': tools, 'max_tokens': 256, 'temperature': 0})
print('  HTTP', s, '%.1fs' % dt)
try:
    j = json.loads(b)
    ch = (j.get('choices') or [{}])[0]
    print('  finish_reason =', ch.get('finish_reason'))
    print('  tool_calls    =', json.dumps(ch.get('message', {}).get('tool_calls'), ensure_ascii=False)[:260])
except Exception:
    print('  body:', b[:300].replace('\n', ' '))

print()
print('=== 图片输入（本机不加载 mmproj，预期不支持）===')
s, b, dt = post('/chat/completions', {
    'model': MODEL, 'max_tokens': 32, 'temperature': 0,
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': 'What is in this image?'},
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=='}}]}]})
print('  HTTP', s, '%.1fs' % dt, '->', b[:220].replace('\n', ' '))

print()
print('=== 输出上限探测（max_tokens 给很大的值）===')
for mt in [8192, 65536, 200000]:
    s, b, dt = post('/chat/completions', {
        'model': MODEL, 'messages': [{'role': 'user', 'content': 'Say OK.'}],
        'max_tokens': mt, 'temperature': 0})
    print('  max_tokens=%-7d -> HTTP %s  %s' % (mt, s, ('' if s == 200 else b[:160].replace('\n', ' '))))

print()
print('=== Anthropic 方言 /v1/messages ===')
s, b, dt = post('/messages', {'model': MODEL, 'max_tokens': 32,
                             'messages': [{'role': 'user', 'content': 'Say OK.'}]})
print('  HTTP', s, '%.1fs' % dt, '->', (b[:200] if s != 200 else b[:200]).replace('\n', ' '))
