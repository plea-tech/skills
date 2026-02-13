#!/usr/bin/env python3
"""
按 worklist.json 批量执行：run_markitdown（文字 → text/）+ 对应 extract_*_images（图片 → images/）。
在 prepare_extraction 之后调用，可替代逐条手动执行 run_markitdown 与抽图脚本。
用法：python run_extraction.py --worklist extracted_content/Inspur/worklist.json [--min-size 120]
      或：python run_extraction.py --extracted-dir extracted_content/Inspur [--min-size 120]
"""
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def _ensure_project_venv() -> None:
    """若项目根下存在 .venv 且当前不在该虚拟环境中，则用 .venv 的 Python 重新执行本脚本（强制在虚拟环境中运行）。"""
    project_root = Path.cwd()
    venv_dir = project_root / ".venv"
    if not venv_dir.is_dir():
        return
    try:
        real_executable = Path(sys.executable).resolve()
        real_venv = venv_dir.resolve()
        if real_venv in real_executable.parents:
            return
        venv_env = os.environ.get("VIRTUAL_ENV")
        if venv_env and Path(venv_env).resolve() == real_venv:
            return
    except Exception:
        return
    # 未在项目 venv 中：用 .venv 的 Python 重新执行本脚本
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
    if not venv_python.is_file():
        print(
            "错误：未在项目虚拟环境中，且未找到 .venv 下的 Python。请先激活：.venv\\Scripts\\Activate.ps1 或 source .venv/bin/activate",
            file=sys.stderr,
        )
        sys.exit(1)
    # 用虚拟环境 Python 替换当前进程，不返回
    os.execv(str(venv_python.resolve()), [str(venv_python)] + sys.argv)


def safe_md_name(filename: str) -> str:
    stem = Path(filename).stem
    name = (re.sub(r"[\s\-]+", "_", stem)).strip() or "doc"
    return name + ".md"


def main():
    _ensure_project_venv()
    parser = argparse.ArgumentParser(
        description="按 worklist 批量执行 run_markitdown 与 extract_*_images"
    )
    parser.add_argument(
        "--worklist",
        type=Path,
        help="worklist.json 的路径",
    )
    parser.add_argument(
        "--extracted-dir",
        type=Path,
        help="extracted_content/<竞品名> 目录；与 --worklist 二选一，将使用该目录下的 worklist.json",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=120,
        metavar="N",
        help="抽图时过滤小图的最小宽高（像素），默认 120；传 0 关闭过滤",
    )
    args = parser.parse_args()

    if args.worklist is not None:
        worklist_path = args.worklist.resolve()
    elif args.extracted_dir is not None:
        worklist_path = args.extracted_dir.resolve() / "worklist.json"
    else:
        raise SystemExit("请指定 --worklist 或 --extracted-dir")

    if not worklist_path.is_file():
        raise SystemExit(f"worklist 不存在: {worklist_path}")

    with open(worklist_path, encoding="utf-8") as f:
        wl = json.load(f)

    extracted_root = Path(wl["extracted_root"])
    documents = wl.get("documents", [])
    text_dir = extracted_root / "text"
    images_dir = extracted_root / "images"
    text_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    run_markitdown = SCRIPTS_DIR / "run_markitdown.py"
    extract_pdf = SCRIPTS_DIR / "extract_pdf_images.py"
    extract_docx = SCRIPTS_DIR / "extract_docx_images.py"
    extract_pptx = SCRIPTS_DIR / "extract_pptx_images.py"
    min_size = str(args.min_size) if args.min_size else "0"
    # 单文档超时（秒），避免某个文件卡死整批；PDF/大文件可能较慢
    doc_timeout = 300

    total = len(documents)
    total_start = time.perf_counter()
    print(f"开始抽取：共 {total} 个文档（每个先抽文字再抽图片），请耐心等待…", flush=True)
    print("-" * 60, flush=True)

    for i, doc in enumerate(documents, 1):
        path = Path(doc["path"])
        filename = doc.get("filename", path.name)
        doc_type = (doc.get("type") or path.suffix.lstrip(".")).lower()
        doc_start = time.perf_counter()
        print(f"\n[{i}/{total}] {filename}", flush=True)
        if not path.is_file():
            print("  SKIP (not found)", file=sys.stderr)
            continue

        # 文字：run_markitdown → text/
        out_md = text_dir / safe_md_name(filename)
        # 强制子进程使用 UTF-8，避免 Windows 下默认 GBK 导致「cannot decode byte」
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        print("  → 抽取文字 (转 Markdown)...", flush=True)
        try:
            r = subprocess.run(
                [sys.executable, str(run_markitdown), str(path), "-o", str(out_md)],
                cwd=str(extracted_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=doc_timeout,
            )
        except subprocess.TimeoutExpired:
            print("  FAIL text (timeout)", file=sys.stderr)
            continue
        if r.returncode == 0:
            print(f"  [OK] 文字完成 ({time.perf_counter() - doc_start:.1f}s)", flush=True)
        else:
            print("  FAIL text", (r.stderr or r.stdout or "")[:200], file=sys.stderr)

        # 图片：按类型调用对应 extract_*_images
        has_images = doc_type in ("pdf", "docx", "pptx") and (
            (doc_type == "pdf" and extract_pdf.is_file())
            or (doc_type == "docx" and extract_docx.is_file())
            or (doc_type == "pptx" and extract_pptx.is_file())
        )
        if has_images:
            print("  → 抽取图片...", flush=True)
        try:
            if doc_type == "pdf" and extract_pdf.is_file():
                r = subprocess.run(
                    [sys.executable, str(extract_pdf), str(path), str(images_dir), "--min-size", min_size],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    timeout=doc_timeout,
                )
                if r.returncode == 0:
                    print(f"  [OK] 图片完成 ({time.perf_counter() - doc_start:.1f}s 本项总耗时)", flush=True)
                else:
                    print("  FAIL images(pdf)", (r.stderr or "")[:200], file=sys.stderr)
            elif doc_type == "docx" and extract_docx.is_file():
                r = subprocess.run(
                    [sys.executable, str(extract_docx), str(path), str(images_dir), "--min-size", min_size],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    timeout=doc_timeout,
                )
                if r.returncode == 0:
                    print(f"  [OK] 图片完成 ({time.perf_counter() - doc_start:.1f}s 本项总耗时)", flush=True)
                else:
                    print("  FAIL images(docx)", (r.stderr or "")[:200], file=sys.stderr)
            elif doc_type == "pptx" and extract_pptx.is_file():
                r = subprocess.run(
                    [sys.executable, str(extract_pptx), str(path), str(images_dir), "--min-size", min_size],
                    cwd=str(extracted_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    timeout=doc_timeout,
                )
                if r.returncode == 0:
                    print(f"  [OK] 图片完成 ({time.perf_counter() - doc_start:.1f}s 本项总耗时)", flush=True)
                else:
                    print("  FAIL images(pptx)", (r.stderr or "")[:200], file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("  FAIL images (timeout)", file=sys.stderr)
        # xlsx 无抽图脚本，跳过
        print(f"  本文档合计: {time.perf_counter() - doc_start:.1f}s", flush=True)

    total_elapsed = time.perf_counter() - total_start
    print("-" * 60, flush=True)
    print(f"run_extraction 完成，共耗时 {total_elapsed:.1f}s ({total_elapsed/60:.1f} 分钟)。", file=sys.stderr)


if __name__ == "__main__":
    main()
