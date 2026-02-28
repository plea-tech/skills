#!/usr/bin/env python3
"""
链接抓取与缓存：读取 links_input.md（或 worklist 中的链接），抓取网页并保存到 extracted_content/links，
生成 links_index.md 供大模型本地阅读，无需重复请求外网。
可选 --with-images：解析 HTML 中的图片并下载到 images/，生成 links_images_manifest.md 供 Step 3 选图。
"""
import argparse
import io
import json
import hashlib
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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


def fetch_url(url: str, ssl_context: ssl.SSLContext | None = None) -> tuple[str, str | None]:
    """抓取 URL，返回 (body_text, error_message)。ssl_context 为 None 时使用默认验证；可传入不验证证书的 context（--insecure）。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CompetitorAnalysis/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
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


def extract_img_srcs_from_html(html: str, base_url: str) -> list[tuple[str, str]]:
    """
    从 HTML 中解析图片 URL 与 alt。返回 [(absolute_url, alt_text), ...]。
    支持 <img src="..."> 与 data-src（懒加载），相对 URL 按 base_url 解析；跳过 data: 内联图。
    """
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    # 匹配 <img ...> 标签，提取 src / data-src 与 alt
    for tag in re.findall(r"<img[^>]*>", html, re.I):
        src = None
        m = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if m:
            src = m.group(1).strip()
        if not src or src.startswith("data:"):
            m = re.search(r'\bdata-src\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if m:
                src = m.group(1).strip()
        if not src or src.startswith("data:"):
            continue
        abs_url = urljoin(base_url, src)
        if abs_url in seen:
            continue
        seen.add(abs_url)
        alt = ""
        m = re.search(r'\balt\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        if m:
            alt = (m.group(1) or "").strip()
        out.append((abs_url, alt))
    return out


def get_image_extension(url: str, content_type: str | None) -> str:
    """根据 URL 路径或 Content-Type 返回扩展名（含点），默认 .png。"""
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if "jpeg" in ct or "jpg" in ct:
            return ".jpg"
        if "png" in ct:
            return ".png"
        if "gif" in ct:
            return ".gif"
        if "webp" in ct:
            return ".webp"
        if "svg" in ct:
            return ".svg"
    path = urlparse(url).path
    if path and "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ("jpg", "jpeg", "png", "gif", "webp", "svg"):
            return "." + ext
    return ".png"


def fetch_image(
    img_url: str,
    save_path: Path,
    timeout: int = 15,
    user_agent: str = "CompetitorAnalysis/1.0",
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[bool, bytes | None, Path | None]:
    """
    下载图片到 save_path，返回 (成功, 原始字节, 实际写入路径)。
    成功时已写入文件；扩展名按 URL/Content-Type 确定，实际路径可能带 .jpg 等。
    """
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type")
        ext = get_image_extension(img_url, content_type)
        if save_path.suffix.lower() != ext:
            save_path = save_path.with_suffix(ext)
        save_path.write_bytes(raw)
        return True, raw, save_path
    except Exception:
        return False, None, None


def get_image_size_from_bytes(data: bytes) -> tuple[int | None, int | None]:
    """从图片字节获取 (width, height)，失败返回 (None, None)。"""
    if not HAS_PIL or not data:
        return None, None
    try:
        pil = Image.open(io.BytesIO(data))
        return pil.size
    except Exception:
        return None, None


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
    parser.add_argument(
        "--with-images",
        action="store_true",
        help="同时解析网页中的图片并下载到 images 目录，生成 links_images_manifest.md 供 Step 3 选图",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="图片输出目录；默认 output-dir 的上级目录下的 images（即 extracted_content/<竞品名>/images）",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        metavar="N",
        help="与 --with-images 同用：宽或高小于 N 像素的图片不保存（默认 0 不过滤；建议 120 过滤 logo/图标）",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="与 --with-images 同用：links 图片 manifest 路径；默认 output-dir 上级目录下的 links_images_manifest.md",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="跳过 HTTPS 证书验证（用于证书过期或自签名的站点，存在中间人风险，仅建议在可信环境使用）",
    )
    args = parser.parse_args()

    ssl_ctx: ssl.SSLContext | None = None
    if getattr(args, "insecure", False):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

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
        if not links:
            if not links_input.is_file():
                print(f"未找到链接列表文件: {links_input}", file=__import__("sys").stderr)
                print("请确认 --ref-dir 指向的目录下存在 links_input.md（例如技能内为 .cursor/skills/Competitor_Analysis_Report_d1/references/Test）", file=__import__("sys").stderr)
            else:
                print(f"links_input.md 中未解析到有效链接（当前查找: {links_input}）", file=__import__("sys").stderr)
                print("每行需为以 http:// 或 https:// 开头的 URL，可选空格后跟说明；# 开头的行会被忽略。", file=__import__("sys").stderr)
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

    with_images = getattr(args, "with_images", False)
    images_dir: Path | None = None
    manifest_path: Path | None = None
    manifest_entries: list[tuple[str, int, str, str, str]] = []  # (page_url, seq, filename, alt_or_context, size_str)
    min_size = max(0, getattr(args, "min_size", 0))
    if with_images:
        images_dir = (args.images_dir or out_dir.parent / "images").resolve()
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = (args.manifest or out_dir.parent / "links_images_manifest.md").resolve()
    if min_size > 0 and not HAS_PIL:
        print("警告: --min-size 需要 PIL，未安装则不过滤尺寸；pip install Pillow", file=__import__("sys").stderr)

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

        body, err = fetch_url(url, ssl_context=ssl_ctx)
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

        # 可选：解析并下载页面中的图片，写入 images_dir 并记录到 manifest
        if with_images and images_dir is not None:
            page_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            for seq, (img_url, alt) in enumerate(extract_img_srcs_from_html(body, url), start=1):
                stem = f"links_{page_hash}_img_{seq:03d}"
                save_path = images_dir / f"{stem}.png"
                ok, raw, written_path = fetch_image(img_url, save_path, ssl_context=ssl_ctx)
                if not ok or written_path is None:
                    continue
                size_str = ""
                if raw and (min_size > 0 and HAS_PIL):
                    w, h = get_image_size_from_bytes(raw)
                    if w is not None and h is not None:
                        size_str = f"{w}×{h}"
                        if w < min_size or h < min_size:
                            try:
                                written_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                            continue
                elif raw and HAS_PIL:
                    w, h = get_image_size_from_bytes(raw)
                    if w is not None and h is not None:
                        size_str = f"{w}×{h}"
                context = f"页面: {url}"
                if alt:
                    context += f" | alt: {alt}"
                manifest_entries.append((url, seq, written_path.name, context, size_str))

    index_path = out_dir / "links_index.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"已抓取 {sum(1 for l in index_lines if '已抓取' in l)} 个链接，索引: {index_path}", file=__import__("sys").stderr)

    if with_images and manifest_path is not None and manifest_entries:
        manifest_header = [
            "# 链接页图片列表",
            "",
            "- 源文件: 链接",
        ]
        if min_size > 0:
            manifest_header.append(f"- 过滤: 宽或高 < {min_size}px 的图片已跳过")
        manifest_header.extend([
            "",
            "| 序号 | 文件名 | 宽×高 | 周边文字 | 说明 |",
            "|------|--------|-------|----------|------|",
        ])
        def cell(s: str) -> str:
            return (s or "").replace("|", "，")


        manifest_body = [
            f"| {seq} | {fname} | {size_str} | {cell(context)} | |"
            for (_url, seq, fname, context, size_str) in manifest_entries
        ]
        manifest_path.write_text(
            "\n".join(manifest_header + manifest_body),
            encoding="utf-8",
        )
        print(f"已下载 {len(manifest_entries)} 张网页图片，manifest: {manifest_path}", file=__import__("sys").stderr)
    elif with_images and manifest_path is not None and not manifest_entries:
        manifest_path.write_text(
            "# 链接页图片列表\n\n- 源文件: 链接\n\n未解析到图片或均被过滤。\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
