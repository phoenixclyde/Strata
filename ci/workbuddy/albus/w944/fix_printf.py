# -*- coding: utf-8 -*-
p = "D:/workbuddy_space/strata_ws/albus/w941/kq_bench.cpp"
s = open(p, encoding="utf-8").read()
old = 'std::printf("shape: type=Q4_K w=[%lld,%lld] n=%d rows/expert=%d total_rows=%d expert_bytes=%zu reps=%d\\n",'
new = 'std::printf("shape: type=%d w=[%lld,%lld] n=%d rows/expert=%d total_rows=%d expert_bytes=%zu reps=%d\\n", tcode,'
assert old in s, "pattern not found"
s = s.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched ok")
