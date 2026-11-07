set +e
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== 所有含 ms 的 strata serve 行，按前缀归类（取首样本） ==="
grep -a "strata serve:" $L | grep -aE "[0-9]+(\.[0-9]+)? ?ms" \
  | sed -E 's/^.*strata serve: //' \
  | sed -E 's/[0-9]+(\.[0-9]+)?/N/g' | sort | uniq -c | sort -rn | head -25
echo
echo "=== resident / expert tiers 样本 ==="
grep -a "strata serve: resident" $L | tail -2
grep -a "strata serve: expert tiers" $L | tail -2
echo
echo "=== adaptive tier 样本 ==="
grep -a "adaptive tier" $L | tail -3
echo
echo "=== spec depth 样本 ==="
grep -a "spec depth" $L | tail -2
echo
echo "=== verify 7 条全文 ==="
grep -a "strata serve: verify" $L | tail -3
