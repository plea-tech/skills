#!/usr/bin/env python3
"""
Step 3 迭代2：根据「图片放置清单」JSON，在目标报告 docx 的指定标题后插入图片并添加图注。
放置清单格式：[{"heading": "2.1 架构&技术分析", "image": "path/to/image.png", "caption": "系统架构图"}, ...]
"""
import argparse
import json
from pathlib import Path

try:
    from docx import Document
except ImportError:
    raise SystemExit("请安装 python-docx：pip install python-docx")


def find_paragraph_index(doc, heading: str) -> int | None:
    """在文档中查找包含 heading 的段落索引（完全匹配或 strip 后匹配）。"""
    for i, p in enumerate(doc.paragraphs):
        t = (p.text or "").strip()
        if t == heading or heading in t:
            return i
    return None


def main():
    parser = argparse.ArgumentParser(
        description="按放置清单将图片插入报告 docx 的指定标题后"
    )
    parser.add_argument("--docx", type=Path, required=True, help="目标报告 docx 路径")
    parser.add_argument(
        "--placement",
        type=Path,
        required=True,
        help="放置清单 JSON 路径，格式为 [{\"heading\": \"章节标题\", \"image\": \"图片路径\", \"caption\": \"图注\"}, ...]",
    )
    parser.add_argument(
        "--width-cm",
        type=float,
        default=14,
        help="插入图片宽度（厘米），默认 14",
    )
    args = parser.parse_args()

    docx_path = args.docx.resolve()
    if not docx_path.is_file():
        raise SystemExit(f"docx 文件不存在: {docx_path}")

    placement_path = args.placement.resolve()
    if not placement_path.is_file():
        raise SystemExit(f"放置清单不存在: {placement_path}")

    with open(placement_path, encoding="utf-8") as f:
        placements = json.load(f)
    if not isinstance(placements, list):
        raise SystemExit("放置清单应为 JSON 数组")

    doc = Document(str(docx_path))
    # 图片路径在放置清单中一般为相对于项目根的路径
    base_dir = Path.cwd()
    inserted = 0

    for item in placements:
        heading = (item.get("heading") or "").strip()
        image_rel = (item.get("image") or "").strip()
        caption = (item.get("caption") or "").strip()
        if not heading or not image_rel:
            continue
        image_path = (base_dir / image_rel).resolve() if not Path(image_rel).is_absolute() else Path(image_rel)
        if not image_path.is_file():
            print(f"跳过（图片不存在）: {image_path}", file=__import__("sys").stderr)
            continue
        idx = find_paragraph_index(doc, heading)
        if idx is None:
            print(f"跳过（未找到标题）: {heading}", file=__import__("sys").stderr)
            continue
        if idx + 1 >= len(doc.paragraphs):
            print(f"跳过（标题后无段落）: {heading}", file=__import__("sys").stderr)
            continue
        next_para = doc.paragraphs[idx + 1]
        # 顺序必须为：标题 -> 图片 -> 图注（图在上、图注在下，符合 output_define）。先插图片段再插图注段，均 insert_before(next_para)，故先插的图片在前、后插的图注在图片与正文之间。
        img_para = next_para.insert_paragraph_before()
        run = img_para.add_run()
        try:
            from docx.shared import Cm
            run.add_picture(str(image_path), width=Cm(args.width_cm))
        except Exception as e:
            print(f"插入图片失败 {image_path}: {e}", file=__import__("sys").stderr)
            continue
        if caption:
            next_para.insert_paragraph_before(text=caption)
        inserted += 1

    doc.save(str(docx_path))
    print(f"已插入 {inserted} 张图片，已保存: {docx_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
