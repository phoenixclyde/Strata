set +e
echo "=== mt_read.py 用法 ==="
head -22 /home/albus/strata166/tmp/mt_read.py
echo "=== dec_corpus.json ==="
python3 -c "import json;d=json.load(open('/home/albus/strata166/tmp/dec_corpus.json'));print(type(d),len(d))" 2>/dev/null
head -c 300 /home/albus/strata166/tmp/dec_corpus.json
