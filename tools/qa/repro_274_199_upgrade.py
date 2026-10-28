"""Step 274 lane A: upgrade path: old kit in Maya mode, restart, install the new zip in the running Blender, switch back.

Phase save : enable the kit (default_set), opt in with the Maya layout, save userpref (sandbox config only), quit.
Phase start: Blender started WITHOUT --factory-startup (reads the sandbox userpref: kit enabled, maya_mode on);
             report state, screenshot, run allset.switch_mode(mode='BLENDER') like the top-bar button, report, shot.
Usage: blender [--enable-event-simulate] --python repro_274_199_restart.py -- <out.json> save|start
"""
import importlib
import json
import os
import sys
import traceback

import addon_utils
import bpy

MODULE = "bl_ext.user_default.allset"
out = sys.argv[sys.argv.index("--") + 1]
phase = sys.argv[sys.argv.index("--") + 2]
shots = os.path.splitext(out)[0] + "_shots"
os.makedirs(shots, exist_ok=True)
res = {"blender": bpy.app.version_string, "phase": phase, "events": []}
cfg = bpy.utils.user_resource('CONFIG')
assert "\\tmp\\" in cfg or "/tmp/" in cfg, cfg


def log(*a):
    s = " ".join(str(x) for x in a)
    res["events"].append(s)
    print("PROBE:", s, flush=True)


def shot(tag):
    path = os.path.join(shots, f"{phase}_{tag}.png")
    try:
        win = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=win, screen=win.screen, area=win.screen.areas[0]):
            bpy.ops.screen.screenshot(filepath=path)
        log("shot", path)
    except Exception as ex:
        log("shot failed", tag, ex)


def state(tag):
    from bpy.types import TOPBAR_HT_upper_bar
    d = {"enabled": MODULE in bpy.context.preferences.addons}
    try:
        sw = importlib.import_module(MODULE + ".switch")
        d["registered_flag"] = sw._registered[0]
        d["maya_mode_pref"] = bool(sw._prefs_addon().maya_mode)
    except Exception as ex:
        d["switch_err"] = repr(ex)
    d["has_menu_tear_off"] = hasattr(bpy.types, "ALLSET_OT_menu_tear_off")
    d["has_MT_File"] = hasattr(bpy.types, "ALLSET_MT_mainFileMenu")
    d["topbar_draw"] = [getattr(f, "__module__", "?") + "." + getattr(f, "__qualname__", "?")
                        for f in getattr(TOPBAR_HT_upper_bar.draw, "_draw_funcs", [TOPBAR_HT_upper_bar.draw])]
    d["topbar_draw_left"] = getattr(TOPBAR_HT_upper_bar.draw_left, "__module__", "?")
    d["allset_types"] = len([n for n in dir(bpy.types) if n.startswith("ALLSET_")])
    d["workspaces"] = [w.name for w in bpy.data.workspaces]
    d["window_workspace"] = bpy.context.window_manager.windows[0].workspace.name
    tools = []
    for mode, items in bpy.types.VIEW3D_PT_tools_active._tools.items():
        for item in items:
            for t in (item if isinstance(item, tuple) else (item,)):
                if t is not None and not callable(t) and getattr(t, "idname", "").startswith("allset"):
                    tools.append(f"{mode}:{t.idname}")
    d["allset_tools"] = tools
    res[tag] = d
    log("state", tag, json.dumps(d))


def win_override():
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    return bpy.context.temp_override(window=win, screen=win.screen, area=area)


STEPS = []


def step(fn):
    STEPS.append(fn)
    return fn


if phase == "save":
    @step
    def s_enable():
        mod = addon_utils.enable(MODULE, default_set=True,
                                 handle_error=lambda ex: log("enable error", traceback.format_exc()))
        log("enabled", mod is not None)

    @step
    def s_opt():
        importlib.import_module(MODULE + ".welcome").opt_in(open_layout=True)
        log("opt_in ok")

    @step
    def s_w():
        state("after_on")

    @step
    def s_save():
        assert "\\tmp\\" in bpy.utils.user_resource('CONFIG')
        bpy.ops.wm.save_userpref()
        log("saved userpref", bpy.utils.user_resource('CONFIG'))
else:
    ZIP = sys.argv[sys.argv.index("--") + 3]

    @step
    def s_w0():
        state("at_start")

    @step
    def s_shot0():
        shot("01_start_old")

    @step
    def s_upgrade():
        try:
            with win_override():
                r = bpy.ops.extensions.package_install_files(filepath=ZIP, repo="user_default", enable_on_install=True)
            log("package_install_files", r)
        except Exception:
            log("upgrade EXC", traceback.format_exc())

    @step
    def s_w1():
        pass

    @step
    def s_w2():
        state("after_upgrade")

    @step
    def s_shot1():
        shot("02_after_upgrade")

    @step
    def s_menu():
        try:
            with win_override():
                bpy.ops.wm.call_menu(name="ALLSET_MT_mainFileMenu")
            log("call_menu File ok")
        except Exception:
            log("call_menu EXC", traceback.format_exc())

    @step
    def s_shot2():
        shot("03_file_menu")

    @step
    def s_esc():
        win = bpy.context.window_manager.windows[0]
        win.event_simulate('ESC', 'PRESS')
        win.event_simulate('ESC', 'RELEASE')

    @step
    def s_switch():
        try:
            with win_override():
                r = bpy.ops.allset.switch_mode(mode='BLENDER')
            log("switch_mode", r)
        except Exception:
            log("switch EXC", traceback.format_exc())

    @step
    def s_w3():
        pass

    @step
    def s_w4():
        state("after_off")

    @step
    def s_shot3():
        shot("04_after_off")


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


bpy.app.timers.register(tick, first_interval=3.0, persistent=True)
