#!/usr/bin/env python3
"""投稿材料包（25 章）的硬校验：Highlights 字数、主张编号、占位符、内链、数据声明。

为什么需要：Highlights 的 85 字符上限是期刊系统里的硬性截断，超一个字符就可能被
拒收；主张编号与占位符则是"PDF 里看不出来"的错误。把这三件事交给脚本，比在投稿
前一天肉眼数 5 行字可靠。

用法：python experiments/check_submission.py
退出码：0=通过；1=有任一检查失败（失败项逐条打印）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "25_submission_package.md"
CLAIMS = ROOT / "experiments" / "paper_claims.json"
MAX_HIGHLIGHT = 85
MAX_HIGHLIGHTS = 5
MIN_HIGHLIGHTS = 3
MIN_DISTINCT_CLAIMS = 8


def claim_ids() -> set[int]:
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return {int(c["id"][1:]) for c in data["claims"]}


def section(body: str, start: str, end: str) -> str:
    i = body.index(start)
    j = body.index(end, i)
    return body[i:j]


def highlights(body: str) -> list[str]:
    sec = section(body, "## 25.2", "## 25.3")
    out = []
    for line in sec.splitlines():
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def main() -> int:
    if not DOC.exists():
        print(f"FAIL: {DOC.relative_to(ROOT)} 不存在")
        return 1
    body = DOC.read_text(encoding="utf-8")
    problems: list[str] = []

    # 1. Highlights：3–5 条，每条 ≤85 字符
    hl = highlights(body)
    if not (MIN_HIGHLIGHTS <= len(hl) <= MAX_HIGHLIGHTS):
        problems.append(f"Highlights 条数 {len(hl)} 不在 {MIN_HIGHLIGHTS}–{MAX_HIGHLIGHTS}")
    for k, item in enumerate(hl, 1):
        if len(item) > MAX_HIGHLIGHT:
            problems.append(f"Highlight {k} 长 {len(item)} 字符（上限 {MAX_HIGHLIGHT}）：{item}")
        if not item.endswith("."):
            problems.append(f"Highlight {k} 不以句号结尾：{item}")

    # 2. 主张编号：只能引用 C1–C15，且至少覆盖 MIN_DISTINCT_CLAIMS 条
    known = claim_ids()
    used = {int(n) for n in re.findall(r"(?<![A-Za-z0-9])C(\d{1,2})(?!\d)", body)}
    unknown = sorted(used - known)
    if unknown:
        problems.append(f"引用了不存在的主张 {['C%d' % n for n in unknown]}")
    if len(used) < MIN_DISTINCT_CLAIMS:
        problems.append(f"主张覆盖过少：{len(used)} < {MIN_DISTINCT_CLAIMS}")

    # 3. 占位符
    for token in ("TODO", "TBD", "XXX", "FIXME", "<insert"):
        if token.lower() in body.lower():
            problems.append(f"残留占位符 {token}")

    # 4. 数据可用性必须写清目录、格式与验收脚本
    for token in ("runs/", "JSONL", "validate_runs.py"):
        if token not in body:
            problems.append(f"Data availability 缺关键字 {token}")

    # 5. Cover letter 必备要素
    if "Dear Editor" not in body:
        problems.append("Cover letter 缺称呼 Dear Editor")
    if len(re.findall(r"\*\*Q\d\.", body)) < 6:
        problems.append("审稿问答少于 6 条")

    # 6. 本地 Markdown 链接必须存在
    for m in re.finditer(r"\]\(([^)#]+?)(#[^)]*)?\)", body):
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (DOC.parent / target).resolve().exists():
            problems.append(f"断链：{target}")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"PASS: highlights {len(hl)}/{len(hl)}，均 ≤{MAX_HIGHLIGHT} 字符；"
          f"主张 {len(used)} 条全部存在；无占位符；内链 0 断；数据声明完整")
    return 0


if __name__ == "__main__":
    sys.exit(main())
