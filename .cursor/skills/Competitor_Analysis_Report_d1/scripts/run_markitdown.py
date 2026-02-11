#!/usr/bin/env python3
"""
在 Python 3.13+ 下运行 markitdown 的包装脚本（标准库 aifc 已移除，其依赖会报错）。
用法与 python -m markitdown 相同，例如：
  python run_markitdown.py path-to-file.pptx
  python run_markitdown.py path-to-file.pptx -o output.md
"""
import runpy
import sys

# 在导入 markitdown 及其依赖之前，用空模块占位 aifc，避免 RuntimeError
if "aifc" not in sys.modules:
    sys.modules["aifc"] = type(sys)("aifc")

# 使 argv 与「python -m markitdown」一致（argv[0] 为 markitdown）
if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
    sys.argv = ["markitdown", sys.argv[1]] + sys.argv[2:]
else:
    sys.argv = ["markitdown"] + sys.argv[1:]

runpy.run_module("markitdown", run_name="__main__")
