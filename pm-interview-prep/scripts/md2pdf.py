#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2pdf.py — 面试准备方案的 Markdown → 干净 PDF 可复现管线
============================================================
设计（关注点分离）：
  内容层  : 由 pm-interview-prep Skill 生成的 .md（语义，无版式）
  转译层  : markdown 库 → HTML（本脚本）
  呈现层  : 打印模板 print.css + Chrome 无头打印 → PDF
之所以不用 pandoc/weasyprint/typst：本机无这些工具；系统 Chrome 对
中文/emoji/表格渲染最稳，且不依赖 GTK 等系统库。

用法：
  python md2pdf.py <输入.md> <输出.pdf> [--chrome "C:/.../chrome.exe"]
"""
import argparse
import base64
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
DEFAULT_CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
CSS_FILE = HERE / "print.css"

# 转译层：Markdown 扩展，覆盖面试方案常用语法
MD_EXT = ["tables", "fenced_code", "toc", "nl2br", "sane_lists", "attr_list"]


def md_to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(
        md_text, extensions=MD_EXT, output_format="html5"
    )
    css = CSS_FILE.read_text(encoding="utf-8") if CSS_FILE.exists() else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>"""


_IMG_RE = re.compile(r'<img\s+[^>]*?src="([^"]+)"[^>]*?>')


def inline_local_images(html: str, base_dir: Path) -> str:
    """把本地图片（相对/绝对路径）内联为 base64 data URI，
    避免 Chrome 在临时目录打印时因路径解析失败而丢图。
    网络图（http/https）与已是 data: 的图跳过。"""
    def repl(m):
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        p = Path(src)
        if not p.is_absolute():
            p = base_dir / p
        p = p.resolve()
        if not p.exists():
            return m.group(0)
        mime, _ = mimetypes.guess_type(str(p))
        if not mime or not mime.startswith("image/"):
            mime = "image/svg+xml" if p.suffix.lower() == ".svg" else "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        new_src = f"data:{mime};base64,{b64}"
        return m.group(0).replace(f'src="{src}"', f'src="{new_src}"', 1)

    return _IMG_RE.sub(repl, html)


def find_chrome(arg_path: str | None) -> str:
    if arg_path and Path(arg_path).exists():
        return arg_path
    if Path(DEFAULT_CHROME).exists():
        return DEFAULT_CHROME
    # 退化到 PATH
    found = shutil.which("chrome") or shutil.which("google-chrome")
    if found:
        return found
    raise FileNotFoundError(
        "找不到 Chrome。请用 --chrome 指定 chrome.exe 路径。"
    )


def print_pdf(chrome: str, html_uri: str, tmp_pdf: Path) -> None:
    user_data = tempfile.mkdtemp(prefix="chrome_md2pdf_")
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--user-data-dir={user_data}",
        f"--print-to-pdf={tmp_pdf}",
        html_uri,
    ]
    # 不把 stderr 当错误：Chrome 常打印无关警告
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not tmp_pdf.exists():
        raise RuntimeError(
            "Chrome 未生成 PDF。stderr:\n" + (proc.stderr[-1500:] or "(空)")
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown → 干净 PDF（Chrome 无头）")
    ap.add_argument("input", help="输入 Markdown 文件路径")
    ap.add_argument("output", help="输出 PDF 文件路径")
    ap.add_argument("--chrome", default=None, help="chrome.exe 路径（可选）")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"[错误] 输入文件不存在: {in_path}", file=sys.stderr)
        return 2

    md_text = in_path.read_text(encoding="utf-8")
    title = in_path.stem
    html = md_to_html(md_text, title)
    html = inline_local_images(html, in_path.parent)

    tmp_dir = Path(tempfile.mkdtemp(prefix="md2pdf_"))
    tmp_html = tmp_dir / "doc.html"
    tmp_html.write_text(html, encoding="utf-8")
    tmp_pdf = tmp_dir / "doc.pdf"

    chrome = find_chrome(args.chrome)
    print(f"[1/3] 转译层完成：MD({len(md_text)}字) → HTML")
    print(f"[2/3] 调用 Chrome 无头打印：{chrome}")
    print_pdf(chrome, tmp_html.as_uri(), tmp_pdf)
    print(f"[3/3] 搬运至最终路径：{out_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp_pdf), str(out_path))

    size_kb = out_path.stat().st_size / 1024
    print(f"[完成] 已生成 PDF：{out_path}  ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
