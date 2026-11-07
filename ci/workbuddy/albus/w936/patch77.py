#!/usr/bin/env python3
# W936: apply e1b27d54 to work/r77 generate.cpp (the only conflicting file)
# ASCII-only source. No curly quotes.
import io, sys, re

P = "/home/albus/strata166/work/r77/src/program/generate.cpp"
s = io.open(P, encoding="utf-8").read()
orig = s

BLOCK = '''// #4350: after a fatal GPU error (an illegal memory access, a launch failure) the device context cannot be used again, and unwinding the
// destructors on it can hang until the stall watchdog (#224).  A failed decode window / commit therefore ends the engine at once when the
// runtime holds a sticky error, with "ERR fatal GPU error: ..." as its last stdout line: the server fails the request in flight with a 503
// and starts the engine again on the next request, like any engine death.
// STRATA_INJECT_FATAL=N (a test hook, off when unset): the Nth decode window fails with the text of a real fatal error, the same way.
[[noreturn]] static void exit_gpu_fatal(const std::string& what) {
    std::fprintf(stderr, "strata serve: fatal GPU error (%s): the engine ends so that the server can start it again\\n", what.c_str());
    std::fflush(stderr);
    std::printf("ERR fatal GPU error: %s\\n", what.c_str());
    std::fflush(stdout);
    std::_Exit(3);
}
static void exit_if_gpu_fatal(const std::string& err) {
    static const long inject = [] { const char* v = std::getenv("STRATA_INJECT_FATAL"); return v != nullptr ? std::atol(v) : 0L; }();
    static long windows = 0;
    if (inject > 0 && ++windows == inject) {
        // STRATA_INJECT_FATAL_ONCE=<file>: fires once across restarts (the file is made when it fires; while it exists nothing is injected)
        const char* once = std::getenv("STRATA_INJECT_FATAL_ONCE");
        bool fire = true;
        if (once != nullptr && *once) {
            if (std::FILE* t = std::fopen(once, "rb")) { std::fclose(t); fire = false; }
            else if (std::FILE* t2 = std::fopen(once, "wb")) std::fclose(t2);
        }
        if (fire) exit_gpu_fatal("injected (STRATA_INJECT_FATAL): an illegal memory access was encountered");
    }
    const cudaError_t sticky = cudaPeekAtLastError();
    if (sticky != cudaSuccess) {
        // (by the runtime's own text, so that CUDA, HIP and SYCL builds read it the same way)
        const std::string text = cudaGetErrorString(sticky);
        static const char* const gone[] = {"illegal memory access", "illegal address", "unspecified launch failure", "launch failure",
                                           "hardware exception", "illegal instruction", "misaligned address", "uncorrectable", "launch timed out",
                                           "device-side assert"};
        bool context_gone = false;
        for (const char* w : gone)
            if (text.find(w) != std::string::npos) context_gone = true;
        if (context_gone) exit_gpu_fatal(err.empty() ? std::string(cudaGetErrorString(sticky)) : err);
    }
}

'''

# 1) insert the two functions right before int main(
anchor_main = "\nint main(int argc, char** argv) {\n"
n = s.count(anchor_main)
if n != 1:
    print("FAIL: int main anchor count =", n); sys.exit(1)
s = s.replace(anchor_main, "\n" + BLOCK + "int main(int argc, char** argv) {\n", 1)

# 2) decode window: hook before ver.run, fatal check inside
a2 = ('                const auto decode_pool_fn = use_mtp && mtp.prob() ? invariant_win_pool_fn : win_pool_fn;\n'
      '                if (!ver.run(T, window.data(), p, decode_pool_fn, win_pool_user, outv.data(), err) || drive.d.failed) {\n'
      '                    std::printf("ERR %s\\n", drive.d.failed && drive.d.fail ? drive.d.fail : err.c_str());\n')
b2 = ('                const auto decode_pool_fn = use_mtp && mtp.prob() ? invariant_win_pool_fn : win_pool_fn;\n'
      '                exit_if_gpu_fatal("");   // (the test hook counts windows here)\n'
      '                if (!ver.run(T, window.data(), p, decode_pool_fn, win_pool_user, outv.data(), err) || drive.d.failed) {\n'
      '                    exit_if_gpu_fatal(drive.d.failed && drive.d.fail ? drive.d.fail : err);\n'
      '                    std::printf("ERR %s\\n", drive.d.failed && drive.d.fail ? drive.d.fail : err.c_str());\n')
if s.count(a2) != 1:
    print("FAIL: ver.run site count =", s.count(a2)); sys.exit(2)
s = s.replace(a2, b2, 1)

# 3) commit failure
a3 = ('                if (!ver.commit(a + 1, err)) {\n'
      '                    if (adapt_thr.joinable()) adapt_thr.join();\n')
b3 = ('                if (!ver.commit(a + 1, err)) {\n'
      '                    exit_if_gpu_fatal(err);\n'
      '                    if (adapt_thr.joinable()) adapt_thr.join();\n')
if s.count(a3) != 1:
    print("FAIL: commit site count =", s.count(a3)); sys.exit(3)
s = s.replace(a3, b3, 1)

# 4) final commit wait (the one after decode_ms)
a4 = ('            // the last commit (set_commit_async): the session is complete before anything reads or copies it\n'
      '            if (!ver.wait_commit(err)) {\n'
      '                std::printf("ERR %s\\n", err.c_str());\n')
b4 = ('            // the last commit (set_commit_async): the session is complete before anything reads or copies it\n'
      '            if (!ver.wait_commit(err)) {\n'
      '                exit_if_gpu_fatal(err);\n'
      '                std::printf("ERR %s\\n", err.c_str());\n')
if s.count(a4) != 1:
    print("FAIL: wait_commit site count =", s.count(a4)); sys.exit(4)
s = s.replace(a4, b4, 1)

io.open(P, "w", encoding="utf-8").write(s)
print("OK: generate.cpp patched, +%d chars" % (len(s) - len(orig)))
print("  exit_if_gpu_fatal call sites =", s.count("exit_if_gpu_fatal(") - 1)  # minus the definition
