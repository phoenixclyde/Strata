set +e
D=/home/albus/strata166/gfx029
echo "===== [A] gfx029/bin/strata 是什么 ====="
ls -l --time-style=+%m-%d_%H:%M "$D/bin/strata" 2>/dev/null
git -C "$D" ls-files bin/strata | head -2
echo "--- 它是不是 git 跟踪的上游文件:"; git -C "$D" status --porcelain bin/strata | head -2
echo "===== [B] 0.1.55 引擎是否已支持 BCO（serve 0.2.9 的 COALESCE 依赖它） ====="
grep -c "BCO" "$D/src/program/generate.cpp" 2>/dev/null
grep -n "BCO" "$D/src/program/generate.cpp" 2>/dev/null | head -6
echo "--- serve 0.2.8（容器里那份）有没有 COALESCE/PAR_COUNTERS:"
grep -c "COALESCE_PREFILL\|PAR_COUNTERS" "$D/serve/server.py"
echo "===== [C] 0.2.8p2 镜像怎么建的（找最近的构建脚本/上下文） ====="
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/ | head -14
echo "--- 今天 10:4x 前后被改的文件:"
find /home/albus/strata166 -maxdepth 2 -newermt "2026-10-31 09:30" ! -newermt "2026-10-31 11:00" -type f 2>/dev/null | grep -vE "data/|\.git/|build-" | head -15
echo "===== [D] src028 里是否有 Dockerfile（0.2.8 树的） ====="
ls -l /home/albus/strata166/src028/Dockerfile 2>/dev/null
grep -n "^COPY\|^ADD" /home/albus/strata166/src028/Dockerfile 2>/dev/null | head -8
