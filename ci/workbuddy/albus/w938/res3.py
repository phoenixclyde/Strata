#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W938: resolve rebase conflict 3 (d963c791, /data/strata-spec ladder).

Upstream restructured the block into S / S_mtp_wide / S_mtp_narrow / S_mtp / S_look and added
--draft auto.  Our commit mutates S and S_mtp from /data/strata-spec (bench only).

Resolution: keep upstream's structure, but read the override BEFORE the derived values so that
every value derived from S sees the overridden S (the old code computed S_mtp from the pre-override
S and then patched it, which no longer works once S has three derived companions).
"""
import io, re, sys

p = "/home/albus/strata166/work/rebase-trial/src/program/generate.cpp"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)
blocks = pat.findall(s)
print("conflict blocks:", len(blocks))
if len(blocks) != 1:
    print("unexpected"); sys.exit(2)
ours, theirs = blocks[0]
print("ours has S_look:", "S_look" in ours, " theirs has strata-spec:", "strata-spec" in theirs)

MERGED = '''        int S = o.spec;   // not const: /data/strata-spec may lower it for one request (bench only)
        // /data/strata-spec "<S> <mtp>" (bench only): both windows per request, so one process sweeps the ladder.
        // S is clamped to --spec, which sized every per-window buffer, the DraftPolicy and the captured graphs.
        // Read BEFORE the derived values: S_mtp_wide / S_mtp_narrow / S_look all follow S, so an override applied
        // afterwards would leave them on the old width.
        bool spec_override = false;
        int spec_mtp = 0;
        {
            std::error_code ec;
            if (std::filesystem::exists("/data/strata-spec", ec))
                if (std::FILE* f = std::fopen("/data/strata-spec", "r")) {
                    int a = 0, b = 0;
                    const int got = std::fscanf(f, "%d %d", &a, &b);
                    std::fclose(f);
                    if (got >= 1 && a >= 2 && a <= o.spec) {
                        S = a;
                        spec_override = true;
                        if (got >= 2 && b >= 2) spec_mtp = b;
                    }
                }
        }
        const int S_mtp_wide = o.mtp_max_t > 0 ? std::min(o.mtp_max_t, S) : S;   // the MTP's windows; suffixes go up to S
        // --draft auto: a request that drafts with the MTP layer has its own widest window (the MTP loses to itself above 4 on Blackwell), the DFlash2 requests S_mtp_wide
        const int S_mtp_narrow = o.draft_auto ? std::min(S_mtp_wide, std::max(2, o.draft_mtp_spec)) : S_mtp_wide;
        int S_mtp = (spec_override && spec_mtp > 0) ? std::min(spec_mtp, S) : S_mtp_wide;   // this request's (set when it starts)
        int S_look = S;   // --draft auto: the widest window a prompt-lookup draft may make for this request (the MTP requests keep the MTP's width, as without DFlash2)
        if (spec_override) { if (use_mtp) mtp.set_max_drafts(S_mtp - 1); }   // set, not just lower: an A/B may raise it
        else if (use_mtp && S_mtp < S) mtp.set_max_drafts(S_mtp - 1);
'''

s = pat.sub(lambda m: MERGED, s, count=1)
io.open(p, "w", encoding="utf-8").write(s)
print("markers left:", s.count("<<<<<<<"))
for k in ("spec_override", "S_mtp_wide", "S_mtp_narrow", "S_look", "strata-spec"):
    print("  %-14s %d" % (k, s.count(k)))
