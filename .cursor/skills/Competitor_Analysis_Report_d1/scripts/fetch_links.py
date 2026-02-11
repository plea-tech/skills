#!/usr/bin/env python3
"""
链接抓取与缓存：读取 links_input.md（或 worklist 中的链接），抓取网页并保存到 extracted_content/links，
生成 links_index.md 供大模型本地阅读，无需重复请求外网。
"""
import argparse
import json
import hashlib
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def parse_links_from_file(links_input_path: Path) -> list[dict]:
    """从 links_input.md 解析链接：每行 URL，可选空白+说明。"""
    if not links_input_path.is_file():
        return []
    links = []
    for line in links_input_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s+", line, maxsplit=1)
        url = (parts[0] or "").strip()
        description = (parts[1] if len(parts) > 1 else "").strip()
        if url and (url.startswith("http://") or url.startswith("https://")):
            links.append({"url": url, "description": description})
    return links


def url_to_filename(url: str) -> str:
    """用 URL 的 hash 生成安全文件名。"""
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{h}.html"


def fetch_url(url: str) -> tuple[str, str | None]:
    """抓取 URL，返回 (body_text, error_message)。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CompetitorAnalysis/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            encoding = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(encoding), None
            except LookupError:
                return raw.decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return "", str(e.reason) if e.reason else str(e)
    except Exception as e:
        return "", str(e)


def main():
    parser = argparse.ArgumentParser(
        description="抓取 links_input.md 中的网页并保存到 extracted_content/links，生成 links_index.md"
    )
    parser.add_argument(
        "--ref-dir",
        type=Path,
        help="竞品目录（含 links_input.md）。与 --worklist 二选一。",
    )
    parser.add_argument(
        "--worklist",
        type=Path,
        help="worklist.json 路径，从中读取 links。与 --ref-dir 二选一。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="链接内容输出目录，即 extracted_content/<竞品名>/links",
    )
    args = parser.parse_args()

    links = []
    if args.worklist is not None:
        wl_path = args.worklist.resolve()
        if not wl_path.is_file():
            raise SystemExit(f"worklist 不存在: {wl_path}")
        data = json.loads(wl_path.read_text(encoding="utf-8"))
        links = data.get("links") or []
    elif args.ref_dir is not None:
        ref_dir = args.ref_dir.resolve()
        links_input = ref_dir / "links_input.md"
        links = parse_links_from_file(links_input)
    else:
        raise SystemExit("请指定 --ref-dir 或 --worklist")

    if not links:
        print("没有需要抓取的链接。", file=__import__("sys").stderr)
        (args.output_dir.resolve()).mkdir(parents=True, exist_ok=True)
        index_path = args.output_dir / "links_index.md"
        index_path.write_text("# 链接索引\n\n无链接或 links_input.md 为空。\n", encoding="utf-8")
        print(f"已写入: {index_path}", file=__import__("sys").stderr)
        return

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    index_lines = [
        "# 链接索引",
        "",
        "| URL | 说明 | 本地文件 | 状态 |",
        "|-----|------|----------|------|",
    ]

    for item in links:
        url = item.get("url", "")
        description = item.get("description", "")
        fname = url_to_filename(url)
        local_path = out_dir / fname

        body, err = fetch_url(url)
        if err:
            index_lines.append(f"| {url} | {description} | - | 抓取失败: {err} |")
            continue
        local_path.write_text(body, encoding="utf-8")
        # 简单从 HTML 取 title
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", body, re.I)
        title = title_match.group(1).strip() if title_match else ""
        if title:
            description = description or title
        index_lines.append(f"| {url} | {description} | {fname} | 已抓取 |")

    index_path = out_dir / "links_index.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"已抓取 {sum(1 for l in index_lines if '已抓取' in l)} 个链接，索引: {index_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
