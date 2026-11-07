# C1 draft — ready to paste as a new issue

> Title: **[Engine] Greedy output is not reproducible: six identical requests to one server give three to five different answers**
>
> Template answers: Area = `[Engine]`; Desktop app/Terminal or source = **Docker**;
> Reproduction status = **Reproduced locally**; version = `0.2.4p4 (engine 0.1.49.2)`;
> hardware = **Radeon Instinct MI50 32 GB (gfx906) · 128 GB RAM · Ubuntu 22.04 · Docker**;
> model = **Qwen3.8-Flash-Next UD-IQ4_XS (huihui abliterated) · 262144 context · k8v4**

## What happened

`temperature 0` is greedy here (`serve/server.py` says an absent temperature keeps the engine's default,
which is greedy, and `temperature=0` is not forwarded; `generate.cpp` takes
`if (sp.greedy || sp.temperature <= 0.0f)`). Even so, **the same request sent repeatedly to the same
running server does not return the same text**, and the answers fall into a few distinct groups rather
than drifting smoothly.

Server: `--spec 4 --spec-min-p 0.70 --prefill auto --expert-cache auto (9873 slots) --pcie-frac 0.20
--max-context 262144 --kv k8v4`, no `--ple-io`, `--prompt-cache-every 8192`; every expert does not fit in
32 GB, so part of the routed experts run on the CPU.

I first saw this while checking that a flag change did not alter the answers (a byte-for-byte gate):
two starts of the *same* build and config disagreed with each other. The data below is from a single
running server, so it is not about startup.

## Smallest steps to reproduce

```bash
# one running server, nothing else in flight
for i in 1 2 3 4 5 6; do
  curl -s localhost:8090/v1/chat/completions -H 'Content-Type: application/json' \
    -d '{"model":"...","messages":[{"role":"user","content":"<the prompt>"}],
         "max_tokens":96,"temperature":0.0,"top_p":1.0,"reasoning_effort":"none"}' \
  | python3 -c 'import sys,json,hashlib;t=json.load(sys.stdin)["choices"][0]["message"]["content"];print(hashlib.sha256(t.encode()).hexdigest()[:32],len(t))'
done
```

**Run A (one server, 4 requests, max_tokens 96): 3 distinct answers**

| requests | sha256 (first 32) | chars |
|---|---|---|
| R0 | `075a93a6eec811c8f12c2ec274a59357` | 543 |
| R1 | `29000c578f44783743fbe376f2b84773` | 545 |
| R2 | `78663efe2f152204656b37f5d06dcfac` | 528 |
| R3 | `78663efe2f152204656b37f5d06dcfac` | 528 |

Pairwise common prefix: R0 vs the others **49 characters**, R1 vs R2/R3 295, R2 == R3 exactly.

**Run B (same server, later, 6 requests): 3 distinct answers, in three groups, not monotonic**

| group | requests | chars |
|---|---|---|
| A | R0 = R3 = R4 | 554 (identical) |
| B | R1 = R2 | 528 |
| C | R5 | 558 (189 shared with group A) |

So the text agrees for ~13 tokens, then the server settles into one of a few attractors; it does not
warm up into a single answer.

**Across starts**: two starts of the same build and config, three 200-token greedy completions each,
gave six different sha256 values, with different lengths (1171 / 1210 / 1169 characters on the first
start, 1140 / 1132 / 1183 on the second).

## What I ruled out

- **A different prompt path per start.** Every request in all three starts logs the same chunk
  (`strata trace: lent 191 slots for 256 tokens`), and the disagreement happens *within* one process.
- **The expert profile file.** The engine reads `/src/data/expert-profile.bin` from the image (same
  `24576 ranked pairs` every start); `/data/profiles/*-learned.bin` is only written at exit, never read.
- **`--spec 0`.** Cannot be tested: the engine refuses to start,
  `is a native (IQ) pack: it needs --native SHARD1, --spec T (T >= 2) and --prefill CHUNK`.
- **`STRATA_ROUTE_TAIL_SKIP`.** Setting it to 0 makes this *worse* (5 distinct answers in 6 requests),
  so the tail skip is not the source.
- **The CPU prompt share.** `STRATA_PREFILL_CPU_SHARE=auto` is the obvious suspect: it splits prompt work
  between the CPU and the GPU, and two runs of the same prompt do not produce the same prefill bytes
  (I measured that separately). But with `STRATA_PREFILL_CPU_SHARE=0` the disagreement stays: 4 distinct
  answers in 6 requests, then 3 in 4. So the share is one contributor at most, not the cause.

The remaining suspects are the ones I cannot switch off from the command line: the verify window's batch
shape (the number of accepted drafts varies per window) and which experts are resident in VRAM at that
moment (CPU vs GPU changes the reduction order). If an early near-tie is hit, those differences flip it.
**No command-line setting I can reach makes the six requests agree**, which is the part that matters for
users.

## Why it matters

1. Any user-level use that compares text (code generation, regression tests, "did my flag change the
   answer") is unreliable on this build.
2. It also means a byte-for-byte gate cannot be used to validate a numerical flag change, which is how I
   found it: I was trying to prove `--ple-io mmap/ram` does not change the answers and could not.
3. #4106 reports greedy disagreement against llama.cpp on v0.2.4 (5/24); within-Strata self-disagreement
   is a different and simpler observation, and it may be the same underlying cause.

## Question

Is this expected for a partially resident expert set? If yes, a line in the docs ("greedy is reproducible
only when the expert path is fixed; the same request may differ between runs") would save the next person
the same afternoon. If not, I can run `STRATA_LOGPOS` on both branches of a diverging pair and post the
per-position log-probs, which should show whether the first difference is a near-tie or a larger gap.

Logs and the two clients I used are available — say the word and I will attach them.
