"""Step 274 lane A: runs inside Blender (-b). Enable the kit, switch Maya mode on, report register failures.

Usage: blender -b --factory-startup --python repro_274_199_probe.py -- <out.json> [switch_back]
"""
import json
import sys
import traceback

import addon_utils
import bpy

MODULE = "bl_ext.user_default.allset"
out = sys.argv[sys.argv.index("--") + 1]
switch_back = "switch_back" in sys.argv
res = {"blender": bpy.app.version_string}

cfg = bpy.utils.user_resource('CONFIG')
assert "\\tmp\\" in cfg or "/tmp/" in cfg, cfg
res["config"] = cfg

# log every register_class failure
failed = []
_orig = bpy.utils.register_class


def _logged(cls):
    try:
        return _orig(cls)
    except Exception as ex:
        failed.append([cls.__name__, repr(ex)])
        raise


bpy.utils.register_class = _logged

before = {n for n in dir(bpy.types) if n.startswith("ALLSET_")}
mod = addon_utils.enable(MODULE, default_set=True, handle_error=lambda ex: res.setdefault("enable_error", traceback.format_exc()))
res["enabled"] = mod is not None
import importlib
switch = importlib.import_module(MODULE + ".switch")
try:
    switch.set_mode(True, layout=False)
    res["set_mode_on"] = "ok"
except Exception:
    res["set_mode_on"] = traceback.format_exc()
res["registered_flag"] = switch._registered[0]
res["maya_mode_pref"] = bool(switch._prefs_addon().maya_mode)
res["register_class_failures"] = failed
res["has_menu_tear_off"] = hasattr(bpy.types, "ALLSET_OT_menu_tear_off")
res["has_op_menu_tear_off"] = "menu_tear_off" in dir(bpy.ops.allset)
after = {n for n in dir(bpy.types) if n.startswith("ALLSET_")}
res["allset_types_after_on"] = len(after - before)

# which MODE modules / ui sub-modules got through
ui = importlib.import_module(MODULE + ".ui")
from bpy.types import TOPBAR_HT_upper_bar
res["topbar_draw_left"] = getattr(TOPBAR_HT_upper_bar.draw_left, "__module__", "?") + "." + getattr(TOPBAR_HT_upper_bar.draw_left, "__qualname__", "?")

if switch_back:
    try:
        switch.set_mode(False, layout=False)
        res["set_mode_off"] = "ok"
    except Exception:
        res["set_mode_off"] = traceback.format_exc()
    res["registered_flag_after_off"] = switch._registered[0]
    left = {n for n in dir(bpy.types) if n.startswith("ALLSET_")} - before
    res["allset_types_left_after_off"] = sorted(left)[:80]
    res["allset_types_left_count"] = len(left)
    res["topbar_draw_left_after_off"] = getattr(TOPBAR_HT_upper_bar.draw_left, "__module__", "?") + "." + getattr(TOPBAR_HT_upper_bar.draw_left, "__qualname__", "?")
    tools = []
    try:
        from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
        cls = ToolSelectPanelHelper._tool_class_from_space_type('VIEW_3D')
        for mode in ('OBJECT', 'EDIT_MESH'):
            for t in cls.tools_from_context(bpy.context, mode=mode) if False else []:
                pass
        for mode, items in bpy.types.VIEW3D_PT_tools_active._tools.items():
            for item in items:
                if item is None:
                    continue
                seq = item if isinstance(item, tuple) else (item,)
                for t in seq:
                    if callable(t):
                        continue
                    if getattr(t, "idname", "").startswith("allset"):
                        tools.append(f"{mode}:{t.idname}")
    except Exception:
        tools.append("ERR " + traceback.format_exc()[-300:])
    res["allset_tools_after_off"] = tools

with open(out, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1)
print("PROBE DONE", out)
