#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
radar.py —— 零依赖纯 SVG 雷达图生成器（pm-interview-prep P3）

读取 `state_A-F.md` 的「状态总览」表，把 A–F 六维等级转成数值，
生成一张纯 SVG 雷达图（不依赖 matplotlib / Pillow / 任何第三方库）。

等级映射：高 = 5，中 = 3，低 = 1（5 分制，便于视觉区分）。

用法：
    python scripts/radar.py [--state <state_A-F.md 路径>] [--out <输出 svg 路径>]

默认：
    --state = 本脚本同级 ../kb/state_A-F.md
    --out   = 当前目录 / A-F_雷达图.svg
"""

import os
import re
import sys
import math

# ---- 默认路径（脚本位于 skill/scripts/，kb 在上级）----
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE = os.path.normpath(os.path.join(HERE, "..", "kb", "state_A-F.md"))
DEFAULT_OUT = os.path.join(os.getcwd(), "A-F_雷达图.svg")

LEVEL_MAP = {"高": 5, "中": 3, "低": 1}
# 维度标签：从 state 表第一列「**A** 决策深度 / 边界感」提取字母后的短名
FALLBACK_LABELS = {
    "A": "决策深度", "B": "数据口径", "C": "表达散",
    "D": "动机", "E": "学习深度", "F": "业务了解",
}
WARN_COLOR = "#e5484d"   # 高（红）
MID_COLOR = "#f5a623"    # 中（琥珀）
OK_COLOR = "#46b06b"     # 低（绿）


def parse_state(path):
    """从 state_A-F.md 解析六维 (字母, 短标签, 等级值, 原始等级字)。"""
    if not os.path.exists(path):
        sys.exit(f"[radar] 找不到状态文件：{path}")
    dims = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s.startswith("|"):
                continue
            # 匹配「| **A** 决策深度 / 边界感 | **高** | ...」
            m = re.match(r"\|\s*\*\*([A-F])\*\*\s*(.+?)\s*\|", s)
            if not m:
                continue
            letter = m.group(1)
            rest = s.split("|")
            # rest[1]=维度列, rest[2]=当前等级列
            if len(rest) < 3:
                continue
            level_cell = rest[2].strip().strip("*")
            val = None
            for k, v in LEVEL_MAP.items():
                if k in level_cell:
                    val = v
                    break
            if val is None:
                continue
            # 短标签：取字母后的第一段，去「 / 边界感」等
            label_raw = m.group(2).split(" / ")[0].strip()
            label = label_raw if label_raw else FALLBACK_LABELS.get(letter, letter)
            dims.append((letter, label, val, level_cell))
    if not dims:
        sys.exit("[radar] 未在状态文件解析到 A–F 等级，请检查 状态总览 表格式。")
    return dims


def build_svg(dims, out_path):
    n = len(dims)
    W, H = 600, 560
    cx, cy = W // 2, H // 2 - 10
    R = 180.0
    max_val = 5.0

    def vertex(i, value):
        ang = -math.pi / 2 + i * (2 * math.pi / n)
        r = (value / max_val) * R
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Microsoft YaHei, PingFang SC, sans-serif">'
    )
    # 背景
    parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    parts.append(f'<text x="{cx}" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#222">A–F 人设状态雷达图</text>')

    # 网格（1..5 层同心多边形）
    for g in range(1, 6):
        pts = " ".join(f"{vertex(i, g)[0]:.1f},{vertex(i, g)[1]:.1f}" for i in range(n))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#e3e3e3" stroke-width="1"/>')
    # 轴线
    for i in range(n):
        x, y = vertex(i, 5)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#cfcfcf" stroke-width="1"/>')

    # 数据多边形
    data_pts = " ".join(f"{vertex(i, dims[i][2])[0]:.1f},{vertex(i, dims[i][2])[1]:.1f}" for i in range(n))
    parts.append(f'<polygon points="{data_pts}" fill="rgba(63,130,246,0.22)" stroke="#3f82f6" stroke-width="2"/>')

    # 顶点 + 维度标签 + 等级色
    for i, (letter, label, val, lvl) in enumerate(dims):
        x, y = vertex(i, val)
        color = WARN_COLOR if lvl == "高" else (MID_COLOR if lvl == "中" else OK_COLOR)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        # 标签位置（顶点外扩）
        lx, ly = vertex(i, 5.35)
        anchor = "middle"
        if lx > cx + 20:
            anchor = "start"
        elif lx < cx - 20:
            anchor = "end"
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="14" '
            f'font-weight="bold" fill="{color}">{letter} {label}</text>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly+16:.1f}" text-anchor="{anchor}" font-size="11" fill="#888">{lvl}风险</text>'
        )

    # 图例
    ly0 = H - 46
    parts.append(f'<circle cx="40" cy="{ly0}" r="5" fill="{WARN_COLOR}"/><text x="52" y="{ly0+4}" font-size="12" fill="#555">高（重点准备）</text>')
    parts.append(f'<circle cx="40" cy="{ly0+20}" r="5" fill="{MID_COLOR}"/><text x="52" y="{ly0+24}" font-size="12" fill="#555">中（保持关注）</text>')
    parts.append(f'<circle cx="40" cy="{ly0+40}" r="5" fill="{OK_COLOR}"/><text x="52" y="{ly0+44}" font-size="12" fill="#555">低（已对冲/跳过）</text>')

    parts.append("</svg>")
    svg = "\n".join(parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return svg


def main():
    state = DEFAULT_STATE
    out = DEFAULT_OUT
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--state", "-s") and i + 1 < len(args):
            state = args[i + 1]; i += 2
        elif args[i] in ("--out", "-o") and i + 1 < len(args):
            out = args[i + 1]; i += 2
        else:
            i += 1
    dims = parse_state(state)
    build_svg(dims, out)
    labels = "、".join(f"{d[0]}={d[3]}" for d in dims)
    print(f"[radar] 已生成：{out}")
    print(f"[radar] 维度等级：{labels}")
    print(f"[radar] Markdown 嵌入片段：\n![A-F 雷达图]({os.path.basename(out)})")


if __name__ == "__main__":
    main()
