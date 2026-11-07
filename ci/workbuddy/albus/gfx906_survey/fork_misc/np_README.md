# strata-gfx906-overlay — AMD MI50 (gfx906) port overlay for Strata

An overlay distribution that brings the PolyStrata rich server (the full-featured
qwen35moe path of [Strata](https://github.com/Niko1221/Strata), MIT licensed) to
AMD Instinct MI50 accelerators under ROCm 6.3, where HIP support had never been
built upstream and ROCm 6.4 removed the gfx906 target entirely.

The port has been validated end-to-end on a MI50 16G card: 262K-token context,
KV `q8_0`, MTP speculative decoding with an independent draft model, pinned
expert residency, and a full quantization sweep — with all raw measurement
data published in [`results/`](results/).

Upstream: Strata (MIT, Copyright Niko1221 and the Strata contributors).
This overlay adds an HIP/CUDA compatibility layer and build/route switches;
all additions are MIT licensed by FasFox. See [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE).

## Repository layout

```
overlay/         complete replacement copies of every upstream file touched by
                 the port, plus the new include/strata/{hip_compat,
                 platform/hip_compat,kernels} headers; apply by copying over a
                 pristine Strata tree
diffs/           unified diffs against the pre-port state of the two files whose
                 pristine copies were retained (CMakeLists.txt, generate.cpp)
configs/         production config for MI50 16G (UD-Q4_K_M + independent MTP
                 draft, 262K context, KV q8_0, pinned expert residency via
                 --kv-whole) and the warm-start expert residency profile
scripts/         launch wrapper and the quantization benchmark suite
results/         raw measurement data of the full quantization sweep (all tiers,
                 per-case records included)
docs/            port notes, measurement methodology and results, and a
                 step-by-step Chinese usage guide
MANIFEST.sha256  checksums for every file in this distribution
```

## Why an overlay exists at all

Two upstream decisions kept gfx906 out:

1. `CMakeLists.txt` excludes the rich server target when `STRATA_HIP` is set
   (`AND NOT STRATA_HIP_GFX906`, three blocks near lines 2050/2073/2081);
2. the qwen35moe family router (`generate.cpp`) dispatches qwen35moe to a
   reduced side engine.

The port opens the switches, supplies an HIP/CUDA compatibility layer
(driver VMM shim, cublas mappings, fp16/intrinsics/math constants), rebuilds
the 18 MMQ kernels through `LANGUAGE HIP`, and excludes MXFP4 (Blackwell FP4
MMA-only path, absent on gfx906). Details in
[`docs/PORT-NOTES-gfx906.md`](docs/PORT-NOTES-gfx906.md).

## Requirements

| Component | Requirement | Notes |
|---|---|---|
| GPU | AMD Instinct MI50 / MI50 II 16G (gfx906) | the 16G variant is the validated target |
| ROCm | **6.3.x** | ROCm 6.4 removed the gfx906 target; do not use 6.4+ |
| Host memory | 32 GB recommended | KV preallocation (`--kv-whole`), checkpoints and conversation parking all live in host memory |
| Disk | ≥ 30 GB free | UD-Q4_K_M main file ≈ 21.5 GB + MTP draft ≈ 1.2 GB |
| OS | Linux, x86-64 | validated on an X99-class platform |

## Getting started on your own machine

Full step-by-step walkthrough (ROCm 6.3 install, model preparation including
a draft-layer integrity check for community GGUFs, config explanation,
launch, API usage, troubleshooting):
**[docs/USAGE.zh-CN.md](docs/USAGE.zh-CN.md)** (Chinese). Short version:

```bash
git clone https://github.com/Niko1221/Strata strata
cp -r overlay/* strata/                        # apply the overlay
sha256sum -c <(sed 's|overlay/|strata/|' MANIFEST.sha256)
cd strata
cmake -B build -DSTRATA_HIP=ON -DSTRATA_HIP_GFX906=ON <your usual flags>
cmake --build build -j$(nproc)                 # product: strata-poly-rich
# prepare the UD-Q4_K_M main file + MTP draft sidecar (USAGE §3), then:
python -m serve.server --engine strata --config <repo>/configs/occamy-main-q4.json --port 8099
```

## Production configuration

`configs/occamy-main-q4.json` is the config every published number was
measured with. Key flags:

| Flag group | Effect |
|---|---|
| `--kv q8_0 --kv-whole` | KV quantized to q8_0 and preallocated for the full window at load time; hot-expert residency becomes fixed and is never displaced by KV growth (the central rule of this deployment) |
| `--max-context 262144` | full 262K-token context window |
| `--threads 8` | physical core count, not SMT thread count (measured within ±4%) |
| `--stage-ahead 2048 --prompt-batch 1536` | prefill staging; see the staging ladder in [`docs/PERF.md`](docs/PERF.md) — `--prompt-batch 2048` was rejected (workspace ≈1.4 MiB/token would displace experts on a 16G card) |
| `--expert-profile configs/occamy-experts-q4.json` | warm-start expert residency: frequently routed experts are pinned into VRAM at load (~49%) |
| `--prompt-cache 24 --prompt-cache-every 4096` | in-memory checkpoints; returning to a previous conversation is fast |
| `--conversation-cache-slots 8 --conversation-cache-mib auto` | in-memory conversation parking; near-instant switching between sessions |

Paths in the config are relative placeholders — adapt them to your
installation layout. `scripts/launch-main.sh` shows the launch wrapper
(`ROCM_LIB` and `STRATA_ENGINE` environment variables).

## Benchmark suite (`scripts/quant-probe/`)

Four rooms, 85 tasks, all programmatically verified — no judge model involved:

- **GSM8K-30** — exact numeric match on the final answer;
- **HumanEval-20** — generated completions executed against the canonical tests;
- **IFEval-15** — verifiable instruction subset (10 check types: word counts,
  JSON format, casing, keyword presence/frequency, forbidden words,
  placeholders);
- **JSON-20** — four schemas over five fixed topics, structural validation.

Methodology: global seed 42 (every quantization tier draws the identical task
subset), greedy decoding (temperature 0), only the `content` channel is
scored. The reasoning budget is uncapped beyond the 8192-token floor; each
case records reasoning/content character counts and total generated tokens —
reasoning spend itself serves as a cross-quantization metric under the same
tokenizer.

The speed block (`measure.py`) measures: health/max-context, three
short-prompt rounds (256 new tokens, median reported, with draft chain
proposed/accepted), and a ≈14.7K-token long prompt (prefill tok/s, decode
tok/s, draft acceptance) read from server-side timings. `quant-block.sh`
runs health gate → speed → quality in one shot; `collect.py` aggregates
`results/` into a per-tag summary.

## Measured results (MI50 16G, 262K context)

### Quantization sweep

| Quant | Quality | Short decode | Hot-expert residency |
|---|---|---|---|
| Q2_K_XL | 82/85 | 78.5 tok/s | 10145/10496 (96%) |
| Q4_K_M | 84/85 | 65.5 tok/s | 5172/10496 (49%) |
| Q6_K | 83/85 | 20.9 tok/s (no draft) | 3842/10240 (37.5%) |

Quality deltas sit inside the sampling noise band; decode speed is the
selector. Q4_K_M is the production choice. On 16G the Q6_K tier has no
usable draft (memory famine — the staging fix that repairs prefill
displaces decode), and the honest undrafted number is 20.9 tok/s.

### Other measured points

| Metric | Value |
|---|---|
| Prefill (14.7K prompt, after staging tuning) | 814.6 tok/s |
| Full-window prefill (253K tokens) | 265 tok/s |
| Full-fill GPU duty cycle (67K-token prompt, fresh) | 83% busy, 481 tok/s |
| Real-traffic GPU duty cycle (231 s window) | 26% busy, no anomalous stalls |

### Raw data

[`results/`](results/) holds every raw JSON report of the sweep, including
per-case records, plus engine boot lines (format documented in
[`results/README.md`](results/README.md)). Methodology narrative and the
failure modes that shaped the current configuration (kv_grow cache squeeze,
Q6 draft famine, staging gaps) are in [`docs/PERF.md`](docs/PERF.md).

## Reproducing the benchmark

1. Build and serve the production config (above), then wait for
   `/health` to report loaded.
2. Prepare the three dataset files under `<repo>/data/` (not redistributed;
   fetch from the official sources):
   - `data/gsm8k_test.parquet.jsonl` — GSM8K test split exported to JSONL,
     one object per line with `question` and `answer` fields;
   - `data/HumanEval.jsonl.gz` — the original OpenAI HumanEval JSONL,
     gzipped;
   - `data/ifeval_data.jsonl` — IFEval rows with `prompt`,
     `instruction_id_list` and `kwargs` (the probe filters to the ten
     supported instruction types).
3. Run the block:

```bash
cd scripts/quant-probe
PORT=8099 ./quant-block.sh q4
python3 collect.py
```

## Known limitations

- **First request after idle is slower** — cold experts must be copied from
  host memory into VRAM. Structural; hot residency is pinned, so it happens
  once, after which latency is normal.
- **Load time (~100 s) is higher than other engines** — `--kv-whole`
  preallocates the full-window KV up front; a one-time cost traded for
  run-time stability.
- **Prefill shows a sawtooth** — cold-expert staging between batches.
  Measured duty cycle: 83% on large fills, 26% on small requests. Both are
  expected.
- **`--prompt-batch` must stay ≤ 1536** — the staging workspace costs
  ≈1.4 MiB/token; beyond that it displaces expert residency on a 16G card.

## License and attribution

- **Upstream Strata** — MIT License, Copyright Niko1221 and the Strata
  contributors. Complete replacement copies of upstream files under
  `overlay/` are redistributed under their original MIT license with their
  original copyright notices intact.
- **This overlay's additions** (`include/strata/hip_compat/**`,
  `include/strata/platform/hip_compat/**`, configs, scripts, docs) — MIT
  License, Copyright FasFox. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
- **Model weights are not distributed with this repository.** Weight files
  are referenced by name only and remain subject to their respective
  publishers' licenses.
