#!/usr/bin/env python3
"""一键跑完投稿前的五道硬门 + 三道文档门，并打印就绪矩阵。

为什么不散着跑：投稿前一天最怕"漏跑一个脚本"。这里把 8 项检查按 26 章的编号
固定下来，任一项失败退出非零，输出可直接贴进 26 章的表格。

用法：python experiments/check_all.py
退出码：0=全部门通过；1=至少一门失败。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted((ROOT / "docs").glob("*.md"))
TEXT_FILES = [ROOT / "README.md", ROOT / "references.md", *DOCS]
LINK_RE = re.compile(r"\]\(([^)#]+?)(#[^)]*)?\)")
REF_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def check_links() -> tuple[bool, str]:
    broken: list[str] = []
    total = 0
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in LINK_RE.finditer(line):
                target = m.group(1)
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                total += 1
                if not (path.parent / target).resolve().exists():
                    broken.append(f"{path.relative_to(ROOT)}:{lineno} -> {target}")
    detail = f"{total} 条内链，{len(broken)} 断"
    if broken:
        detail += "；" + "；".join(broken[:5])
    return not broken, detail


def check_refs() -> tuple[bool, str]:
    refs = ROOT / "references.md"
    nums = []
    for line in refs.read_text(encoding="utf-8").splitlines():
        m = REF_ROW_RE.match(line)
        if m:
            nums.append(int(m.group(1)))
    ok = nums == list(range(1, len(nums) + 1)) and len(nums) > 0
    return ok, f"{len(nums)} 条编号，连续={ok}"


def check_escaping() -> tuple[bool, str]:
    hits = [
        str(p.relative_to(ROOT))
        for p in TEXT_FILES
        if "\\n" in p.read_text(encoding="utf-8")
    ]
    return not hits, "无字面 \\n" if not hits else "残留：" + ", ".join(hits[:5])


def run_script(name: str) -> tuple[bool, str]:
    path = ROOT / "experiments" / name
    proc = subprocess.run(
        [sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True
    )
    last = (proc.stdout.strip().splitlines() or [""])[-1]
    return proc.returncode == 0, last[:120] if last else f"退出 {proc.returncode}"


def main() -> int:
    gates = [
        ("D1 内链", check_links),
        ("D2 文献编号", check_refs),
        ("D3 转义残留", check_escaping),
        ("D4 主张-正文", lambda: run_script("check_claims.py")),
        ("D5 Table 1", lambda: run_script("check_related_table.py")),
        ("D6 引言编号", lambda: run_script("check_intro.py")),
        ("D7 材料包", lambda: run_script("check_submission.py")),
        ("D8 数据验收", lambda: run_script("validate_runs.py")),
    ]
    width = max(len(name) for name, _ in gates)
    rows: list[str] = []
    failed = 0
    for name, fn in gates:
        ok, detail = fn()
        if not ok:
            failed += 1
        rows.append(f"| {name.ljust(width)} | {'PASS' if ok else 'FAIL'} | {detail} |")
    print(f"docs: {len(DOCS)} 个；文件: {len(TEXT_FILES)} 个")
    print("| 门 | 结果 | 说明 |")
    print("| --- | --- | --- |")
    for row in rows:
        print(row)
    print(f"\n结论：{len(gates) - failed}/{len(gates)} 通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
