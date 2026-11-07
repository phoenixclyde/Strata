#!/bin/bash
# H5 必要性直证 v3 —— 无嵌套引号；每步自证；nm 区分「定义」与「引用」
C=strata166-402
set +e

docker exec $C bash -lc '
set +e
cd /src/build-906
echo "=== [A] 归档里 q6_k 实例：定义还是引用 ==="
echo "-- libstrata_mmq.a 中所有 mul_mat_q_case<(ggml_type)14> 符号（含类型码）--"
nm -C libstrata_mmq.a 2>/dev/null | grep "mul_mat_q_case<(ggml_type)14>" | cut -c1-140
echo "-- 仅「定义」(T/t/W/V) 计数 --"
nm -C --defined-only libstrata_mmq.a 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>"
echo "-- 仅「未定义引用」(U) 计数 --"
nm -C libstrata_mmq.a 2>/dev/null | grep " U " | grep -c "mul_mat_q_case<(ggml_type)14>"
echo "-- 该定义在哪个成员里 --"
ar t libstrata_mmq.a | while read m; do
  n=$(ar p libstrata_mmq.a "$m" 2>/dev/null | nm -C --defined-only - 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>")
  [ "$n" != "0" ] && echo "    member=$m  定义数=$n"
done
echo "-- 谁在引用它（U 的成员）--"
ar t libstrata_mmq.a | while read m; do
  n=$(ar p libstrata_mmq.a "$m" 2>/dev/null | nm -C - 2>/dev/null | grep " U " | grep -c "mul_mat_q_case<(ggml_type)14>")
  [ "$n" != "0" ] && echo "    member=$m  引用数=$n"
done

echo
echo "=== [B] 其它归档里有没有 q6_k 的定义 ==="
for a in libstrata_engine.a libstrata_prefill.a libstrata_spec.a libstrata_kernels.a libstrata_core.a libstrata_kernels_cpu.a; do
  if [ -f "$a" ]; then echo -n "  $a 定义数="; nm -C --defined-only $a 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>"; fi
done
echo -n "  ggml 侧(mmq 实例源) 定义数="
find /src -name "mmq-instance-q6_k*" 2>/dev/null | head -3

echo
echo "=== [C] 取链接命令 ==="
ninja -t commands strata > /tmp/allcmd.txt 2>/dev/null
LN=$(grep -n " -o strata " /tmp/allcmd.txt | tail -1 | cut -d: -f1)
sed -n "${LN}p" /tmp/allcmd.txt > /tmp/link.txt
wc -c /tmp/link.txt
grep -o "[^ ]*libstrata_mmq\.a" /tmp/link.txt
grep -o " -o [^ ]*" /tmp/link.txt

echo
echo "=== [D] 去掉 q6_k 实例后重链 ==="
cp libstrata_mmq.a /tmp/m_noh5.a
ar d /tmp/m_noh5.a mmq-instance-q6_k.cu.o
echo -n "  原归档 q6_k 成员="; ar t libstrata_mmq.a | grep -c q6_k
echo -n "  新归档 q6_k 成员="; ar t /tmp/m_noh5.a | grep -c q6_k
echo -n "  新归档里 14 号定义数="; nm -C --defined-only /tmp/m_noh5.a 2>/dev/null | grep -c "mul_mat_q_case<(ggml_type)14>"
sed "s#[^ ]*libstrata_mmq\.a#/tmp/m_noh5.a#g" /tmp/link.txt | sed "s# -o strata # -o /tmp/strata_noh5 #g" > /tmp/link_noh5.txt
echo -n "  替换自证: m_noh5 命中="; grep -o m_noh5 /tmp/link_noh5.txt | wc -l
echo -n "  替换自证: strata_noh5 命中="; grep -o strata_noh5 /tmp/link_noh5.txt | wc -l
rm -f /tmp/strata_noh5
bash /tmp/link_noh5.txt > /tmp/link_noh5.log 2>&1
echo "  link_rc=$?"
echo -n "  产物: "; ls -la /tmp/strata_noh5 2>/dev/null | tail -1; [ -f /tmp/strata_noh5 ] || echo "(未生成)"
echo "  --- 错误行 ---"
grep -iE "undefined|ld\.lld: error|error:" /tmp/link_noh5.log | head -8

echo
echo "=== [E] 对照：原归档原命令 ==="
sed "s# -o strata # -o /tmp/strata_ok #g" /tmp/link.txt > /tmp/link_ok.txt
rm -f /tmp/strata_ok
bash /tmp/link_ok.txt > /tmp/link_ok.log 2>&1
echo "  ctrl_rc=$?"
ls -la /tmp/strata_ok 2>/dev/null | tail -1

rm -f /tmp/m_noh5.a /tmp/strata_noh5 /tmp/strata_ok /tmp/link.txt /tmp/link_noh5.txt /tmp/link_ok.txt /tmp/link_noh5.log /tmp/link_ok.log /tmp/allcmd.txt
echo "  cleaned"
'
