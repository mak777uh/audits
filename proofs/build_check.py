import subprocess, pathlib, time
files = sorted(pathlib.Path(".").glob("*.lean"))
ok, fail = [], []
for f in files:
    t0 = time.time()
    r = subprocess.run(["lean", str(f)], capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    dt = time.time()-t0
    if r.returncode == 0 and not (r.stdout or "").strip() and not (r.stderr or "").strip():
        ok.append((f.name, round(dt,1)))
        print(f"✅ {f.name:16} компилируется чисто ({dt:.1f}с)")
    else:
        fail.append(f.name)
        msg = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        print(f"❌ {f.name:16} код {r.returncode}: {msg[0][:150] if msg else 'без вывода'}")
print(f"\nитог: чисто {len(ok)} из {len(files)}")
