"""Step 274 lane A: GUI probe (runs inside a GUI Blender on the hidden desktop).

Enable the kit, wrap every Maya-mode module's register / unregister to log exceptions, opt in like the welcome
dialog (welcome.opt_in, Maya layout), screenshot, open the Maya File menu, switch back to Blender, screenshot,
report. Usage: blender --factory-startup --python repro_274_199_gui.py -- <out.json>
"""
import functools
import importlib
import json
import os
import sys
import traceback

import addon_utils
import bpy

MODULE = "bl_ext.user_default.allset"
out = sys.argv[sys.argv.index("--") + 1]
shots = os.path.splitext(out)[0] + "_shots"
os.makedirs(shots, exist_ok=True)
res = {"blender": bpy.app.version_string, "events": []}
cfg = bpy.utils.user_resource('CONFIG')
assert "\\tmp\\" in cfg or "/tmp/" in cfg, cfg


def log(*a):
    s = " ".join(str(x) for x in a)
    res["events"].append(s)
    print("PROBE:", s, flush=True)


def wrap(mod, name):
    fn = getattr(mod, name)

    @functools.wraps(fn)
    def w(*a, **k):
        try:
            return fn(*a, **k)
        except Exception:
            log(f"EXC in {mod.__name__}.{name}:\n{traceback.format_exc()}")
            raise
    setattr(mod, name, w)


def shot(tag):
    path = os.path.join(shots, f"{tag}.png")
    try:
        win = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=win, screen=win.screen, area=win.screen.areas[0]):
            bpy.ops.screen.screenshot(filepath=path)
        log("shot", path)
    except Exception as ex:
        log("shot failed", tag, ex)


def state(tag):
    from bpy.types import TOPBAR_HT_upper_bar
    sw = importlib.import_module(MODULE + ".switch")
    d = {
        "registered_flag": sw._registered[0],
        "maya_mode_pref": bool(sw._prefs_addon().maya_mode),
        "has_menu_tear_off": hasattr(bpy.types, "ALLSET_OT_menu_tear_off"),
        "has_MT_File": hasattr(bpy.types, "ALLSET_MT_mainFileMenu"),
        "topbar_draw": [getattr(f, "__module__", "?") + "." + getattr(f, "__qualname__", "?")
                        for f in getattr(TOPBAR_HT_upper_bar.draw, "_draw_funcs", [TOPBAR_HT_upper_bar.draw])],
        "allset_types": len([n for n in dir(bpy.types) if n.startswith("ALLSET_")]),
        "workspaces": [w.name for w in bpy.data.workspaces],
        "window_workspace": bpy.context.window_manager.windows[0].workspace.name,
    }
    tools = []
    for mode, items in bpy.types.VIEW3D_PT_tools_active._tools.items():
        for item in items:
            for t in (item if isinstance(item, tuple) else (item,)):
                if t is not None and not callable(t) and getattr(t, "idname", "").startswith("allset"):
                    tools.append(f"{mode}:{t.idname}")
    d["allset_tools"] = tools
    res[tag] = d
    log("state", tag, json.dumps(d))


STEPS = []


def step(fn):
    STEPS.append(fn)
    return fn


@step
def s_enable():
    mod = addon_utils.enable(MODULE, default_set=True,
                             handle_error=lambda ex: log("enable error", traceback.format_exc()))
    log("enabled", mod is not None)
    root = importlib.import_module(MODULE)
    ui = importlib.import_module(MODULE + ".ui")
    for m in list(root.MODE) + list(ui._modules):
        wrap(m, "register")
        wrap(m, "unregister")
    for a in sys.argv:
        if a.startswith("inject="):     # simulate a register failure in one ui module (mechanism check)
            target = getattr(ui, a.split("=", 1)[1])

            def boom(*_a, **_k):
                raise RuntimeError("injected register failure in " + target.__name__)
            target.register = boom
            log("injected failure into", target.__name__)


@step
def s_opt_in():
    try:
        importlib.import_module(MODULE + ".welcome").opt_in(open_layout=True)
        log("opt_in ok")
    except Exception:
        log("opt_in EXC", traceback.format_exc())


@step
def s_wait1():
    pass


@step
def s_wait1b():
    pass


@step
def s_wait1c():
    state("after_on")


@step
def s_wait1d():
    pass


@step
def s_shot_on():
    shot("01_maya_on")


@step
def s_menu():
    win = bpy.context.window_manager.windows[0]
    top = None
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            top = area
    try:
        with bpy.context.temp_override(window=win, area=top):
            bpy.ops.wm.call_menu(name="ALLSET_MT_mainFileMenu")
        log("call_menu File ok")
    except Exception:
        log("call_menu EXC", traceback.format_exc())


@step
def s_shot_menu():
    shot("02_file_menu")


@step
def s_close_menu():
    win = bpy.context.window_manager.windows[0]
    try:
        win.event_simulate('ESC', 'PRESS')
        win.event_simulate('ESC', 'RELEASE')
    except Exception as ex:
        log("esc", ex)


@step
def s_off():
    try:
        importlib.import_module(MODULE + ".switch").set_mode(False, layout=True)
        log("set_mode off ok")
    except Exception:
        log("set_mode off EXC", traceback.format_exc())


@step
def s_wait2():
    state("after_off")


@step
def s_shot_off():
    shot("03_blender_after_off")


@step
def s_done():
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print("PROBE DONE", flush=True)
    bpy.ops.wm.quit_blender()


_i = [0]


def tick():
    if _i[0] >= len(STEPS):
        return None
    fn = STEPS[_i[0]]
    _i[0] += 1
    try:
        fn()
    except Exception:
        log("step EXC", fn.__name__, traceback.format_exc())
    return 1.0


bpy.app.timers.register(tick, first_interval=2.0, persistent=True)
