#!/usr/bin/env python3
"""
将 extracted_content/<竞品>/ 下多个 *_images_manifest.md 合并为单一 images_manifest.md，
便于 Step 3 选图时一次阅读；合并后每行增加「源文件」列，仍可追溯图片来自哪份材料。
用法：python merge_manifests.py --extracted-dir extracted_content/Inspur
"""
import argparse
import re
from pathlib import Path


def extract_source_name(content: str) -> str:
    """从 manifest 内容中解析「- 源文件: xxx」得到源文件名。"""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- 源文件:") or line.startswith("- 源文件："):
            return line.split(":", 1)[-1].split("：", 1)[-1].strip()
    return ""


def extract_table(content: str) -> tuple[list[str], list[list[str]]]:
    """
    从 markdown 内容中解析出第一个表格的表头行与数据行。
    返回 (header_cells, data_rows)，每个 cell 为去掉首尾 | 并 strip 后的内容。
    """
    header = []
    rows = []
    in_table = False
    for line in content.splitlines():
        if not line.strip().startswith("|"):
            if in_table:
                break
            continue
        in_table = True
        # 按 | 分割；通常格式为 | a | b |，故 parts[0]/parts[-1] 常为空
        parts = line.strip().split("|")
        cells = [p.strip() for p in (parts[1:-1] if len(parts) > 2 else parts)][:10]
        if not cells:
            continue
        if all(re.match(r"^-+$", c) for c in cells):
            continue
        if not header:
            header = cells
        else:
            rows.append(cells)
    return header, rows


def row_to_unified(header: list[str], row: list[str], source: str) -> list[str]:
    """
    将单行按统一格式输出：源文件 | 页码/幻灯片号/序号 | 文件名 | 宽×高 | 周边文字 | 说明。
    根据 header 中列名找到对应列索引，缺失的填空串（如 docx/pptx 无宽×高列则填空）。
    """
    def idx(keywords: list[str]) -> int:
        for kw in keywords:
            for i, h in enumerate(header):
                if kw in h:
                    return i
        return -1

    loc_idx = idx(["页码", "幻灯片号", "序号"])
    file_idx = idx(["文件名"])
    size_idx = idx(["宽×高"])
    ctx_idx = idx(["周边文字", "周边"])
    note_idx = idx(["说明"])

    def get(i: int) -> str:
        if i >= 0 and i < len(row):
            return row[i]
        return ""

    return [
        source,
        get(loc_idx),
        get(file_idx),
        get(size_idx),
        get(ctx_idx),
        get(note_idx),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="将多个 *_images_manifest.md 合并为单一 images_manifest.md，首列增加「源文件」"
    )
    parser.add_argument(
        "--extracted-dir",
        type=Path,
        required=True,
        help="extracted_content/<竞品名> 的路径",
    )
    args = parser.parse_args()

    extracted_root = args.extracted_dir.resolve()
    if not extracted_root.is_dir():
        raise SystemExit(f"目录不存在: {extracted_root}")

    # 所有 *xxx_images_manifest.md，排除已合并的 images_manifest.md
    pattern = "*_images_manifest.md"
    manifest_files = sorted(extracted_root.glob(pattern))
    if extracted_root / "images_manifest.md" in manifest_files:
        manifest_files = [f for f in manifest_files if f.name != "images_manifest.md"]
    if not manifest_files:
        print("未找到任何 *_images_manifest.md 文件", file=__import__("sys").stderr)
        return

    unified_header = ["源文件", "页码/幻灯片号/序号", "文件名", "宽×高", "周边文字", "说明"]
    merged_rows = []
    for mf in manifest_files:
        content = mf.read_text(encoding="utf-8")
        source = extract_source_name(content)
        header, rows = extract_table(content)
        if not header or not rows:
            continue
        for row in rows:
            merged_rows.append(row_to_unified(header, row, source))

    out_path = extracted_root / "images_manifest.md"
    lines = [
        "# 图片清单（合并）",
        "",
        "由多个源文档的 manifest 合并而成，便于 Step 3 选图时一次阅读。",
        "",
        "| " + " | ".join(unified_header) + " |",
        "| " + " | ".join("---" for _ in unified_header) + " |",
    ]
    for row in merged_rows:
        lines.append("| " + " | ".join(row) + " |")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"已合并 {len(manifest_files)} 个 manifest，写入: {out_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
