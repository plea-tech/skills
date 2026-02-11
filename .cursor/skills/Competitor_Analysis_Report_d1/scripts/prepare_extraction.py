#!/usr/bin/env python3
"""
抽取前准备：根据竞品目录和 docs_input.md 创建 extracted_content 结构并输出 worklist。
大模型在 Step 2 开始前调用，再按 worklist 用各 skill 处理文档。
"""
import argparse
import json
import re
import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS = (".docx", ".pdf", ".pptx", ".xlsx")


def parse_docs_input(ref_dir: Path) -> list[dict]:
    """解析 docs_input.md：每行 文件名+空白+说明，返回 [{path, type, description}]。"""
    docs_path = ref_dir / "docs_input.md"
    if not docs_path.is_file():
        return []

    documents = []
    for line in docs_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 按连续空白拆成「文件名」与「说明」
        parts = re.split(r"\s{2,}|\t", line, maxsplit=1)
        filename = (parts[0] or "").strip()
        description = (parts[1] if len(parts) > 1 else "").strip()
        if not filename:
            continue
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        doc_path = ref_dir / filename
        if not doc_path.is_file():
            continue
        doc_type = ext.lstrip(".")
        documents.append({
            "path": str(doc_path.resolve()),
            "filename": filename,
            "type": doc_type,
            "description": description,
        })
    return documents


def parse_links_input(ref_dir: Path) -> list[dict]:
    """解析 links_input.md：每行一个 URL，可选后面跟空白+说明。"""
    links_path = ref_dir / "links_input.md"
    if not links_path.is_file():
        return []

    links = []
    for line in links_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=1)
        url = (parts[0] or "").strip()
        description = (parts[1] if len(parts) > 1 else "").strip()
        if url and (url.startswith("http://") or url.startswith("https://")):
            links.append({"url": url, "description": description})
    return links


def main():
    parser = argparse.ArgumentParser(
        description="准备竞品抽取目录与工作清单（文档列表 + 链接列表）"
    )
    parser.add_argument(
        "--ref-dir",
        type=Path,
        required=True,
        help="竞品目录路径，即 references/<竞品名>，内含 docs_input.md（及可选 links_input.md）",
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=Path.cwd(),
        help="项目根目录，将在此下创建 extracted_content/<竞品名>/（默认：当前工作目录）",
    )
    args = parser.parse_args()

    ref_dir = args.ref_dir.resolve()
    if not ref_dir.is_dir():
        raise SystemExit(f"竞品目录不存在或不是目录: {ref_dir}")

    competitor_name = ref_dir.name
    out_root = (args.output_base.resolve() / "extracted_content" / competitor_name)

    documents = parse_docs_input(ref_dir)
    links = parse_links_input(ref_dir)

    # 每次重新执行时清除此前已抽取的内容，避免与本次抽取结果混杂
    if out_root.exists():
        shutil.rmtree(out_root)
        print(f"已清除旧抽取目录: {out_root}", file=__import__("sys").stderr)

    (out_root / "text").mkdir(parents=True, exist_ok=True)
    (out_root / "images").mkdir(parents=True, exist_ok=True)
    (out_root / "links").mkdir(parents=True, exist_ok=True)

    worklist = {
        "competitor": competitor_name,
        "ref_dir": str(ref_dir),
        "extracted_root": str(out_root),
        "documents": documents,
        "links": links,
    }
    worklist_path = out_root / "worklist.json"
    worklist_path.write_text(json.dumps(worklist, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(worklist, ensure_ascii=False, indent=2))
    print(f"\n已创建目录: {out_root}", file=__import__("sys").stderr)
    print(f"已写入工作清单: {worklist_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
