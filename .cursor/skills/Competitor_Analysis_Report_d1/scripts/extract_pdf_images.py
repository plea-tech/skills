#!/usr/bin/env python3
"""
从 PDF 中抽取内嵌图片并保存为 PNG，不依赖 pdfimages/poppler。
支持按最小宽高过滤，避免抽取 LOGO、图标等小图。
用法：python extract_pdf_images.py <pdf路径> <输出目录> [--min-size 120] [--manifest <manifest.md>]
"""
import argparse
import io
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    raise SystemExit("请先安装 pypdf：pip install pypdf")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_image_size(img) -> tuple[int | None, int | None]:
    """获取图片宽高 (width, height)，无法获取时返回 (None, None)。"""
    if getattr(img, "image", None) is not None and HAS_PIL:
        w, h = img.image.size
        return (w, h)
    if getattr(img, "data", None) and HAS_PIL:
        try:
            pil = Image.open(io.BytesIO(img.data))
            return pil.size
        except Exception:
            return (None, None)
    return (None, None)


def main():
    parser = argparse.ArgumentParser(
        description="从 PDF 抽取内嵌图片到目录，不依赖 pdfimages；可过滤过小图片（如 LOGO、图标）"
    )
    parser.add_argument("pdf_path", type=Path, help="PDF 文件路径")
    parser.add_argument("output_dir", type=Path, help="图片输出目录")
    parser.add_argument(
        "--min-size",
        type=int,
        default=120,
        metavar="N",
        help="最小宽、高（像素），宽或高任一小于 N 的图片不抽取，用于过滤 LOGO/图标等（默认 120，设为 0 关闭过滤）",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="图片列表 manifest 的写入路径；不指定时默认写入「输出目录同级/<源文件名>_images_manifest.md」",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path.resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"文件不存在: {pdf_path}")

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^\w\-]", "_", pdf_path.stem)[:50]
    # 未指定 manifest 时默认写入「输出目录同级 / 源文件 stem_images_manifest.md」
    if args.manifest is None:
        args.manifest = out_dir.parent / f"{safe_stem}_images_manifest.md"

    min_size = max(0, args.min_size)
    reader = PdfReader(str(pdf_path))
    manifest_lines = [
        "# PDF 抽取图片列表",
        "",
        f"- 源文件: {pdf_path.name}",
    ]
    if min_size > 0:
        manifest_lines.append(f"- 过滤: 宽或高 < {min_size}px 的图片已跳过（避免 LOGO/图标）")
    manifest_lines.append("- 同一页多图时按尺寸（宽×高）从大到小排列，优先选本页尺寸最大的图。")
    manifest_lines.extend(["", "| 页码 | 文件名 | 宽×高 | 周边文字（该页原文摘要） | 说明（可补） |", "|------|--------|-------|--------------------------|--------------|"])
    count = 0
    skipped_small = 0
    seq = 0  # 文件内唯一递增序号
    max_context_len = 120  # 摘要长度，便于在 manifest 中区分 logo 与架构图等

    def safe_utf8(s: str) -> str:
        """确保字符串可安全写入 UTF-8，避免 PDF 内非 UTF-8 编码导致 decode 报错。"""
        if not s:
            return ""
        if isinstance(s, bytes):
            return s.decode("utf-8", errors="replace")
        return s.encode("utf-8", errors="replace").decode("utf-8")

    def save_image_and_get_fname(img, page_num: int, ext: str) -> str | None:
        """将 img 保存到 out_dir，返回文件名；失败返回 None。不修改 seq，由调用方递增。"""
        nonlocal seq
        seq += 1
        fname = f"pdf_{safe_stem}_IMG_{seq:03d}(Page{page_num}){ext}"
        out_path = out_dir / fname
        try:
            if getattr(img, "image", None) is not None and HAS_PIL:
                img.image.save(str(out_path))
            elif getattr(img, "data", None):
                out_path.write_bytes(img.data)
            else:
                seq -= 1
                return None
            return fname
        except Exception:
            seq -= 1
            return None

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text()
            if raw_text is None:
                raw_text = ""
            if isinstance(raw_text, bytes):
                raw_text = raw_text.decode("utf-8", errors="replace")
            page_text = safe_utf8(raw_text.replace("\n", " ").strip()[:max_context_len])
        except Exception:
            page_text = ""
        try:
            images = page.images
        except Exception:
            images = []
        # 本页通过尺寸过滤的图片，先收集 (img, w, h)，再按面积从大到小排序，再落盘并写 manifest
        candidates: list[tuple[object, int, int]] = []
        for img in images:
            try:
                w, h = get_image_size(img)
                if min_size > 0:
                    if w is None or h is None:
                        skipped_small += 1
                        continue
                    if w < min_size or h < min_size:
                        skipped_small += 1
                        continue
                candidates.append((img, w or 0, h or 0))
            except Exception:
                skipped_small += 1
        candidates.sort(key=lambda x: x[1] * x[2], reverse=True)
        context_cell = (page_text.replace("|", " ").replace("\n", " ") if page_text else "")
        for img, w, h in candidates:
            try:
                ext = ".png"
                if getattr(img, "image", None) is not None and HAS_PIL:
                    pass
                elif getattr(img, "data", None):
                    raw = img.data
                    ext = ".jpg" if raw[:2] == b"\xff\xd8" else ".png"
                else:
                    continue
                fname = save_image_and_get_fname(img, page_num, ext)
                if fname is None:
                    manifest_lines.append(f"| {page_num} | (抽取失败) |  | {context_cell} |  |")
                    continue
                size_cell = f"{w}×{h}"
                manifest_lines.append(f"| {page_num} | {fname} | {size_cell} | {context_cell} |  |")
                count += 1
            except Exception as e:
                manifest_lines.append(f"| {page_num} | (抽取失败) |  | {context_cell} | {e!r} |")

    if args.manifest:
        args.manifest.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"已写入 manifest: {args.manifest}", file=__import__("sys").stderr)
    print(f"共抽取 {count} 张图片到 {out_dir}" + (f"，已跳过 {skipped_small} 张过小图片（< {min_size}px）" if skipped_small else ""), file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
