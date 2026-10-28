"""Step 274 lane A: #192 Graph Editor: object not shown / tangents not visible at the top.

Maya mode + Maya layout, a cube keyed on Translate at frames 1 and 24 (Maya S-style key via keyframe_insert),
Windows > Animation Editors > Graph Editor (allset.open_editor FCURVES, a new window). Screenshots + state with the
cube selected, after View All, after deselect, and with the main 3D view itself turned into a Graph Editor.
Usage: blender --factory-startup --enable-event-simulate --python repro_274_192_gui.py -- <out.json>
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
shots = os.path.splitext(out)[0] + "_shots"
os.makedirs(shots, exist_ok=True)
res = {"blender": bpy.app.version_string, "events": []}
assert "\\tmp\\" in bpy.utils.user_resource('CONFIG')


def log(*a):
    s = " ".join(str(x) for x in a)
    res["events"].append(s)
    print("PROBE:", s, flush=True)


def graph_areas():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'GRAPH_EDITOR':
                yield w, a


def shot(tag, window=None):
    wm = bpy.context.window_manager
    win = window or wm.windows[-1]
    path = os.path.join(shots, f"{tag}.png")
    try:
        with bpy.context.temp_override(window=win, screen=win.screen, area=win.screen.areas[0]):
            bpy.ops.screen.screenshot(filepath=path)
        log("shot", path)
    except Exception as ex:
        log("shot failed", tag, ex)


def gstate(tag):
    d = []
    for w, a in graph_areas():
        sp = a.spaces.active
        ds = sp.dopesheet
        e = {"window": w.as_pointer() == bpy.context.window_manager.windows[0].as_pointer() and "main" or "other",
             "ui_type": a.ui_type, "size": [a.width, a.height],
             "regions": [(r.type, r.width, r.height, r.y) for r in a.regions],
             "show_only_selected": ds.show_only_selected, "filter_collection": getattr(ds.filter_collection, "name", None),
             "show_hidden": ds.show_hidden, "show_only_errors": ds.show_only_errors,
             "filter_text": ds.filter_text, "show_handles": getattr(sp, "show_handles", None),
             "use_only_selected_keyframe_handles": getattr(sp, "use_only_selected_keyframe_handles", None),
             "pref_only_selected_handles": getattr(bpy.context.preferences.edit, "use_only_selected_keyframe_handles", None),
             "show_region_channels": getattr(sp, "show_region_channels", None),
             "show_region_ui": getattr(sp, "show_region_ui", None)}
        try:
            win_reg = next(r for r in a.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=w, screen=w.screen, area=a, region=win_reg):
                e["visible_fcurves"] = [f"{fc.id_data.name}:{fc.data_path}[{fc.array_index}] hide={fc.hide}"
                                        for fc in (bpy.context.visible_fcurves or [])]
                v2d = win_reg.view2d
                e["view_rect_bl"] = v2d.region_to_view(0, 0)
                e["view_rect_tr"] = v2d.region_to_view(win_reg.width, win_reg.height)
        except Exception:
            e["ctx_err"] = traceback.format_exc()[-300:]
        d.append(e)
    ob = bpy.data.objects.get("pCube1") or bpy.context.view_layer.objects.active
    if ob is not None:
        from bpy_extras import anim_utils  # noqa
        try:
            sw = importlib.import_module(MODULE + ".compat")
            fcs = list(sw.id_fcurves(ob))
            d.append({"object": ob.name, "selected": ob.select_get(), "fcurves": [(f.data_path, f.array_index, f.hide, f.select,
                      [tuple(k.co) for k in f.keyframe_points]) for f in fcs]})
        except Exception:
            d.append({"fc_err": traceback.format_exc()[-300:]})
    colls = [c.name for c in bpy.data.collections if "allset_list" in c or c.name.startswith(".Allset")]
    d.append({"kit_list_collections": colls})
    res[tag] = d
    log("gstate", tag, json.dumps(d, default=str)[:3000])


def main_override():
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return win, area, bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region)


STEPS = []


def step(fn):
    STEPS.append(fn)
    return fn


@step
def s_enable():
    addon_utils.enable(MODULE, default_set=True, handle_error=lambda ex: log("enable error", traceback.format_exc()))
    importlib.import_module(MODULE + ".welcome").opt_in(open_layout=True)
    log("opt_in ok")


@step
def s_w():
    pass


@step
def s_cube():
    win, area, ov = main_override()
    with ov:
        r = bpy.ops.allset.create(kind='CUBE') if hasattr(bpy.ops.allset, "create") else None
    ob = bpy.context.view_layer.objects.active
    log("create", r, ob and ob.name)
    scene = bpy.context.scene
    if "nokeys" in sys.argv:     # #192: a selected object with no animation yet (Maya lists it anyway)
        for o in bpy.context.view_layer.objects:
            o.select_set(o == ob)
        return
    scene.frame_set(1)
    ob.keyframe_insert("location")
    scene.frame_set(24)
    ob.location = (ob.location.x + 5, ob.location.y, ob.location.z + 3)
    ob.keyframe_insert("location")
    scene.frame_set(12)
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob


@step
def s_open():
    win, area, ov = main_override()
    with ov:
        try:
            r = bpy.ops.allset.menu_item(item="Windows/Animation Editors/Graph Editor")
            log("menu_item Graph Editor", r)
        except Exception:
            log("menu_item EXC", traceback.format_exc()[-400:])
            r = bpy.ops.allset.open_editor(ui_type='FCURVES')
            log("open_editor", r)


@step
def s_w2():
    pass


@step
def s_w3():
    gstate("selected")


@step
def s_shot1():
    shot("01_graph_selected")


@step
def s_view_all():
    for w, a in graph_areas():
        reg = next(r for r in a.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=w, screen=w.screen, area=a, region=reg):
            try:
                bpy.ops.graph.view_all()
            except Exception as ex:
                log("view_all", ex)


@step
def s_w4():
    gstate("after_view_all")


@step
def s_shot2():
    shot("02_graph_view_all")


@step
def s_deselect():
    for o in bpy.context.view_layer.objects:
        o.select_set(False)


@step
def s_w5():
    gstate("deselected")


@step
def s_shot3():
    shot("03_graph_deselected")


@step
def s_main_as_graph():
    ob = bpy.data.objects.get("pCube1") or bpy.context.scene.objects[-1]
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    # close the extra window, turn the main 3D view into a Graph Editor (Maya Panels > Panel > Graph Editor)
    win, area, ov = main_override()
    area.ui_type = 'FCURVES'


@step
def s_w6():
    pass


@step
def s_w7():
    gstate("main_area_graph")


@step
def s_shot4():
    shot("04_main_area_graph", bpy.context.window_manager.windows[0])


@step
def s_done():
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
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
    return 1.5


bpy.app.timers.register(tick, first_interval=2.0, persistent=True)
