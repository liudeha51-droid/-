"""Misty Lake environment kit: modular in-house props for the dark, stylised slice.

Outputs one .glb per prop in assets/models/environment/misty_lake/.
Blender axes: Z up; props are centred on the origin at ground level.
"""
import math
import os
import random
import sys

import bpy  # noqa: I001
import bmesh
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402

OUT = "assets/models/environment/misty_lake"


def mats():
    return {
        "vermilion": C.material("Vermilion", (0.5, 0.06, 0.04), 0.6),
        "black": C.material("Lacquer", (0.03, 0.025, 0.025), 0.35),
        "stone": C.material("Stone", (0.3, 0.29, 0.3), 0.95),
        "moss": C.material("Moss", (0.12, 0.15, 0.1), 1.0),
        "wood": C.material("DarkWood", (0.17, 0.11, 0.08), 0.8),
        "roof": C.material("RoofTile", (0.09, 0.09, 0.1), 0.6),
        "rope": C.material("Rope", (0.6, 0.53, 0.38), 0.9),
        "paper": C.material("Paper", (0.9, 0.88, 0.82), 0.8),
        "flame": C.material("Flame", (1.0, 0.62, 0.3), 0.5, emission=4.0),
        "bark": C.material("Bark", (0.07, 0.06, 0.06), 0.9),
        "needles": C.material("Needles", (0.07, 0.09, 0.09), 1.0),
        "reed": C.material("Reed", (0.26, 0.23, 0.17), 0.9),
        "gold": C.material("Gold", (0.7, 0.55, 0.25), 0.35, 0.8),
    }


def start():
    C.reset_scene()
    return mats()


def finish(name, objs):
    C.export_glb(f"{OUT}/{name}.glb", objs)


def beam(name, start, end, w, h, mat, curve=0.0, segments=12):
    """Rectangular beam, optionally bowed upward at the ends (torii kasagi)."""
    pts, radii = [], []
    for i in range(segments + 1):
        t = i / segments
        p = Vector(start).lerp(Vector(end), t)
        p.z += curve * (2 * t - 1) ** 4
        pts.append(p)
        radii.append(1.0)
    obj = C.tube(name, pts, [w * 0.7071] * len(pts), 4, mat, (1.0, h / w))
    # Rotate the 4-sided tube 45 degrees about its axis so faces are flat.
    return obj


# ------------------------------------------------------------------ torii
def build_torii(broken=False):
    M = start()
    parts = []
    span, height = 2.6, 6.0
    for sx in (-1, 1):
        if broken and sx == 1:
            # Snapped pillar: a stump and a fallen upper half.
            parts.append(C.tube("PillarStump", [Vector((sx * span, 0, 0)), Vector((sx * span, 0, 2.2)), Vector((sx * span + 0.08, 0.02, 2.5))], [0.3, 0.29, 0.22], 16, M["vermilion"]))
            fallen = C.tube("PillarFallen", [Vector((0, 0, 0)), Vector((0, 0, 3.4))], [0.26, 0.24], 16, M["vermilion"])
            C.transform(fallen, Matrix.Translation((sx * span + 0.9, -1.2, 0.26)) @ Matrix.Rotation(math.radians(86), 4, "X") @ Matrix.Rotation(math.radians(20), 4, "Y"))
            parts.append(fallen)
        else:
            top = Vector((sx * (span - 0.12), 0, height))
            parts.append(C.tube("Pillar", [Vector((sx * span, 0, 0)), top], [0.3, 0.26], 16, M["vermilion"]))
        parts.append(C.tube("Base", [Vector((sx * span, 0, 0)), Vector((sx * span, 0, 0.5))], [0.38, 0.36], 16, M["black"]))
    if broken:
        # The lintels hang from the surviving pillar and rest in the mud.
        kasagi = beam("Kasagi", (-3.9, 0, 0.0), (3.9, 0, 0.0), 0.55, 0.45, M["black"], 0.35)
        C.transform(kasagi, Matrix.Translation((-1.2, 0.3, 3.1)) @ Matrix.Rotation(math.radians(-38), 4, "Y"))
        nuki = beam("Nuki", (-3.2, 0, 0), (3.2, 0, 0), 0.3, 0.26, M["vermilion"])
        C.transform(nuki, Matrix.Translation((0.4, -0.6, 0.35)) @ Matrix.Rotation(math.radians(8), 4, "Z"))
        parts += [kasagi, nuki]
    else:
        parts.append(beam("Kasagi", (-3.9, 0, height + 0.35), (3.9, 0, height + 0.35), 0.55, 0.42, M["black"], 0.35))
        parts.append(beam("Shimaki", (-3.5, 0, height), (3.5, 0, height), 0.45, 0.3, M["vermilion"], 0.2))
        parts.append(beam("Nuki", (-3.2, 0, height - 0.95), (3.2, 0, height - 0.95), 0.32, 0.26, M["vermilion"]))
        parts.append(C.box("Gakuzuka", (0.28, 0.24, 0.8), (0, 0, height - 0.5), M["vermilion"]))
        parts.append(C.box("Plaque", (0.7, 0.14, 1.0), (0, -0.14, height - 0.45), M["black"]))
        parts.append(C.box("PlaqueFrame", (0.8, 0.12, 1.1), (0, -0.1, height - 0.45), M["gold"]))
    obj = C.join(parts, "ToriiBroken" if broken else "Torii")
    finish("torii_broken" if broken else "torii", [obj])


