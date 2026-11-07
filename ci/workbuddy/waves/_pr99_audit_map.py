import os, io, re

SRC = r"D:/strata166/tmp/src402/Strata-0.1.40.2"
H_W32 = os.path.join(SRC, "include", "strata", "hip_compat", "cuda_runtime.h")
H_906 = os.path.join(SRC, "include", "strata", "platform", "hip_compat", "strata_hip.h")

def defines(path):
    s = io.open(path, encoding="utf-8", errors="replace").read()
    d = {}
    for m in re.finditer(r"^\s*#define\s+(cuda[A-Za-z0-9_]+)\s+(.+?)\s*$", s, re.M):
        d[m.group(1)] = m.group(2)
    return d, s

A, sa = defines(H_W32)      # wave32 头（对照基准）
B, sb = defines(H_906)      # gfx906 头（待补）

print("=== [1] 两个头的 cuda* 映射数 ===")
print("  wave32  cuda_runtime.h      : %d 个 define" % len(A))
print("  gfx906  strata_hip.h        : %d 个 define" % len(B))

missing = sorted(set(A) - set(B))
print()
print("=== [2] wave32 有、gfx906 缺的（候选 %d 个）===" % len(missing))
for k in missing:
    print("  %-44s -> %s" % (k, A[k][:60]))

print()
print("=== [3] 扫全树，看这些候选哪些真的被用到 ===")
used = {}
EXCL = ("sycl", "hip_compat", "third_party", "tests")
for dp, dn, fn in os.walk(SRC):
    rel_d = os.path.relpath(dp, SRC).replace("\\", "/")
    if any(x in rel_d for x in EXCL):
        continue
    for f in fn:
        if not f.endswith((".cu", ".cuh", ".cpp", ".h", ".hpp")):
            continue
        fp = os.path.join(dp, f)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for k in missing:
            # 词边界匹配
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])", s):
                rel = os.path.relpath(fp, SRC).replace("\\", "/")
                for i, l in enumerate(s.split("\n")):
                    if re.search(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])", l):
                        used.setdefault(k, []).append((rel, i + 1, l.strip()[:100]))

print()
print("=== [4] 结论：必须补的映射 ===")
need = []
for k in missing:
    if k in used:
        need.append(k)
        print("  [!] %-40s 被用到（%d 处）" % (k, len(used[k])))
        for rel, ln, txt in used[k][:3]:
            print("        %-44s :%-5d %s" % (rel, ln, txt))
    else:
        print("  [ ] %-40s 未被使用（可不补）" % k)

print()
print("=== [5] 最终待补清单 ===")
print("  NEED =", need)
