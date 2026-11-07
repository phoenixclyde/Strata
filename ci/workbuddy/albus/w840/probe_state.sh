set +e
echo "=== state_q.py ==="
python3 /home/albus/strata166/tmp/state_q.py 2>&1
echo "=== rc_state=$? ==="
echo "=== verify_patches.sh ==="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1
echo "=== rc_verify=$? ==="