# ------------------------------------------------------------------ stone lantern (tōrō)
def build_lantern():
    M = start()
    parts = []
    stack = [  # (radius_bottom, radius_top, z0, z1, sides)
        (0.36, 0.32, 0.0, 0.18, 6),     # kiso (base)
        (0.12, 0.11, 0.18, 0.9, 12),    # sao (post)
        (0.3, 0.26, 0.9, 1.02, 6),      # chūdai
        (0.21, 0.21, 1.02, 1.38, 6),    # hibukuro (fire box)
    ]
    for rb, rt, z0, z1, sides in stack:
        parts.append(C.tube("Stack", [Vector((0, 0, z0)), Vector((0, 0, z1))], [rb, rt], sides, M["stone"]))
    # Kasa (roof) with upturned corners, then hōju (jewel).
    bm = bmesh.new()
    sides = 6
    ring_lo, ring_hi = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        ring_lo.append(bm.verts.new((math.cos(a) * 0.52, math.sin(a) * 0.52, 1.46)))
        ring_hi.append(bm.verts.new((math.cos(a) * 0.12, math.sin(a) * 0.12, 1.7)))
    apex = bm.verts.new((0, 0, 1.72))
    base_c = bm.verts.new((0, 0, 1.38))
    for k in range(sides):
        n = (k + 1) % sides
        bm.faces.new((ring_lo[k], ring_lo[n], ring_hi[n], ring_hi[k]))
        bm.faces.new((ring_hi[k], ring_hi[n], apex))
        bm.faces.new((ring_lo[n], ring_lo[k], base_c))
    for v in ring_lo:
        v.co.z += 0.08  # warabi-te curl at the corners
    parts.append(C.new_object("Kasa", bm, M["stone"], smooth=False))
    parts.append(C.uv_sphere("Hoju", 0.08, (0, 0, 1.8), (1, 1, 1.3), 12, 8, M["stone"]))
    # Window openings are faked with an emissive inner box behind two sides.
    parts.append(C.box("Glow", (0.3, 0.3, 0.26), (0, 0, 1.2), M["flame"]))
    for k in range(3):
        a = math.radians(60 * k)
        parts.append(C.box("Mullion", (0.05, 0.44, 0.3), (0, 0, 1.2), M["stone"], (0, 0, 60 * k + 30)))
    # Moss on the base.
    parts.append(C.tube("MossRing", [Vector((0, 0, 0.15)), Vector((0, 0, 0.2))], [0.34, 0.25], 6, M["moss"]))
    obj = C.join(parts, "StoneLantern")
    finish("stone_lantern", [obj])


