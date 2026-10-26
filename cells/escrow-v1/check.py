"""check.py - one command that turns the escrow-v1 cell into a verdict and a receipt.

What it does, in order:
  1. hashes the statement file (SPEC.md) and the model (Escrow.lean) with sha256 - these are the inputs;
  2. compiles the model with `lean` and records the exit code, the toolchain version and stdout/stderr hashes;
  3. greps the model for `sorry` / `admit` and refuses a pass if either appears;
  4. asks Lean for the axioms of every theorem and refuses a pass if anything outside
     {propext, Classical.choice, Quot.sound} shows up;
  5. writes receipt.json - a deterministic JSON document bound to (statement hash, model hash).

Verdict is `pass` only if every step above succeeded. Anything else is `fail` with the reason.

    python cells/escrow-v1/check.py            # write receipt.json
    python cells/escrow-v1/check.py --check     # verify the existing receipt still matches (for CI)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).parent
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = ("sorry", "admit")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lean_bin() -> str:
    return shutil.which("lean") or "lean"


def axioms(model: pathlib.Path, names: list[str]) -> tuple[dict, str]:
    probe = model.read_text(encoding="utf-8") + "\n\n" + "\n".join(
        f"#print axioms EscrowV1.{n}" for n in names) + "\n"
    tmp = HERE / "_axioms_probe.lean"
    tmp.write_text(probe, encoding="utf-8")
    try:
        r = subprocess.run([lean_bin(), str(tmp)], capture_output=True, text=True, timeout=900,
                           encoding="utf-8", errors="replace")
    finally:
        tmp.unlink(missing_ok=True)
    out = (r.stdout or "") + (r.stderr or "")
    found = {}
    for m in re.finditer(r"'EscrowV1\.([A-Za-z0-9_]+)' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", out):
        found[m.group(1)] = [] if m.group(2).startswith("does not") else [
            a.strip() for a in (m.group(3) or "").split(",") if a.strip()]
    return found, out


def run(write: bool) -> int:
    spec, model = HERE / "SPEC.md", HERE / "Escrow.lean"
    src = model.read_text(encoding="utf-8")
    names = re.findall(r"theorem\s+([A-Za-z0-9_]+)", src)

    bad_tokens = [t for t in FORBIDDEN if re.search(rf"(?<![A-Za-z_]){t}(?![A-Za-z_])", src)]
    t0 = time.time()
    proc = subprocess.run([lean_bin(), str(model)], capture_output=True, text=True, timeout=900,
                          encoding="utf-8", errors="replace")
    wall = int((time.time() - t0) * 1000)
    ver = subprocess.run([lean_bin(), "--version"], capture_output=True, text=True, timeout=120,
                         encoding="utf-8", errors="replace").stdout.strip()
    ax, ax_raw = axioms(model, names)

    extra = {n: [a for a in v if a not in ALLOWED] for n, v in ax.items()}
    extra = {n: v for n, v in extra.items() if v}

    verdict = "pass"
    error = None
    if bad_tokens:
        verdict, error = "fail", f"forbidden tokens in model: {bad_tokens}"
    elif proc.returncode != 0:
        verdict, error = "fail", f"lean exited {proc.returncode}"
    elif not ax:
        verdict, error = "fail", "no axiom report produced"
    elif extra:
        verdict, error = "fail", f"axioms outside allowlist: {extra}"

    receipt = {
        "cell": "escrow-v1",
        "statement_sha256": sha256(spec),
        "model_sha256": sha256(model),
        "toolchain": ver,
        "theorems": sorted(names),
        "axioms": ax,
        "forbidden_tokens": bad_tokens,
        "verdict": verdict,
        "error": error,
        "lean_exit_code": proc.returncode,
        "wall_clock_ms": wall,
        "stdout_sha256": hashlib.sha256((proc.stdout or "").encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256((proc.stderr or "").encode()).hexdigest(),
    }
    out = HERE / "receipt.json"

    if write:
        out.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=1))
        return 0 if verdict == "pass" else 1

    if not out.exists():
        print("::error::receipt.json отсутствует"); return 1
    old = json.loads(out.read_text(encoding="utf-8"))
    if old.get("statement_sha256") != receipt["statement_sha256"]:
        print("::error::SPEC.md изменился, квитанция устарела"); return 1
    if old.get("model_sha256") != receipt["model_sha256"]:
        print("::error::Escrow.lean изменился, квитанция устарела"); return 1
    if old.get("verdict") != "pass" or receipt["verdict"] != "pass":
        print(f"::error::вердикт не pass: {old.get('verdict')} / {receipt['verdict']}"); return 1
    print(f"квитанция актуальна: {len(names)} теорем, вердикт pass")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="проверить, что receipt.json соответствует файлам")
    a = ap.parse_args()
    return run(write=not a.check)


if __name__ == "__main__":
    sys.exit(main())
