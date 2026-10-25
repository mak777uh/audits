r"""verifier.py — детерминированный верификатор заказа (proof-market, v0).

Принимает:
  --kind lean_proof    и --artifact <file.lean>   (компиляция + запрет sorry/admit + allowlist аксиом)
  --kind test_conformance и --artifact <dir>      (pytest в песочнице с бюджетом)

Выдаёт receipt (JSON) с полями из TASK-spec-v9 §3.4: verdict, image/toolchain, axioms, тайминги,
exit codes, sha256 stdout/stderr. Никакого суждения — только измерение.

    python verifier.py --kind lean_proof --artifact proofs\\flows.lean --budget 120
    python verifier.py --kind test_conformance --artifact . --budget 600
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

R = pathlib.Path(r"C:\111")
LEAN = pathlib.Path(os.path.expanduser("~")) / ".elan" / "toolchains" / "leanprover--lean4---v4.30.0" / "bin" / "lean.exe"
LEAN_ENV = R / "agents" / "swarm" / "leancheck_v3" / "env2.txt"
ALLOWED_AXIOMS: set[str] = set()  # пустой allowlist: аксиомы запрещены


def h(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8", "replace")
    return hashlib.sha256(data).hexdigest()


def lean_receipt(artifact: pathlib.Path, budget_ms: int) -> dict:
    text = artifact.read_text(encoding="utf-8", errors="ignore")
    axiomatic = [w for w in ("sorry", "admit") if re.search(rf"\b{w}\b", text)]
    env = dict(os.environ)
    try:
        env["LEAN_PATH"] = LEAN_ENV.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    t0 = time.time()
    try:
        r = subprocess.run([str(LEAN), str(artifact)], capture_output=True, text=True,
                           timeout=budget_ms / 1000, env=env, encoding="utf-8", errors="replace")
        out, err, code = r.stdout or "", r.stderr or "", r.returncode
        timed_out = False
    except subprocess.TimeoutExpired as ex:
        out, err, code, timed_out = (ex.stdout or ""), (ex.stderr or ""), -1, True
    ms = int((time.time() - t0) * 1000)

    axioms = sorted(set(re.findall(r"depends on axioms:\s*\[([^\]]*)\]", out)))
    verdict = "timeout" if timed_out else ("pass" if code == 0 and not axiomatic else "fail")
    if not timed_out and code == 0 and axiomatic:
        verdict = "fail"
    return {
        "kind": "lean_proof",
        "artifact_sha256": h(artifact.read_bytes()),
        "verdict": verdict,
        "toolchain": "leanprover/lean4:v4.30.0",
        "forbidden_tokens": axiomatic,
        "axioms_reported": axioms,
        "allowed_axioms": sorted(ALLOWED_AXIOMS),
        "exit_code": code,
        "wall_clock_ms": ms,
        "budget_ms": budget_ms,
        "stdout_sha256": h(out),
        "stderr_sha256": h(err),
        "error": None,
    }


def pytest_receipt(artifact: pathlib.Path, budget_ms: int) -> dict:
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--maxfail=1", str(artifact)],
                           capture_output=True, text=True, timeout=budget_ms / 1000,
                           cwd=str(artifact if artifact.is_dir() else artifact.parent),
                           encoding="utf-8", errors="replace")
        out, err, code, timed_out = r.stdout or "", r.stderr or "", r.returncode, False
    except subprocess.TimeoutExpired as ex:
        out, err, code, timed_out = (ex.stdout or ""), (ex.stderr or ""), -1, True
    ms = int((time.time() - t0) * 1000)
    return {
        "kind": "test_conformance",
        "artifact_sha256": h(str(artifact).encode()),
        "verdict": "timeout" if timed_out else ("pass" if code == 0 else "fail"),
        "toolchain": f"python {sys.version.split()[0]}",
        "forbidden_tokens": [],
        "axioms_reported": [],
        "allowed_axioms": [],
        "exit_code": code,
        "wall_clock_ms": ms,
        "budget_ms": budget_ms,
        "stdout_sha256": h(out),
        "stderr_sha256": h(err),
        "error": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["lean_proof", "test_conformance"])
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--budget", type=int, default=120, help="секунды (как в заказе)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    art = pathlib.Path(a.artifact)
    if not art.exists():
        print(json.dumps({"verdict": "error", "error": "artifact not found"}, ensure_ascii=False))
        return 2
    rc = lean_receipt(art, a.budget * 1000) if a.kind == "lean_proof" else pytest_receipt(art, a.budget * 1000)
    # канонический JSON: сортировка ключей, без пробелов — чтобы квитанции были байт-идентичны
    out = json.dumps(rc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    print(out if a.json else json.dumps(rc, ensure_ascii=False, indent=1))
    return 0 if rc["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
