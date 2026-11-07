cd /home/albus/strata166/data/w828kl
echo "=== md5 + lines ==="
md5sum E0r.tsv E0br.tsv Eallr.tsv 2>/dev/null
wc -l E0r.tsv E0br.tsv Eallr.tsv 2>/dev/null
echo
echo "=== KL (kl_prop, kl_pair2 口径) ==="
python3 /home/albus/strata166/tmp/kl_cmp3.py /home/albus/strata166/data/w828kl E0r E0br Eallr 2>&1 | tail -12
