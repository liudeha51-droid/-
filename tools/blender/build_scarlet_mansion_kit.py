"""Scarlet Devil Mansion environment kit: modular in-house pieces for the gate, the
front garden and the gothic interior, hollowed now that faith has left Gensokyo.

Outputs one .glb per piece in assets/models/environment/scarlet_mansion/.
Blender axes: Z up, real-world metres, the "front" of every piece faces -Y
(which becomes +Z in Godot). Pieces sit on the origin at ground level, except:
  - chandelier: the origin is the ceiling mount; it hangs down along -Z.
  - clock_face_wall: the origin is the bottom of the dial's back plane, so it
    can be hung flush on a wall; it projects out along -Y.
Walls (wall_segment, wall_panel, wall_window, doorway) are 4 m modules whose
core is centred on the origin line; floor_tile is 4 x 4 m with its top at z=0.

Palette: the mansion's crimson is drained and dark (wine, rust, dried rose) so
Reimu's red still reads against it (docs/GAME_DESIGN.md section 7). The only
saturated crimson is the emissive glow behind the windows (the red moon).
"""
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402

OUT = "assets/models/environment/scarlet_mansion"
STATS = []
FROZEN_TIME = (11, 59)  # every clock in the mansion stopped at the same moment


def mats():
    return {
        "brick": C.material("SDM_Brick", (0.2, 0.055, 0.05), 0.9),
        "brick_dark": C.material("SDM_BrickDark", (0.11, 0.035, 0.035), 0.95),
        "stone": C.material("SDM_Stone", (0.3, 0.28, 0.29), 0.95),
        "stone_dark": C.material("SDM_StoneDark", (0.13, 0.12, 0.13), 0.95),
        "plaster": C.material("Plaster", (0.26, 0.23, 0.22), 0.95),
        "iron": C.material("WroughtIron", (0.035, 0.033, 0.037), 0.55, 0.7),
        "brass": C.material("TarnishedBrass", (0.42, 0.32, 0.16), 0.45, 0.85),
        "wood": C.material("Ebony", (0.06, 0.035, 0.03), 0.6),
        "wood_red": C.material("Mahogany", (0.15, 0.055, 0.04), 0.7),
        "paper": C.material("Wallpaper", (0.2, 0.04, 0.05), 0.9),
        "stripe": C.material("WallpaperStripe", (0.12, 0.025, 0.035), 0.9),
        "marble_l": C.material("MarbleLight", (0.4, 0.38, 0.38), 0.3),
        "marble_d": C.material("MarbleDark", (0.06, 0.04, 0.05), 0.3),
        "velvet": C.material("Velvet", (0.17, 0.02, 0.035), 1.0),
        "velvet_lt": C.material("VelvetFaded", (0.3, 0.1, 0.11), 1.0),
        "thread": C.material("GoldThread", (0.36, 0.27, 0.12), 0.8),
        "bone": C.material("ClockFace", (0.6, 0.56, 0.48), 0.6),
        "glow": C.material("WindowGlow", (0.75, 0.05, 0.05), 0.5, emission=2.5),
        "void": C.material("Void", (0.01, 0.008, 0.01), 0.3),
        "glass": C.material("DeadGlass", (0.05, 0.05, 0.06), 0.1),
        "crystal": C.material("Crystal", (0.55, 0.52, 0.56), 0.1, 0.3),
        "wax": C.material("Wax", (0.72, 0.68, 0.6), 0.7),
        "flame": C.material("Flame", (1.0, 0.62, 0.3), 0.5, emission=4.0),
        "eye": C.material("EyeGlow", (0.8, 0.06, 0.05), 0.5, emission=3.0),
        "dead": C.material("DeadBranch", (0.07, 0.055, 0.05), 0.9),
        "rose": C.material("DeadRose", (0.16, 0.015, 0.03), 0.8),
        "leaf": C.material("DeadLeaf", (0.16, 0.11, 0.07), 1.0),
        "soil": C.material("Soil", (0.06, 0.05, 0.045), 1.0),
        "moss": C.material("Moss", (0.12, 0.15, 0.1), 1.0),
        "roof": C.material("Slate", (0.07, 0.07, 0.08), 0.6),
        "book1": C.material("Book1", (0.14, 0.05, 0.04), 0.8),
        "book2": C.material("Book2", (0.08, 0.07, 0.11), 0.8),
        "book3": C.material("Book3", (0.12, 0.1, 0.06), 0.8),
        "book4": C.material("Book4", (0.06, 0.09, 0.07), 0.8),
        "book5": C.material("Book5", (0.3, 0.26, 0.2), 0.8),
    }


def start():
    C.reset_scene()
    return mats()


