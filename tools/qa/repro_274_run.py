"""Step 274 lane A runner: sandbox per (Blender, kit zip), install, run a probe script. Holds a Blender slot."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import blender_slots  # noqa: E402

BLENDERS = {
    "5.0.1": r"C:\Users\ohnsk\AppData\Local\allset_blenders\blender-5.0.1-windows-x64\blender.exe",
    "5.1.0": r"C:\Users\ohnsk\AppData\Local\allset_blenders\blender-5.1.0-windows-x64\blender.exe",
    "5.1.2": r"C:\Users\ohnsk\AppData\Local\allset_blenders\blender-5.1.2-windows-x64\blender.exe",
    "5.2.3": r"C:\Users\ohnsk\AppData\Local\allset_blenders\blender-5.2.3-windows-x64\blender.exe",
}


def sandbox(ver, kit, fresh=True):
    sb = ROOT / "tmp" / f"s274_env_{ver}_{kit}{os.environ.get('S274_TAG', '')}"
    assert sb.resolve().is_relative_to(ROOT / "tmp")
    env = os.environ.copy()
    for var, sub in (("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts"),
                     ("BLENDER_USER_EXTENSIONS", "extensions")):
        d = sb / sub
        d.mkdir(parents=True, exist_ok=True)
        env[var] = str(d)
    (sb / "logs").mkdir(exist_ok=True)
    env["ALLSET_PROJECTS_DIR"] = str(sb / "projects")
    env["ALLSET_NO_WELCOME"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return sb, env


def run(ver, args, env, log):
    with blender_slots.slot(f"repro_274 {ver}"), open(log, "w", encoding="utf-8", errors="replace") as fh:
        r = subprocess.run([BLENDERS[ver], *args], env=env, stdin=subprocess.DEVNULL,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=600)
    return r.returncode


def install(ver, kit, env, sb):
    z = ROOT / "dist" / f"maya-workflow-kit-{kit}.zip"
    if (sb / "extensions" / "user_default" / "allset" / "__init__.py").exists():
        return 0
    return run(ver, ["--factory-startup", "--command", "extension", "install-file", "-r", "user_default", str(z)],
               env, sb / "logs" / "install.log")


if __name__ == "__main__":
    gui = "--gui" in sys.argv
    nofactory = "--nofactory" in sys.argv
    argv = [a for a in sys.argv if a not in ("--gui", "--nofactory")]
    if gui:
        import hidden_desktop
        hidden_desktop.ensure_hidden()
    ver, kit, script = argv[1], argv[2], argv[3]
    extra = argv[4:]
    sb, env = sandbox(ver, kit)
    print("install rc", install(ver, kit, env, sb))
    tag = Path(script).stem + ("_" + "_".join(Path(e).stem for e in extra) if extra else "")
    out = sb / f"{tag}.json"
    log = sb / "logs" / f"{tag}.log"
    head = ["--factory-startup", "--enable-event-simulate"] if gui else ["-b", "--factory-startup"]
    if nofactory:
        head = [h for h in head if h != "--factory-startup"]
    rc = run(ver, [*head, "--python", str(Path(script).resolve()), "--", str(out), *extra], env, log)
    print(ver, kit, "rc", rc, "log", log)
    print(out.read_text(encoding="utf-8") if out.exists() else "NO RESULT")
