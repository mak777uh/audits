"""Аксиомный аудит Lean-моделей.

Печатает аксиомы каждой теоремы/леммы и падает (exit 1), если появится что-то, кроме
propext / Classical.choice / Quot.sound — то есть если доказательство опирается на
собственную аксиому или на `sorryAx`.

    python proofs/axioms_check.py            # проверить и напечатать
    python proofs/axioms_check.py --quiet     # только вердикт
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = {"sorryAx"}


def names(src: str) -> list[str]:
    out = []
    for m in re.finditer(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?(?:theorem|lemma)\s+([A-Za-z0-9_\u0300-\u036f']+)",
                         src, re.M):
        out.append(m.group(1))
    return out


def check_file(path: pathlib.Path) -> tuple[bool, list[tuple[str, set[str]]]]:
    src = path.read_text(encoding="utf-8")
    thms = names(src)
    if not thms:
        return True, []
    probe = src + "\n\n" + "\n".join(f"#print axioms {t}" for t in thms) + "\n"
    tmp = path.with_suffix(".axioms.lean")
    tmp.write_text(probe, encoding="utf-8")
    try:
        r = subprocess.run(["lean", str(tmp)], capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace")
    finally:
        tmp.unlink(missing_ok=True)
    text = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and "does not depend on any axioms" not in text:
        if "error" in text.lower():
            print(f"  {path.name}: lean вернул ошибку\n{text[:600]}")
            return False, []
    rows = []
    for m in re.finditer(r"'([^']+)' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", text):
        name = m.group(1)
        ax = set() if m.group(2).startswith("does not") else {a.strip() for a in (m.group(3) or "").split(",") if a.strip()}
        rows.append((name, ax))
    return True, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    files = sorted(pathlib.Path(__file__).parent.glob("*.lean"))
    bad, total, axiomless = [], 0, 0
    for f in files:
        ok, rows = check_file(f)
        if not ok:
            bad.append((f.name, "lean error"))
            continue
        for name, ax in rows:
            total += 1
            if not ax:
                axiomless += 1
            extra = ax - ALLOWED
            if extra & FORBIDDEN:
                bad.append((f"{f.name}::{name}", "sorryAx"))
            elif extra:
                bad.append((f"{f.name}::{name}", ", ".join(sorted(extra))))
            if not a.quiet:
                print(f"{f.name:16} {name:38} {'(no axioms)' if not ax else ', '.join(sorted(ax))}")
    print(f"\nпроверено утверждений: {total}, без аксиом: {axiomless}, нарушений: {len(bad)}")
    for where, why in bad:
        print(f"  FAIL {where}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
