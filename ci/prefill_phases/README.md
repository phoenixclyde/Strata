# prefill_phases — the prompt path's phase table, and the numbers R95 quotes

`STRATA_PREFILL_TIMING=1` has the engine print 26 GPU phases per prompt. Everything the tuning
plan says about "where the 2K penalty is" comes from that print, and for five rounds it came from
**one** 2056-token line and **one** 15757-token line of a log that spans a dozen builds.

W1005 replaced both: `w1005_probe.py` asks for three lengths against the running service with
unique prompts (so nothing is a prefix of anything), three times each, and `phases.py --raw`
turns the lines that run appended into `PREFILL_PHASES.tsv`.

## What the old numbers got wrong

| claim (W990, five rounds) | measured now (2K, n=3) | why it moved |
|---|---|---|
| gemm gate/up 1.91× | **1.57×** | 2056 tokens against 15757 was a 1.19× longer prompt than the current 2K sample and came from an older path |
| gemm down 1.87× | **1.52×** | same |
| dequant 3.9× (266 ms) | **161 ms, and not per-token at all** | it is a per-chunk cost: 161 ms @2K, 525 @8K, 491 @16K. Normalising it by tokens turns a saturating cost into a fake penalty |
| wait copy 14× (170 ms) | **37 ms (1.2%)** | the issuer thread and the per-group gather landed after that line was written; the phase is now 5× smaller in absolute terms |

## What the phases actually are

- `dequant` is **not** dequantization. It is `mmq::gather_native_group` — the device-side scatter
  of every expert's blob into its position in the MMQ group buffer (`prefill.cpp:5543/5588/7005`,
  corrected once already in W993 and mis-quoted since).
- `wait copy` is the *exposed* wait on the last streamed copy of a group; the copies themselves
  run on a second stream under an issuer thread, so this number is what could not be hidden.
- `host grouping` is GPU idle while the host builds the group plan (91 ms at 2K, 2.9%).

## Gate

    python3 ci/prefill_phases/phases.py --check ci/prefill_phases/PREFILL_PHASES.tsv

Two things must hold, and both are checked against the **plan's** figures, not the other way
round: every row's phases must sum to its GPU timeline (±3%, the print rounds to whole ms), and
the ten values the plan quotes (`EXPECTED` in `phases.py`) must be what the table says. Change the
data without changing the plan and the gate fails; that is the point.

Negative self-tests (4/4 fail as intended): tamper `dequant` in the 2K cluster, break a row's sum,
delete the 16K cluster, inflate `gpu_ms`.

## Reproduce

    python3 ci/prefill_phases/w1005_probe.py --reps 3 --lengths 1735,6915,13824

The probe asks for 1735/6915/13824 because the word-based prompt builder overshoots by ~1.19×;
those requests land at 2084/8271/16375 tokens. The first request of a length is colder than the
rest (PLE page cache); the artefact keeps all three and the gate uses medians.
