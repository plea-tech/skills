#!/usr/bin/env python3
"""
从 DOCX 中抽取内嵌图片并保存为 PNG（或保留原格式），不依赖 python-docx。
支持按最小宽高过滤；生成 manifest（序号、文件名、所在段落文字）供选图用。
用法：python extract_docx_images.py <docx路径> <输出目录> [--min-size 120] [--manifest <manifest.md>]
"""
import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# 可选：用 PIL 做尺寸过滤与统一存为 PNG
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rId": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def get_image_size(data: bytes) -> tuple[int | None, int | None]:
    if not HAS_PIL:
        return (None, None)
    try:
        pil = Image.open(io.BytesIO(data))
        return pil.size
    except Exception:
        return (None, None)


def text_of_element(el: ET.Element, ns: dict) -> str:
    """递归取元素下所有 w:t / a:t 文本。"""
    out = []
    for e in el.iter():
        if e.tag.endswith("}t"):
            if e.text:
                out.append(e.text)
            if e.tail:
                out.append(e.tail)
    return "".join(out).replace("\n", " ").strip()


def collect_embeds_and_paragraphs(doc_xml: bytes) -> list[tuple[str, str, int]]:
    """
    按文档顺序收集 (rId, 所在段落文字, 页码)。
    遍历 body 时：遇到分页符（w:br type=page、w:lastRenderedPageBreak）则页码+1；
    遇到 w:p 更新当前段落文字；遇到 r:embed 则记录 (rid, 段落文字, 当前页)。
    Word 中看到的“页”在 XML 里由分页符体现，此处据此推算近似页码。
    """
    root = ET.fromstring(doc_xml)
    body = root.find(".//w:body", NS)
    if body is None:
        return []

    w_ns = NS["w"]
    r_ns = NS["r"]
    result = []
    current_p_text = ""
    current_page = 1
    for el in body.iter():
        tag = el.tag
        if tag == f"{{{w_ns}}}br":
            if el.get(f"{{{w_ns}}}type") == "page":
                current_page += 1
        elif tag == f"{{{w_ns}}}lastRenderedPageBreak":
            current_page += 1
        elif tag == f"{{{w_ns}}}p":
            current_p_text = text_of_element(el, NS)
        rid = el.get(f"{{{r_ns}}}embed")
        if rid:
            result.append((rid, current_p_text, current_page))
    return result


def get_rels(zip_f: zipfile.ZipFile) -> dict[str, str]:
    """word/_rels/document.xml.rels -> rId -> target path (e.g. media/image1.png)."""
    rels_path = "word/_rels/document.xml.rels"
    if rels_path not in zip_f.namelist():
        return {}
    rels = ET.fromstring(zip_f.read(rels_path))
    out = {}
    for rel in rels:
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            out[rid] = target
    return out


def main():
    parser = argparse.ArgumentParser(
        description="从 DOCX 抽取内嵌图片到目录；可过滤过小图片；生成 manifest"
    )
    parser.add_argument("docx_path", type=Path, help="DOCX 文件路径")
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

    docx_path = args.docx_path.resolve()
    if not docx_path.is_file():
        raise SystemExit(f"文件不存在: {docx_path}")

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    min_size = max(0, args.min_size)
    stem = docx_path.stem
    safe_stem = re.sub(r"[^\w\-]", "_", stem)[:50]
    # 未指定 manifest 时默认写入「输出目录同级 / 源文件 stem_images_manifest.md」
    if args.manifest is None:
        args.manifest = out_dir.parent / f"{safe_stem}_images_manifest.md"

    manifest_lines = [
        "# DOCX 抽取图片列表",
        "",
        f"- 源文件: {docx_path.name}",
    ]
    if min_size > 0:
        manifest_lines.append(f"- 过滤: 宽或高 < {min_size}px 的图片已跳过")
    manifest_lines.extend([
        "",
        "| 序号 | 页码 | 文件名 | 周边文字（所在段落） | 说明（可补） |",
        "|------|------|--------|----------------------|--------------|",
    ])
    max_context_len = 120
    count = 0
    skipped_small = 0

    def safe_utf8(s: str) -> str:
        """确保段落/周边文字可安全写入 UTF-8。"""
        if not s:
            return ""
        return s.encode("utf-8", errors="replace").decode("utf-8")

    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            raise SystemExit("不是有效的 DOCX（缺少 word/document.xml）")
        doc_xml = zf.read("word/document.xml")
        rels = get_rels(zf)
        order = collect_embeds_and_paragraphs(doc_xml)

        for idx, (rid, p_text, page_num) in enumerate(order):
            target = rels.get(rid)
            if not target or not target.startswith("media/"):
                continue
            # 实际路径在 zip 里是 word/media/xxx
            zip_name = "word/" + target
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

            ext = Path(target).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".emf", ".wmf"):
                ext = ".png"
            if ext in (".emf", ".wmf") and HAS_PIL:
                try:
                    from PIL import Image
                    # EMF/WMF 需系统支持，尝试转 PNG
                    pil = Image.open(io.BytesIO(raw))
                    raw = io.BytesIO()
                    pil.save(raw, format="PNG")
                    raw = raw.getvalue()
                    ext = ".png"
                except Exception:
                    pass
            # 命名: docx_<文件名>_IMG_<序号>(Page<页码>). 页码由文档中的分页符推算，与 Word 中看到的页对应
            seq = idx + 1
            fname = f"docx_{safe_stem}_IMG_{seq:03d}(Page{page_num}){ext}"
            out_path = out_dir / fname
            out_path.write_bytes(raw)

            context = safe_utf8((p_text[:max_context_len] if p_text else "").replace("|", " "))
            manifest_lines.append(f"| {seq} | {page_num} | {fname} | {context} |  |")
            count += 1

    if args.manifest:
        args.manifest.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"已写入 manifest: {args.manifest}", file=__import__("sys").stderr)
    print(f"共抽取 {count} 张图片到 {out_dir}" + (f"，已跳过 {skipped_small} 张过小图片" if skipped_small else ""), file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