# ------------------------------------------------------------------ wayside shrine (hokora)
def build_hokora():
    M = start()
    parts = []
    parts.append(C.box("Plinth", (1.8, 1.4, 0.3), (0, 0, 0.15), M["stone"]))
    parts.append(C.box("Step", (1.0, 0.4, 0.15), (0, -0.85, 0.075), M["stone"]))
    parts.append(C.box("Body", (1.1, 0.85, 0.95), (0, 0.1, 0.78), M["wood"]))
    parts.append(C.box("Doors", (0.7, 0.04, 0.7), (0, -0.34, 0.75), M["black"]))
    # Curved gable roof: two concave slabs sweeping out to upturned eaves.
    for sx in (-1, 1):
        bm = bmesh.new()
        rows = []
        for i in range(9):
            t = i / 8
            x = sx * t * 0.98
            z = 1.95 - t * 0.7 + 0.18 * t ** 3
            rows.append([bm.verts.new((x, y, z)) for y in (-0.8, 1.0)])
        for i in range(8):
            a, b = rows[i]
            c, d = rows[i + 1]
            bm.faces.new((a, b, d, c) if sx > 0 else (a, c, d, b))
        slab = C.new_object("Roof", bm, M["roof"], smooth=True)
        C.solidify(slab, 0.07)
        parts.append(slab)
    parts.append(beam("Ridge", (0, -0.85, 1.98), (0, 1.05, 1.98), 0.16, 0.14, M["roof"]))
    # Gable walls fill the space between the body and the roof.
    parts.append(C.box("Gable", (0.95, 0.8, 0.3), (0, 0.1, 1.38), M["wood"]))
    parts.append(C.box("GableTop", (0.5, 0.8, 0.3), (0, 0.1, 1.64), M["wood"]))
    # Donation box (賽銭箱) and a sacred rope with paper streamers.
    parts.append(C.box("OfferingBox", (0.8, 0.45, 0.45), (0, -0.7, 0.52), M["wood"]))
    for i in range(5):
        parts.append(C.box("Slat", (0.78, 0.05, 0.02), (0, -0.7 - 0.2 + i * 0.1, 0.755), M["black"]))
    rope_pts = [Vector((-0.6 + 1.2 * i / 10, -0.42, 1.28 - 0.08 * math.sin(math.pi * i / 10))) for i in range(11)]
    parts.append(C.tube("Shimenawa", rope_pts, [0.05] * 11, 10, M["rope"]))
    for i in range(3):
        x = -0.35 + i * 0.35
        bm = bmesh.new()
        prev = None
        for j in range(5):
            z = 1.22 - j * 0.06
            ox = 0.02 if j % 2 else -0.02
            a = bm.verts.new((x + ox - 0.03, -0.43, z))
            b = bm.verts.new((x + ox + 0.03, -0.43, z))
            if prev:
                bm.faces.new((prev[0], prev[1], b, a))
            prev = (a, b)
        s = C.new_object("Shide", bm, M["paper"], smooth=False)
        C.solidify(s, 0.004)
        parts.append(s)
    obj = C.join(parts, "Hokora")
    finish("hokora", [obj])


# ------------------------------------------------------------------ the Wayside God (道祖神)
def build_dosojin():
    M = start()
    rng = random.Random(3)
    stone = C.uv_sphere("Stone", 1.0, (0, 0, 0), (0.42, 0.26, 0.62), 32, 16, M["stone"])
    for v in stone.data.vertices:
        v.co.z = max(v.co.z, -0.1)
        v.co += v.co.normalized() * noise.noise(v.co * 4.0) * 0.03
        v.co.z += 0.1
    parts = [stone]
    # Two figures carved in relief: the left is crisp, the right worn almost smooth.
    for sx, depth in ((-1, 0.05), (1, 0.012)):
        head = C.uv_sphere("FigureHead", 0.065, (sx * 0.11, -0.225 - depth, 0.53), (1, 0.5, 1.1), 16, 8, M["stone"])
        body = C.uv_sphere("FigureBody", 0.09, (sx * 0.11, -0.235 - depth * 0.8, 0.33), (1, 0.45, 1.5), 16, 8, M["stone"])
        parts += [head, body]
    # Flame niche and moss at the foot.
    parts.append(C.box("Niche", (0.14, 0.1, 0.1), (0, -0.2, 0.1), M["black"]))
    parts.append(C.uv_sphere("Flame", 0.03, (0, -0.25, 0.1), (1, 1, 1.6), 12, 6, M["flame"]))
    parts.append(C.tube("Moss", [Vector((0, 0, 0)), Vector((0, 0, 0.12))], [0.46, 0.4], 12, M["moss"]))
    # A small red bib (よだれかけ) someone still ties on it.
    bib = C.tube("Bib", [Vector((-0.17, -0.27, 0.45)), Vector((-0.05, -0.27, 0.45))], [0.07, 0.07], 3, C.material("FadedRed", (0.35, 0.06, 0.05), 0.9), (1.0, 0.1))
    parts.append(bib)
    obj = C.join(parts, "Dosojin")
    finish("dosojin", [obj])


