"""Send files/dirs to the Windows Recycle Bin (never permanent delete).

Usage: python recycle.py <path> [<path> ...]
Rule: 本机删除一律进回收站，回收站由机主自己清。
"""
import ctypes
import os
import sys
from ctypes import wintypes

FO_DELETE = 0x0003
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def recycle(paths):
    ok, bad = [], []
    for p in paths:
        ap = os.path.abspath(p)
        if not os.path.exists(ap):
            bad.append((p, "not found"))
            continue
        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = ap + "\0\0"          # double-NUL terminated list
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if rc == 0 and not op.fAnyOperationsAborted:
            ok.append(ap)
        else:
            bad.append((p, "rc=%d aborted=%d" % (rc, op.fAnyOperationsAborted)))
    return ok, bad


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: recycle.py <path> [...]")
        sys.exit(2)
    ok, bad = recycle(args)
    for p in ok:
        print("recycled  " + p)
    for p, why in bad:
        print("FAILED    %s  (%s)" % (p, why))
    sys.exit(0 if not bad else 1)
