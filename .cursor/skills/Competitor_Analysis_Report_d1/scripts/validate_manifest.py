#!/usr/bin/env python3
"""
图片清单校验：校验 images/ 下图片文件与 manifest 记录是否一致，
可输出校验报告或合并多个 manifest。Step 2 完成后、Step 3 迭代 2 之前可选调用。
"""
import argparse
import re
from pathlib import Path

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
MANIFEST_NAME = "images_manifest.md"


def find_manifest(extracted_root: Path) -> Path | None:
    """在抽取根目录或 images 子目录下查找 images_manifest.md。"""
    for candidate in (extracted_root / MANIFEST_NAME, extracted_root / "images" / MANIFEST_NAME):
        if candidate.is_file():
            return candidate
    return None


def list_image_files(images_dir: Path) -> set[str]:
    """列出 images 目录下所有图片文件名（小写扩展名）。"""
    if not images_dir.is_dir():
        return set()
    return {f.name for f in images_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS}


def parse_manifest_for_filenames(manifest_path: Path) -> set[str]:
    """从 manifest 文本中解析出被引用的图片文件名（含扩展名）。"""
    text = manifest_path.read_text(encoding="utf-8")
    # 匹配明显作为文件名出现的 xxx.png / xxx.jpg / xxx.jpeg（含 - _ 等）
    pattern = re.compile(r"\b([\w.-]+\.(?:png|jpeg|jpg))\b", re.IGNORECASE)
    return set(m.group(1) for m in pattern.finditer(text))


def main():
    parser = argparse.ArgumentParser(
        description="校验图片目录与 manifest 是否一致，或合并多个 manifest"
    )
    parser.add_argument(
        "--extracted-dir",
        type=Path,
        help="extracted_content/<竞品名> 的路径；与 --manifest/--images-dir 二选一。",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="manifest 文件路径。与 --extracted-dir 二选一，需同时指定 --images-dir。",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        help="图片目录路径。与 --manifest 配合使用。",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="若存在多个 manifest，合并为 extracted_dir 下的单一 images_manifest.md（仅与 --extracted-dir 配合）。",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="将校验报告写入该文件；不指定则打印到 stdout。",
    )
    args = parser.parse_args()

    manifest_path = None
    images_dir = None

    if args.extracted_dir is not None:
        extracted_root = args.extracted_dir.resolve()
        if not extracted_root.is_dir():
            raise SystemExit(f"抽取目录不存在或不是目录: {extracted_root}")
        manifest_path = find_manifest(extracted_root)
        images_dir = extracted_root / "images"
    elif args.manifest is not None and args.images_dir is not None:
        manifest_path = args.manifest.resolve()
        images_dir = args.images_dir.resolve()
        if not manifest_path.is_file():
            raise SystemExit(f"manifest 文件不存在: {manifest_path}")
    else:
        raise SystemExit("请指定 --extracted-dir，或同时指定 --manifest 与 --images-dir")

    image_files = list_image_files(images_dir)
    if manifest_path is None:
        lines = [
            "# 图片清单校验报告",
            "",
            f"未找到 manifest 文件（未找到 {MANIFEST_NAME}）。",
            f"图片目录中共 {len(image_files)} 个文件，均无 manifest 记录。",
            "",
            "## 图片文件列表（未在 manifest 中）",
            "",
        ]
        for n in sorted(image_files):
            lines.append(f"- {n}")
        report_text = "\n".join(lines)
        if args.report:
            args.report.resolve().write_text(report_text, encoding="utf-8")
            print(f"已写入报告: {args.report}", file=__import__("sys").stderr)
        else:
            print(report_text)
        return

    referenced = parse_manifest_for_filenames(manifest_path)
    without_entry = image_files - referenced
    without_file = referenced - image_files

    lines = [
        "# 图片清单校验报告",
        "",
        f"- Manifest: {manifest_path}",
        f"- 图片目录: {images_dir}",
        "",
        "## 结果摘要",
        "",
        f"- 图片目录中文件数: {len(image_files)}",
        f"- Manifest 中引用数: {len(referenced)}",
        f"- 有文件无记录（建议补全 manifest）: {len(without_entry)}",
        f"- 有记录无文件（建议删除或补图）: {len(without_file)}",
        "",
    ]
    if without_entry:
        lines.append("## 有文件无 manifest 记录")
        lines.append("")
        for n in sorted(without_entry):
            lines.append(f"- {n}")
        lines.append("")
    if without_file:
        lines.append("## 有 manifest 记录但文件不存在")
        lines.append("")
        for n in sorted(without_file):
            lines.append(f"- {n}")
        lines.append("")

    report_text = "\n".join(lines)
    if args.report:
        args.report.resolve().write_text(report_text, encoding="utf-8")
        print(f"已写入报告: {args.report}", file=__import__("sys").stderr)
    else:
        print(report_text)

    if args.merge and args.extracted_dir is not None:
        # 仅当使用 --extracted-dir 时合并：当前只找到一个 manifest，合并逻辑可扩展为扫描多个 .md
        target = extracted_root / MANIFEST_NAME
        if manifest_path != target and manifest_path.is_file():
            content = manifest_path.read_text(encoding="utf-8")
            target.write_text(content, encoding="utf-8")
            print(f"已合并写入: {target}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
