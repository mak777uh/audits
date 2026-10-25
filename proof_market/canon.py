r"""canon.py — канонизация утверждения в хеш (спецификация заказа v0).

Правила (совпадают с TASK-spec-v9 §3.2):
  1. UTF-8, NFC, LF, без хвостовых пробелов;
  2. hash = sha256(domain || 0x00 || kind || 0x00 || normalized_bytes);
  3. domain = "vecdht/paid_order/v1".

    python canon.py <file> [--kind lean_proof|test_conformance|repro_run]
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import unicodedata

DOMAIN = b"vecdht/paid_order/v1"


def normalize(text: str) -> bytes:
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).encode("utf-8")


def statement_hash(text: str, kind: str) -> str:
    payload = DOMAIN + b"\x00" + kind.encode() + b"\x00" + normalize(text)
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--kind", default="lean_proof",
                    choices=["lean_proof", "test_conformance", "repro_run"])
    a = ap.parse_args()
    p = pathlib.Path(a.file)
    text = p.read_text(encoding="utf-8", errors="strict")
    print(statement_hash(text, a.kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())
