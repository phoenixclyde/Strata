"""Print the exact argv `quant_quality.py prompt` would launch, without starting an engine.

Run inside the image:  python3 /w1035/show_args.py 001 010
"""
import json
import sys

sys.path.insert(0, "/src/tools")
import quant_quality as QQ  # noqa: E402

for tag in sys.argv[1:]:
    cfg = json.load(open("/w1035/qq_%s.json" % tag, encoding="utf-8-sig"))
    st = json.load(open("/src/data/quant_quality/v1/set.ids.json"))
    a = QQ.engine_args(cfg, True, max(QQ.PROMPT_LENS))
    k = a.index("--short-read")
    del a[k:k + 2]
    k = a.index("--prefill")
    a[k + 1] = "auto"
    print("%s LENS=%s seg_tokens=%d segments=%d" % (tag, QQ.PROMPT_LENS, st["seg_tokens"], len(st["segments"])))
    print("%s ARGV: %s" % (tag, " ".join(a)))
    print("%s ENV : FIXED=%s" % (tag, QQ.FIXED_ENV))
    print("%s cfgenv: %s" % (tag, json.dumps(cfg.get("env", {}), ensure_ascii=False)))
