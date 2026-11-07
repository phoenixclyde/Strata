#!/bin/bash
# W837: does apply_arch_defaults("gfx906") actually set them, and does the banner say the right thing?
W=/home/albus/strata166/gfx906
IMG=strata-gfx906:0.2.8p2
docker run --rm --security-opt label=disable -v "$W":/src "$IMG" bash -lc '
  cd /src || exit 1
  cat > /tmp/probe.cpp <<EOF
#include "strata/core/arch_defaults.hpp"
#include <cstdio>
#include <cstdlib>
int main() {
    const char* cases[] = {"gfx906", "gfx906:sramecc-:xnack-"};
    for (const char* a : cases) {
        std::printf("--- apply_arch_defaults(%s) ---\n", a);
        auto v = strata::core::apply_arch_defaults(a);
        std::printf("  set %zu:\n", v.size());
        for (auto& k : v) std::printf("    %-38s = %s\n", k.c_str(), std::getenv(k.c_str()) ? std::getenv(k.c_str()) : "(unset)");
    }
    std::printf("--- with STRATA_GFX906_TUNED=1 ---\n");
    setenv("STRATA_GFX906_TUNED", "1", 1);
    // clear what the first pass set so the tuned set is visible on its own
    unsetenv("STRATA_GFX906_TUNED");
    setenv("STRATA_GFX906_TUNED", "1", 1);
    auto v2 = strata::core::gfx906_tuned_env("gfx906");
    std::printf("  tuned entries: %zu\n", v2.size());
    for (auto& kv : v2) std::printf("    %-38s = %s\n", kv.first.c_str(), kv.second.c_str());
    std::printf("--- a user setting must win ---\n");
    setenv("STRATA_GDN_HEAD", "0", 1);
    auto v3 = strata::core::apply_arch_defaults("gfx906");
    std::printf("  set %zu (GDN_HEAD should be absent), GDN_HEAD=%s\n", v3.size(), std::getenv("STRATA_GDN_HEAD"));
    return 0;
}
EOF
  g++ -std=c++17 -O1 -I include -o /tmp/probe /tmp/probe.cpp src/core/arch_defaults.cpp 2>&1 | head -12
  echo "compile rc=$?"
  /tmp/probe; echo "probe rc=$?"
' 2>&1 | tail -35
