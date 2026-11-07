# -*- coding: utf-8 -*-
"""0.1.48 在 gfx906 上的兼容缺口：src/core/dflash2.cpp 用 STRATA_USE_HIP 判 CUDA/HIP 分支，
而 gfx906 构建只定义 STRATA_HIP_GFX906（CMakeLists.txt:78 明说两者是 separate backends）。
=> 编译报 cudaDeviceGetStreamPriorityRange / cudaStreamCreateWithPriority 未声明。
修法：**只给该文件**加 STRATA_USE_HIP=1（全局加会把 CUDA-only 路径误开，W717/P23 已实测过这个坑）。
fail-closed：anchor 必须唯一命中。
"""
import subprocess, base64

HOST = "albus@192.168.50.166"
CM = "/home/albus/strata166/build023/src/CMakeLists.txt"

ANCHOR = "    src/core/arch_defaults.cpp src/core/nv_defaults.cpp src/core/vmm.cpp src/core/conversation_file.cpp)\n"

PATCH = ANCHOR + (
    "\n"
    "  # [W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp keys its\n"
    "  # CUDA-vs-HIP branches on it (stream priority + the fork default). Scope the definition to that one\n"
    "  # file: a global STRATA_USE_HIP would switch CUDA-only paths elsewhere (W717/P23 measured that).\n"
    "  if(STRATA_HIP_GFX906)\n"
    "    set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS \"STRATA_USE_HIP=1\")\n"
    "  endif()\n"
)

SH = r'''
set -e
python3 - <<'PY'
import io
p = "%s"
a = %r
patch = %r
s = io.open(p, encoding="utf-8").read()
n = s.count(a)
print("anchor hits:", n)
if n != 1:
    raise SystemExit("FAIL-CLOSED: anchor hits %%d" %% n)
if "STRATA_USE_HIP=1" in s:
    print("already patched, skip")
else:
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(a, patch, 1))
    print("patched")
PY
grep -n "STRATA_USE_HIP=1" %s
''' % (CM, ANCHOR, PATCH, CM)

p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                   input=base64.b64encode(SH.encode()).decode("ascii").encode("ascii"),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
print(p.stdout.decode("utf-8", "replace"))