def finish(name, parts, ground=False):
    obj = C.join(parts, "".join(w.title() for w in name.split("_")))
    if ground:  # rest on z=0 and centre the footprint (loose, tumbled props)
        bb = [Vector(v.co) for v in obj.data.vertices]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        C.transform(obj, Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    C.activate(obj)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception:  # older Blender: keep the per-face flags from the builders
        pass
    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    vs = [v.co for v in obj.data.vertices]
    dims = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
    zr = (min(v.z for v in vs), max(v.z for v in vs))
    STATS.append((name, tris, dims, zr))
    C.export_glb(f"{OUT}/{name}.glb", [obj])


# ------------------------------------------------------------------ geometry helpers
def _plane(plane, u, v, w):
    if plane == "xz":  # profile in x/z, extruded along y
        return (u, w, v)
    if plane == "xy":  # profile in x/y, extruded along z
        return (u, v, w)
    return (w, u, v)  # "yz": profile in y/z, extruded along x


def extrude(name, pts, a0, a1, mat, plane="xz"):
    """Solid prism from a closed 2D polygon."""
    bm = bmesh.new()
    f = [bm.verts.new(_plane(plane, u, v, a0)) for u, v in pts]
    b = [bm.verts.new(_plane(plane, u, v, a1)) for u, v in pts]
    bm.faces.new(f)
    bm.faces.new(b[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat, smooth=False)


def band(name, outer, inner, a0, a1, mat, plane="xz", closed=False):
    """Solid strip between two matching polylines (arch frames, rings)."""
    bm = bmesh.new()
    n = len(outer)
    fo = [bm.verts.new(_plane(plane, u, v, a0)) for u, v in outer]
    fi = [bm.verts.new(_plane(plane, u, v, a0)) for u, v in inner]
    bo = [bm.verts.new(_plane(plane, u, v, a1)) for u, v in outer]
    bi = [bm.verts.new(_plane(plane, u, v, a1)) for u, v in inner]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        bm.faces.new((fo[i], fo[j], fi[j], fi[i]))
        bm.faces.new((bo[i], bi[i], bi[j], bo[j]))
        bm.faces.new((fo[i], bo[i], bo[j], fo[j]))
        bm.faces.new((fi[i], fi[j], bi[j], bi[i]))
    if not closed:
        for k in (0, n - 1):
            bm.faces.new((fo[k], fi[k], bi[k], bo[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat, smooth=False)


def lathe(name, prof, segs, mat, center=(0, 0, 0), smooth=True):
    """Revolve an (r, z) profile that starts and ends on the axis (r = 0)."""
    bm = bmesh.new()
    cx, cy, cz = center
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((cx, cy, cz + z))])
        else:
            rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * k / segs), cy + r * math.sin(2 * math.pi * k / segs), cz + z)) for k in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs):
            k1 = (k + 1) % segs
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k], b[k1]))
            elif len(b) == 1:
                bm.faces.new((a[k], b[0], a[k1]))
            else:
                bm.faces.new((a[k], b[k], b[k1], a[k1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat, smooth)


def cyl(name, r, z0, z1, mat, segs=12, x=0.0, y=0.0, r1=None):
    return lathe(name, [(0, z0), (r, z0), (r if r1 is None else r1, z1), (0, z1)], segs, mat, (x, y, 0))


def circle(r, n, cx=0.0, cy=0.0, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def arch(w, spring, segs=6, cx=0.0, z0=0.0, R=None):
    """Opening outline: up the right jamb, over a (pointed) arch, down the left.

    R = w/2 gives a round arch; larger R gives a gothic pointed arch. Frames
    built with the same centre and R + t stay concentric."""
    R = 0.8 * w if R is None else R
    zs = z0 + spring
    amax = math.acos(max(-1.0, min(1.0, (R - w / 2) / R)))
    pts = [(cx + w / 2, z0), (cx + w / 2, zs)]
    ccx = cx + w / 2 - R
    for k in range(1, segs + 1):
        a = amax * k / segs
        pts.append((ccx + R * math.cos(a), zs + R * math.sin(a)))
    ccx = cx - w / 2 + R
    for k in range(segs - 1, -1, -1):
        a = math.pi - amax * k / segs
        pts.append((ccx + R * math.cos(a), zs + R * math.sin(a)))
    pts.append((cx - w / 2, z0))
    return pts


def arch_frame(name, w, spring, t, a0, a1, mat, cx=0.0, z0=0.0, segs=6):
    R = 0.8 * w
    inner = arch(w, spring, segs, cx, z0, R)
    outer = arch(w + 2 * t, spring, segs, cx, z0, R + t)
    return band(name, outer, inner, a0, a1, mat, "xz")


def gear_pts(r_root, r_tip, teeth):
    pts = []
    step = 2 * math.pi / teeth
    for k in range(teeth):
        a = k * step
        pts += [(r_root * math.cos(a), r_root * math.sin(a)),
                (r_tip * math.cos(a + 0.15 * step), r_tip * math.sin(a + 0.15 * step)),
                (r_tip * math.cos(a + 0.45 * step), r_tip * math.sin(a + 0.45 * step)),
                (r_root * math.cos(a + 0.6 * step), r_root * math.sin(a + 0.6 * step))]
    return pts


def cut(objs, cutter):
    """Boolean-subtract `cutter` from each object, then delete the cutter."""
    for o in objs:
        m = o.modifiers.new("Cut", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.object = cutter
        m.solver = "EXACT"
        C.apply_modifiers(o)
    bpy.data.objects.remove(cutter)


def spear(name, x, y, z, h, r, mat):
    """Wrought-iron spear finial: a collar and a four-sided point."""
    return lathe(name, [(0, z), (r, z), (r * 0.5, z + h * 0.25), (r * 1.3, z + h * 0.4), (0, z + h)], 4, mat, (x, y, 0), smooth=False)


def clock_hand(name, length, width, theta_deg, cx, cz, y0, y1, mat):
    """An ornate spade-tipped hand pointing at clockwise angle theta from 12."""
    L, w = length, width
    pts = [(-w * 0.6, -L * 0.18), (w * 0.6, -L * 0.18), (w * 0.4, L * 0.7), (w * 1.8, L * 0.8),
           (0, L), (-w * 1.8, L * 0.8), (-w * 0.4, L * 0.7)]
    h = extrude(name, pts, y0, y1, mat, "xz")
    C.transform(h, Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(math.radians(theta_deg), 4, "Y"))
    return h


def roman_ring(text_list, R, cz, glyph_h, stroke, y, depth, mat, cx=0.0):
    """Radially set roman numerals built from stroke boxes (clock-maker's IIII)."""
    parts = []
    for hour, text in enumerate(text_list, start=1):
        theta = math.radians(hour * 30)
        up = Vector((math.sin(theta), math.cos(theta)))
        right = Vector((math.cos(theta), -math.sin(theta)))
        widths = {"I": stroke, "V": glyph_h * 0.55, "X": glyph_h * 0.55}
        gap = stroke * 0.8
        total = sum(widths[c] for c in text) + gap * (len(text) - 1)
        u = -total / 2
        strokes = []
        for ch in text:
            w = widths[ch]
            c = u + w / 2
            if ch == "I":
                strokes.append((c, 0, glyph_h, 0))
            elif ch == "V":
                a = math.degrees(math.atan2(w / 2, glyph_h))
                ln = math.hypot(w / 2, glyph_h)
                strokes += [(c - w / 4, 0, ln, -a), (c + w / 4, 0, ln, a)]
            else:
                a = math.degrees(math.atan2(w, glyph_h))
                ln = math.hypot(w, glyph_h)
                strokes += [(c, 0, ln, -a), (c, 0, ln, a)]
            u += w + gap
        for sv in (-1, 1):  # serif bars under and over the whole numeral
            strokes.append((0, sv * glyph_h / 2, total + stroke, 90))
        for su, sv, ln, alpha in strokes:
            p = Vector((cx, cz)) + up * (R + sv) + right * su
            parts.append(C.box("Stroke", (stroke if alpha != 90 else stroke * 0.7, depth, ln), (p.x, y, p.y), mat, (0, math.degrees(theta) + alpha, 0)))
    return parts


ROMAN = ["I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


# ------------------------------------------------------------------ gate and garden
def build_gate_pillar():
    M = start()
    P = [C.box("Plinth", (1.3, 1.3, 0.45), (0, 0, 0.225), M["stone"]),
         C.box("PlinthTop", (1.16, 1.16, 0.12), (0, 0, 0.51), M["stone"]),
         C.box("Shaft", (0.96, 0.96, 3.1), (0, 0, 0.57 + 1.55), M["brick"])]
    for i in range(7):  # alternating stone quoins on every corner
        z = 0.57 + 0.22 + i * 0.44
        w = (0.34, 0.22) if i % 2 == 0 else (0.22, 0.34)
        for sx in (-1, 1):
            for sy in (-1, 1):
                P.append(C.box("Quoin", (w[0], w[1], 0.2), (sx * (0.49 - w[0] / 2), sy * (0.49 - w[1] / 2), z), M["stone"]))
    P += [C.box("Cornice", (1.24, 1.24, 0.16), (0, 0, 3.75), M["stone"]),
          C.box("Cornice2", (1.1, 1.1, 0.12), (0, 0, 3.89), M["stone"])]
    cap = lathe("Cap", [(0, 3.95), (0.72, 3.95), (0.0, 4.45)], 4, M["stone_dark"], smooth=False)
    C.transform(cap, Matrix.Rotation(math.radians(45), 4, "Z"))
    P.append(cap)
    # A dead iron lantern crowns the pillar: no one lights it any more.
    P.append(C.box("LampPost", (0.08, 0.08, 0.5), (0, 0, 4.6), M["iron"]))
    P.append(C.box("LampGlass", (0.3, 0.3, 0.4), (0, 0, 5.05), M["glass"]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(C.box("LampFrame", (0.04, 0.04, 0.46), (sx * 0.16, sy * 0.16, 5.05), M["iron"]))
    P.append(C.box("LampBase", (0.38, 0.38, 0.05), (0, 0, 4.83), M["iron"]))
    roof = lathe("LampRoof", [(0, 5.27), (0.3, 5.27), (0, 5.55)], 4, M["iron"], smooth=False)
    C.transform(roof, Matrix.Rotation(math.radians(45), 4, "Z"))
    P.append(roof)
    P.append(spear("LampSpike", 0, 0, 5.5, 0.25, 0.03, M["iron"]))
    # Brass name plate on the front (the text has long since worn away).
    P.append(C.box("Plate", (0.56, 0.03, 0.34), (0, -0.495, 2.4), M["brass"]))
    P.append(C.box("PlateBack", (0.64, 0.02, 0.42), (0, -0.485, 2.4), M["stone"]))
    P.append(C.box("MossFoot", (1.34, 1.34, 0.08), (0, 0, 0.04), M["moss"]))
    finish("gate_pillar", P)


def build_gate_iron():
    M = start()
    P = [C.box("Sill", (4.4, 0.6, 0.1), (0, 0, 0.05), M["stone"])]

    def top(x):
        return 2.7 + 0.6 * (1 - (x / 2.0) ** 2)

    for sx in (-1, 1):  # frame stiles at the hinge and the meeting edge
        for x in (sx * 1.96, sx * 0.05):
            P.append(C.box("Stile", (0.08, 0.08, top(x) - 0.1), (x, 0, 0.1 + (top(x) - 0.1) / 2), M["iron"]))
    P.append(C.box("RailLow", (4.0, 0.06, 0.08), (0, 0, 0.16), M["iron"]))
    P.append(C.box("RailDog", (4.0, 0.05, 0.06), (0, 0, 0.58), M["iron"]))
    P.append(C.box("RailMid", (4.0, 0.06, 0.08), (0, 0, 2.2), M["iron"]))
    pts = [Vector((-2.0 + 4.0 * i / 16, 0, top(-2.0 + 4.0 * i / 16))) for i in range(17)]
    P.append(C.tube("RailTop", pts, [0.045] * 17, 4, M["iron"], (1.0, 1.4)))
    for k in range(25):
        x = -1.92 + k * 0.16
        if abs(x) < 0.12 or abs(x) > 1.9:
            continue
        h = top(x) + 0.12
        if k == 16:  # one bar was forced aside long ago
            P.append(C.tube("BentBar", [Vector((x, 0, 0.16)), Vector((x + 0.06, -0.16, 1.2)), Vector((x, 0, 2.2)), Vector((x, 0, h))], [0.022] * 4, 4, M["iron"]))
        else:
            P.append(C.box("Bar", (0.036, 0.036, h - 0.12), (x, 0, 0.12 + (h - 0.12) / 2), M["iron"]))
        P.append(spear("Spear", x, 0, h, 0.24, 0.04, M["iron"]))
        if abs(x + 0.08) > 0.12 and abs(x + 0.08) < 1.9:  # dog bars between the low rails
            P.append(C.box("DogBar", (0.026, 0.026, 0.42), (x + 0.08, 0, 0.37), M["iron"]))
    for sx in (-1, 1):  # a roundel on each leaf
        cx, cz = sx * 1.0, 1.4
        P.append(band("Roundel", circle(0.46, 24, cx, cz), circle(0.4, 24, cx, cz), -0.04, 0.04, M["iron"], "xz", True))
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            ox, oz = cx + 0.17 * math.cos(a), cz + 0.17 * math.sin(a)
            P.append(band("Foil", circle(0.16, 12, ox, oz), circle(0.12, 12, ox, oz), -0.03, 0.03, M["iron"], "xz", True))
        P.append(C.box("Scroll", (0.05, 0.05, 0.36), (sx * 1.0, 0, 2.62), M["iron"]))
    for i in range(7):  # the chain and the padlock Meiling never opens
        z = 1.62 - i * 0.07
        P.append(C.box("Link", (0.07 if i % 2 else 0.02, 0.02 if i % 2 else 0.07, 0.09), (0.0, -0.07, z), M["iron"]))
    P.append(C.box("Padlock", (0.14, 0.07, 0.16), (0.0, -0.08, 1.06), M["brass"]))
    P.append(C.tube("Shackle", [Vector((-0.04, -0.08, 1.14)), Vector((-0.04, -0.08, 1.22)), Vector((0.04, -0.08, 1.22)), Vector((0.04, -0.08, 1.14))], [0.012] * 4, 6, M["brass"]))
    finish("gate_iron", P)


def garden_wall_parts(M, rng, broken):
    P = [C.box("Plinth", (4.0, 0.62, 0.45), (0, 0, 0.225), M["stone"]),
         C.box("Body", (4.0, 0.5, 2.0), (0, 0, 1.45), M["brick"]),
         C.box("Coping", (4.0, 0.66, 0.12), (0, 0, 2.51), M["stone"]),
         extrude("Ridge", [(-0.3, 2.57), (0.3, 2.57), (0, 2.72)], -2.0, 2.0, M["stone"], "yz"),
         C.box("RailTop", (3.4, 0.04, 0.05), (0, 0, 3.2), M["iron"])]
    for sx in (-1, 1):  # half pilasters: two neighbouring modules make a whole one
        P.append(C.box("Pilaster", (0.25, 0.72, 2.75), (sx * 1.875, 0, 1.375), M["brick_dark"]))
        P.append(C.box("PilCap", (0.3, 0.8, 0.14), (sx * 1.85, 0, 2.82), M["stone"]))
        P.append(C.box("PilCap2", (0.22, 0.6, 0.18), (sx * 1.89, 0, 2.98), M["stone_dark"]))
    for k in range(14):
        x = -1.62 + k * 0.25
        if broken and -1.2 < x < 1.5:
            continue
        P.append(C.box("Rail", (0.03, 0.03, 0.62), (x, 0, 2.95), M["iron"]))
        P.append(spear("Spear", x, 0, 3.26, 0.16, 0.03, M["iron"]))
    # Stucco clinging to the brick, and a band of moss at the foot.
    for _ in range(9):
        sy = rng.choice((-1, 1))
        w, h = rng.uniform(0.4, 1.2), rng.uniform(0.3, 0.9)
        x, z = rng.uniform(-1.6 + w / 2, 1.6 - w / 2), rng.uniform(0.5 + h / 2, 2.4 - h / 2)
        P.append(C.box("Stucco", (w, 0.02, h), (x, sy * 0.255, z), M["plaster"]))
    P.append(C.box("Moss", (4.0, 0.66, 0.06), (0, 0, 0.47), M["moss"]))
    for _ in range(2):  # dead ivy
        x = rng.uniform(-1.4, 1.4)
        pts = [Vector((x + rng.uniform(-0.25, 0.25), -0.27, 0.45 + i * 0.35)) for i in range(6)]
        P.append(C.tube("Ivy", pts, [0.025] * 6, 4, M["dead"]))
    return P


def build_wall_segment(broken=False):
    M = start()
    rng = random.Random(7 if broken else 5)
    P = garden_wall_parts(M, rng, broken)
    if broken:
        jag = [(-1.2, 3.6), (-1.05, 2.05), (-0.6, 2.2), (-0.2, 1.35), (0.35, 1.7), (0.8, 1.2), (1.25, 2.3), (1.5, 3.6)]
        cutter = extrude("Breach", jag, -1.0, 1.0, M["stone"], "xz")
        hit = [o for o in P if o.name.split(".")[0] in ("Body", "Coping", "Ridge", "RailTop", "Stucco", "Ivy")]
        cut(hit, cutter)
        for _ in range(16):  # the collapsed brick piles against both faces
            s = rng.uniform(0.15, 0.45)
            y = rng.choice((-1, 1)) * rng.uniform(0.35, 0.95)
            P.append(C.box("Rubble", (s, s * rng.uniform(0.5, 1), s * 0.6), (rng.uniform(-1.0, 1.2), y, s * 0.25),
                           rng.choice((M["brick"], M["brick_dark"], M["stone"])), (rng.uniform(-20, 20), rng.uniform(-20, 20), rng.uniform(0, 90))))
    finish("wall_segment_broken" if broken else "wall_segment", P)


def window_unit(M, cx, z0, w, spring, y_face, lit, P):
    """A facade window: stone arch frame, mullion, transom and a glowing pane."""
    P.append(arch_frame("WinFrame", w, spring, 0.2, y_face - 0.14, y_face + 0.02, M["stone"], cx, z0))
    P.append(extrude("Pane", arch(w, spring, 6, cx, z0), y_face - 0.02, y_face + 0.01, M["glow"] if lit else M["void"], "xz"))
    top = z0 + spring + 0.74 * w
    P.append(C.box("Mullion", (0.07, 0.06, top - z0), (cx, y_face - 0.04, (z0 + top) / 2), M["stone_dark"]))
    P.append(C.box("Transom", (w, 0.06, 0.07), (cx, y_face - 0.04, z0 + spring), M["stone_dark"]))
    P.append(C.box("Sill", (w + 0.5, 0.3, 0.12), (cx, y_face - 0.12, z0 - 0.04), M["stone"]))


def build_mansion_facade():
    M = start()
    yf = -1.0  # front face of the brick body
    P = [C.box("Body", (16.0, 2.0, 12.0), (0, 0, 6.0), M["brick"]),
         C.box("Plinth", (16.2, 2.2, 1.0), (0, 0, 0.5), M["stone"]),
         C.box("String", (16.3, 2.3, 0.25), (0, 0, 5.9), M["stone"]),
         C.box("Cornice", (16.4, 2.4, 0.4), (0, 0, 11.8), M["stone"]),
         extrude("Roof", [(-1.0, 12.0), (1.0, 12.0), (0.0, 14.2)], -7.9, 7.9, M["roof"], "yz")]
    for k in range(16):  # parapet merlons
        if k in (7, 8):
            continue
        P.append(C.box("Merlon", (0.6, 0.5, 0.7), (-7.5 + k * 1.0, yf + 0.25, 12.35), M["brick_dark"]))
    for x in (-7.8, -4.5, -1.6, 1.6, 4.5, 7.8):
        P.append(C.box("Pilaster", (0.5, 0.3, 10.6), (x, yf - 0.1, 6.3), M["brick_dark"]))
    for i, x in enumerate((-6.1, -3.05, 3.05, 6.1)):
        window_unit(M, x, 1.7, 1.4, 1.9, yf, i in (1, 3), P)
        window_unit(M, x, 7.0, 1.4, 1.9, yf, i in (0, 2), P)
    # Main door under the clock tower.
    P.append(arch_frame("DoorFrame", 2.6, 2.4, 0.35, yf - 0.2, yf + 0.02, M["stone"], 0, 1.0))
    P.append(extrude("Door", arch(2.6, 2.4, 6, 0, 1.0), yf - 0.04, yf + 0.01, M["wood"], "xz"))
    P.append(C.box("DoorSplit", (0.06, 0.05, 4.2), (0, yf - 0.06, 3.1), M["iron"]))
    for sx in (-1, 1):
        for z in (1.8, 2.8, 3.8):
            P.append(C.box("Strap", (1.1, 0.04, 0.08), (sx * 0.65, yf - 0.06, z), M["iron"]))
    P.append(C.box("Steps", (4.2, 1.2, 0.5), (0, yf - 0.6, 0.75), M["stone"]))
    P.append(C.box("Steps2", (5.0, 1.8, 0.5), (0, yf - 0.9, 0.25), M["stone"]))
    window_unit(M, 0, 7.0, 1.8, 1.9, yf, True, P)
    P.append(C.box("Balcony", (3.0, 0.8, 0.2), (0, yf - 0.4, 6.8), M["stone"]))
    # Clock tower: the mansion's clock stopped with everything else.
    P += [C.box("Tower", (4.4, 2.4, 7.0), (0, 0, 15.1), M["brick"]),
          C.box("TowerCornice", (4.8, 2.8, 0.35), (0, 0, 18.7), M["stone"])]
    roof = lathe("Spire", [(0, 18.85), (3.2, 18.85), (0, 23.5)], 4, M["roof"], smooth=False)
    C.transform(roof, Matrix.Scale(0.75, 4, (0, 1, 0)) @ Matrix.Rotation(math.radians(45), 4, "Z"))
    P.append(roof)
    P.append(spear("Finial", 0, 0, 23.3, 1.2, 0.12, M["iron"]))
    cz, yc = 15.4, -1.2
    P.append(extrude("TowerDial", circle(1.35, 32, 0, cz), yc - 0.05, yc + 0.01, M["bone"], "xz"))
    P.append(band("TowerBezel", circle(1.55, 32, 0, cz), circle(1.35, 32, 0, cz), yc - 0.12, yc + 0.01, M["brass"], "xz", True))
    for k in range(12):
        a = math.radians(k * 30)
        P.append(C.box("Tick", (0.1, 0.03, 0.3), (1.12 * math.sin(a), yc - 0.07, cz + 1.12 * math.cos(a)), M["iron"], (0, k * 30, 0)))
    h, m = FROZEN_TIME
    P.append(clock_hand("Hour", 0.8, 0.07, (h + m / 60) * 30, 0, cz, yc - 0.1, yc - 0.06, M["iron"]))
    P.append(clock_hand("Minute", 1.15, 0.05, m * 6, 0, cz, yc - 0.13, yc - 0.1, M["iron"]))
    finish("mansion_facade", P)


def build_rose_bush():
    M = start()
    rng = random.Random(21)
    verts, edges, radii = [Vector((0, 0, 0))], [], [0.07]
    tips = []

    def grow(i, d, length, r, level):
        prev, pos = i, verts[i]
        for s in range(3):
            d = (d + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(-0.15, 0.3)))).normalized()
            pos = pos + d * (length / 3)
            r *= 0.8
            verts.append(pos.copy())
            radii.append(max(r, 0.008))
            edges.append((prev, len(verts) - 1))
            prev = len(verts) - 1
            if level < 2 and rng.random() < 0.6:
                grow(prev, Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 0.9))), length * 0.6, r * 0.85, level + 1)
        tips.append(pos.copy())

    for k in range(6):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        grow(0, Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1.0)), rng.uniform(0.7, 1.1), 0.045, 0)
    mesh = bpy.data.meshes.new("Bush")
    mesh.from_pydata([tuple(v) for v in verts], edges, [])
    obj = bpy.data.objects.new("Bush", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new("Skin", "SKIN")
    for i, r in enumerate(radii):
        obj.data.skin_vertices[0].data[i].radius = (r, r)
    obj.data.skin_vertices[0].data[0].use_root = True
    C.apply_modifiers(obj)
    obj.data.materials.append(M["dead"])
    P = [obj, lathe("Mound", [(0, 0), (0.75, 0), (0.5, 0.12), (0, 0.18)], 10, M["soil"])]
    for t in rng.sample(tips, min(8, len(tips))):  # a few withered blooms still cling on
        rs = rng.uniform(0.06, 0.09)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rs)
        for v in bm.verts:
            v.co.z *= 0.7
            v.co += Vector(t)
        P.append(C.new_object("Rose", bm, M["rose"], smooth=False))
    for _ in range(14):  # fallen petals
        r, a = rng.uniform(0.2, 0.9), rng.uniform(0, 2 * math.pi)
        z = max(0.01, 0.18 * (1 - r / 0.75)) if r < 0.75 else 0.01
        P.append(C.box("Petal", (0.05, 0.035, 0.008), (r * math.cos(a), r * math.sin(a), z), M["rose"], (0, 0, rng.uniform(0, 180))))
    finish("rose_bush_dead", P)


