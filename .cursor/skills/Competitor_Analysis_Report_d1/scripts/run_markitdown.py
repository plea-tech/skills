#!/usr/bin/env python3
"""
在 Python 3.13+ 下运行 markitdown 的包装脚本（标准库 aifc 已移除，其依赖会报错）。
Python 3.12 及以下保留标准库 aifc，不注入占位模块。
用法与 python -m markitdown 相同，例如：
  python run_markitdown.py path-to-file.pptx
  python run_markitdown.py path-to-file.pptx -o output.md
"""
import runpy
import sys
import traceback

# 仅 Python 3.13+ 中 aifc 已从标准库移除，需用空模块占位；3.12 及以下勿替换，否则会破坏依赖 aifc 的代码
if sys.version_info >= (3, 13) and "aifc" not in sys.modules:
    sys.modules["aifc"] = type(sys)("aifc")

# 使 argv 与「python -m markitdown」一致（argv[0] 为 markitdown）
if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
    sys.argv = ["markitdown", sys.argv[1]] + sys.argv[2:]
else:
    sys.argv = ["markitdown"] + sys.argv[1:]

try:
    runpy.run_module("markitdown", run_name="__main__")
except Exception:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
