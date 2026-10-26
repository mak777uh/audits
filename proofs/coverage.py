"""Генератор coverage.json: какое утверждение к какому классу инвариантов относится.

Честно о методе: классы определяются по ключевым словам в имени и теле теоремы, то есть
это **разметка, а не доказательство покрытия**. Файл нужен для двух вещей:
  1. ревьюер видит, что именно покрыто, а что нет — без чтения шести файлов;
  2. CI проверяет, что каждая теорема из proofs/*.lean попала в матрицу (ничего не потеряно).

    python proofs/coverage.py            # пересобрать coverage.json
    python proofs/coverage.py --check     # проверить, что матрица полная (для CI)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

CLASSES = {
    "accounting-conservation": ("учёт: сумма не появляется и не исчезает", ["total", "sum", "balance", "ledger", "conserv", "append"]),
    "authorization":           ("права: кто может менять состояние", ["auth", "owner", "agent", "sender", "permission", "no_source"]),
    "idempotency":             ("повторный вызов не удваивает эффект", ["dup", "twice", "idemp", "repeat", "step_dup"]),
    "escrow-release":          ("выпуск эскроу: условия и границы", ["escrow", "release", "finalize", "cancel", "locked"]),
    "upgrade-safety":          ("апгрейд: состояние и права при замене кода", ["upgrade", "impl", "proxy", "slot"]),
    "call-ordering":           ("порядок кросс-контрактных вызовов", ["stack", "order", "call", "sequence"]),
}


def theorem_names(src: str) -> list[tuple[str, str]]:
    """(имя, тело) для каждой теоремы/леммы."""
    out = []
    for m in re.finditer(r"^\s*(?:theorem|lemma)\s+([A-Za-z0-9_\u0300-\u036f']+)", src, re.M):
        start = m.start()
        nxt = re.search(r"^\s*(?:theorem|lemma|def|end)\s", src[m.end():], re.M)
        body = src[start: m.end() + (nxt.start() if nxt else 400)]
        out.append((m.group(1), body))
    return out


def build() -> dict:
    proofs = pathlib.Path(__file__).parent
    rows = []
    for f in sorted(proofs.glob("*.lean")):
        src = f.read_text(encoding="utf-8")
        for name, body in theorem_names(src):
            low = (name + " " + body).lower()
            hits = [c for c, (_, kw) in CLASSES.items() if any(k in low for k in kw)]
            rows.append({"file": f.name, "theorem": name, "classes": hits})
    covered = {r["theorem"] for r in rows}
    matrix = {}
    for c, (title, _) in CLASSES.items():
        thms = [r["theorem"] for r in rows if c in r["classes"]]
        matrix[c] = {
            "title": title,
            "status": "proved-in-lean" if thms else "not-covered",
            "theorems": thms,
            "note": "разметка по ключевым словам, см. proofs/coverage.py" if thms else "нет теоремы с этим классом",
        }
    return {"generated_by": "proofs/coverage.py",
            "method": "keyword labelling of theorem name+body; not a proof of coverage",
            "theorems_total": len(rows),
            "classes": matrix,
            "theorems": sorted(covered)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    data = build()
    out = pathlib.Path(__file__).parent / "coverage.json"
    if a.check:
        if not out.exists():
            print("coverage.json отсутствует"); return 1
        old = json.loads(out.read_text(encoding="utf-8"))
        if sorted(old.get("theorems", [])) != data["theorems"]:
            print("::error::coverage.json устарел: список теорем не совпадает с proofs/*.lean")
            print("  добавьте:", sorted(set(data["theorems"]) - set(old.get("theorems", []))))
            print("  исчезли:", sorted(set(old.get("theorems", [])) - set(data["theorems"])))
            return 1
        print(f"coverage.json актуален: {data['theorems_total']} утверждений")
        return 0
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"coverage.json: {data['theorems_total']} утверждений")
    for c, v in data["classes"].items():
        print(f"  {c:24} {v['status']:14} теорем: {len(v['theorems'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
