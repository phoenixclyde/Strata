echo "--- third_party ---"
ls /home/albus/strata166/src028/third_party/ 2>/dev/null
echo "--- llamacpp dir ---"
ls /home/albus/strata166/src028/third_party/llama.cpp 2>/dev/null | head -12
echo "count: $(find /home/albus/strata166/src028/third_party/llama.cpp -maxdepth 1 | wc -l)"
du -sh /home/albus/strata166/src028/third_party/llama.cpp 2>/dev/null
echo "--- ggml present? ---"
ls /home/albus/strata166/src028/third_party/llama.cpp/ggml 2>/dev/null | head -5
echo "--- cmake line 1930-1945 ---"
sed -n '1930,1945p' /home/albus/strata166/src028/CMakeLists.txt
