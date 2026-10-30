"""F over the Outliner = Maya's Reveal Selected: the tree opens to every selected object (not only Blender's active
one, and also with no active object, as after a marquee) and scrolls to the lead; the selection is kept."""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import check, ev, load_maya_layout, run, setup, step, tap, win  # noqa: E402

FILLERS = 60
TREE = {"G1": None, "G2": "G1", "leaf": "G2", "H": None, "ball": "H"}


def outl():
    a = next(a for a in win().screen.areas if a.type == 'OUTLINER')
    return a, next(r for r in a.regions if r.type == 'WINDOW')


def row_h():
    return 20 * bpy.context.preferences.system.ui_scale


def row_xy(i):
    _a, r = outl()
    _x, y = r.view2d.view_to_region(0, -(i + 0.5) * row_h(), clip=False)
    return r.x + int(2.5 * row_h()), r.y + int(y)


def ob(n):
    return bpy.data.objects[n]


def redraw():
    for a in win().screen.areas:
        a.tag_redraw()


def rows_check(expected, label):
    """Steps: hover each of the first rows, hit-test it like the kit does (selection put back)."""
    got = []

    def mover(i):
        def s():
            x, y = row_xy(i)
            ev('MOUSEMOVE', 'NOTHING', x=x, y=y)
        return s

    def hitter():
        from importlib import import_module
        from sim import MODULE
        od = import_module(MODULE + ".operators.outliner_drag")
        a, r = outl()
        with bpy.context.temp_override(window=win(), area=a, region=r):
            o = od._first_object(od.hit_ids(bpy.context))
        got.append(o.name if o else None)

    for i in range(len(expected)):
        step(mover(i))
        step(hitter)

    @step
    def s_check():
        check(f"{label} ({got})", got == expected)


def press_f():
    @step
    def s_hover():
        _a, r = outl()
        ev('MOUSEMOVE', 'NOTHING', x=r.x + r.width // 2, y=r.y + r.height // 2)

    @step
    def s_f():
        tap('F')

    @step
    def s_wait():
        redraw()


def select(*names):
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in names)
    bpy.context.view_layer.objects.active = None      # a marquee leaves no active object
    redraw()


@step
def s_setup():
    setup()
    load_maya_layout()


@step
def s_scene():
    bpy.ops.allset.keymap_activate()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    col = bpy.context.scene.collection.children[0]
    names = list(TREE) + [f"f{i:02d}" for i in range(FILLERS)] + ["Z", "zleaf"]
    for n in names:
        o = bpy.data.objects.new(n, None)
        col.objects.link(o)
    for n, parent in {**TREE, "zleaf": "Z"}.items():
        if parent:
            ob(n).parent = ob(parent)
    select("leaf", "ball")


rows_check(["G1", "H", "f00"], "collapsed: only the top rows")
press_f()
rows_check(["G1", "G2", "leaf", "H", "ball", "f00"], "F opens the tree to both selected objects")


@step
def s_kept():
    sel = sorted(o.name for o in bpy.context.selected_objects)
    check(f"selection kept, still no active object ({sel})",
          sel == ["ball", "leaf"] and bpy.context.view_layer.objects.active is None)
    select("zleaf")


press_f()


@step
def s_scrolled():
    _a, r = outl()
    index = len(TREE) + FILLERS + 1                   # zleaf, under the expanded Z
    _x, y = r.view2d.view_to_region(0, -(index + 0.5) * row_h(), clip=False)
    check(f"F scrolls to the lead far down the list (row y {y} in 0..{r.height})", 0 <= y <= r.height)


rows_check(["G1", "G2", "leaf", "H", "ball", "f00"], "the earlier rows stay open")


@step
def s_end():
    redraw()


run()
