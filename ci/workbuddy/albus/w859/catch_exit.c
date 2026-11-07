// W859：拦 exit() 打调用栈（容器里没 gdb）。LD_PRELOAD 这个 .so 即可。
#define _GNU_SOURCE
#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void exit(int code) {
    void* bt[40];
    int n = backtrace(bt, 40);
    fprintf(stderr, "=== exit(%d) caught, backtrace ===\n", code);
    backtrace_symbols_fd(bt, n, 2);
    fflush(stderr);
    _exit(code);
}