def build_fountain():
    M = start()
    rng = random.Random(4)
    oct_o, oct_i = circle(2.6, 8, rot=math.pi / 8), circle(2.3, 8, rot=math.pi / 8)
    P = [band("Basin", oct_o, oct_i, 0.0, 0.6, M["stone"], "xy", True),
         band("Rim", circle(2.72, 8, rot=math.pi / 8), circle(2.22, 8, rot=math.pi / 8), 0.6, 0.72, M["stone"], "xy", True),
         extrude("Floor", oct_i, 0.0, 0.12, M["stone_dark"], "xy"),
         extrude("Stain", circle(1.6, 12, rot=0.2), 0.12, 0.13, M["soil"], "xy"),
         lathe("Pedestal", [(0, 0.12), (0.6, 0.12), (0.6, 0.3), (0.4, 0.4), (0.28, 0.55), (0.24, 1.2), (0.32, 1.32), (0, 1.36)], 16, M["stone"]),
         lathe("Bowl", [(0, 1.3), (0.35, 1.32), (0.92, 1.5), (1.02, 1.64), (0.92, 1.66), (0.3, 1.56), (0, 1.54)], 20, M["stone"]),
         lathe("Column", [(0, 1.54), (0.16, 1.54), (0.12, 2.2), (0.2, 2.3), (0, 2.3)], 12, M["stone"]),
         lathe("UpperBowl", [(0, 2.25), (0.2, 2.28), (0.45, 2.42), (0.48, 2.5), (0.4, 2.51), (0, 2.46)], 16, M["stone"]),
         lathe("Orb", [(0, 2.46), (0.1, 2.5), (0.14, 2.6), (0.1, 2.7), (0.02, 2.78), (0, 3.0)], 10, M["stone_dark"])]
    P.append(band("MossRing", circle(2.66, 8, rot=math.pi / 8), circle(2.6, 8, rot=math.pi / 8), 0.0, 0.12, M["moss"], "xy", True))
    for _ in range(40):  # dead leaves in the empty basin and blown against the rim
        r, a = rng.uniform(0.6, 2.2), rng.uniform(0, 2 * math.pi)
        P.append(C.box("Leaf", (0.09, 0.05, 0.006), (r * math.cos(a), r * math.sin(a), 0.135), M["leaf"], (rng.uniform(-10, 10), 0, rng.uniform(0, 180))))
    # A chunk of the rim has fallen out and lies outside the basin.
    P.append(C.box("RimChunk", (0.8, 0.45, 0.3), (2.95, -1.3, 0.15), M["stone"], (4, -8, 32)))
    P.append(C.box("RimChunk2", (0.35, 0.3, 0.2), (3.3, -0.7, 0.1), M["stone"], (0, 10, 70)))
    finish("fountain_dry", P)


