set +e
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('exe=',d['exe'],'env=',sorted((d.get('env') or {}).keys()))"
ls -t /home/albus/strata166/data/w842_b_*.txt 2>/dev/null | head -2
pgrep -af "run_b.sh|mt_read|mt_gen" | head -3
