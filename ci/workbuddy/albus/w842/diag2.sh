set +e
echo "=== data/bin 现状 ==="
ls -l --time-style=+%H:%M /home/albus/strata166/data/bin/
echo
echo "=== 容器状态 / health ==="
docker ps --format '{{.Names}} {{.Status}}' | head -2
curl -s --max-time 3 http://127.0.0.1:8090/health; echo
echo
echo "=== 配置现状 ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe=',d['exe'],'env_n=',len(d.get('env') or {}),'args_n=',len(d['args']))"
echo
echo "=== 引擎日志：几次 session up 的时间线（含 n4 报错前后的上下文） ==="
grep -an "session is up\|No such file or directory: '/home/albus/strata166/data/bin\|loading the experts" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -12
