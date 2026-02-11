#!/usr/bin/env python3
"""
竞品名解析：根据用户输入的竞品名或别名，结合 alias.md 解析出标准竞品目录名与 references 下的路径。
大模型在 Step 2 前若只有竞品名（如「浪潮」），可先调用本脚本得到 --ref-dir，再调用 prepare_extraction。
"""
import argparse
from pathlib import Path


def load_alias(refs_root: Path) -> dict[str, str]:
    """
    解析 alias.md：每行「标准目录名 别名1 别名2 ...」，返回 别名/标准名 -> 标准目录名 的映射。
    """
    alias_path = refs_root / "alias.md"
    if not alias_path.is_file():
        return {}

    mapping = {}
    for line in alias_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if not tokens:
            continue
        canonical = tokens[0]
        for t in tokens:
            key = t.strip().lower()
            if key:
                mapping[key] = canonical
        mapping[canonical.lower()] = canonical
    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="根据竞品名或别名解析出 references 下的竞品目录路径"
    )
    parser.add_argument(
        "--competitor",
        type=str,
        required=True,
        help="竞品名或别名（不区分大小写），如 Inspur、浪潮、LC",
    )
    parser.add_argument(
        "--refs-root",
        type=Path,
        default=None,
        help="references 目录的路径；默认尝试从本脚本位置推导（技能目录/references）",
    )
    parser.add_argument(
        "--print-dir-only",
        action="store_true",
        help="只打印竞品目录的绝对路径，便于脚本串联",
    )
    args = parser.parse_args()

    if args.refs_root is not None:
        refs_root = args.refs_root.resolve()
    else:
        # 从脚本所在目录推导：scripts/ -> 技能目录 -> references
        script_dir = Path(__file__).resolve().parent
        skill_root = script_dir.parent
        refs_root = skill_root / "references"

    if not refs_root.is_dir():
        raise SystemExit(f"references 目录不存在: {refs_root}")

    alias_map = load_alias(refs_root)
    key = args.competitor.strip().lower()
    canonical = alias_map.get(key)

    if canonical is None:
        # 未在 alias 中找到，尝试直接当作目录名（忽略大小写匹配现有目录）
        for d in refs_root.iterdir():
            if d.is_dir() and d.name.lower() == key:
                canonical = d.name
                break
        if canonical is None:
            raise SystemExit(f"未找到竞品名或别名对应的目录: {args.competitor}")

    competitor_dir = refs_root / canonical
    if not competitor_dir.is_dir():
        raise SystemExit(f"竞品目录不存在: {competitor_dir}")

    if args.print_dir_only:
        print(competitor_dir)
    else:
        print(f"标准名称: {canonical}")
        print(f"竞品目录: {competitor_dir}")


if __name__ == "__main__":
    main()
