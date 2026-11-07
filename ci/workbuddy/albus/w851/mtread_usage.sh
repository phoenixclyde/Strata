set +e
echo "===== mt_read.py 的参数与 pool 处理（能否指定 <1024 的 token 数） ====="
sed -n '1,50p' /home/albus/strata166/tmp/mt_read.py
echo "--- pool:"
python3 -c "
import json;d=json.load(open('/home/albus/strata166/tmp/kl_pool2.json'))
print(type(d), len(d))
print(str(d)[:300])
" 2>/dev/null