def bat_parts(M, s=1.0, base=(0, 0, 0)):
    """A perched stone bat with spread wings (scale s, feet at `base`)."""
    bx, by, bz = base
    P = [C.uv_sphere("Body", 1.0, (0, 0, 0.5), (0.26, 0.22, 0.42), 16, 10, M["stone"]),
         C.uv_sphere("Head", 0.19, (0, -0.04, 1.02), (1, 0.95, 1), 14, 8, M["stone"]),
         C.uv_sphere("Snout", 0.08, (0, -0.2, 0.97), (1, 1, 0.8), 8, 6, M["stone"])]
    for sx in (-1, 1):
        ear = lathe("Ear", [(0, 0), (0.08, 0), (0, 0.28)], 4, M["stone"], smooth=False)
        C.transform(ear, Matrix.Translation((sx * 0.1, -0.02, 1.12)) @ Matrix.Rotation(math.radians(sx * 20), 4, "Y"))
        P.append(ear)
        P.append(C.uv_sphere("Eye", 0.03, (sx * 0.075, -0.17, 1.06), (1, 0.6, 1), 8, 4, M["eye"]))
        P.append(C.box("Foot", (0.14, 0.2, 0.08), (sx * 0.12, -0.12, 0.04), M["stone"]))
        wing = [(0, 0.1), (0.35, 0.4), (0.8, 0.75), (1.25, 0.95), (1.35, 0.7), (1.2, 0.25), (1.05, -0.25),
                (0.9, -0.05), (0.75, -0.5), (0.55, -0.2), (0.35, -0.55), (0.2, -0.3), (0, -0.35)]
        w = extrude("Wing", [(sx * (0.15 + u), 0.7 + v) for u, v in wing], -0.03, 0.03, M["stone"], "xz")
        bones = [C.tube("Arm", [Vector((sx * 0.15, 0, 0.8)), Vector((sx * 0.95, 0, 1.45))], [0.05, 0.035], 5, M["stone"])]
        for fu, fv in ((1.25, 0.95), (1.2, 0.25), (0.75, -0.5), (0.35, -0.55)):
            bones.append(C.tube("Finger", [Vector((sx * 0.95, 0, 1.45)), Vector((sx * (0.15 + fu), 0, 0.7 + fv))], [0.03, 0.012], 4, M["stone"]))
        m = Matrix.Translation((sx * 0.15, 0, 0)) @ Matrix.Rotation(math.radians(sx * -22), 4, "Z") @ Matrix.Translation((-sx * 0.15, 0, 0))
        for o in [w] + bones:
            C.transform(o, m)
        P += [w] + bones
    for o in P:
        C.transform(o, Matrix.Translation((bx, by, bz)) @ Matrix.Scale(s, 4))
    return P


def build_bat_statue():
    M = start()
    P = [C.box("Base", (1.2, 1.2, 0.18), (0, 0, 0.09), M["stone"]),
         C.box("Die", (0.9, 0.9, 1.0), (0, 0, 0.68), M["stone_dark"]),
         C.box("Panel", (0.6, 0.02, 0.6), (0, -0.46, 0.68), M["stone"]),
         C.box("Cornice", (1.08, 1.08, 0.14), (0, 0, 1.25), M["stone"]),
         C.box("Moss", (1.22, 1.22, 0.06), (0, 0, 0.03), M["moss"])]
    P += bat_parts(M, 1.0, (0, 0, 1.32))
    finish("bat_statue", P)


# ------------------------------------------------------------------ interior shell
def build_floor_tile():
    M = start()
    rng = random.Random(9)
    P = [C.box("Slab", (4.0, 4.0, 0.3), (0, 0, -0.16), M["stone_dark"])]
    for i in range(4):
        for j in range(4):
            x, y = -1.5 + i, -1.5 + j
            mat = M["marble_l"] if (i + j) % 2 == 0 else M["marble_d"]
            if (i, j) == (2, 1):  # cracked in two, one half sunk
                P.append(C.box("TileA", (0.97, 0.47, 0.03), (x, y - 0.25, -0.015), mat))
                P.append(C.box("TileB", (0.97, 0.47, 0.03), (x, y + 0.25, -0.03), mat, (2.5, 0, 1.5)))
            elif (i, j) == (0, 3):  # lifted and askew
                P.append(C.box("Tile", (0.97, 0.97, 0.03), (x + 0.03, y, -0.01), mat, (0, 1.5, 4)))
            elif (i, j) == (3, 3):  # missing: slab and rubble show through
                for _ in range(3):
                    s = rng.uniform(0.12, 0.25)
                    P.append(C.box("Chip", (s, s * 0.7, 0.03), (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), -0.0), mat, (0, 0, rng.uniform(0, 90))))
            else:
                P.append(C.box("Tile", (0.97, 0.97, 0.03), (x, y, -0.015), mat))
    for i in range(3):
        for j in range(3):
            d = C.box("Inlay", (0.14, 0.14, 0.032), (-1 + i, -1 + j, -0.014), M["brass"], (0, 0, 45))
            P.append(d)
    finish("floor_tile", P)


