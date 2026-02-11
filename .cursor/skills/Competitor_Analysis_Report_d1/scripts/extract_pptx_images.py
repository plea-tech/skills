#!/usr/bin/env python3
"""
从 PPTX 中抽取内嵌图片并保存为 PNG（或保留原格式），不依赖 python-pptx。
支持按最小宽高过滤；生成 manifest（幻灯片号、文件名、该页文字摘要）供选图用。
用法：python extract_pptx_images.py <pptx路径> <输出目录> [--min-size 120] [--manifest <manifest.md>]
"""
import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def get_image_size(data: bytes) -> tuple[int | None, int | None]:
    if not HAS_PIL:
        return (None, None)
    try:
        pil = Image.open(io.BytesIO(data))
        return pil.size
    except Exception:
        return (None, None)


def text_of_slide(slide_xml: bytes) -> str:
    """取单页幻灯片中所有 a:t 文本。"""
    root = ET.fromstring(slide_xml)
    parts = []
    for e in root.iter():
        if e.tag.endswith("}t"):
            if e.text:
                parts.append(e.text)
            if e.tail:
                parts.append(e.tail)
    return "".join(parts).replace("\n", " ").strip()


def get_slide_rels(zip_f: zipfile.ZipFile, slide_path: str) -> dict[str, str]:
    """e.g. ppt/slides/_rels/slide1.xml.rels -> rId -> target (可能为 ../media/image1.png)。"""
    # slide_path = ppt/slides/slide1.xml -> rels = ppt/slides/_rels/slide1.xml.rels
    rels_path = slide_path.replace(".xml", ".xml.rels").replace("/slides/", "/slides/_rels/")
    if rels_path not in zip_f.namelist():
        return {}
    rels = ET.fromstring(zip_f.read(rels_path))
    out = {}
    for rel in rels:
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            # target 可能为 ../media/image1.png，相对于 slide 所在目录
            if target.startswith("../"):
                target = target[3:]
            elif not target.startswith("media/"):
                target = "media/" + target
            out[rid] = target
    return out


def collect_blips_in_slide(slide_xml: bytes) -> list[str]:
    """按出现顺序收集该页中所有 a:blip 的 r:embed (rId)。"""
    root = ET.fromstring(slide_xml)
    r_ns = NS["r"]
    rids = []
    for el in root.iter():
        rid = el.get(f"{{{r_ns}}}embed")
        if rid:
            rids.append(rid)
    return rids


def main():
    parser = argparse.ArgumentParser(
        description="从 PPTX 抽取内嵌图片到目录；可过滤过小图片；生成 manifest"
    )
    parser.add_argument("pptx_path", type=Path, help="PPTX 文件路径")
    parser.add_argument("output_dir", type=Path, help="图片输出目录")
    parser.add_argument(
        "--min-size",
        type=int,
        default=120,
        metavar="N",
        help="最小宽、高（像素），宽或高任一小于 N 的图片不抽取（默认 120，设为 0 关闭）",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="图片列表 manifest 的写入路径；不指定时默认写入「输出目录同级/<源文件名>_images_manifest.md」",
    )
    args = parser.parse_args()

    pptx_path = args.pptx_path.resolve()
    if not pptx_path.is_file():
        raise SystemExit(f"文件不存在: {pptx_path}")

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    min_size = max(0, args.min_size)
    stem = pptx_path.stem
    safe_stem = re.sub(r"[^\w\-]", "_", stem)[:50]
    # 未指定 manifest 时默认写入「输出目录同级 / 源文件 stem_images_manifest.md」
    if args.manifest is None:
        args.manifest = out_dir.parent / f"{safe_stem}_images_manifest.md"

    manifest_lines = [
        "# PPTX 抽取图片列表",
        "",
        f"- 源文件: {pptx_path.name}",
    ]
    if min_size > 0:
        manifest_lines.append(f"- 过滤: 宽或高 < {min_size}px 的图片已跳过")
    manifest_lines.extend([
        "",
        "| 幻灯片号 | 文件名 | 周边文字（该页原文摘要） | 说明（可补） |",
        "|----------|--------|--------------------------|--------------|",
    ])
    max_context_len = 120
    count = 0
    skipped_small = 0
    seq = 0  # 文件内唯一递增序号

    def safe_utf8(s: str) -> str:
        """确保幻灯片摘要可安全写入 UTF-8。"""
        if not s:
            return ""
        return s.encode("utf-8", errors="replace").decode("utf-8")

    with zipfile.ZipFile(pptx_path, "r") as zf:
        slide_files = sorted(
            n for n in zf.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml") and "_rels" not in n
        )
        if not slide_files:
            raise SystemExit("不是有效的 PPTX（未找到 ppt/slides/slideN.xml）")

        for slide_path in slide_files:
            # slide1.xml -> 1
            num_part = Path(slide_path).stem
            if not num_part.startswith("slide"):
                continue
            try:
                slide_num = int(num_part[5:])
            except ValueError:
                continue
            slide_xml = zf.read(slide_path)
            slide_text = safe_utf8(text_of_slide(slide_xml)[:max_context_len].replace("|", " "))
            rels = get_slide_rels(zf, slide_path)
            rids = collect_blips_in_slide(slide_xml)

            for img_idx, rid in enumerate(rids):
                target = rels.get(rid)
                if not target:
                    continue
                # rels 里 target 多为 ../media/xxx，已规范为 media/xxx；zip 内为 ppt/media/xxx
                zip_name = "ppt/" + target if not target.startswith("ppt/") else target
                if zip_name not in zf.namelist():
                    zip_name = "ppt/media/" + target.split("/")[-1]
                if zip_name not in zf.namelist():
                    continue
                raw = zf.read(zip_name)
                w, h = get_image_size(raw) if min_size > 0 else (None, None)
                if min_size > 0:
                    if w is None or h is None:
                        skipped_small += 1
                        continue
                    if w < min_size or h < min_size:
                        skipped_small += 1
                        continue

                seq += 1
                ext = Path(zip_name).suffix.lower()
                if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".emf", ".wmf"):
                    ext = ".png"
                if ext in (".emf", ".wmf") and HAS_PIL:
                    try:
                        pil = Image.open(io.BytesIO(raw))
                        raw = io.BytesIO()
                        pil.save(raw, format="PNG")
                        raw = raw.getvalue()
                        ext = ".png"
                    except Exception:
                        pass
                # 命名: pptx_<文件名>_IMG_<序号>(Page<幻灯片号>)
                fname = f"pptx_{safe_stem}_IMG_{seq:03d}(Page{slide_num}){ext}"
                out_path = out_dir / fname
                out_path.write_bytes(raw)

                manifest_lines.append(f"| {slide_num} | {fname} | {slide_text} |  |")
                count += 1

    if args.manifest:
        args.manifest.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"已写入 manifest: {args.manifest}", file=__import__("sys").stderr)
    print(f"共抽取 {count} 张图片到 {out_dir}" + (f"，已跳过 {skipped_small} 张过小图片" if skipped_small else ""), file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
