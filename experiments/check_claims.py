"""投稿主张的一致性审计：JSON 主张清单 ↔ 源章节 ↔ docs/22 表格。

背景：docs/22 是投稿骨架，里面每条主张都带一个数字。这个脚本要挡的是
"骨架里的数字和正文里的数字悄悄分叉"——改了一章忘了改另一章，投稿版
就会出现两个不同的数。规则只有两条：

1. 每条主张的 number 必须能在 source 指定的章节原文中找到；
2. docs/22 的表格必须同时出现该编号与同一个 number。

只依赖标准库；任何一条不满足即非零退出。用法：

    python experiments/check_claims.py [--claims experiments/paper_claims.json]
                                      [--skeleton docs/22_submission_skeleton.md]

退出码：0 = 全部一致；1 = 有缺失或分叉；2 = 输入文件缺失/JSON 非法。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="check paper claims consistency")
    p.add_argument("--claims", default="experiments/paper_claims.json")
    p.add_argument("--skeleton", default="docs/22_submission_skeleton.md")
    return p.parse_args()


def load_claims(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("claims 必须是非空列表")
    return claims


def split_table_rows(text: str) -> list[list[str]]:
    """抓出所有 markdown 表格行（以 | 开头、至少 4 列）。"""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.startswith("|---") or set(s) <= set("|-: "):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) >= 4:
            rows.append(cells)
    return rows


def main() -> int:
    args = parse_args()
    claims_path = ROOT / args.claims
    skeleton_path = ROOT / args.skeleton
    if not claims_path.exists():
        print(f"[FAIL] claims file not found: {claims_path}")
        return 2
    if not skeleton_path.exists():
        print(f"[FAIL] skeleton not found: {skeleton_path}")
        return 2

    try:
        claims = load_claims(claims_path)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] invalid claims file: {exc}")
        return 2

    skeleton = skeleton_path.read_text(encoding="utf-8-sig")
    rows = split_table_rows(skeleton)

    seen_ids: set[str] = set()
    problems: list[str] = []
    for claim in claims:
        cid = claim.get("id", "?")
        number = str(claim.get("number", "")).strip()
        source = claim.get("source", "")

        if cid in seen_ids:
            problems.append(f"{cid}: duplicate id")
        seen_ids.add(cid)

        if not number:
            problems.append(f"{cid}: empty number")
            continue

        src_path = ROOT / source
        if not src_path.exists():
            problems.append(f"{cid}: source not found: {source}")
            continue
        src_text = src_path.read_text(encoding="utf-8-sig")
        if number not in src_text:
            problems.append(f"{cid}: number '{number}' not found in {source}")

        if not re.search(rf"\b{re.escape(cid)}\b", skeleton):
            problems.append(f"{cid}: id missing in skeleton")
        if not any(cid in cells and any(number in c for c in cells) for cells in rows):
            problems.append(f"{cid}: no skeleton table row with id + number '{number}'")

    print(f"claims: {len(claims)}  skeleton table rows: {len(rows)}")
    if problems:
        print("\n[FAIL]")
        for p in problems:
            print("  -", p)
        return 1
    print("[OK] all claim numbers match source chapters and skeleton")
    return 0


if __name__ == "__main__":
    sys.exit(main())