def interior_wall_parts(M, rng):
    """Shared 4 m x 6 m interior wall: plaster core, wainscot, wallpaper, crown."""
    yf = -0.15
    P = [C.box("Core", (4.0, 0.3, 6.0), (0, 0, 3.0), M["plaster"]),
         C.box("Skirting", (4.0, 0.06, 0.2), (0, yf - 0.03, 0.1), M["wood"]),
         C.box("Wainscot", (4.0, 0.03, 1.2), (0, yf - 0.015, 0.6), M["wood"]),
         C.box("ChairRail", (4.0, 0.08, 0.08), (0, yf - 0.04, 1.24), M["wood"]),
         C.box("Paper", (4.0, 0.02, 4.3), (0, yf - 0.01, 3.43), M["paper"]),
         C.box("Frieze", (4.0, 0.04, 0.22), (0, yf - 0.02, 5.47), M["wood_red"]),
         C.box("Crown", (4.0, 0.16, 0.16), (0, yf - 0.08, 5.84), M["wood"]),
         C.box("Crown2", (4.0, 0.1, 0.1), (0, yf - 0.05, 5.71), M["wood"])]
    for sx in (-1, 1):
        P.append(C.box("Panel", (1.5, 0.03, 0.72), (sx * 0.95, yf - 0.045, 0.66), M["wood_red"]))
        P.append(C.box("HalfPilaster", (0.12, 0.1, 5.4), (sx * 1.94, yf - 0.05, 2.9), M["wood"]))
    for k in range(8):
        P.append(C.box("Stripe", (0.12, 0.012, 4.3), (-1.75 + k * 0.5, yf - 0.026, 3.43), M["stripe"]))
    for _ in range(3):  # wallpaper fallen away to bare plaster
        w, h = rng.uniform(0.3, 0.8), rng.uniform(0.4, 1.3)
        P.append(C.box("Bare", (w, 0.004, h), (rng.uniform(-1.5, 1.5), yf - 0.034, rng.uniform(1.6 + h / 2, 5.2 - h / 2)), M["plaster"]))
    for _ in range(2):  # peeling strips curling off the wall
        x, z = rng.uniform(-1.6, 1.6), rng.uniform(3.0, 5.0)
        P.append(C.box("Peel", (0.45, 0.006, 0.9), (x, yf - 0.1, z - 0.4), M["paper"], (-12, 0, rng.uniform(-6, 6))))
    return P


def build_wall_panel():
    M = start()
    finish("wall_panel", interior_wall_parts(M, random.Random(12)))


def build_wall_window():
    M = start()
    rng = random.Random(13)
    P = interior_wall_parts(M, rng)
    w, spring, z0 = 1.6, 2.3, 1.5
    cutter = extrude("Opening", arch(w, spring, 8, 0, z0), -0.6, 0.6, M["plaster"], "xz")
    names = ("Core", "Paper", "Stripe", "Bare", "Peel", "Frieze")
    cut([o for o in P if o.name.split(".")[0] in names], cutter)
    P.append(arch_frame("Frame", w, spring, 0.18, -0.26, 0.19, M["wood"], 0, z0, 8))
    P.append(extrude("Glass", arch(w, spring, 8, 0, z0), 0.04, 0.06, M["glow"], "xz"))
    top = z0 + spring + 0.74 * w
    P.append(C.box("Mullion", (0.06, 0.06, top - z0), (0, 0.0, (z0 + top) / 2), M["iron"]))
    for z in (z0 + 0.8, z0 + 1.6, z0 + spring):
        P.append(C.box("Lead", (w, 0.05, 0.05), (0, 0.0, z), M["iron"]))
    rz = z0 + spring + 0.55
    P.append(band("Rose", circle(0.34, 16, 0, rz), circle(0.28, 16, 0, rz), -0.03, 0.03, M["iron"], "xz", True))
    P.append(C.box("Sill", (2.1, 0.4, 0.1), (0, -0.2, z0 - 0.05), M["wood"]))
    # Heavy velvet drapes, one torn down to a rag.
    P.append(C.box("CurtainRod", (2.9, 0.05, 0.05), (0, -0.33, top + 0.35), M["brass"]))
    P.append(extrude("Drape", [(-1.45, top + 0.35), (-0.95, top + 0.35), (-0.9, 0.6), (-1.05, 0.45), (-1.2, 0.55), (-1.45, 0.4)], -0.36, -0.3, M["velvet"], "xz"))
    P.append(extrude("DrapeTorn", [(0.95, top + 0.35), (1.45, top + 0.35), (1.42, 3.2), (1.25, 2.9), (1.12, 3.4), (0.98, 3.0)], -0.36, -0.3, M["velvet"], "xz"))
    finish("wall_window", P)


def build_doorway():
    M = start()
    rng = random.Random(14)
    P = interior_wall_parts(M, rng)
    w, spring = 2.6, 2.8
    cutter = extrude("Opening", arch(w, spring, 8, 0, -0.1), -0.6, 0.6, M["plaster"], "xz")
    names = ("Core", "Skirting", "Wainscot", "ChairRail", "Panel", "Paper", "Stripe", "Bare", "Peel", "Frieze")
    cut([o for o in P if o.name.split(".")[0] in names], cutter)
    P.append(arch_frame("Frame", w, spring, 0.3, -0.28, 0.2, M["stone"], 0, 0.0, 8))
    P.append(arch_frame("FrameInner", w + 0.08, spring, 0.06, -0.32, -0.27, M["wood"], 0, 0.0, 8))
    apex = spring + 0.74 * w
    P.append(C.box("Keystone", (0.42, 0.46, 0.6), (0, -0.03, apex + 0.2), M["stone"]))
    P.append(extrude("Emblem", circle(0.22, 16, 0, apex + 0.72), -0.28, -0.24, M["brass"], "xz"))
    P.append(C.box("EmblemHand", (0.03, 0.02, 0.18), (0.0, -0.29, apex + 0.78), M["iron"]))
    P.append(C.box("Threshold", (w, 0.5, 0.03), (0, 0, 0.015), M["stone"]))
    finish("doorway", P)


def build_pillar():
    M = start()
    P = [C.box("Plinth", (1.0, 1.0, 0.3), (0, 0, 0.15), M["stone_dark"]),
         lathe("Base", [(0, 0.3), (0.46, 0.3), (0.46, 0.38), (0.4, 0.46), (0.36, 0.56), (0, 0.56)], 16, M["stone"]),
         cyl("Shaft", 0.3, 0.56, 5.2, M["stone"], 16),
         lathe("Capital", [(0, 5.2), (0.34, 5.2), (0.36, 5.28), (0.46, 5.45), (0.52, 5.56), (0, 5.56)], 16, M["stone"]),
         C.box("Abacus", (1.06, 1.06, 0.44), (0, 0, 5.78), M["stone_dark"])]
    for k in range(4):  # clustered gothic shafts
        a = math.pi / 4 + k * math.pi / 2
        P.append(cyl("Colonette", 0.1, 0.56, 5.2, M["stone"], 8, 0.31 * math.cos(a), 0.31 * math.sin(a)))
    for z in (2.2, 4.0):
        P.append(lathe("Band", [(0, z), (0.44, z), (0.44, z + 0.1), (0, z + 0.1)], 16, M["brass"]))
    # A torn crimson banner hangs from the capital.
    P.append(extrude("Banner", [(-0.3, 5.1), (0.3, 5.1), (0.3, 3.2), (0.12, 3.35), (0.0, 3.0), (-0.14, 3.3), (-0.3, 3.15)], -0.46, -0.44, M["velvet"], "xz"))
    P.append(C.box("BannerRod", (0.8, 0.04, 0.04), (0, -0.45, 5.12), M["brass"]))
    finish("pillar", P)


