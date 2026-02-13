#!/usr/bin/env python3
"""
Step 3 迭代1（分段撰写时）：将 sections/ 下的小节 Markdown 按文件名顺序合并为 report_draft.md。
小节文件命名建议带序号以控制顺序，如 01_公司概况.md、02_1.1_行业位置.md、10_2.1_架构分析.md。
"""
import argparse
import re
from pathlib import Path


def _natural_sort_key(name: str):
    """用于文件名的自然排序，使 2.1_xxx.md 在 2.10_xxx.md 前。"""
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts if p]


def main():
    parser = argparse.ArgumentParser(
        description="将 sections/ 下的小节 .md 按文件名顺序合并为 report_draft.md"
    )
    parser.add_argument(
        "--sections-dir",
        type=Path,
        default=None,
        help="小节所在目录（默认 extracted_content/<竞品>/sections）",
    )
    parser.add_argument(
        "--extracted-dir",
        type=Path,
        default=None,
        help="竞品抽取根目录（如 extracted_content/Inspur），与 --sections-dir 二选一；指定时小节目录为 <extracted-dir>/sections",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="合并输出路径（默认 <sections 父目录>/report_draft.md）",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="读写编码，默认 utf-8",
    )
    args = parser.parse_args()

    if args.sections_dir is not None:
        sections_dir = args.sections_dir.resolve()
    elif args.extracted_dir is not None:
        sections_dir = (args.extracted_dir.resolve() / "sections")
    else:
        raise SystemExit("请指定 --sections-dir 或 --extracted-dir")

    if not sections_dir.is_dir():
        raise SystemExit(f"小节目录不存在: {sections_dir}")

    md_files = sorted(
        [f for f in sections_dir.iterdir() if f.suffix.lower() == ".md" and f.is_file()],
        key=lambda f: _natural_sort_key(f.name),
    )
    if not md_files:
        raise SystemExit(f"未找到 .md 文件: {sections_dir}")

    if args.output is not None:
        out_path = args.output.resolve()
    else:
        out_path = sections_dir.parent / "report_draft.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    for f in md_files:
        text = f.read_text(encoding=args.encoding)
        parts.append(text.rstrip())
    out_path.write_text("\n\n".join(parts) + "\n", encoding=args.encoding)
    print(f"已合并 {len(md_files)} 个小节 -> {out_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