# ------------------------------------------------------------------ trees
def branch_graph(rng, height, spread, depth):
    """Random branching skeleton for a dead tree: returns verts, edges, radii."""
    verts, edges, radii = [Vector((0, 0, 0))], [], [0.28]

    def grow(i, direction, length, radius, level):
        steps = 4
        prev = i
        pos = verts[i]
        d = direction.normalized()
        for s in range(steps):
            d = (d + Vector((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), rng.uniform(-0.1, 0.25)))).normalized()
            pos = pos + d * (length / steps)
            radius *= 0.8
            verts.append(pos.copy())
            radii.append(max(radius, 0.015))
            edges.append((prev, len(verts) - 1))
            prev = len(verts) - 1
            if level < depth and s >= 1 and rng.random() < 0.85:
                side = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 0.8)))
                grow(prev, side * spread + d * 0.3, length * 0.55, radius * 0.8, level + 1)

    grow(0, Vector((0, 0, 1)), height, 0.34, 0)
    return verts, edges, radii


def build_dead_tree(seed):
    M = start()
    rng = random.Random(seed)
    verts, edges, radii = branch_graph(rng, rng.uniform(6.0, 9.0), 1.1, 3)
    mesh = bpy.data.meshes.new("DeadTree")
    mesh.from_pydata([tuple(v) for v in verts], edges, [])
    obj = bpy.data.objects.new("DeadTree", mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("Skin", "SKIN")
    for i, r in enumerate(radii):
        obj.data.skin_vertices[0].data[i].radius = (r, r)
    obj.data.skin_vertices[0].data[0].use_root = True
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    C.apply_modifiers(obj)
    obj.data.materials.append(M["bark"])
    # Root flare.
    roots = C.tube("Roots", [Vector((0, 0, -0.1)), Vector((0, 0, 0.6))], [0.55, 0.22], 8, M["bark"])
    obj = C.join([obj, roots], "DeadTree")
    finish(f"tree_dead_{seed}", [obj])


def build_ink_pine(seed):
    M = start()
    rng = random.Random(seed)
    h = rng.uniform(7.0, 11.0)
    parts = [C.tube("Trunk", [Vector((0, 0, 0)), Vector((0.1, 0, h * 0.5)), Vector((0.2, 0.05, h))], [0.3, 0.2, 0.05], 8, M["bark"])]
    tiers = 5
    for i in range(tiers):
        t = i / tiers
        z = h * (0.3 + t * 0.65)
        r = (1.0 - t) * h * 0.26 + 0.4
        bm = bmesh.new()
        seg = 9
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg + rng.uniform(-0.15, 0.15)
            rr = r * rng.uniform(0.75, 1.15)
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z - rng.uniform(0.0, 0.5))))
        tip = bm.verts.new((0.15, 0.03, z + r * 0.9))
        centre = bm.verts.new((0.1, 0, z - 0.2))
        for k in range(seg):
            bm.faces.new((ring[k], ring[(k + 1) % seg], tip))
            bm.faces.new((ring[(k + 1) % seg], ring[k], centre))
        parts.append(C.new_object("Tier", bm, M["needles"], smooth=False))
    obj = C.join(parts, "InkPine")
    finish(f"tree_pine_{seed}", [obj])


# ------------------------------------------------------------------ rocks and reeds
def build_rock(seed):
    M = start()
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    for v in bm.verts:
        n = noise.noise(v.co * 1.6 + off)
        v.co *= 1.0 + n * 0.35
        v.co.z = v.co.z * 0.6 if v.co.z > 0 else v.co.z * 0.3
    obj = C.new_object("Rock", bm, M["stone"], smooth=False)
    moss = [p for p in obj.data.polygons if p.normal.z > 0.75]
    obj.data.materials.append(M["moss"])
    for p in moss:
        p.material_index = 1
    finish(f"rock_{seed}", [obj])


def build_reeds():
    M = start()
    rng = random.Random(11)
    bm = bmesh.new()
    for _ in range(40):
        x, y = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
        h = rng.uniform(0.7, 1.6)
        lean = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
        w = 0.025
        a = bm.verts.new((x - w, y, 0))
        b = bm.verts.new((x + w, y, 0))
        c = bm.verts.new((x + lean.x, y + lean.y, h))
        bm.faces.new((a, b, c))
    obj = C.new_object("Reeds", bm, M["reed"], smooth=False)
    C.solidify(obj, 0.004)
    finish("reeds", [obj])


build_torii(False)
build_torii(True)
build_lantern()
build_hokora()
build_dosojin()
for s in (1, 2, 3):
    build_dead_tree(s)
for s in (1, 2):
    build_ink_pine(s)
for s in (1, 2, 3):
    build_rock(s)
build_reeds()
