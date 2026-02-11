#!/usr/bin/env python3
"""
报告路径桩：根据规则生成报告文件名与完整路径，并确保 reports/ 目录存在。
Step 3 写 docx 前调用，保证输出路径和命名符合技能约定。
"""
import argparse
from datetime import date
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="生成竞品分析报告文件名与路径，并确保 reports 目录存在"
    )
    parser.add_argument(
        "--competitor",
        type=str,
        required=True,
        help="竞品名（用于文件名，如 Inspur）",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="报告日期，格式 YYYYMMDD；默认当天",
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=Path.cwd(),
        help="reports 所在根目录（默认当前目录），将创建 reports/ 于其下",
    )
    parser.add_argument(
        "--avoid-overwrite",
        action="store_true",
        help="若当日文件已存在，在文件名后加 _1、_2 等序号，避免覆盖",
    )
    parser.add_argument(
        "--print-path-only",
        action="store_true",
        help="只打印最终路径，不打印其他说明",
    )
    args = parser.parse_args()

    if args.date:
        try:
            d = date(int(args.date[:4]), int(args.date[4:6]), int(args.date[6:8]))
        except (ValueError, IndexError):
            raise SystemExit(f"无效日期格式，请使用 YYYYMMDD: {args.date}")
    else:
        d = date.today()

    date_str = d.strftime("%Y%m%d")
    base_name = f"{args.competitor}_v1.0_{date_str}.docx"
    reports_dir = args.reports_root.resolve() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    out_path = reports_dir / base_name
    if args.avoid_overwrite:
        stem = f"{args.competitor}_v1.0_{date_str}"
        suffix = ".docx"
        n = 0
        while out_path.is_file():
            n += 1
            out_path = reports_dir / f"{stem}_{n}{suffix}"

    if args.print_path_only:
        print(out_path)
    else:
        print(f"reports 目录: {reports_dir}")
        print(f"报告路径: {out_path}")
        print(f"文件名: {out_path.name}")


if __name__ == "__main__":
    main()
