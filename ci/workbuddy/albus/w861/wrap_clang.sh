#!/bin/bash
# W861: clang wrapper -- 吃掉 clang 24 已删除的两个 -cc1 参数，其余原样透传。
# 规则：`-mllvm X` 成对出现；若 X 是 --amdhsa-code-object-version=* 或 -amdgpu-prelink，整对丢弃
#       （这两个在 code object v5 下本来就是默认行为）；其它 -mllvm 对保留。
set -u
real=/opt/rocm/llvm/bin/clang
# 留痕：证明 comgr 到底有没有走 PATH 找 clang
{ printf '%s ARGV: %s\n' "$(date +%s.%N)" "$*" >> /tmp/wrap_clang.log; } 2>/dev/null || true

out=()
skip_next=0
for a in "$@"; do
  if [ "$skip_next" = "1" ]; then
    skip_next=0
    case "$a" in
      --amdhsa-code-object-version=*|-amdgpu-prelink)
        continue
        ;;
      *)
        out+=("-mllvm")
        out+=("$a")
        continue
        ;;
    esac
  fi
  case "$a" in
    -mllvm)
      skip_next=1
      continue
      ;;
    --amdhsa-code-object-version=*|-amdgpu-prelink)
      continue
      ;;
  esac
  out+=("$a")
done
[ "$skip_next" = "1" ] && out+=("-mllvm")
exec "$real" "${out[@]}"
