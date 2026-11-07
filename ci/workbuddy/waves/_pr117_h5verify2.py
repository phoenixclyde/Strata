# -*- coding: utf-8 -*-
"""H5 必要性直证 v2 —— 修正 v1 的替换漏洞，并加自证（替换是否真命中 / 产物是否生成 / 符号是否消失）"""
import sys
sys.path.insert(0, r"D:/workbuddy/_z_rk80")
sys.stdout.reconfigure(encoding='utf-8')
import _sshutil

SCRIPT = r'''
set +e
C=strata166-402
docker exec $C bash -lc '
set +e
cd /src/build-906
echo "=== [A] 取全部命令，定位链接行 ==="
ninja -t commands strata > /tmp/allcmd.txt 2>/dev/null
wc -l /tmp/allcmd.txt
LINK=$(grep -n " -o strata " /tmp/allcmd.txt | tail -1 | cut -d: -f1)
echo "链接行号 = $LINK"
sed -n "${LINK}p" /tmp/allcmd.txt > /tmp/link.txt
wc -c /tmp/link.txt
echo "--- 链接行里的 mmq 归档引用 ---"
grep -o "[^ ]*libstrata_mmq\.a" /tmp/link.txt
echo "--- 链接行里 -o 的用法 ---"
grep -o "\-o [^ ]*" /tmp/link.txt

echo
echo "=== [B] 构造替换（去掉 q6_k 实例）==="
cp libstrata_mmq.a /tmp/m_noh5.a
ar d /tmp/m_noh5.a mmq-instance-q6_k.cu.o
echo -n "原归档 q6_k 成员 = "; ar t libstrata_mmq.a | grep -c q6_k
echo -n "新归档 q6_k 成员 = "; ar t /tmp/m_noh5.a | grep -c q6_k
sed "s#[^ ]*libstrata_mmq\.a#/tmp/m_noh5.a#g; s#-o strata #-o /tmp/strata_noh5 #g" /tmp/link.txt > /tmp/link_noh5.txt
echo -n "替换命中 m_noh5 次数 = "; grep -o "m_noh5" /tmp/link_noh5.txt | wc -l
echo -n "替换命中 strata_noh5 次数 = "; grep -o "strata_noh5" /tmp/link_noh5.txt | wc -l
echo "--- 替换后链接行里的 -o 与 mmq ---"
grep -o "\-o [^ ]*" /tmp/link_noh5.txt
grep -o "[^ ]*mmq[^ ]*" /tmp/link_noh5.txt

echo
echo "=== [C] 执行为证 ===
rm -f /tmp/strata_noh5
bash /tmp/link_noh5.txt > /tmp/link_noh5.log 2>&1
echo "link_rc=$?"
echo -n "产物存在 = "; ls -la /tmp/strata_noh5 2>/dev/null || echo NO
echo "--- 链接日志里 error/undefined 相关（前 20 行）---"
grep -iE "undefined|error|ld\.lld|cannot find" /tmp/link_noh5.log | head -20
echo "--- 日志尾部 ---"
tail -6 /tmp/link_noh5.log

echo
echo "=== [D] 对照：原归档 + 原命令（应成功）===
sed "s#-o strata #-o /tmp/strata_ok #g" /tmp/link.txt > /tmp/link_ok.txt
rm -f /tmp/strata_ok
bash /tmp/link_ok.txt > /tmp/link_ok.log 2>&1
echo "ctrl_rc=$?"
ls -la /tmp/strata_ok 2>/dev/null | tail -1

echo
echo "=== [E] 若反证未复现，检查符号是否来自别处 ==="
echo -n "新归档里 mul_mat_q_case 的 q6_k 定义 = "
nm -C /tmp/m_noh5.a 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>"
echo -n "engines 归档里是否有 q6_k 实例 = "
for a in libstrata_engine.a libstrata_prefill.a libstrata_kernels.a libstrata_core.a; do
  echo -n "$a: "; nm -C $a 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>"
done

rm -f /tmp/m_noh5.a /tmp/strata_noh5 /tmp/strata_ok /tmp/link*.txt /tmp/link*.log /tmp/allcmd.txt
echo cleaned
'
'''
rc, out, err = _sshutil.run_remote(SCRIPT, timeout=900, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:1500])
