set +e
D=/home/albus/strata166/gfx029
echo "===== [1] gfx029/Dockerfile 全文 ====="
sed -n '1,110p' "$D/Dockerfile"
echo
echo "===== [2] 关键 ARG / stage / COPY ====="
grep -nE "^ARG|^FROM|^COPY|^RUN" "$D/Dockerfile" | head -40
echo
echo "===== [3] 0.2.8p2 怎么构建的 ====="
grep -rln "docker build" /home/albus/strata166 --include=*.sh 2>/dev/null | head -8
grep -rl "0\.2\.8p2" /home/albus/strata166 --include=*.sh 2>/dev/null | head -8
echo "--- 最近改的脚本:"
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/*.sh 2>/dev/null | head -6
echo
echo "===== [4] third_party / llama.cpp ====="
ls -d "$D/third_party"/* 2>/dev/null | head -8
ls -d /home/albus/strata166/src028/third_party/llama.cpp 2>/dev/null && du -sh /home/albus/strata166/src028/third_party/llama.cpp
