#!/usr/bin/env python3
"""第 24 章文字稿的硬校验：主张编号与引用编号都必须存在，且 15 条主张全部用到。

为什么单独写一个：22 章的 C1–C15 是投稿审计表的唯一入口，24 章要在正文里逐条
引用它们。手写时最容易犯的错是"引了一个不存在的编号"（C16）或"漏引一条主张"，
这两种错在 PDF 里都看不出来，只有脚本能查。引用编号同理：`[84]` 写成 `[999]`
不会被任何 Markdown 渲染器报错。

用法：python experiments/check_intro.py
退出码：0=通过；1=有未知/漏引主张，或引用越界。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTRO = ROOT / "docs" / "24_intro_related_prose.md"
CLAIMS = ROOT / "experiments" / "paper_claims.json"
REFS = ROOT / "references.md"

# 主张编号：C1..C15，不能用 C 开头后接多位数字时把 C1 误判成 C10 的前缀。
CLAIM_RE = re.compile(r"(?<![A-Za-z0-9])C(\d{1,2})(?!\d)")
# 引用编号：只认"纯编号列表"形式，[22.2](...) 这类章节链接不在其中。
CITE_RE = re.compile(r"\[([0-9][0-9,\s\u2013-]*)\]")


def load_claim_ids() -> set[int]:
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return {int(c["id"][1:]) for c in data["claims"]}


def load_ref_ids() -> set[int]:
    ids: set[int] = set()
    for line in REFS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|", line)
        if m:
            ids.add(int(m.group(1)))
    return ids


def expand_cites(body: str) -> set[int]:
    out: set[int] = set()
    for m in CITE_RE.finditer(body):
        for part in m.group(1).split(","):
            part = part.strip().replace("\u2013", "-")
            if not part:
                continue
            if "-" in part:
                lo, hi = part.split("-", 1)
                if lo.strip().isdigit() and hi.strip().isdigit():
                    out.update(range(int(lo), int(hi) + 1))
            elif part.isdigit():
                out.add(int(part))
    return out


def main() -> int:
    if not INTRO.exists():
        print(f"FAIL: {INTRO.relative_to(ROOT)} 不存在")
        return 1
    body = INTRO.read_text(encoding="utf-8")
    claim_ids = load_claim_ids()
    ref_ids = load_ref_ids()

    used_claims = {int(m.group(1)) for m in CLAIM_RE.finditer(body)}
    unknown_claims = sorted(used_claims - claim_ids)
    missing_claims = sorted(claim_ids - used_claims)

    used_refs = expand_cites(body)
    unknown_refs = sorted(used_refs - ref_ids)

    print(f"chapter: {INTRO.name}")
    print(f"claims   : used {len(used_claims)}/{len(claim_ids)}")
    print(f"citations: used {len(used_refs)} unique, refs table {len(ref_ids)}")
    ok = True
    if unknown_claims:
        print(f"FAIL: 正文引用了不存在的主张 {['C%d' % n for n in unknown_claims]}")
        ok = False
    if missing_claims:
        print(f"FAIL: 正文漏引主张 {['C%d' % n for n in missing_claims]}")
        ok = False
    if unknown_refs:
        print(f"FAIL: 正文引用了不存在的文献编号 {unknown_refs}")
        ok = False
    if ok:
        print("PASS: 主张编号与引用编号全部有效，且 C1–C15 全部出现")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
