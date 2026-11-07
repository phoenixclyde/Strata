import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
LOG=/home/albus/strata166/logs/build-402.log
echo "===== 日志规模 ====="
wc -l "$LOG"; ls -l "$LOG"
echo
echo "===== 错误行（error / FAILED / undefined）====="
grep -nE '(^|: )(error|Error)|FAILED:|undefined|ld\.lld|ninja: build stopped' "$LOG" | head -40
echo
echo "===== 最后一个编译单元附近（[118/139] 上下文，60 行）====="
awk '/\[11[0-9]\/139\]/{p=NR} END{}' "$LOG" >/dev/null
grep -n '\[1[0-9][0-9]/139\]' "$LOG" | tail -3
S=$(grep -n '\[11[0-9]/139\]' "$LOG" | tail -1 | cut -d: -f1)
[ -n "$S" ] && sed -n "${S},$((S+70))p" "$LOG" || tail -70 "$LOG"
''', timeout=240, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
