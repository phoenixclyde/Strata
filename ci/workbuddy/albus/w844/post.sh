set +e
echo "=== 落产日志 ==="
cat /home/albus/strata166/data/w844_deploy_192952.txt 2>/dev/null | head -40
echo
echo "=== 现状 ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe=',d['exe'],'args=',len(d['args']),'env=',len(d.get('env') or {}))"
docker ps --format '{{.Names}} {{.Status}}' | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
