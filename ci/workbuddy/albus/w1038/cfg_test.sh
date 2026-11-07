#!/bin/bash
# 在副本上验证 set_kv 的往返与语义
W=/home/albus/strata166/tmp/w1038
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
T=$W/cfg_test.json
cp -f "$CFG" "$T"
python3 - "$T" <<'PY'
import io, json, sys, hashlib
p = sys.argv[1]
d = json.load(io.open(p, encoding="utf-8-sig"))
print("keys:", sorted(d.keys()))
a = d["args"]
print("args n:", len(a), "| --kv at", a.index("--kv") if "--kv" in a else None)
i = a.index("--kv")
print("kv value element:", repr(a[i+1]))
print("exe:", d.get("exe"), "| port:", d.get("port"), "| model:", str(d.get("model"))[:60])
PY
echo "--- 原 md5: $(md5sum "$CFG" | cut -d' ' -f1)"
echo "--- 副本 md5: $(md5sum "$T" | cut -d' ' -f1)"
# 只改 kv 再改回，看 md5 是否回到原值（证明写法无损）
python3 - "$T" <<'PY'
import io, json, sys
p = sys.argv[1]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["args"][d["args"].index("--kv") + 1] = "int8"
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
PY
echo "--- 改 int8 后: $(md5sum "$T" | cut -d' ' -f1)"
grep -o '"--kv"[^]]*' "$T" | head -2
python3 - "$T" <<'PY'
import io, json, sys
p = sys.argv[1]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["args"][d["args"].index("--kv") + 1] = "k8v4"
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
PY
echo "--- 改回 k8v4: $(md5sum "$T" | cut -d' ' -f1)"
diff <(python3 -c "import json,io;print(json.dumps(json.load(io.open('$CFG',encoding='utf-8-sig')),sort_keys=True,ensure_ascii=False,indent=1))") \
     <(python3 -c "import json,io;print(json.dumps(json.load(io.open('$T',encoding='utf-8-sig')),sort_keys=True,ensure_ascii=False,indent=1))") \
  && echo "SEMANTIC-SAME"
