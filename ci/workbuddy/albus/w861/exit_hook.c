// W861: exit hook -- 抓"谁在 exit"并打 backtrace。
// comgr 的 JIT 失败后走 exit(EXIT_FAILURE)，进程不是崩溃，gdb 默认抓不到。
#define _GNU_SOURCE
#include <dlfcn.h>
#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>

static void dump(int status, const char* who) {
  void* bt[48];
  int n = backtrace(bt, 48);
  fprintf(stderr, "\n=== W861 %s(%d) caught ===\n", who, status);
  fflush(stderr);
  backtrace_symbols_fd(bt, n, 2);
  fflush(stderr);
}

void exit(int status) {
  dump(status, "exit");
  syscall(SYS_exit_group, status);
  __builtin_unreachable();
}

void _exit(int status) {
  dump(status, "_exit");
  syscall(SYS_exit_group, status);
  __builtin_unreachable();
}
