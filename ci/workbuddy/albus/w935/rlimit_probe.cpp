// W935: 复刻 ngram.cpp 的 RLIMIT_MEMLOCK 提限逻辑，用 prlimit 喂三种场景验证。
// 目的：验证 setrlimit(soft -> hard) 在内核层面可行（这是 5a13c34f 的前半段）。
#include <sys/mman.h>
#include <sys/resource.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cerrno>

static const char* fmt(rlim_t v) {
    static char buf[4][32];
    static int i = 0;
    if (v == RLIM_INFINITY) return "infinity";
    std::snprintf(buf[i & 3], 32, "%.1f MiB", (double) v / 1048576.0);
    return buf[(i++) & 3];
}

int main() {
    const size_t need = 512ull << 20;   // 512 MiB（不跑满 26.8 GiB，避免宿主内存压力）

    struct rlimit rl {};
    if (getrlimit(RLIMIT_MEMLOCK, &rl) != 0) { std::perror("getrlimit"); return 1; }
    std::printf("before: soft=%s hard=%s\n", fmt(rl.rlim_cur), fmt(rl.rlim_max));

    // ---- 5a13c34f 的前半段（逐字复刻）----
    if (rl.rlim_cur != RLIM_INFINITY && (uint64_t) rl.rlim_cur < need && rl.rlim_max > rl.rlim_cur) {
        const rlim_t room = (rlim_t) need + ((rlim_t) 1 << 30);
        const rlim_t want = rl.rlim_max == RLIM_INFINITY ? room : (rl.rlim_max < room ? rl.rlim_max : room);
        struct rlimit up = rl;
        up.rlim_cur = want;
        if (setrlimit(RLIMIT_MEMLOCK, &up) == 0)
            std::printf("raised: soft %s -> %s\n", fmt(rl.rlim_cur), fmt(want));
        else
            std::printf("raise FAILED: %s\n", std::strerror(errno));
    } else {
        std::printf("no raise needed/possible (cond: cur<need=%d, max>cur=%d)\n",
                    (int)(rl.rlim_cur < need), (int)(rl.rlim_max > rl.rlim_cur));
    }

    struct rlimit now {};
    getrlimit(RLIMIT_MEMLOCK, &now);
    std::printf("after : soft=%s hard=%s\n", fmt(now.rlim_cur), fmt(now.rlim_max));

    // ---- 真的 mlock 512 MiB ----
    void* p = mmap(nullptr, need, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { std::perror("mmap"); return 1; }
    std::memset(p, 1, need);            // fault in
    const int rc = mlock(p, need);
    std::printf("mlock(512 MiB) -> %s\n", rc == 0 ? "OK" : std::strerror(errno));
    if (rc == 0) munlock(p, need);
    munmap(p, need);
    return rc == 0 ? 0 : 2;
}
