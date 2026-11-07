# -*- coding: utf-8 -*-
"""Patch cmake/strata_ggml_tq_overlay.cmake:
   1) anchor the ggml.h insertion on the enumerator NAME, not on '= 43,' (it is 44 on upstream 0.8.0);
   2) fail hard instead of silently disabling the overlay (STRATA_TQ_OVERLAY_SOFT=ON keeps the old behaviour).
Run on the build host: python3 fix_overlay.py <path-to-repo>
"""
import io, sys

repo = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/pr/strata-fork"
p = repo + "/cmake/strata_ggml_tq_overlay.cmake"
s = io.open(p, encoding="utf-8").read()

OLD_ANCHOR = '''  _tq_edit(_h BEFORE "        GGML_TYPE_COUNT   = 43,"
    "        GGML_TYPE_TQ2_T   = 144, // Agention trellis types (Strata overlay; the fork's ids)
        GGML_TYPE_TQK6    = 145,
        GGML_TYPE_TQK7    = 146,
        GGML_TYPE_TQP5    = 147, // Gyro-L pair trellis (the same fork's 147-149)
        GGML_TYPE_TQP6    = 148,
        GGML_TYPE_TQP7    = 149,
")'''

NEW_ANCHOR = '''  # The enum count moves with every new ggml type (43 on 0.4.1 / e6ab7c1a4, 44 on 0.8.0 / b12099): anchoring on
  # "= 43," silently disabled this overlay on 0.8.0 while configure still returned 0 (W955/AUDIT24).  Anchor on the
  # name and take whatever value upstream has.
  string(REGEX MATCH "([ \\t]*GGML_TYPE_COUNT[ \\t]*=[ \\t]*[0-9]+,)" _tq_cnt "${_h}")
  if(NOT _tq_cnt)
    set(_tq_fail "GGML_TYPE_COUNT enumerator not found in ggml.h")
  else()
    set(_tq_types "        GGML_TYPE_TQ2_T   = 144, // Agention trellis types (Strata overlay; the fork's ids)
        GGML_TYPE_TQK6    = 145,
        GGML_TYPE_TQK7    = 146,
        GGML_TYPE_TQP5    = 147, // Gyro-L pair trellis (the same fork's 147-149)
        GGML_TYPE_TQP6    = 148,
        GGML_TYPE_TQP7    = 149,
")
    string(REPLACE "${_tq_cnt}" "${_tq_types}${_tq_cnt}" _h "${_h}")
  endif()'''

OLD_FAIL = '''  if(_tq_fail)
    message(STATUS "trellis MMQ overlay off: ${_tq_fail}")
    return()
  endif()'''

NEW_FAIL = '''  if(_tq_fail)
    # Silent degradation is the defect this project keeps paying for (W955): a configure that returns 0 while a
    # requested feature is quietly dropped.  Fail unless the caller asked for the soft behaviour.
    if(STRATA_TQ_OVERLAY_SOFT)
      message(STATUS "trellis MMQ overlay off (STRATA_TQ_OVERLAY_SOFT=ON): ${_tq_fail}")
      return()
    endif()
    message(FATAL_ERROR "trellis MMQ overlay: ${_tq_fail}\\n"
                        "  fix the anchor above, or configure with -DSTRATA_MMQ_TQ_OVERLAY=OFF\\n"
                        "  (soft: -DSTRATA_TQ_OVERLAY_SOFT=ON)")
  endif()'''

n1 = s.count(OLD_ANCHOR)
n2 = s.count(OLD_FAIL)
if n1 and n2:
    s = s.replace(OLD_ANCHOR, NEW_ANCHOR, 1).replace(OLD_FAIL, NEW_FAIL, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
print("anchor", n1, "fail-block", n2)
