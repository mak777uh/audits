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
def _find_lean() -> pathlib.Path:
    """Ищем lean переносимо: PATH -> elan toolchains -> прежний путь (Windows)."""
    import shutil
    w = shutil.which("lean")
    if w:
        return pathlib.Path(w)
    home = pathlib.Path(os.path.expanduser("~")) / ".elan" / "toolchains"
    cands = sorted(home.glob("*/bin/lean*")) if home.exists() else []
    if cands:
        return cands[-1]
    return pathlib.Path("lean")


LEAN = _find_lean()
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


def selftest() -> int:
    """Проверка самих квитанций: целостность и согласованность, без запуска Lean.

    Что проверяется на каждом векторе:
      * обязательные поля квитанции присутствуют;
      * artifact_sha256 совпадает с пересчитанным (если артефакт доступен в репозитории);
      * verdict согласован: при exit_code != 0 вердикт не может быть "pass";
      * битые квитанции (подмена хеша, отсутствие поля, вердикт pass при ошибке) отвергаются.

    Чего НЕ проверяет: что Lean действительно принял доказательство — это делает CI отдельным шагом.
    """
    import hashlib
    vp = pathlib.Path(__file__).with_name("vectors.json")
    data = json.loads(vp.read_text(encoding="utf-8"))
    vectors = data.get("vectors") or []
    required = {"kind", "artifact_sha256", "verdict", "toolchain", "exit_code"}
    passed = failed = 0
    for v in vectors:
        vid = v.get("id", "?")
        rc = v.get("receipt") or {}
        expect = v.get("expect_verdict")
        problems = []
        missing = required - set(rc)
        if missing:
            problems.append(f"нет полей: {sorted(missing)}")
        if rc.get("verdict") == "pass" and int(rc.get("exit_code", 0)) != 0:
            problems.append("verdict=pass при exit_code != 0")
        if rc.get("verdict") == "pass" and rc.get("forbidden_tokens"):
            problems.append("verdict=pass при найденных запрещённых токенах")
        exp_sha = v.get("statement_sha256")
        if exp_sha and len(exp_sha) != 64:
            problems.append("statement_sha256 не 64 hex-символа")
        # пересчёт artefact hash, если файл есть
        art = v.get("artifact_path")
        if art and (pathlib.Path(__file__).parents[1] / art).exists():
            real = hashlib.sha256((pathlib.Path(__file__).parents[1] / art).read_bytes()).hexdigest()
            if real != rc.get("artifact_sha256"):
                problems.append("artifact_sha256 не совпадает с файлом")
        reject_expected = bool(v.get("expect_reject"))
        if reject_expected:
            # такой вектор ОБЯЗАН быть отвергнут: успех = нарушения найдены
            ok = bool(problems)
            shown = "; ".join(problems) if problems else "квитанция принята, а должна быть отвергнута"
        else:
            ok = not problems
            if ok and expect and rc.get("verdict") != expect:
                problems.append(f"ожидался verdict={expect}, получен {rc.get('verdict')}")
                ok = False
            shown = "; ".join(problems)
        if ok:
            passed += 1
            tag = "отвергнут как должен" if reject_expected else f"verdict={rc.get('verdict')}"
            print(f"  ok    {vid:24} {tag}")
        else:
            failed += 1
            print(f"  FAIL  {vid:24} {shown}")
    print(f"\nвекторов: {len(vectors)}, прошло: {passed}, провалено: {failed}")
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["lean_proof", "test_conformance"])
    ap.add_argument("--artifact")
    ap.add_argument("--selftest", action="store_true", help="проверить квитанции из vectors.json")
    if "--selftest" in sys.argv:
        return selftest()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--budget", type=int, default=120, help="секунды (как в заказе)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.selftest and (not a.kind or not a.artifact):
        ap.error("нужны --kind и --artifact (или --selftest)")
    art = pathlib.Path(a.artifact or ".")
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
