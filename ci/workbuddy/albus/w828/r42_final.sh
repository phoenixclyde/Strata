python3 - <<'PY'
import json, urllib.request
B='http://127.0.0.1:8090'
m=json.loads(urllib.request.urlopen(B+'/v1/models',timeout=10).read())['data'][0]['id']
r=urllib.request.Request(B+'/v1/chat/completions',
    data=json.dumps({'model':m,'messages':[{'role':'user','content':'回答两个字：正常吗'}],
                     'max_tokens':16,'temperature':0}).encode(),
    headers={'Content-Type':'application/json'})
j=json.loads(urllib.request.urlopen(r,timeout=180).read())
print('FINAL', j['choices'][0].get('finish_reason'), (j['choices'][0]['message'].get('content') or '')[:60].replace('\n',' '))
print('usage', j.get('usage'))
PY
docker ps --format '{{.Names}} {{.Status}} {{.Image}}' | grep strata166
docker logs strata166-407 2>&1 | grep -a -c "expert cache 9"
