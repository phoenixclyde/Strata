# bundle_budget — why the 5% gate stopped being an item gate (W1013)

The plan's adoption rule for prefill work is a measured `>= 5%` at 2K tokens. That rule was
written when the card still had 8-40% items in it. It does not have any left: every candidate
that survived the audits measures 2-3% of prefill, and every one of them was rejected by a
threshold it could have passed *together with two others*.

This directory is the arithmetic that replaces the per-item reading of the rule:

* `BUNDLE.tsv` — one row per candidate: its phase, that phase's measured 2K cost, the measured
  delta of that phase, and whether the delta is measured (`bench`) or arithmetic on a mechanism
  nobody has measured yet (`estimate`).
* `bundle.py` — re-derives every share from `ci/prefill_phases/PREFILL_PHASES.tsv`, refuses a
  typed `phase_ms`, refuses a `bench` delta inside 2x its own CV, and refuses an `ADOPT` row (or
  a bundle) whose measured sum does not reach the gate. Estimates never count toward the gate.

```
python3 ci/bundle_budget/bundle.py              # report: measured sum, estimates, distance to -5%
python3 ci/bundle_budget/bundle.py --check      # same, non-zero exit on any of the above
python3 ci/bundle_budget/bundle.py --self-test  # 6 planted defects, all must fail
```

## Where the rule stands (2026-11-05, W1013)

| row | phase (2K) | delta | of prefill | basis |
|---|---|---:|---:|---|
| R86-dn down-only repack | gemm down 510 ms | -20.0% | **-3.20%** | bench (`WIDTH_SWEEP.tsv`) |
| R95-plan plan build on the issuer thread | host grouping 91 ms | -100% | -2.85% | estimate |
| R21-v3hc v3 read on int8 codes | hc read: down+silu 117 ms | -40% | -1.47% | estimate |
| GDN-chunk chunked recurrence | gdn recurrence 121 ms | -50% | -1.90% | estimate |
| R98-wc wait-copy depth | wait copy 37 ms | -50% | -0.58% | estimate |

Measured sum **0.00%** — nothing is adopted yet. Everything on the table together is **-9.99%**,
which is the number that says the queue is not out of physics, it is out of *single* items.

The rule this file enforces, and the one the plan now states:

> A bundle may be adopted on its sum (`<= -5%` of prefill@2K). Every item in it still has to
> clear 2x its own CV on its own phase. Any item that changes rounding needs one quality run
> (`Q:` row) for the bundle, not one per item. An estimate is a place in the queue, never a
> contribution to the sum.
