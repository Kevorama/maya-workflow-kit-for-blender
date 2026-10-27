"""Step 30 follow-up in a real UI: a Move tool whose fallback is Blender's Tweak (a workspace that had no transform
tool yet, e.g. a user startup.blend's "General") gets Select Box when Maya mode activates it, so a drag off the
manipulator is Maya's marquee, not a move; Rotate too; a Lasso fallback the user picked stays."""

import os
import sys

import bmesh
import bpy
from bpy_extras import view3d_utils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import check, ev, run, step, setup, view3d  # noqa: E402

C = {}


def cube():
    return bpy.data.objects["Cube"]


def rect():
    area, region = view3d()
    rv3d = area.spaces.active.region_3d
    ob = cube()
    pts = [view3d_utils.location_3d_to_region_2d(region, rv3d, ob.matrix_world @ v.co) for v in ob.data.vertices]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    m = 25
    return (region.x + int(min(xs)) - m, region.y + int(min(ys)) - m,
            region.x + int(max(xs)) + m, region.y + int(max(ys)) + m)


def selected():
    bm = bmesh.from_edit_mesh(cube().data)
    return sum(v.select for v in bm.verts)


def coords():
    return [tuple(round(c, 4) for c in v.co) for v in bmesh.from_edit_mesh(cube().data).verts]


def tool_op(idname, as_fallback=False):
    area, region = view3d()
    with bpy.context.temp_override(window=bpy.context.window_manager.windows[0], area=area, region=region):
        bpy.ops.wm.tool_set_by_id(name=idname, as_fallback=as_fallback, space_type='VIEW_3D')


def tool():
    return bpy.context.window_manager.windows[0].workspace.tools.from_space_view3d_mode('EDIT_MESH')


@step
def s_setup():
    setup()
    bpy.context.view_layer.objects.active = cube()
    cube().select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bm = bmesh.from_edit_mesh(cube().data)
    bm.verts.ensure_lookup_table()
    bm.verts[0].select = True                                   # a selection a drag-as-tweak would move
    bmesh.update_edit_mesh(cube().data)
    tool_op("builtin.move")
    tool_op("builtin.select", as_fallback=True)                 # the state a user startup.blend left
    C["r"] = rect()
    C["co"] = coords()
    check(f"setup: Move tool with Blender's Tweak fallback ({tool().idname}, {tool().idname_fallback})",
          (tool().idname, tool().idname_fallback) == ("builtin.move", "builtin.select"))
    tool_op("builtin.select_box")
    tool_op("builtin.move")                                     # W (the Maya keymap's wm.tool_set_by_id)


@step
def s_fallback():
    check(f"Move tool activated: the fallback is Select Box ({tool().idname_fallback})",
          tool().idname_fallback == "builtin.select_box")


@step
def s_press():
    x0, y0 = C["r"][:2]
    ev('MOUSEMOVE', 'NOTHING', x=x0, y=y0)
    ev('LEFTMOUSE', 'PRESS', x=x0, y=y0)


@step
def s_move():
    x0, y0, x1, y1 = C["r"]
    ev('MOUSEMOVE', 'NOTHING', x=(x0 + x1) // 2, y=(y0 + y1) // 2)
    ev('MOUSEMOVE', 'NOTHING', x=x1, y=y1)


@step
def s_release():
    x1, y1 = C["r"][2:]
    ev('LEFTMOUSE', 'RELEASE', x=x1, y=y1)


@step
def s_settle():
    pass


@step
def s_marquee():
    check(f"drag in empty space with the Move tool = marquee, selects 8 ({selected()})", selected() == 8)
    check("nothing moved", coords() == C["co"])
    tool_op("builtin.rotate")
    tool_op("builtin.select", as_fallback=True)
    tool_op("builtin.move")
    tool_op("builtin.rotate")
    check(f"Rotate tool: Tweak fallback becomes Select Box too ({tool().idname_fallback})",
          tool().idname_fallback == "builtin.select_box")
    tool_op("builtin.select_lasso", as_fallback=True)
    tool_op("builtin.select_box")
    tool_op("builtin.move")
    check(f"a Lasso fallback the user picked stays ({tool().idname_fallback})",
          tool().idname_fallback == "builtin.select_lasso")


run()
