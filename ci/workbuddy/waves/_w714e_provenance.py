# 定真相：① 扫 GGUF 头部元数据找发布者痕迹（本机 D: 那份，10.9 MB 小片） ② 翻我们工作区当初的下载记录
import io, os, re, glob

D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
print("=== ① GGUF 头（前 4 MB）里的可打印串，含关键词的行 ===")
raw = open(D, "rb").read(4 << 20)
print("  magic:", raw[:4], " version:", int.from_bytes(raw[4:8], "little"))
s = raw.decode("latin-1")
pat = re.compile(r"[ -~]{4,200}")
keys = ["huihui", "abliterat", "uncensored", "Uncensored", "unsloth", "Unsloth", "general.name",
        "general.basename", "general.finetune", "general.architecture", "quantized_by", "license",
        "Qwen3.8-Flash-Next", "repository", "url"]
seen = set()
for m in pat.finditer(s):
    t = m.group(0)
    if any(k.lower() in t.lower() for k in keys) and t not in seen:
        seen.add(t)
        print("   ", t[:180])
        if len(seen) > 40:
            break

print()
print("=== ② 工作区里当初下载/推送权重的记录 ===")
WS = r"D:/workbuddy_space/strata_ws"
cands = []
for pat2 in ["deploy/logs/_dl_*.txt", "deploy/logs/_push_*.txt", "waves/_dl*.py", "waves/_push*.py",
             "deploy/scripts/_dl*.py", "deploy/scripts/_push*.py", "waves/_w*.py", "deploy/logs/*.txt"]:
    cands += glob.glob(os.path.join(WS, pat2))
hits = 0
for p in sorted(set(cands)):
    try:
        t = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if re.search(r"huggingface|hf-mirror|modelscope|civitai|hf\.co|/resolve/|wget|curl .*gguf|blob/main", t, re.I):
        print("---- %s (%d B)" % (os.path.relpath(p, WS), len(t)))
        for ln in t.splitlines():
            if re.search(r"https?://\S*(gguf|huggingface|modelscope|hf-mirror)\S*", ln, re.I):
                print("     ", ln.strip()[:190]); hits += 1
            if hits > 25:
                break
    if hits > 25:
        break
print("(下载 URL 命中 %d 条)" % hits)
