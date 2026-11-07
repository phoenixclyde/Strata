# -*- coding: utf-8 -*-
"""H5 必要性直证（廉价且决定性）：
   H5 的唯一作用 = 是否把 `mmq-instance-q6_k.cu.o` 编进 libstrata_mmq.a。
   所以"不打 H5"在链接期的等价物 = 从归档里移除该 .o，再按原链接命令行重链一次。
   若复现 `undefined symbol: mul_mat_q_case<(ggml_type)14>` ⇒ H5 必要性成立（不是推测）。
   另附：当前镜像内该符号在（正证）。
"""
import sys, time, base64
sys.path.insert(0, r"D:/workbuddy/_z_rk80")
sys.stdout.reconfigure(encoding='utf-8')
import _sshutil

SCRIPT = r'''
set +e
C=strata166-402
echo "===== [1] 归档与实例清单 ====="
docker exec $C bash -lc '
ls -la /src/build-906/libstrata_mmq.a 2>&1
echo "--- 归档内 q6_k 相关成员 ---"
ar t /src/build-906/libstrata_mmq.a 2>/dev/null | grep -i q6_k
echo "--- 归档内成员总数 ---"
ar t /src/build-906/libstrata_mmq.a 2>/dev/null | wc -l
'
echo
echo "===== [2] 正证：引擎二进制里 Q6_K 实例在 ====="
docker exec $C bash -lc '
nm -C /src/build-906/strata 2>/dev/null | grep -o "mul_mat_q_case<(ggml_type)[0-9]*>" | sort -u | tr "\n" " "
echo
echo -n "mul_mat_q_case 符号总数 = "; nm -C /src/build-906/strata 2>/dev/null | grep -c "mul_mat_q_case"
'
echo
echo "===== [3] 取链接命令行 ====="
docker exec $C bash -lc '
cd /src/build-906
ninja -t commands strata 2>/dev/null | tail -1 > /tmp/link_cmd.txt
wc -c /tmp/link_cmd.txt
head -c 300 /tmp/link_cmd.txt
echo
'
echo
echo "===== [4] 反证：移除 q6_k 实例后重链 ====="
docker exec $C bash -lc '
cd /src/build-906
cp libstrata_mmq.a /tmp/m_noh5.a
ar d /tmp/m_noh5.a mmq-instance-q6_k.cu.o
echo -n "移除后归档内 q6_k 成员数 = "; ar t /tmp/m_noh5.a | grep -ci q6_k
echo -n "移除后成员总数 = "; ar t /tmp/m_noh5.a | wc -l
# 把链接命令里的归档路径换掉，输出改到 /tmp/strata_noh5
sed "s#/src/build-906/libstrata_mmq.a#/tmp/m_noh5.a#g; s#-o strata#-o /tmp/strata_noh5#g" /tmp/link_cmd.txt > /tmp/link_noh5.sh
chmod +x /tmp/link_noh5.sh
echo "--- 已改写的链接命令（前 200 字符）---"
head -c 200 /tmp/link_noh5.sh; echo
echo "--- 执行 ---"
bash -c "$(cat /tmp/link_noh5.sh)" 2>&1 | grep -iE "undefined|error|ld.lld" | head -12
echo "link_rc=${PIPESTATUS[0]}"
'
echo
echo "===== [5] 对照：原归档重链应成功 ====="
docker exec $C bash -lc '
cd /src/build-906
sed "s#-o strata#-o /tmp/strata_ok#g" /tmp/link_cmd.txt > /tmp/link_ok.sh
bash -c "$(cat /tmp/link_ok.sh)" >/dev/null 2>&1; echo "ctrl_link_rc=$?"
ls -la /tmp/strata_ok 2>&1 | tail -1
'
echo
echo "===== [6] 清掉临时产物 ====="
docker exec $C bash -lc 'rm -f /tmp/m_noh5.a /tmp/strata_noh5 /tmp/strata_ok /tmp/link_noh5.sh /tmp/link_ok.sh /tmp/link_cmd.txt; echo cleaned'
'''
rc, out, err = _sshutil.run_remote(SCRIPT, timeout=900, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
