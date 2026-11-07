import io

p = ".workbuddy/memory/2026-11-07.md"
s = io.open(p, encoding="utf-8").read()
bad = "- ** 相位逐毫秒不变**（578.3→577.3；2237.5→2241.0）⇒ 改的代码没在跑。查 ：预填派发顺序 ①gated → ②qsa_prompt_attn_batch → ③qsa_pattn_batch → ④**最后才**是 qsa_decode_attn_batch（注释\"the decode kernel\"）。我们的开关只改 ④。\n- **新落点 = **（2504 行、0 处 dp4a、fp32 fmaf at :353/:471/:725/:776）。PORT_PLAN §4 的「B2 落点=qsa_decode_attn，非 qsa_pattn」作废。"
good = ("- **`qsa attn` 相位逐毫秒不变**（578.3→577.3；2237.5→2241.0）⇒ 改的代码没在跑。查 `prefill.cpp:4398-4426`："
        "预填派发顺序 ①gated → ②qsa_prompt_attn_batch → ③qsa_pattn_batch → ④**最后才**是 qsa_decode_attn_batch"
        "（源码注释 \"the decode kernel, 32 queries at a time\"）。我们的开关只改 ④。\n"
        "- **新落点 = `qsa_prompt_attn.cu`**（2504 行、0 处 dp4a、fp32 fmaf at :353/:471/:725/:776）。"
        "PORT_PLAN §4 的「B2 落点=qsa_decode_attn，非 qsa_pattn」作废。")
assert bad in s, "anchor not found"
s = s.replace(bad, good, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("memory repaired")
