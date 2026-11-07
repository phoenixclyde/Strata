// W861: open hook -- 打印所有 TensileLibrary / Mapping / hsaco 的打开路径。
// 用途：TENSILE_DB 报 Unknown key hardwarePredicate，但磁盘上的库文件里确认没有该键，
// 必须知道引擎到底读了哪个 inode，而不是继续猜路径。
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int (*real_openat)(int, const char*, int, ...) = 0;
static int (*real_open)(const char*, int, ...) = 0;

static int interesting(const char* p) {
  return p && (strstr(p, "TensileLibrary") || strstr(p, "Mapping") || strstr(p, "hsaco"));
}

int openat(int dirfd, const char* path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) {
    va_list ap;
    va_start(ap, flags);
    mode = va_arg(ap, mode_t);
    va_end(ap);
  }
  if (interesting(path)) fprintf(stderr, "[OPEN] %s\n", path);
  if (!real_openat) real_openat = dlsym(RTLD_NEXT, "openat");
  return real_openat(dirfd, path, flags, mode);
}

int open(const char* path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) {
    va_list ap;
    va_start(ap, flags);
    mode = va_arg(ap, mode_t);
    va_end(ap);
  }
  if (interesting(path)) fprintf(stderr, "[OPEN] %s\n", path);
  if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
  return real_open(path, flags, mode);
}

int open64(const char* path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) {
    va_list ap;
    va_start(ap, flags);
    mode = va_arg(ap, mode_t);
    va_end(ap);
  }
  if (interesting(path)) fprintf(stderr, "[OPEN64] %s\n", path);
  return open(path, flags, mode);
}
