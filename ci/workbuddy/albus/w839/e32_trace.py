#!/usr/bin/env python3
# W839-32 给调用块加 trace（只在 STRATA_W839_TRACE=1 时打印）
import io, sys

OLD = ('        cudaDeviceProp ad{};\n'
       '        if (cudaGetDeviceProperties(&ad, 0) == cudaSuccess) {\n'
       '            bool all_igpu = ad.integrated != 0;   // a discrete MI50: false')

NEW = ('        cudaDeviceProp ad{};\n'
       '        const cudaError_t rc = cudaGetDeviceProperties(&ad, 0);\n'
       '        if (std::getenv("STRATA_W839_TRACE") != nullptr)\n'
       '            std::fprintf(stderr, "strata: [W839] device probe rc=%d name=%s\\n", (int) rc,\n'
       '                         rc == cudaSuccess ? ad.gcnArchName : "-");\n'
       '        if (rc == cudaSuccess) {\n'
       '            bool all_igpu = ad.integrated != 0;   // a discrete MI50: false')

for P in sys.argv[1:]:
    s = io.open(P, encoding="utf-8").read()
    if "STRATA_W839_TRACE" in s:
        print("already traced:", P); continue
    n = s.count(OLD)
    print("%s  pattern=%d" % (P, n))
    if n != 1:
        print("  skip (not unique)"); continue
    io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(OLD, NEW, 1))
    print("  traced")