def build_staircase():
    M = start()
    n, rise, run, width = 15, 0.2, 0.32, 3.2
    y0 = -3.0
    corners = [(y0, 0.0)]
    for i in range(n):
        corners += [(y0 + i * run, (i + 1) * rise), (y0 + (i + 1) * run, (i + 1) * rise)]
    body = corners + [(3.0, n * rise), (3.0, 0.0)]
    P = [extrude("Steps", body, -width / 2, width / 2, M["stone"], "yz")]
    top_y = y0 + n * run
    for sx in (-1, 1):
        para = [(y0, 0.0), (y0, 1.0), (top_y, n * rise + 1.0), (3.0, n * rise + 1.0), (3.0, 0.0)]
        P.append(extrude("Parapet", para, sx * width / 2, sx * (width / 2 + 0.3), M["stone_dark"], "yz"))
        slope = math.degrees(math.atan2(n * rise, top_y - y0))
        length = math.hypot(n * rise, top_y - y0)
        P.append(C.box("Coping", (0.4, length, 0.1), (sx * (width / 2 + 0.15), (y0 + top_y) / 2, 1.0 + n * rise / 2 + 0.05), M["stone"], (slope, 0, 0)))
        P.append(C.box("CopingTop", (0.4, 3.0 - top_y, 0.1), (sx * (width / 2 + 0.15), (top_y + 3.0) / 2, n * rise + 1.05), M["stone"]))
        P.append(C.box("Newel", (0.46, 0.46, 1.4), (sx * (width / 2 + 0.15), y0 + 0.2, 0.7), M["stone"]))
        P.append(C.uv_sphere("NewelOrb", 0.17, (sx * (width / 2 + 0.15), y0 + 0.2, 1.57), (1, 1, 1), 10, 6, M["stone_dark"]))
        P.append(C.box("NewelTop", (0.46, 0.46, 0.6), (sx * (width / 2 + 0.15), 2.8, n * rise + 1.3), M["stone"]))
    d = 0.02  # the runner is a thin stepped shell laid over the treads
    run_end = 3.0 - 0.3
    inner = corners[1:] + [(run_end, n * rise)]
    outer = [(y - d, z + d) for y, z in inner]
    outer[-1] = (run_end, n * rise + d)
    poly = [(y0 - d, 0.0)] + outer + inner[::-1] + [(y0, 0.0)]
    P.append(extrude("Runner", poly, -0.75, 0.75, M["velvet"], "yz"))
    for i in range(n):
        y, z = y0 + i * run + 0.03, (i + 1) * rise + d
        P.append(C.tube("StairRod", [Vector((-0.8, y, z)), Vector((0.8, y, z))], [0.015, 0.015], 6, M["brass"]))
    finish("staircase", P)


# ------------------------------------------------------------------ clocks and light
def build_grand_clock():
    M = start()
    P = [C.box("Plinth", (0.78, 0.52, 0.3), (0, 0, 0.15), M["wood"]),
         C.box("Step", (0.7, 0.47, 0.06), (0, 0, 0.33), M["wood"]),
         C.box("Trunk", (0.6, 0.4, 1.4), (0, 0, 1.06), M["wood_red"]),
         C.box("DoorFrame", (0.44, 0.02, 1.1), (0, -0.205, 1.06), M["wood"]),
         C.box("Glass", (0.3, 0.012, 0.86), (0, -0.215, 1.1), M["glass"]),
         C.box("Rod", (0.018, 0.006, 0.62), (0.04, -0.224, 1.18), M["brass"]),
         C.tube("Bob", [Vector((0.04, -0.222, 0.83)), Vector((0.04, -0.232, 0.83))], [0.085, 0.085], 16, M["brass"]),
         C.box("Waist", (0.68, 0.48, 0.08), (0, 0, 1.78), M["wood"]),
         C.box("Hood", (0.7, 0.46, 0.62), (0, 0, 2.13), M["wood"]),
         C.box("HoodCap", (0.78, 0.52, 0.07), (0, 0, 2.475), M["wood"])]
    cz = 2.13
    P.append(extrude("Dial", circle(0.24, 24, 0, cz), -0.25, -0.23, M["bone"], "xz"))
    P.append(band("Bezel", circle(0.28, 24, 0, cz), circle(0.24, 24, 0, cz), -0.265, -0.23, M["brass"], "xz", True))
    for k in range(12):
        a = math.radians(k * 30)
        P.append(C.box("Mark", (0.02, 0.006, 0.05 if k % 3 else 0.07), (0.2 * math.sin(a), -0.253, cz + 0.2 * math.cos(a)), M["iron"], (0, k * 30, 0)))
    h, m = FROZEN_TIME
    P.append(clock_hand("Hour", 0.13, 0.012, (h + m / 60) * 30, 0, cz, -0.262, -0.256, M["iron"]))
    P.append(clock_hand("Minute", 0.19, 0.009, m * 6, 0, cz, -0.268, -0.262, M["iron"]))
    P.append(C.box("Crack", (0.006, 0.004, 0.22), (0.07, -0.2535, cz - 0.06), M["void"], (0, 28, 0)))
    for sx in (-1, 1):
        P.append(cyl("Column", 0.025, 1.84, 2.43, M["brass"], 8, sx * 0.31, -0.2))
    P.append(extrude("Pediment", arch(0.72, 0.02, 6, 0, 2.51, 0.5), -0.2, 0.2, M["wood"], "xz"))
    for x, z in ((-0.34, 2.51), (0.34, 2.51), (0, 2.93)):
        P.append(lathe("Finial", [(0, z), (0.04, z), (0.05, z + 0.06), (0.015, z + 0.16), (0, z + 0.2)], 8, M["brass"], (x, 0, 0)))
    finish("grand_clock", P)


def build_clock_face_wall():
    M = start()
    Rr, cz = 3.0, 3.0
    P = [extrude("Back", circle(2.95, 48, 0, cz), -0.15, 0.0, M["stone_dark"], "xz"),
         band("Rim", circle(Rr, 48, 0, cz), circle(2.7, 48, 0, cz), -0.4, 0.0, M["brass"], "xz", True),
         band("Chapter", circle(2.7, 48, 0, cz), circle(1.9, 48, 0, cz), -0.22, -0.15, M["bone"], "xz", True),
         band("Inner", circle(1.9, 48, 0, cz), circle(1.75, 48, 0, cz), -0.3, -0.15, M["brass"], "xz", True)]
    # A wedge of the chapter ring has broken away near IIII.
    wedge = [(0, cz), (3.2 * math.sin(math.radians(110)), cz + 3.2 * math.cos(math.radians(110))),
             (2.2 * math.sin(math.radians(118)), cz + 2.2 * math.cos(math.radians(118))),
             (3.2 * math.sin(math.radians(127)), cz + 3.2 * math.cos(math.radians(127))),
             (2.4 * math.sin(math.radians(134)), cz + 2.4 * math.cos(math.radians(134)))]
    cut([P[2]], extrude("Break", wedge, -0.5, -0.155, M["bone"], "xz"))
    P += roman_ring(ROMAN, 2.3, cz, 0.46, 0.07, -0.25, 0.06, M["iron"])
    for k in range(60):  # minute track
        a = math.radians(k * 6)
        big = k % 5 == 0
        P.append(C.box("Tick", (0.05 if big else 0.025, 0.04, 0.16 if big else 0.1), (2.6 * math.sin(a), -0.24, cz + 2.6 * math.cos(a)), M["iron"], (0, k * 6, 0)))
    # Skeleton movement behind the hands (Sakuya's arena).
    for gx, gz, r, teeth, y0, y1 in ((-0.55, 0.3, 1.1, 28, -0.21, -0.16), (0.8, -0.6, 0.78, 20, -0.26, -0.21), (0.3, 0.9, 0.5, 14, -0.27, -0.22), (0.9, -1.6, 0.6, 16, -0.2, -0.155)):
        g = extrude("Gear", [(gx + u, cz + gz + v) for u, v in gear_pts(r, r + 0.12, teeth)], y0, y1, M["brass"], "xz")
        for k in range(5):
            a = 2 * math.pi * k / 5
            hole = extrude("Hole", circle(r * 0.26, 10, gx + r * 0.55 * math.cos(a), cz + gz + r * 0.55 * math.sin(a)), y0 - 0.1, y1 + 0.1, M["brass"], "xz")
            cut([g], hole)
        P.append(g)
        P.append(C.tube("Arbor", [Vector((gx, y0 - 0.03, cz + gz)), Vector((gx, 0.0, cz + gz))], [0.08, 0.08], 10, M["iron"]))
    h, m = FROZEN_TIME
    P.append(clock_hand("Hour", 1.55, 0.1, (h + m / 60) * 30, 0, cz, -0.36, -0.32, M["iron"]))
    P.append(clock_hand("Minute", 2.35, 0.07, m * 6, 0, cz, -0.41, -0.37, M["iron"]))
    P.append(C.tube("Hub", [Vector((0, -0.44, cz)), Vector((0, -0.15, cz))], [0.16, 0.16], 16, M["brass"]))
    # Crest over the XII: a pointed arch with two small spires.
    P.append(arch_frame("Crest", 0.9, 0.0, 0.14, -0.2, 0.0, M["brass"], 0, cz + 2.9, 6))
    for sx in (-1, 1):
        P.append(spear("Spire", sx * 0.8, -0.1, cz + 2.82, 0.5, 0.06, M["brass"]))
    finish("clock_face_wall", P)


def candle(M, x, y, z, h, lit, P, r=0.035):
    P.append(cyl("Candle", r, z, z + h, M["wax"], 8, x, y))
    P.append(C.uv_sphere("Drip", r * 1.3, (x + r * 0.5, y, z + h * 0.5), (0.6, 0.6, 1.5), 6, 4, M["wax"]))
    if lit:
        P.append(C.uv_sphere("Flame", r * 0.8, (x, y, z + h + r * 1.4), (1, 1, 2.2), 8, 5, M["flame"]))
    else:
        P.append(C.box("Wick", (0.006, 0.006, 0.03), (x, y, z + h + 0.015), M["iron"]))


