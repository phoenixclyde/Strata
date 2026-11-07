#!/bin/bash
echo "=== stray dir from my bad push (check before touching) ==="
find "/home/albus/D:" -maxdepth 6 2>/dev/null | head -10
echo "=== w862_prod contents ==="
ls -la /home/albus/w862_prod/
echo "=== earlier A/B output (format + numbers) ==="
cat /home/albus/w862_prod2.out
