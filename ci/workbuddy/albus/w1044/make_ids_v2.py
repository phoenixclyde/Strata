#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1044: build a NON-REPEATING 32K ids set.

The first attempt repeated the 20K ids to 32768; the model then predicted the
next token with top1=1.000000 / entropy=0 at 32K, so every arm's KL collapsed to
~1e-8 and the G3 ratio became noise. Fix: keep the first 20000 ids EXACTLY the
same as set20k (so 1K/8K/20K still reproduce W1041/W1042), then append 12768
ids tokenized from a DIFFERENT source (kernel .cu/.cpp text).

Run inside the strata container:
  docker run --rm -v $W:/w -v $S/data:/data $IMG python3 /w/make_ids_v2.py
"""
import io
import json
import pathlib
import sys

sys.path.insert(0, "/w")
import strata_tokenizer as ST  # noqa: E402

W = pathlib.Path("/w")
TP = pathlib.Path("/data/packs/ud-q4_k_xl/tokenizer")
N = 32768

vocab = json.loads((TP / "vocab.json").read_text())
toks = [None] * len(vocab)
for t, i in vocab.items():
    toks[i] = t
tok = ST.Tokenizer(toks, (TP / "merges.txt").read_text().split("\n"),
                   json.loads((TP / "token_type.json").read_text()))

old = json.loads((W / "set32k.ids.json").read_text())
base = old["segments"][0]["ids"][:20000]
assert len(base) == 20000

text = (W / "longsrc.txt").read_text(encoding="utf-8", errors="replace")
new_ids = tok.encode(text, parse_special=False)
print("new source chars=%d tokens=%d" % (len(text), len(new_ids)))
assert len(new_ids) >= N - 20000, "longsrc.txt too short: %d" % len(new_ids)
tail = list(new_ids[:N - 20000])
# a genuinely different tail: not the periodic repeat of the first 12768
assert tail != base[:len(tail)], "tail still equals the repeat"

ids = base + tail
assert len(ids) == N
out = {"version": "w1044-v2-nonrepeat", "seg_tokens": N,
       "vocab_size": old.get("vocab_size"),
       "segments": [{"name": "long", "ids": ids}],
       "note": "first 20000 ids identical to W1041 set20k; last 12768 tokenized from build022 kernel sources (non-repeating)"}
(W / "set32k_v2.ids.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print("wrote set32k_v2.ids.json: %d ids, first20k_same=%s, tail_first8=%s"
      % (len(ids), ids[:20000] == base, tail[:8]))
