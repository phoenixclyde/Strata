set +e
S=/home/albus/strata166/src028/serve/server.py
echo "=== server.py 里 exe 的解析/映射 ==="
grep -n "def .*exe\|engine_exe\|self.exe\|strata166\|/data/bin" "$S" | head -20
echo
echo "=== 9320-9345（报错点） ==="
sed -n '9315,9345p' "$S"