def build_chandelier():
    M = start()
    rng = random.Random(31)
    P = [lathe("Rose", [(0, 0), (0.3, 0), (0.28, -0.05), (0.12, -0.1), (0, -0.1)], 16, M["brass"])]
    for i in range(10):  # chain
        z = -0.16 - i * 0.12
        ring = [(0.045 * math.cos(2 * math.pi * k / 8), z + 0.07 * math.sin(2 * math.pi * k / 8)) for k in range(8)]
        inner = [(0.028 * math.cos(2 * math.pi * k / 8), z + 0.052 * math.sin(2 * math.pi * k / 8)) for k in range(8)]
        link = band("Link", ring, inner, -0.01, 0.01, M["iron"], "xz", True)
        if i % 2:
            C.transform(link, Matrix.Rotation(math.radians(90), 4, "Z"))
        P.append(link)
    P.append(lathe("Column", [(0, -1.3), (0.06, -1.3), (0.1, -1.45), (0.06, -1.6), (0.16, -1.9), (0.22, -2.15), (0.14, -2.35), (0.2, -2.45), (0.05, -2.65), (0, -2.9)], 12, M["brass"]))
    P.append(band("Hoop", circle(1.06, 32), circle(0.99, 32), -2.34, -2.29, M["iron"], "xy", True))
    for tier, (count, reach, zb, zt) in enumerate(((8, 1.02, -2.2, -2.08), (6, 0.55, -1.72, -1.62))):
        for k in range(count):
            a = 2 * math.pi * (k + 0.5 * tier) / count
            ca, sa = math.cos(a), math.sin(a)
            prof = [(0.1, zb), (reach * 0.4, zb - 0.2), (reach * 0.7, zb - 0.22), (reach * 0.95, zb - 0.1), (reach, zt - 0.04)]
            P.append(C.tube("Arm", [Vector((r * ca, r * sa, z)) for r, z in prof], [0.028] * 5, 6, M["iron"]))
            x, y = reach * ca, reach * sa
            P.append(lathe("Cup", [(0, zt - 0.06), (0.03, zt - 0.06), (0.08, zt), (0, zt)], 8, M["brass"], (x, y, 0)))
            if tier == 0 and k == 5:
                continue  # a candle long gone
            candle(M, x, y, zt, rng.uniform(0.08, 0.22), (tier, k) in ((0, 0), (0, 3), (1, 2)), P)
    for k in range(16):  # crystal drops, a few missing
        if k in (3, 11):
            continue
        a = 2 * math.pi * k / 16
        x, y = 1.02 * math.cos(a), 1.02 * math.sin(a)
        P.append(C.box("Wire", (0.006, 0.006, 0.1), (x, y, -2.39), M["iron"]))
        P.append(lathe("Drop", [(0, -2.44), (0.035, -2.5), (0, -2.64)], 4, M["crystal"], (x, y, 0), smooth=False))
    finish("chandelier", P)


def build_candelabra():
    M = start()
    P = [lathe("Foot", [(0, 0), (0.32, 0), (0.3, 0.05), (0.16, 0.1), (0.09, 0.2), (0, 0.2)], 16, M["iron"]),
         lathe("Stem", [(0, 0.2), (0.035, 0.2), (0.03, 0.6), (0.07, 0.66), (0.03, 0.72), (0.028, 1.15), (0.06, 1.2), (0.03, 1.25), (0.03, 1.5), (0, 1.5)], 10, M["iron"])]
    for k in range(3):  # three claw feet
        a = 2 * math.pi * k / 3
        P.append(C.box("Claw", (0.08, 0.34, 0.06), (0.3 * math.cos(a), 0.3 * math.sin(a), 0.03), M["iron"], (0, 0, math.degrees(a) + 90)))
    tips = [(0, 0, 1.5)]
    for reach, ang in ((0.42, 0), (0.42, 180), (0.26, 90), (0.26, 270)):
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        pts = [Vector((0.02 * c, 0.02 * s, 1.22)), Vector((reach * 0.5 * c, reach * 0.5 * s, 1.16)), Vector((reach * c, reach * s, 1.24)), Vector((reach * c, reach * s, 1.4))]
        P.append(C.tube("Arm", pts, [0.022] * 4, 6, M["iron"]))
        tips.append((reach * c, reach * s, 1.4))
    for i, (x, y, z) in enumerate(tips):
        P.append(lathe("Cup", [(0, z - 0.03), (0.03, z - 0.03), (0.07, z + 0.02), (0, z + 0.02)], 8, M["brass"], (x, y, 0)))
        candle(M, x, y, z + 0.02, [0.24, 0.12, 0.2, 0.08, 0.16][i], i in (0, 2), P)
    finish("candelabra", P)


# ------------------------------------------------------------------ furniture
def build_bookshelf():
    M = start()
    rng = random.Random(41)
    books = [M["book1"], M["book2"], M["book3"], M["book4"], M["book5"]]
    P = [C.box("Plinth", (2.3, 0.55, 0.15), (0, 0, 0.075), M["wood"]),
         C.box("Back", (2.2, 0.03, 3.2), (0, 0.235, 1.6), M["wood_red"]),
         C.box("Cornice", (2.38, 0.6, 0.14), (0, 0, 3.27), M["wood"]),
         extrude("Crest", arch(1.0, 0.02, 6, 0, 3.34, 0.56), -0.02, 0.02, M["wood"], "xz")]
    for sx in (-1, 1):
        P.append(C.box("Side", (0.08, 0.5, 3.2), (sx * 1.06, 0, 1.6), M["wood"]))
        P.append(lathe("Finial", [(0, 3.34), (0.06, 3.34), (0.07, 3.42), (0.02, 3.58), (0, 3.62)], 8, M["wood"], (sx * 1.08, -0.2, 0)))
    for k in range(6):
        P.append(C.box("Shelf", (2.04, 0.46, 0.04), (0, 0, 0.17 + k * 0.6), M["wood"]))
    for k in range(5):
        z0 = 0.19 + k * 0.6
        x = -1.0
        while x < 0.98:
            if rng.random() < 0.08:  # gaps where books were taken, or crumbled
                x += rng.uniform(0.15, 0.4)
                continue
            w, h, d = rng.uniform(0.035, 0.08), rng.uniform(0.28, 0.46), rng.uniform(0.22, 0.32)
            if x + w > 0.99:
                break
            lean = 0.0
            if rng.random() < 0.06 and x < 0.8:
                lean = rng.uniform(12, 22)
            P.append(C.box("Book", (w, d, h), (x + w / 2 + (h / 2) * math.sin(math.radians(lean)), 0.23 - d / 2 - 0.02, z0 + h / 2 * math.cos(math.radians(lean))),
                           rng.choice(books), (0, lean, 0)))
            x += w + (h * math.sin(math.radians(lean)) if lean else 0.004)
    for i in range(3):  # fallen books at the foot
        P.append(C.box("Fallen", (0.24, 0.32, 0.05), (-0.4 + i * 0.35, -0.5, 0.025 + (0.05 if i == 1 else 0)), books[i], (0, 0, rng.uniform(-40, 40))))
    finish("bookshelf", P)


def build_rug_runner():
    M = start()
    P = [C.box("Rug", (2.0, 8.0, 0.012), (0, 0, 0.006), M["velvet"])]
    for inset, wid, mat in ((0.08, 0.06, M["thread"]), (0.2, 0.03, M["thread"])):
        L, W = 8.0 - 2 * inset, 2.0 - 2 * inset
        P += [C.box("Border", (W, wid, 0.004), (0, sy * (L / 2), 0.013), mat) for sy in (-1, 1)]
        P += [C.box("Border", (wid, L, 0.004), (sx * (W / 2), 0, 0.013), mat) for sx in (-1, 1)]
    for k in range(5):
        y = -3.0 + k * 1.5
        P.append(extrude("Medallion", [(0, y - 0.55), (0.45, y), (0, y + 0.55), (-0.45, y)], 0.012, 0.015, M["thread"], "xy"))
        P.append(extrude("MedallionIn", [(0, y - 0.35), (0.28, y), (0, y + 0.35), (-0.28, y)], 0.015, 0.017, M["velvet"], "xy"))
    P.append(extrude("Worn", [(-0.5, 1.2), (0.1, 0.9), (0.6, 1.3), (0.4, 2.0), (-0.2, 2.2), (-0.6, 1.8)], 0.012, 0.0165, M["velvet_lt"], "xy"))
    for sy in (-1, 1):  # fringe, frayed away on one end
        for k in range(24):
            if sy > 0 and 8 <= k <= 15:
                continue
            P.append(C.box("Fringe", (0.02, 0.12, 0.006), (-0.92 + k * 0.08, sy * 4.06, 0.003), M["thread"]))
    finish("rug_runner", P)


def build_broken_chair():
    M = start()
    P = [C.box("Seat", (0.56, 0.52, 0.07), (0, 0, 0.46), M["wood"]),
         C.box("Cushion", (0.5, 0.46, 0.06), (0, -0.01, 0.52), M["velvet"])]
    for sx in (-1, 1):
        for sy in (-1, 1):
            if (sx, sy) == (-1, -1):  # snapped front leg: a jagged stub
                P.append(C.box("Stub", (0.06, 0.06, 0.14), (sx * 0.23, sy * 0.2, 0.36), M["wood"], (0, 8, 0)))
                continue
            P.append(C.box("Leg", (0.06, 0.06, 0.46), (sx * 0.23, sy * 0.2, 0.23), M["wood"]))
        P.append(C.box("Stile", (0.06, 0.06, 1.05), (sx * 0.23, 0.22, 1.02), M["wood"]))
        P.append(lathe("Knob", [(0, 1.545), (0.04, 1.545), (0.045, 1.6), (0, 1.66)], 8, M["wood"], (sx * 0.23, 0.22, 0)))
        P.append(C.box("Stretcher", (0.04, 0.4, 0.04), (sx * 0.23, 0, 0.14), M["wood"]))
    P.append(extrude("BackPanel", arch(0.4, 0.55, 6, 0, 0.58), 0.2, 0.24, M["velvet"], "xz"))
    P.append(arch_frame("BackFrame", 0.4, 0.55, 0.04, 0.19, 0.25, M["wood"], 0, 0.58))
    chair = C.join(P, "Chair")
    # Toppled onto its back.
    C.transform(chair, Matrix.Translation((0, 0.25, 0)) @ Matrix.Rotation(math.radians(-80), 4, "X") @ Matrix.Translation((0, -0.25, 0)))
    minz = min(v.co.z for v in chair.data.vertices)
    C.transform(chair, Matrix.Translation((0, 0, -minz)))
    leg = C.box("LooseLeg", (0.06, 0.06, 0.32), (0.55, -0.55, 0.03), M["wood"], (90, 0, 35))
    shard = C.box("Splinter", (0.03, 0.03, 0.18), (-0.5, -0.3, 0.015), M["wood"], (90, 0, -60))
    finish("broken_chair", [chair, leg, shard], ground=True)


