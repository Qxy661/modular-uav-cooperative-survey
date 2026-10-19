"""相关工作对照表的结构校验：docs/23 表 ↔ references 编号。

要挡的是"表里引用了不存在的文献编号"和"表格列被改坏"——这两类错误在
markdown 里不会报错，只会在审稿时被发现。规则：

1. docs/23 表里每个 [n] 必须在 1–86 且存在于 references.md 的编号表；
2. 每条表的行至少 6 列（六列结构：工作/平台/通信/力感知/故障/差异）；
3. 打印行数、去重引用数，便于与 22 章的 Table 1 对齐。

只依赖标准库；不满足即非零退出。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "docs/23_related_work_table.md"
REFS = ROOT / "references.md"

CITE = re.compile(r"\[(\d+)\]")
REF_ROW = re.compile(r"^\|\s*(\d+)\s*\|")


def ref_ids(text: str) -> set[int]:
    ids = {}
    for line in text.splitlines():
        m = REF_ROW.match(line.strip())
        if m:
            ids[int(m.group(1))] = True
    return set(ids)


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("| ["):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        rows.append(cells)
    return rows


def main() -> int:
    if not TABLE.exists():
        print(f"[FAIL] table not found: {TABLE}")
        return 2
    if not REFS.exists():
        print(f"[FAIL] references not found: {REFS}")
        return 2

    refs = ref_ids(REFS.read_text(encoding="utf-8-sig"))
    rows = table_rows(TABLE.read_text(encoding="utf-8-sig"))
    problems: list[str] = []
    cited: set[int] = set()

    if not rows:
        problems.append("表里没有任何行")

    for i, cells in enumerate(rows, start=1):
        if len(cells) < 6:
            problems.append(f"row {i}: only {len(cells)} columns (need 6)")
        ids = [int(x) for x in CITE.findall(cells[0])] if cells else []
        if not ids:
            problems.append(f"row {i}: no [n] citation in first column")
        for n in ids:
            cited.add(n)
            if n not in refs:
                problems.append(f"row {i}: reference [{n}] not in references.md")

    print(f"rows: {len(rows)}  unique refs: {len(cited)}  refs in file: {len(refs)}")
    if problems:
        print("\n[FAIL]")
        for p in problems:
            print("  -", p)
        return 1
    print("[OK] related-work table structure and citations are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())

