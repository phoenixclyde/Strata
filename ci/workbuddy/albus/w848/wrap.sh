set +e
C=strata166-407
echo "===== wrapper 内容 ====="
docker exec "$C" cat /usr/local/bin/strata
echo
echo "===== 相关 env ====="
docker exec "$C" bash -lc 'env | grep -iE "^(PORT|STRATA_)" | sort'
