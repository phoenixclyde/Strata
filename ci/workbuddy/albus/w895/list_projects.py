import re
from collections import Counter
from pathlib import Path

text = Path(r"D:/workbuddy_space/strata_ws/albus/w893/conversation.txt").read_text(encoding="utf-8")
patterns = [
    r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b",
    r"\b(NInfer(?:-[A-Za-z0-9]+)?)\b",
    r"\b(DeepInfer|deepseek-recipe|llama\.cpp|vLLM|SGLang|TensorRT-LLM|hipfire|Strata|Avalon)\b",
]
c = Counter()
for pat in patterns:
    for m in re.finditer(pat, text, re.IGNORECASE if "NInfer" in pat else 0):
        s = m.group(1)
        if "/" in s and ("." in s.split("/")[1] or s.split("/")[1] in {"cpp", "cpp-gfx906", "ninfer", "Strata", "hipfire"}):
            c[s] += 1
        elif "/" not in s:
            c[s] += 1
for k, v in c.most_common():
    print(f"{v:3} {k}")