def goblet(M, x, y, z, P, toppled=False):
    g = lathe("Goblet", [(0, 0), (0.04, 0), (0.04, 0.01), (0.008, 0.025), (0.008, 0.1), (0.035, 0.12), (0.042, 0.2), (0, 0.19)], 10, M["brass"])
    if toppled:
        C.transform(g, Matrix.Rotation(math.radians(80), 4, "Y"))
        C.transform(g, Matrix.Translation((0, 0, 0.042)))
    C.transform(g, Matrix.Translation((x, y, z)))
    P.append(g)


def build_table_long():
    M = start()
    P = [C.box("Top", (5.0, 1.2, 0.08), (0, 0, 0.78), M["wood"]),
         C.box("ApronF", (4.8, 0.04, 0.14), (0, -0.52, 0.67), M["wood_red"]),
         C.box("ApronB", (4.8, 0.04, 0.14), (0, 0.52, 0.67), M["wood_red"]),
         C.box("Stretcher", (4.6, 0.08, 0.08), (0, 0, 0.16), M["wood"]),
         C.box("Runner", (5.02, 0.56, 0.006), (0, 0, 0.823), M["velvet"])]
    for sx in (-1, 1):
        P.append(C.box("Drop", (0.006, 0.56, 0.36), (sx * 2.513, 0, 0.64), M["velvet"]))
        P.append(C.box("ApronE", (0.04, 1.08, 0.14), (sx * 2.4, 0, 0.67), M["wood_red"]))
    prof = [(0, 0), (0.07, 0), (0.07, 0.08), (0.05, 0.12), (0.085, 0.3), (0.05, 0.46), (0.045, 0.6), (0.065, 0.66), (0.065, 0.74), (0, 0.74)]
    for x in (-2.3, 0.0, 2.3):
        for sy in (-1, 1):
            P.append(lathe("Leg", prof, 10, M["wood"], (x, sy * 0.48, 0)))
    for x in (-1.6, -0.4, 1.3):
        P.append(lathe("Plate", [(0, 0.82), (0.14, 0.82), (0.16, 0.84), (0, 0.832)], 16, M["stone"], (x, -0.35, 0)))
    goblet(M, -1.3, -0.2, 0.826, P)
    goblet(M, 1.6, -0.25, 0.826, P, toppled=True)
    goblet(M, 0.4, 0.3, 0.826, P)
    P.append(lathe("Stick", [(0, 0.826), (0.08, 0.826), (0.03, 0.86), (0.025, 1.0), (0.05, 1.02), (0, 1.02)], 10, M["brass"], (0, 0, 0)))
    candle(M, 0, 0, 1.02, 0.1, False, P, 0.03)
    finish("table_long", P)


def torn_panel(name, width, top, length, rng, mat, plane, a0, a1, c=0.0):
    pts = [(c - width / 2, top), (c + width / 2, top)]
    bottom = top - length
    for k in range(6, -1, -1):
        pts.append((c - width / 2 + width * k / 6, bottom + rng.uniform(0, 0.4)))
    return extrude(name, pts, a0, a1, mat, plane)


def build_coffin_bed():
    M = start()
    rng = random.Random(51)
    P = [C.box("Dais", (3.8, 4.6, 0.15), (0, 0, 0.075), M["stone_dark"]),
         C.box("Dais2", (3.2, 4.0, 0.15), (0, 0, 0.225), M["stone_dark"]),
         C.box("Carpet", (3.0, 3.8, 0.01), (0, 0, 0.305), M["velvet"])]
    outline = [(0.3, -1.2), (0.5, 0.5), (0.36, 1.2), (-0.36, 1.2), (-0.5, 0.5), (-0.3, -1.2)]
    inner = [(x * 0.84, y * 0.93 + 0.01) for x, y in outline]
    P.append(extrude("CoffinBase", outline, 0.31, 0.62, M["wood"], "xy"))
    P.append(band("CoffinWall", outline, inner, 0.62, 0.95, M["wood"], "xy", True))
    P.append(extrude("Lining", inner, 0.62, 0.68, M["velvet"], "xy"))
    P.append(C.box("Pillow", (0.4, 0.28, 0.1), (0, 0.9, 0.72), M["velvet_lt"]))
    P.append(band("Trim", [(x * 1.02, y * 1.01) for x, y in outline], outline, 0.9, 0.96, M["brass"], "xy", True))
    lid = extrude("Lid", outline, 0.0, 0.08, M["wood"], "xy")
    cross = [C.box("CrossV", (0.08, 1.0, 0.03), (0, 0.1, 0.095), M["brass"]), C.box("CrossH", (0.5, 0.08, 0.03), (0, 0.35, 0.095), M["brass"])]
    lid = C.join([lid] + cross, "Lid")
    C.transform(lid, Matrix.Translation((0.88, -0.1, 0.63)) @ Matrix.Rotation(math.radians(6), 4, "Z") @ Matrix.Rotation(math.radians(40), 4, "Y"))
    P.append(lid)
    # Headboard: a pointed arch of velvet framed in ebony.
    P.append(extrude("Headboard", arch(2.0, 1.2, 8, 0, 0.3), 1.9, 1.96, M["velvet"], "xz"))
    P.append(arch_frame("HeadFrame", 2.0, 1.2, 0.12, 1.88, 1.98, M["wood"], 0, 0.3, 8))
    P += bat_parts(M, 0.35, (0, 1.86, 2.08))
    for sx in (-1, 1):  # four-poster canopy, the curtains rotted to rags
        for sy in (-1, 1):
            P.append(C.box("Post", (0.12, 0.12, 3.1), (sx * 1.45, sy * 1.85, 1.85), M["wood"]))
            P.append(spear("PostFinial", sx * 1.45, sy * 1.85, 3.4, 0.3, 0.07, M["wood"]))
        P.append(C.box("RailSide", (0.1, 3.8, 0.12), (sx * 1.45, 0, 3.34), M["wood"]))
        P.append(torn_panel("CurtainSide", 1.4, 3.3, rng.uniform(1.6, 2.6), rng, M["velvet"], "yz", sx * 1.5, sx * 1.52, c=sx * 0.9))
    for sy in (-1, 1):
        P.append(C.box("RailEnd", (2.9, 0.1, 0.12), (0, sy * 1.85, 3.34), M["wood"]))
    P.append(torn_panel("CurtainHead", 2.7, 3.3, 1.2, rng, M["velvet"], "xz", 1.88, 1.9))
    P.append(torn_panel("CurtainFoot", 0.9, 3.3, 2.7, rng, M["velvet"], "xz", -1.9, -1.88, c=-0.9))
    finish("coffin_bed", P)


def build_rubble_pile():
    M = start()
    rng = random.Random(61)
    P = []
    for _ in range(28):
        r, a = rng.uniform(0, 1.2) ** 1.3, rng.uniform(0, 2 * math.pi)
        s = rng.uniform(0.12, 0.45)
        z = max(0.0, 0.55 * (1 - r / 1.25)) + s * 0.2
        P.append(C.box("Chunk", (s, s * rng.uniform(0.5, 1.0), s * rng.uniform(0.35, 0.7)), (r * math.cos(a), r * math.sin(a), z),
                       rng.choice((M["brick"], M["brick"], M["brick_dark"], M["stone"], M["plaster"])),
                       (rng.uniform(-25, 25), rng.uniform(-25, 25), rng.uniform(0, 180))))
    P.append(lathe("Dust", [(0, 0), (1.3, 0), (0.9, 0.18), (0, 0.4)], 10, M["plaster"]))
    finish("rubble_pile", P, ground=True)


if __name__ == "__main__":
    build_gate_pillar()
    build_gate_iron()
    build_wall_segment(False)
    build_wall_segment(True)
    build_mansion_facade()
    build_rose_bush()
    build_fountain()
    build_bat_statue()
    build_floor_tile()
    build_wall_panel()
    build_wall_window()
    build_doorway()
    build_pillar()
    build_staircase()
    build_grand_clock()
    build_clock_face_wall()
    build_chandelier()
    build_candelabra()
    build_bookshelf()
    build_rug_runner()
    build_broken_chair()
    build_table_long()
    build_coffin_bed()
    build_rubble_pile()
    print("\npiece                   tris   size x*y*z (m)          z range")
    for name, tris, d, (z0, z1) in STATS:
        print(f"{name:22s} {tris:6d}   {d[0]:5.2f} x {d[1]:5.2f} x {d[2]:5.2f}   {z0:6.2f}..{z1:5.2f}")
