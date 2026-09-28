"""The Collector of Names (名集め): in-house stylised model, rig and animations.

Output: assets/models/characters/collector/collector.glb

See docs/STORY_AND_CHARACTERS.md ("4. The Collector of Names"). A tsukumogami: the awakened
spirit of the Hakurei Shrine's worshipper register (参拝帳). She wears a long coat of stitched
register pages, shingled like scales, with ink running down it and soaking the hem. Her face is
a blank page showing the faint brushed name she currently holds (名). A fan of standing pages
rises behind her neck like the fore-edge of a book. She holds the open ledger on her left
forearm, a writing kit (yatate) is tucked in her sash, name-slips hang on red binding thread
and a few loose pages drift around her. The merchant NPC at Muenzuka.

Same conventions as build_reimu.py / build_story_characters.py / build_utsushimi.py:
Blender axes: Z up, she faces -Y, her left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
Adult proportions (the Former Shrine Maiden's skeleton, ~1.7 m). Pose-bone `hips@loc` is
(x, up, forward) in metres.

Extra bones:
  ledger       (child of hand.L, same axes as the hand) the open ledger, rigid.
  ledger_page  (child of ledger) the one sheet that turns: Y rotation flips it over the spine.
  slip         (child of hand.R) the name-slip she hands over; scaled to ~0 except in `offer`.
  drift.1..3   (children of root) loose pages drifting around her.

Actions (30 fps): idle (loop), talk (loop), offer, bow, turn_page.
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

C.reset_scene()
RNG = random.Random(7)

# ---------------------------------------------------------------- materials
M = {
    "skin": C.material("PaperSkin", (0.79, 0.75, 0.67), 0.6),
    "page": C.material("RegisterPage", (0.55, 0.5, 0.39), 0.92),
    "page_old": C.material("RegisterPageOld", (0.42, 0.37, 0.28), 0.92),
    "page_soaked": C.material("InkSoakedPage", (0.07, 0.065, 0.075), 0.8),
    "under": C.material("CoatLining", (0.11, 0.1, 0.11), 0.85),
    "ink": C.material("RunningInk", (0.015, 0.015, 0.022), 0.12),
    "script": C.material("Script", (0.13, 0.11, 0.1), 0.8),
    "faint": C.material("FaintName", (0.2, 0.18, 0.17), 0.8),
    "face": C.material("BlankPage", (0.88, 0.85, 0.76), 0.85, emission=0.12),
    "thread": C.material("RedBindingThread", (0.62, 0.05, 0.05), 0.5, emission=0.12),
    "hair": C.material("InkHair", (0.025, 0.025, 0.035), 0.45),
    "obi": C.material("IndigoSash", (0.08, 0.09, 0.16), 0.75),
    "inner": C.material("InnerCollar", (0.04, 0.04, 0.05), 0.7),
    "cover": C.material("LedgerCover", (0.26, 0.12, 0.07), 0.7),
    "edge": C.material("LedgerEdge", (0.62, 0.57, 0.45), 0.9),
    "lacquer": C.material("BlackLacquer", (0.04, 0.03, 0.03), 0.3),
    "tabi": C.material("Tabi", (0.62, 0.6, 0.56), 0.85),
    "brass": C.material("YatateBrass", (0.45, 0.35, 0.18), 0.45, 0.6),
}

# ---------------------------------------------------------------- skeleton (adult, maiden proportions)
BONES = [
    ("root", (0, 0, 0), (0, 0, 0.15), None),
    ("hips", (0, 0, 0.96), (0, 0, 1.08), "root"),
    ("spine", (0, 0, 1.08), (0, 0, 1.22), "hips"),
    ("chest", (0, 0, 1.22), (0, 0, 1.4), "spine"),
    ("neck", (0, 0, 1.4), (0, 0, 1.48), "chest"),
    ("head", (0, 0, 1.48), (0, 0, 1.7), "neck"),
]
for s, sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"shoulder.{s}", (sx * 0.03, 0, 1.37), (sx * 0.15, 0, 1.37), "chest"),
        (f"upper_arm.{s}", (sx * 0.17, 0, 1.36), (sx * 0.24, 0.0, 1.08), f"shoulder.{s}"),
        (f"forearm.{s}", (sx * 0.24, 0, 1.08), (sx * 0.29, -0.03, 0.84), f"upper_arm.{s}"),
        (f"hand.{s}", (sx * 0.29, -0.03, 0.84), (sx * 0.31, -0.04, 0.75), f"forearm.{s}"),
        (f"thigh.{s}", (sx * 0.095, 0, 0.97), (sx * 0.1, 0, 0.52), "hips"),
        (f"shin.{s}", (sx * 0.1, 0, 0.52), (sx * 0.1, 0.01, 0.09), f"thigh.{s}"),
        (f"foot.{s}", (sx * 0.1, 0.01, 0.09), (sx * 0.1, -0.12, 0.02), f"shin.{s}"),
    ]
DRIFT = {  # loose pages: bone head (the page centre), size, base tilt
    "drift.1": (Vector((-0.34, 0.16, 1.52)), (0.075, 0.11), (18, -30, 25)),
    "drift.2": (Vector((0.36, 0.2, 1.3)), (0.065, 0.1), (-12, 40, -20)),
    "drift.3": (Vector((-0.28, 0.3, 0.98)), (0.07, 0.105), (25, 15, 60)),
}
for name, (c, _, _) in DRIFT.items():
    BONES.append((name, tuple(c), tuple(c + Vector((0, 0, 0.06))), "root"))

arm_data = bpy.data.armatures.new("CollectorRig")
arm = bpy.data.objects.new("CollectorRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
C.activate(arm)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    if name.startswith("shoulder"):
        eb.align_roll(Vector((0, -1, 0)))
    elif name.startswith("foot"):
        eb.align_roll(Vector((0, 0, 1)))
    else:
        eb.align_roll(Vector((0, -1, 0)))
    if parent:
        eb.parent = arm_data.edit_bones[parent]
        eb.use_connect = False
# Prop bones share the hand's axes: ledger / ledger_page on hand.L, slip on hand.R.
hl = arm_data.edit_bones["hand.L"]
HAND_L_MAT = hl.matrix.copy()
LEDGER_LOCAL = Vector((0.035, 0.05, 0.0))  # hand space: +X palm normal, +Y along the fingers, +Z forward
for name, parent, off in (("ledger", "hand.L", LEDGER_LOCAL),):
    eb = arm_data.edit_bones.new(name)
    eb.head = HAND_L_MAT @ off
    eb.tail = HAND_L_MAT @ (off + Vector((0, 0.08, 0)))
    eb.roll = hl.roll
    eb.parent = arm_data.edit_bones[parent]
hr = arm_data.edit_bones["hand.R"]
eb = arm_data.edit_bones.new("slip")
eb.head = hr.head.copy() + (hr.tail - hr.head) * 0.7
eb.tail = eb.head + (hr.tail - hr.head)
eb.roll = hr.roll
eb.parent = hr
bpy.ops.object.mode_set(mode="OBJECT")
arm_data.display_type = "STICK"

BODY_BONES = [b[0] for b in BONES if b[0] != "root" and not b[0].startswith("drift")]


def P(name, t):
    b = arm.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


# ---------------------------------------------------------------- mesh helpers
def loft(name, rings_spec, seg, mat, cap=False):
    """Loft horizontal ellipse rings: [(center, rx, ry)]."""
    bm = bmesh.new()
    rings = []
    for c, rx, ry in rings_spec:
        rings.append([bm.verts.new(Vector(c) + Vector((math.cos(2 * math.pi * k / seg) * rx, math.sin(2 * math.pi * k / seg) * ry, 0))) for k in range(seg)])
    for r in range(len(rings) - 1):
        for k in range(seg):
            bm.faces.new((rings[r][k], rings[r][(k + 1) % seg], rings[r + 1][(k + 1) % seg], rings[r + 1][k]))
    if cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat)


class Sheets:
    """Collects flat quads (strokes, text lines, stitches) into one mesh."""

    def __init__(self):
        self.bm = bmesh.new()

    def quad(self, a, b, c, d):
        vs = [self.bm.verts.new(p) for p in (a, b, c, d)]
        self.bm.faces.new(vs)

    def strip(self, pts, widths, side_of):
        """A ribbon through `pts`; side_of(p, dir) gives the across-direction at each point."""
        n = len(pts)
        left, right = [], []
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            s = side_of(p, d)
            left.append(self.bm.verts.new(p + s * widths[i] / 2))
            right.append(self.bm.verts.new(p - s * widths[i] / 2))
        for i in range(n - 1):
            self.bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))

    def obj(self, name, mat, out=None):
        """out(centre) -> the direction the quads must face (they are single-sided)."""
        if out is not None:
            for f in self.bm.faces:
                f.normal_update()
                if f.normal.dot(out(f.calc_center_median())) < 0:
                    f.normal_flip()
        return C.new_object(name, self.bm, mat, smooth=False)


def RADIAL(c):
    return Vector((c.x, c.y, 0))


def frame_quad(bm, c, t, v, w, h):
    """Quad centred on c spanning t (across, width w) and v (down, height h)."""
    vs = [bm.verts.new(c + t * sx * w / 2 + v * sy * h / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return bm.faces.new(vs)


# ---------------------------------------------------------------- body (skin modifier)
def build_body():
    verts, edges, radii = [], [], []

    def v(co, r):
        verts.append(co)
        radii.append(r)
        return len(verts) - 1

    pelvis = v((0, 0, 0.95), (0.115, 0.085))
    waist = v((0, 0, 1.1), (0.082, 0.066))
    chest = v((0, 0, 1.26), (0.1, 0.078))
    upper = v((0, 0, 1.35), (0.1, 0.07))
    neck_b = v((0, 0, 1.41), (0.038, 0.038))
    neck_t = v((0, 0, 1.5), (0.031, 0.031))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
    for sx in (1.0, -1.0):
        sh = v((sx * 0.16, 0, 1.365), (0.042, 0.042))
        el = v((sx * 0.24, 0, 1.08), (0.029, 0.029))
        wr = v((sx * 0.29, -0.03, 0.845), (0.021, 0.021))
        hip = v((sx * 0.095, 0, 0.93), (0.07, 0.07))
        kn = v((sx * 0.1, 0, 0.52), (0.046, 0.046))
        an = v((sx * 0.1, 0.01, 0.1), (0.028, 0.028))
        toe = v((sx * 0.1, -0.1, 0.035), (0.032, 0.026))
        edges += [(upper, sh), (sh, el), (el, wr), (pelvis, hip), (hip, kn), (kn, an), (an, toe)]

    mesh = bpy.data.meshes.new("Body")
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new("Body", mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    for i, r in enumerate(radii):
        obj.data.skin_vertices[0].data[i].radius = r
    obj.data.skin_vertices[0].data[pelvis].use_root = True
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    C.apply_modifiers(obj)
    for key in ("under", "skin", "tabi"):
        obj.data.materials.append(M[key])
    for poly in obj.data.polygons:
        c = poly.center
        if c.z < 0.16:
            poly.material_index = 2
        elif c.z > 1.405 or (abs(c.x) > 0.2 and c.z < 0.95):
            poly.material_index = 1
        else:
            poly.material_index = 0
        poly.use_smooth = True
    C.weight_by_bones(obj, arm, [b for b in BODY_BONES if b not in ("ledger", "slip")], power=4.0)
    return obj


def build_hands():
    """Slender paper-pale hands: palm plate and tapered fingers (rest: palm faces in)."""
    parts = []
    for s, sx in (("L", 1.0), ("R", -1.0)):
        b = arm.data.bones[f"hand.{s}"]
        down = (b.tail_local - b.head_local).normalized()
        base = P(f"hand.{s}", 0.05)
        palm = C.uv_sphere(f"Palm.{s}", 1.0, (0, 0, 0), (0.011, 0.028, 0.036), 10, 6, M["skin"])
        C.transform(palm, Matrix.Translation(base + down * 0.035) @ Matrix.Rotation(math.atan2(b.tail_local.y - b.head_local.y, -(b.tail_local.z - b.head_local.z)), 4, "X"))
        hp = [palm]
        root = base + down * 0.062
        for dy, ln in ((-0.018, 0.052), (-0.006, 0.06), (0.006, 0.057), (0.017, 0.046)):
            a = root + Vector((0, dy, 0))
            tip = a + down * ln + Vector((sx * 0.004, dy * 0.35, 0))
            mid = a.lerp(tip, 0.5) + Vector((-sx * 0.003, 0, 0))
            hp.append(C.tube("Finger", [a, mid, tip], [0.0075, 0.0065, 0.004], 6, M["skin"]))
        t0 = base + down * 0.03 + Vector((-sx * 0.004, -0.024, 0))
        t2 = t0 + Vector((-sx * 0.006, -0.022, -0.035))
        hp.append(C.tube("Thumb", [t0, t0.lerp(t2, 0.5), t2], [0.0085, 0.007, 0.0045], 6, M["skin"]))
        # A red binding thread wound round the wrist.
        w = P(f"forearm.{s}", 0.96)
        hp.append(C.tube("WristThread", [w + Vector((0, 0, 0.006)), w - Vector((0, 0, 0.006))], [0.024, 0.024], 12, M["thread"]))
        for p in hp:
            C.rigid(p, f"hand.{s}")
        parts += hp
    return parts


# ---------------------------------------------------------------- head: blank page face, ink-black bob
HC = Vector((0, 0, 1.565))
FACE_R = 0.1055


def face_point(u, v, lift=0.0):
    """u, v in [0, 1] on the face page (u = her right -> left, v = chin -> brow)."""
    a = -math.pi / 2 + (u - 0.5) * math.radians(88)
    z = 1.485 + v * 0.16
    # The page follows the jaw's taper toward the chin.
    k = 1.0 - max(0.0, (1.54 - z) / 0.06) * 0.1
    r = (FACE_R + lift) * k
    return Vector((math.cos(a) * r, math.sin(a) * r - (1 - k) * 0.02, z))


def build_head():
    parts = []
    head = C.uv_sphere("Head", 0.098, tuple(HC), (0.9, 0.98, 1.1), 20, 10, M["skin"])
    for v in head.data.vertices:
        dz = v.co.z - HC.z
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.11) * 0.3
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.03
    parts.append(head)

    # The face: a blank register page laid over it, ragged at the chin, one corner curling.
    bm = bmesh.new()
    nu, nv = 9, 7
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            p = face_point(u, v)
            if j == 0:
                p.z += (0.006 if i % 2 else -0.004) * (0.0 if i in (0, nu) else 1.0)
            if j == nv and i == nu:
                p += Vector((0.006, -0.012, 0.006))  # curled corner at her upper left
            row.append(bm.verts.new(p))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    page = C.new_object("FacePage", bm, M["face"])
    C.solidify(page, 0.003)
    parts.append(page)

    # The name she is holding: 名, brushed faintly (夕 over 口).
    sh = Sheets()

    def stroke(pts, w0, w1):
        dense = [pts[0]]
        for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(u1 - u0, v1 - v0) / 0.05))
            dense += [(u0 + (u1 - u0) * i / n, v0 + (v1 - v0) * i / n) for i in range(1, n + 1)]
        fp = [face_point(u, v, 0.0028) for u, v in dense]
        ws = [w0 + (w1 - w0) * i / (len(fp) - 1) for i in range(len(fp))]
        sh.strip(fp, ws, lambda p, d: d.cross(Vector((p.x, p.y, 0)).normalized()).normalized())

    stroke([(0.5, 0.9), (0.42, 0.8), (0.33, 0.72)], 0.009, 0.004)                     # 夕: first sweep
    stroke([(0.44, 0.83), (0.66, 0.83), (0.6, 0.68), (0.45, 0.56), (0.3, 0.49)], 0.008, 0.004)  # hook
    stroke([(0.48, 0.7), (0.56, 0.64)], 0.008, 0.006)                                  # dot
    stroke([(0.4, 0.44), (0.4, 0.12)], 0.008, 0.007)                                   # 口 left
    stroke([(0.4, 0.44), (0.7, 0.44), (0.69, 0.12)], 0.008, 0.007)                     # 口 top / right
    stroke([(0.41, 0.15), (0.68, 0.15)], 0.007, 0.007)                                 # 口 bottom
    parts.append(sh.obj("FaceName", M["faint"], out=lambda c: c - HC))

    # Ink-black bob: cap, straight bangs cut above the page, side curtains to the jaw.
    cap = C.uv_sphere("HairCap", 0.107, (0, 0.008, 1.575), (0.95, 1.0, 1.08), 22, 11, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.03 and v.co.z < 1.63], context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.005)
    parts.append(cap)
    for i in range(8):
        x = -0.077 + i * 0.022
        top = Vector((x * 0.75, -0.075, 1.685))
        bottom = Vector((x * 1.05, -0.112 + abs(x) * 0.22, 1.638 + abs(x) * 0.18))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.012, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.017, 0.015, 0.012], 6, M["hair"], (1.0, 0.45)))
    for sx in (1.0, -1.0):
        pts = [Vector((sx * 0.094, -0.03, 1.66)), Vector((sx * 0.108, -0.05, 1.56)), Vector((sx * 0.106, -0.058, 1.47)), Vector((sx * 0.104, -0.058, 1.445))]
        parts.append(C.tube("SideCurtain", pts, [0.03, 0.036, 0.036, 0.034], 8, M["hair"], (0.45, 1.0), twist_up=Vector((0, -1, 0))))
    back = [Vector((0, 0.03, 1.66)), Vector((0, 0.075, 1.56)), Vector((0, 0.085, 1.47)), Vector((0, 0.085, 1.44))]
    parts.append(C.tube("BackBob", back, [0.105, 0.12, 0.118, 0.114], 16, M["hair"], (1.0, 0.55), twist_up=Vector((0, -1, 0))))
    # Ink dripping from the cut ends of the hair.
    for x, ln in ((-0.06, 0.05), (0.02, 0.08), (0.075, 0.035), (-0.1, 0.03)):
        y = 0.13 if abs(x) < 0.09 else 0.02
        a = Vector((x, y if abs(x) < 0.09 else 0.02, 1.445))
        if abs(x) >= 0.09:
            a = Vector((x, -0.05, 1.445))
        parts.append(C.tube("HairDrip", [a, a + Vector((0, 0, -ln * 0.7)), a + Vector((0, 0, -ln))], [0.006, 0.004, 0.001], 6, M["ink"]))
        parts.append(C.uv_sphere("HairDripBead", 0.0055, tuple(a + Vector((0, 0, -ln * 0.88))), (1, 1, 1.4), 6, 4, M["ink"]))
    # A red binding thread tied round the head like a book cord, the knot at the back.
    ring = []
    for k in range(17):
        ang = -math.pi / 2 + 2 * math.pi * k / 16
        ring.append(Vector((math.cos(ang) * 0.1125, 0.008 + math.sin(ang) * 0.117, 1.655 - 0.012 * math.sin(ang))))
    parts.append(C.tube("HeadThread", ring, [0.0045] * len(ring), 6, M["thread"], cap=False))
    knot = Vector((0.0, 0.128, 1.643))
    parts.append(C.uv_sphere("HeadKnot", 0.012, tuple(knot), (1.3, 0.8, 1.0), 8, 5, M["thread"]))
    for sx, ln in ((1.0, 0.16), (-1.0, 0.22)):
        pts = [knot, knot + Vector((sx * 0.02, 0.02, -ln * 0.5)), knot + Vector((sx * 0.03, 0.03, -ln))]
        parts.append(C.tube("HeadThreadTail", pts, [0.004, 0.0035, 0.003], 5, M["thread"]))
    for p in parts:
        C.rigid(p, "head")
    return parts


# ---------------------------------------------------------------- the coat of pages
COAT_RINGS = [  # (z, rx, ry) for the coat's base shell, neck to hem
    (1.455, 0.058, 0.055), (1.425, 0.13, 0.08), (1.39, 0.185, 0.098), (1.34, 0.165, 0.103), (1.26, 0.145, 0.105),
    (1.17, 0.135, 0.103), (1.1, 0.14, 0.108), (1.02, 0.172, 0.135), (0.9, 0.2, 0.155), (0.7, 0.222, 0.172),
    (0.5, 0.238, 0.183), (0.3, 0.252, 0.193), (0.12, 0.266, 0.203), (0.08, 0.268, 0.205),
]


def coat_r(z):
    rs = COAT_RINGS
    if z >= rs[0][0]:
        return rs[0][1], rs[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(rs, rs[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return rs[-1][1], rs[-1][2]


def surf(a, z):
    rx, ry = coat_r(z)
    return Vector((math.cos(a) * rx, math.sin(a) * ry, z))


def surf_normal(a, z):
    rx, ry = coat_r(z)
    return Vector((math.cos(a) / rx, math.sin(a) / ry, 0)).normalized()


def build_coat():
    parts = []
    base = loft("CoatShell", [((0, 0, z), rx, ry) for z, rx, ry in COAT_RINGS], 36, M["page"])
    C.solidify(base, 0.006)
    # Dark lining visible under the hem.
    base.data.materials.append(M["under"])
    for poly in base.data.polygons:
        if poly.center.z < 0.13:
            poly.material_index = 1
    parts.append(base)

    tiles_bm = {"page": bmesh.new(), "page_old": bmesh.new(), "page_soaked": bmesh.new()}
    text = Sheets()
    ink = Sheets()
    stitch = Sheets()
    rows = []  # per row: list of (angle centre, half-angle, frame)

    def tile_frame(ac, zt, zb):
        top, bot = surf(ac, zt), surf(ac, zb)
        n_t, n_b = surf_normal(ac, zt), surf_normal(ac, zb)
        top += n_t * 0.003
        bot += n_b * 0.014
        v = (bot - top).normalized()
        t = Vector((0, 0, 1)).cross(n_t).normalized()  # across, towards increasing angle
        n = v.cross(t).normalized()
        if n.dot(n_t) < 0:
            n = -n
        return (top + bot) / 2, t, v, n, (bot - top).length

    def add_rows(z_top, z_bot, count, per_row, h_extra, stagger=True, soak_rows=0, text_ok=True):
        spacing = (z_top - z_bot) / count
        for r in range(count):
            zt = z_top - r * spacing
            zb = zt - spacing - h_extra
            if r == count - 1:
                zb = z_bot - 0.005
            row = []
            off = (0.5 if (r % 2 and stagger) else 0.0) * 2 * math.pi / per_row
            for k in range(per_row):
                ac = off + 2 * math.pi * k / per_row + RNG.uniform(-0.03, 0.03)
                ha = math.pi / per_row * 1.12
                zb_k = zb - (RNG.uniform(0.0, 0.035) if r == count - 1 else RNG.uniform(-0.008, 0.008))
                c, t, v, n, h = tile_frame(ac, zt + RNG.uniform(-0.006, 0.006), zb_k)
                rx, ry = coat_r((zt + zb_k) / 2)
                w = 2 * ha * (rx + ry) / 2
                # slight in-plane rotation
                rot = Matrix.Rotation(RNG.uniform(-0.05, 0.05), 3, n)
                t2, v2 = rot @ t, rot @ v
                key = "page_soaked" if r >= count - soak_rows and RNG.random() < (0.9 if r == count - 1 else 0.45) else ("page_old" if RNG.random() < 0.35 else "page")
                frame_quad(tiles_bm[key], c, t2, v2, w, h)
                row.append((ac, ha, c, t2, v2, n, w, h, key))
                # Written columns (top to bottom, right to left), a few struck out.
                if text_ok and key != "page_soaked":
                    lift = n * 0.0028
                    ncols = RNG.randint(2, 4)
                    for ci in range(ncols):
                        u = (0.3 - ci * 0.2) * w
                        v0 = 0.25 * h
                        v1 = v0 + RNG.uniform(0.3, 0.62) * h
                        cc = c + lift + t2 * u - v2 * h / 2
                        text.quad(cc + v2 * v0 - t2 * 0.002, cc + v2 * v0 + t2 * 0.002, cc + v2 * v1 + t2 * 0.002, cc + v2 * v1 - t2 * 0.002)
                    if RNG.random() < 0.2:
                        vv = RNG.uniform(0.4, 0.7) * h
                        cc = c + lift * 1.3 - v2 * h / 2 + v2 * vv
                        text.quad(cc - t2 * w * 0.42 - v2 * 0.003, cc + t2 * w * 0.42 - v2 * 0.0015, cc + t2 * w * 0.42 + v2 * 0.0015, cc - t2 * w * 0.42 + v2 * 0.003)
                # Red cross-stitches binding each page to its neighbour.
                if k % 3 == r % 3:
                    for vv in (0.6,):
                        cc = c + n * 0.0032 - v2 * h / 2 + v2 * vv * h + t2 * w * 0.47
                        for dd in (1, -1):
                            a0 = cc - t2 * 0.012 - v2 * 0.01 * dd
                            b0 = cc + t2 * 0.012 + v2 * 0.01 * dd
                            dirv = (b0 - a0).normalized()
                            side = n.cross(dirv).normalized() * 0.0016
                            stitch.quad(a0 - side, a0 + side, b0 + side, b0 - side)
            rows.append(row)
        return rows[-count:]

    skirt = add_rows(1.04, 0.075, 7, 15, 0.035, soak_rows=2)
    torso = add_rows(1.36, 1.17, 2, 13, 0.03)

    # Ink running down from the collar: streaks over the torso tiles and on down the skirt,
    # ending in drip beads; the hem rows are soaked through.
    def ink_on_rows(rows_, a, width, stop_row, stop_v, seed):
        rr = random.Random(seed)
        for ri, row in enumerate(rows_):
            if ri > stop_row:
                break
            best = min(row, key=lambda tl: abs(math.atan2(math.sin(a - tl[0]), math.cos(a - tl[0]))))
            ac, ha, c, t, v, n, w, h, key = best
            da = math.atan2(math.sin(a - ac), math.cos(a - ac))
            u = da / ha * w / 2 * 0.9
            v_end = h if ri < stop_row else stop_v * h
            pts, ws = [], []
            steps = 5
            for i in range(steps + 1):
                vv = v_end * i / steps
                uu = u + math.sin(vv * 40 + seed) * 0.004
                pts.append(c + n * 0.0035 + t * uu - v * h / 2 + v * vv)
                ws.append(width * (1.0 - 0.45 * i / steps if ri == stop_row else 1.0) * rr.uniform(0.85, 1.1))
            ink.strip(pts, ws, lambda p, d, n=n: n.cross(d).normalized())
            if ri == stop_row:
                bead = pts[-1] + v * 0.008
                b = C.uv_sphere("InkBead", 1.0, (0, 0, 0), (width * 0.55, width * 0.3, width * 0.85), 6, 4, M["ink"])
                C.transform(b, Matrix.Translation(bead + n * 0.002))
                parts.append(b)

    streaks = [(-math.pi / 2 + 0.35, 0.016, 1, 0.8, 4, 0.6), (-math.pi / 2 - 0.5, 0.011, 1, 0.9, 2, 0.4), (-math.pi / 2 - 0.12, 0.009, 1, 0.5, -1, 0),
               (0.2, 0.014, 1, 0.7, 3, 0.8), (math.pi / 2 + 0.3, 0.018, 1, 0.9, 5, 0.5), (math.pi / 2 - 0.45, 0.012, 1, 0.6, 3, 0.9),
               (math.pi - 0.3, 0.013, 1, 0.8, 4, 0.7), (math.pi / 2 + 1.0, 0.01, 0, 0.7, -1, 0)]
    for i, (a, wdt, t_stop, t_v, s_stop, s_v) in enumerate(streaks):
        ink_on_rows(torso, a, wdt, t_stop, t_v if s_stop < 0 else 1.0, i)
        if s_stop >= 0:
            ink_on_rows(skirt, a, wdt, s_stop, s_v, i + 20)

    for key, bm in tiles_bm.items():
        o = C.new_object("CoatPages", bm, M[key], smooth=False)
        C.solidify(o, 0.003)
        parts.append(o)
    parts.append(text.obj("CoatScript", M["script"], out=RADIAL))
    parts.append(ink.obj("CoatInk", M["ink"], out=RADIAL))
    parts.append(stitch.obj("CoatStitch", M["thread"], out=RADIAL))

    # Crossed front collar: black inner collar, paper outer collar with a red stitched edge.
    for sx, zb, mat, r, dy in ((-1.0, 1.1, "inner", 0.013, 0.0), (1.0, 1.13, "inner", 0.013, 0.0), (-1.0, 1.1, "page", 0.017, -0.008), (1.0, 1.13, "page", 0.017, -0.008)):
        k = 1.25 if mat == "page" else 1.0
        pts = [Vector((-sx * 0.05 * k, 0.045, 1.465)), Vector((-sx * 0.072 * k, -0.02, 1.425)), Vector((-sx * 0.055 * k, -0.08 + dy, 1.36)),
               Vector((-sx * 0.012 * k, -0.105 + dy, 1.26)), Vector((sx * 0.04, -0.112 + dy, zb))]
        if mat == "page":
            pts = [p + Vector((-sx * 0.012, 0, 0)) for p in pts]
        parts.append(C.tube("Collar", pts, [r] * 5, 8, M[mat], (1.0, 0.35)))

    # Fan of standing pages behind the neck, like a book's fore-edge fanned open.
    fan_bm = bmesh.new()
    fan_text = Sheets()
    count = 9
    for k in range(count):
        a = math.radians(12 + 156 * k / (count - 1))
        base_c = Vector((math.cos(a) * 0.1, 0.012 + math.sin(a) * 0.088, 1.4))
        out = Vector((math.cos(a), math.sin(a), 0))
        lean = math.radians(34 - 8 * abs(k - (count - 1) / 2) / 4)
        up = (Vector((0, 0, 1)) * math.cos(lean) + out * math.sin(lean)).normalized()
        across = Vector((0, 0, 1)).cross(out).normalized()
        hgt = 0.16 + 0.03 * math.cos(math.pi * (k - (count - 1) / 2) / (count - 1)) + RNG.uniform(-0.01, 0.01)
        c = base_c + up * hgt / 2 + out * 0.003 * (k % 2)
        frame_quad(fan_bm, c, across, -up, 0.078, hgt)
        n = up.cross(across).normalized()
        if n.dot(out) < 0:
            n = -n
        for ci in range(2):
            u = (0.012 - ci * 0.022)
            c0 = c + n * 0.0026 + across * u + up * (hgt / 2 - 0.02)
            ln = RNG.uniform(0.06, 0.1)
            fan_text.quad(c0 - across * 0.002, c0 + across * 0.002, c0 - up * ln + across * 0.002, c0 - up * ln - across * 0.002)
    fan = C.new_object("CollarFan", fan_bm, M["page"], smooth=False)
    C.solidify(fan, 0.004)
    fan.data.materials.append(M["page_old"])
    for i, poly in enumerate(fan.data.polygons):
        poly.material_index = 1 if (i // 6) % 2 else 0
    parts.append(fan)
    parts.append(fan_text.obj("FanScript", M["script"], out=lambda c: Vector((c.x, c.y - 0.012, 0))))
    # A red thread lacing the fan's base.
    lace = [Vector((math.cos(math.radians(a)) * 0.103, 0.012 + math.sin(math.radians(a)) * 0.091, 1.415)) for a in range(8, 175, 12)]
    parts.append(C.tube("FanThread", lace, [0.0045] * len(lace), 6, M["thread"], cap=False))

    for p in parts:
        if p.name.startswith(("CollarFan", "FanScript", "FanThread", "Collar")):
            C.weight_by_bones(p, arm, ["neck", "chest"], power=4.0)
        else:
            C.weight_by_bones(p, arm, ["neck", "chest", "spine", "hips", "thigh.L", "thigh.R", "shin.L", "shin.R", "upper_arm.L", "upper_arm.R"], power=4.0, keep=3)
    return parts


def build_sash():
    parts = []
    obi = loft("Sash", [((0, 0, 1.175), 0.142, 0.113), ((0, 0, 1.03), 0.18, 0.14)], 32, M["obi"])
    C.solidify(obi, 0.008)
    parts.append(obi)
    cord = loft("SashCord", [((0, 0, 1.108), 0.166, 0.13), ((0, 0, 1.094), 0.168, 0.132)], 24, M["thread"])
    C.solidify(cord, 0.008)
    parts.append(cord)
    knot = Vector((0.02, -0.14, 1.1))
    parts.append(C.uv_sphere("SashKnot", 0.017, tuple(knot), (1.3, 0.7, 1.0), 8, 6, M["thread"]))
    # Name-slips (tanzaku) hanging from the sash cord on red thread, written and struck out.
    slips = Sheets()
    text = Sheets()
    for dx, ln, ang in ((0.0, 0.06, 4), (0.05, 0.1, -6), (-0.06, 0.04, 8)):
        a = knot + Vector((dx * 0.4, -0.004, -0.01))
        b = Vector((knot.x + dx, knot.y - 0.012 - abs(dx) * 0.15, knot.z - ln))
        parts.append(C.tube("SlipThread", [a, a.lerp(b, 0.5) + Vector((0, -0.004, 0)), b], [0.003, 0.003, 0.003], 5, M["thread"]))
        t = Vector((math.cos(math.radians(ang)), 0, math.sin(math.radians(ang))))
        v = Vector((-math.sin(math.radians(ang)), 0.08, -math.cos(math.radians(ang)))).normalized()
        c = b + v * 0.06
        bm = slips.bm
        frame_quad(bm, c, t, v, 0.03, 0.12)
        n = Vector((0, -1, 0))
        text.quad(c + n * 0.003 - t * 0.002 - v * 0.04, c + n * 0.003 + t * 0.002 - v * 0.04, c + n * 0.003 + t * 0.002 + v * 0.035, c + n * 0.003 - t * 0.002 + v * 0.035)
    so = slips.obj("SashSlips", M["page"])
    C.solidify(so, 0.003)
    parts += [so, text.obj("SlipScript", M["script"], out=lambda c: Vector((0, -1, 0)))]
    # Yatate (portable brush case with ink pot) tucked into the sash at her right hip.
    y0 = Vector((-0.12, -0.11, 1.16))
    y1 = y0 + Vector((-0.06, 0.02, -0.17))
    parts.append(C.tube("YatateCase", [y0, y1], [0.011, 0.011], 8, M["lacquer"]))
    parts.append(C.uv_sphere("YatatePot", 0.022, tuple(y0 + Vector((0.004, -0.004, 0.015))), (1, 0.8, 0.9), 10, 6, M["brass"]))
    parts.append(C.tube("YatateBrush", [y1, y1 + (y1 - y0).normalized() * 0.03], [0.009, 0.001], 6, M["ink"]))
    for p in parts:
        C.weight_by_bones(p, arm, ["hips", "spine"], power=4.0)
    return parts


def build_sleeves():
    parts = []
    for s, sx in (("L", 1.0), ("R", -1.0)):
        p0 = P(f"upper_arm.{s}", 0.05)
        p1 = P(f"forearm.{s}", 0.0)
        p2 = P(f"forearm.{s}", 1.0)
        d = (p2 - p1).normalized()
        pts = [p0, p0.lerp(p1, 0.5), p1, p1.lerp(p2, 0.5), p2 - d * 0.02]
        radii = [0.065, 0.09, 0.115, 0.135, 0.145]
        sleeve = C.tube(f"Sleeve.{s}", pts, radii, 14, M["page"], (0.42, 1.0), cap=False, twist_up=Vector((0, -1, 0)))

        def sag(obj, amount=0.1):
            for v in obj.data.vertices:
                t = max(0.0, (p0.z - v.co.z) / (p0.z - p2.z))
                if v.co.y > 0.0:
                    v.co.z -= amount * t * (v.co.y / 0.145)

        sag(sleeve)
        C.solidify(sleeve, 0.006)
        sleeve.data.materials.append(M["under"])
        C.weight_by_bones(sleeve, arm, [f"upper_arm.{s}", f"forearm.{s}", "chest"], power=4.0)
        parts.append(sleeve)
        # Red stitched seams at the shoulder and the cuff, and an ink-soaked cuff band.
        for t0, r, mat in ((0.0, 0.066, "thread"), (1.0, 0.1465, "page_soaked")):
            q = pts[0] if t0 == 0.0 else p2 - d * 0.03
            q2 = q + (pts[1] - pts[0]).normalized() * 0.008 if t0 == 0.0 else p2 - d * 0.012
            band = C.tube("SleeveBand", [q, q2], [r, r], 14, M[mat], (0.43, 1.02), cap=False, twist_up=Vector((0, -1, 0)))
            if t0 == 1.0:
                sag(band)
            C.solidify(band, 0.008)
            C.weight_by_bones(band, arm, [f"upper_arm.{s}", f"forearm.{s}", "chest"], power=4.0)
            parts.append(band)
        # Loose pages hanging by red thread from the low corner of the sleeve bag.
        low = min((v.co for v in sleeve.data.vertices), key=lambda co: co.z).copy()
        hang = []
        for j, (dx, ln) in enumerate(((0.0, 0.05), (sx * 0.025, 0.09))):
            a = low + Vector((dx * 0.3, 0, 0.01))
            b = low + Vector((dx, 0.005 * j, -ln))
            hang.append(C.tube("CuffThread", [a, b], [0.003, 0.003], 5, M["thread"]))
            bm = bmesh.new()
            frame_quad(bm, b + Vector((0, 0, -0.045)), Vector((1, 0, 0)) * 1.0, Vector((0, 0, -1)), 0.035, 0.09)
            sl = C.new_object("CuffPage", bm, M["page_old"], smooth=False)
            C.transform(sl, Matrix.Translation(b) @ Matrix.Rotation(math.radians(80 + 10 * j), 4, "Z") @ Matrix.Translation(-b))
            C.solidify(sl, 0.003)
            hang.append(sl)
        for h in hang:
            C.rigid(h, f"forearm.{s}")
        parts += hang
    return parts


def build_feet():
    parts = []
    for s, sx in (("L", 1.0), ("R", -1.0)):
        sole = C.box(f"Geta.{s}", (0.085, 0.22, 0.02), (sx * 0.1, -0.05, 0.03), M["lacquer"])
        teeth = [C.box("GetaTooth", (0.08, 0.02, 0.022), (sx * 0.1, -0.05 + dy, 0.011), M["lacquer"]) for dy in (-0.06, 0.06)]
        strap = C.tube("Hanao", [Vector((sx * 0.06, -0.02, 0.04)), Vector((sx * 0.1, -0.11, 0.075)), Vector((sx * 0.14, -0.02, 0.04))], [0.008, 0.009, 0.008], 6, M["thread"])
        for p in [sole, strap] + teeth:
            C.rigid(p, f"foot.{s}")
        parts += [sole, strap] + teeth
    return parts


# ---------------------------------------------------------------- props on their own bones
def hand_space(bone):
    return arm.data.bones[bone].matrix_local


def build_ledger():
    """The open ledger in ledger-bone space: +X up out of the palm, +Y along the spine, Z across."""
    parts = []
    L = 0.3        # along the spine
    W = 0.2        # each half's width across
    T = 0.03       # page block thickness per half
    CV = 0.006     # cover thickness
    spine_y0 = -0.12
    sh = Sheets()
    for side in (1.0, -1.0):
        cov = C.box("LedgerCover", (CV, L + 0.012, W + 0.008), (0, spine_y0 + L / 2, side * (W / 2 + 0.002)), M["cover"])
        block = C.box("LedgerBlock", (T, L, W), (CV / 2 + T / 2, spine_y0 + L / 2, side * (W / 2 + 0.004)), M["edge"])
        parts += [cov, block]
        # Written columns on the open spread (running along the spine), a few struck out.
        top = CV / 2 + T + 0.0012
        for ci in range(7):
            z = side * (0.022 + ci * 0.024)
            y0 = spine_y0 + 0.03
            y1 = y0 + RNG.uniform(0.12, L - 0.07)
            sh.quad(Vector((top, y0, z - 0.0025)), Vector((top, y0, z + 0.0025)), Vector((top, y1, z + 0.0025)), Vector((top, y1, z - 0.0025)))
    parts.append(sh.obj("LedgerScript", M["script"], out=lambda c: Vector((1, 0, 0))))
    strike = Sheets()
    top = CV / 2 + T + 0.0018
    for z, y in ((0.07, 0.0), (-0.12, 0.05)):
        strike.quad(Vector((top, spine_y0 + 0.1 + y, z - 0.012)), Vector((top, spine_y0 + 0.1 + y, z + 0.012)), Vector((top, spine_y0 + 0.104 + y, z + 0.012)), Vector((top, spine_y0 + 0.104 + y, z - 0.012)))
    parts.append(strike.obj("LedgerStrike", M["thread"], out=lambda c: Vector((1, 0, 0))))
    # Red binding thread: four stitches over the spine, a bookmark cord hanging from its end.
    for k in range(4):
        y = spine_y0 + 0.04 + k * (L - 0.08) / 3
        parts.append(C.tube("SpineStitch", [Vector((-CV, y, -0.012)), Vector((-CV, y, 0.012))], [0.003, 0.003], 5, M["thread"]))
    parts.append(C.tube("SpineCord", [Vector((-CV, spine_y0 + 0.02, 0)), Vector((-CV, spine_y0 + L - 0.02, 0))], [0.0028, 0.0028], 5, M["thread"]))
    e = Vector((-0.004, spine_y0 + L, 0.0))
    for dz, ln in ((0.006, 0.14), (-0.006, 0.1)):
        b = e + Vector((-ln, 0.02, dz * 3))
        parts.append(C.tube("Bookmark", [e, e.lerp(b, 0.5) + Vector((0, 0.02, 0)), b], [0.0028, 0.0028, 0.0028], 5, M["thread"]))
    # Title slip on the underside of the cover.
    parts.append(C.box("TitleSlip", (0.002, 0.16, 0.035), (-CV / 2 - 0.001, spine_y0 + L / 2, 0.14), M["page"]))
    # The sheet that turns (her left half), pivoting on the spine at page height.
    pivot_x = CV / 2 + T + 0.0022
    return parts, (L, W, spine_y0, pivot_x)


def build_turning_page(dims):
    L, W, spine_y0, pivot_x = dims
    parts = []
    sheet = C.box("LedgerPage", (0.0012, L - 0.01, W - 0.006), (pivot_x, spine_y0 + L / 2, W / 2 + 0.004), M["edge"])
    parts.append(sheet)
    sh = Sheets()
    for side in (1.0, -1.0):
        x = pivot_x + side * 0.0009
        for ci in range(5):
            z = 0.03 + ci * 0.03
            y0 = spine_y0 + 0.04
            y1 = y0 + RNG.uniform(0.1, L - 0.08)
            sh.quad(Vector((x, y0, z - 0.0025)), Vector((x, y0, z + 0.0025)), Vector((x, y1, z + 0.0025)), Vector((x, y1, z - 0.0025)))
    parts.append(sh.obj("PageScript", M["script"], out=lambda c: Vector((c.x - pivot_x, 0, 0))))
    return parts


def build_slip():
    """The name-slip she offers, in slip-bone space (+Y along the fingers, -X out of the palm).
    It stands up out of the upturned palm, its face toward whoever she is dealing with."""
    parts = [C.box("OfferSlip", (0.18, 0.002, 0.052), (-0.075, 0.03, 0.0), M["face"])]
    for y in (0.0285, 0.0315):
        parts.append(C.box("OfferSlipName", (0.1, 0.0012, 0.008), (-0.085, y, 0.0), M["script"]))
        parts.append(C.box("OfferSlipSeal", (0.02, 0.0012, 0.02), (-0.145, y, 0.0), M["thread"]))
    parts.append(C.box("OfferSlipThread", (0.004, 0.0024, 0.054), (-0.02, 0.03, 0.0), M["thread"]))
    return parts


def build_drift_pages():
    parts = []
    for name, (c, (w, h), rot) in DRIFT.items():
        pg = [C.box("DriftPage", (w, 0.002, h), (0, 0, 0), M["page_old"])]
        sh = Sheets()
        for ci in range(3):
            x = w * (0.28 - ci * 0.28)
            ln = RNG.uniform(0.4, 0.7) * h
            for yy in (-0.0014, 0.0014):
                sh.quad(Vector((x - 0.002, yy, h * 0.38)), Vector((x + 0.002, yy, h * 0.38)), Vector((x + 0.002, yy, h * 0.38 - ln)), Vector((x - 0.002, yy, h * 0.38 - ln)))
        pg.append(sh.obj("DriftScript", M["script"], out=lambda c: Vector((0, c.y, 0))))
        # A frayed tail of red thread: the page tore loose from its binding.
        pg.append(C.tube("DriftThread", [Vector((-w * 0.4, 0, h * 0.45)), Vector((-w * 0.6, 0.01, h * 0.62)), Vector((-w * 0.5, 0.02, h * 0.8))], [0.0025, 0.0025, 0.002], 5, M["thread"]))
        for p in pg:
            C.transform(p, Matrix.Translation(c) @ C.euler_matrix(rot))
            C.rigid(p, name)
        parts += pg
    return parts


# ---------------------------------------------------------------- assemble
body = build_body()
hands = build_hands()
head_parts = build_head()
coat = build_coat()
sash = build_sash()
sleeves = build_sleeves()
feet = build_feet()
drift = build_drift_pages()

# Ledger: modelled in hand.L space, then parked on its bones in bind pose.
ledger_parts, LEDGER_DIMS = build_ledger()
page_parts = build_turning_page(LEDGER_DIMS)
slip_parts = build_slip()
LM = arm.data.bones["ledger"].matrix_local.copy()
for p in ledger_parts:
    C.transform(p, LM)
    C.rigid(p, "ledger")

# The turning page gets its own bone, pivoting on the spine line (bone +Y along the spine).
C.activate(arm)
bpy.ops.object.mode_set(mode="EDIT")
led = arm_data.edit_bones["ledger"]
L, W, SPINE_Y0, PIVOT_X = LEDGER_DIMS
eb = arm_data.edit_bones.new("ledger_page")
eb.head = LM @ Vector((PIVOT_X, SPINE_Y0, 0))
eb.tail = LM @ Vector((PIVOT_X, SPINE_Y0 + L, 0))
eb.roll = led.roll
eb.align_roll(LM.to_3x3() @ Vector((0, 0, 1)))
eb.parent = led
bpy.ops.object.mode_set(mode="OBJECT")
for p in page_parts:
    # Lay the sheet on the half that is her left once posed (decided below), local +Z side.
    C.transform(p, LM @ Matrix.Translation((0, 0, 0)))
    C.rigid(p, "ledger_page")
SM = arm.data.bones["slip"].matrix_local.copy()
for p in slip_parts:
    C.transform(p, SM)
    C.rigid(p, "slip")

collector = C.join([body] + hands + head_parts + coat + sash + sleeves + feet + ledger_parts, "Collector")
page = C.join(page_parts, "LedgerPage")
slip = C.join(slip_parts, "OfferSlip")
drift_obj = C.join(drift, "DriftPages")
meshes = [collector, page, slip, drift_obj]
for o in meshes:
    mod = o.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    o.parent = arm

# ---------------------------------------------------------------- animation
arm.animation_data_create()
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"

DRIFT_KEYS = {  # bob amplitude (m), sway (deg), phase
    "drift.1": (0.03, 12, 0.0), "drift.2": (0.025, 16, 2.1), "drift.3": (0.035, 10, 4.2),
}


def action(name, frames, keys, cycles=1):
    """keys: {frame: {bone: (rx, ry, rz) deg, 'bone@loc': (x, y, z), 'bone@scale': s}}.
    Drifting pages and the hidden slip / page are keyed in every action."""
    keys = {f: dict(p) for f, p in keys.items()}
    step = 5
    for f in range(0, frames + 1, step):
        keys.setdefault(f, None)
    # Fill the in-between drift frames with the pose interpolated by Blender (only drift keys).
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    body_frames = sorted(f for f, p in keys.items() if p is not None)
    used = set()
    for f in body_frames:
        used.update(keys[f].keys())
    used.update({"ledger_page", "slip@scale"})
    for f in body_frames:
        pose = keys[f]
        for bone in used:
            pb = arm.pose.bones[bone.split("@")[0]]
            if bone.endswith("@loc"):
                pb.location = pose.get(bone, (0, 0, 0))
                pb.keyframe_insert("location", frame=f)
            elif bone.endswith("@scale"):
                sc = pose.get(bone, 0.001 if bone.startswith("slip") else 1.0)
                pb.scale = (sc, sc, sc)
                pb.keyframe_insert("scale", frame=f)
            else:
                pb.rotation_euler = [math.radians(a) for a in pose.get(bone, (0, 0, 0))]
                pb.keyframe_insert("rotation_euler", frame=f)
    for f in range(0, frames + 1, step):
        ph = 2 * math.pi * cycles * f / frames
        for i, (bone, (amp, sway, phase)) in enumerate(DRIFT_KEYS.items()):
            pb = arm.pose.bones[bone]
            pb.location = (0.3 * amp * math.sin(ph + phase), amp * math.sin(ph + phase + 1.0), 0.3 * amp * math.cos(ph + phase))
            pb.rotation_euler = (math.radians(sway * math.sin(ph + phase)), math.radians(sway * 1.5 * math.sin(ph + phase + 2)), math.radians(sway * 0.6 * math.cos(ph + phase)))
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_euler", frame=f)
    act.frame_range = (0, frames)
    return act


def pose_matrices(pose):
    """Armature-space pose matrices for a static pose (used to set up the ledger page)."""
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    for bone, val in pose.items():
        if "@" not in bone:
            arm.pose.bones[bone].rotation_euler = [math.radians(a) for a in val]
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix.copy() for pb in arm.pose.bones}


# Rest: the ledger open on her left forearm, palm up under it; right hand loose at her side.
REST = {"upper_arm.L": (-2, -17, -40), "forearm.L": (69, -8, 0), "hand.L": (1, -48, -44),
        "upper_arm.R": (6, 0, -6), "forearm.R": (18, 0, 0), "hand.R": (4, 0, 0),
        "head": (6, 0, 0), "slip@scale": 0.001}


def R(p=None):
    out = dict(REST)
    out.update(p or {})
    return out


if os.environ.get("COLLECTOR_PROBE"):
    # Offline pose helper (not used by the build): fits the right arm to hand targets.
    rr = random.Random(1)

    def fit(base, pos, xdir, ydir=None):
        pos, xdir = Vector(pos), Vector(xdir).normalized()
        ydir = Vector(ydir).normalized() if ydir else None

        def pose_of(q):
            out = dict(base)
            out.update({"upper_arm.R": tuple(q[0:3]), "forearm.R": (q[3], q[4], 0), "hand.R": tuple(q[5:8])})
            return out

        def score(q):
            pm_ = pose_matrices(pose_of(q))
            m = pm_["hand.R"]
            pb = arm.pose.bones["hand.R"]
            palm = pb.head.lerp(pb.tail, 0.6)
            r = m.to_3x3()
            sc_ = -6 * (palm - pos).length + r.col[0].dot(xdir) - 0.003 * sum(abs(x) for x in q[5:8]) - 0.001 * abs(q[4])
            if ydir:
                sc_ += 0.6 * r.col[1].dot(ydir)
            return sc_

        lo = [-30, -70, -80, 0, -90, -60, -80, -60]
        hi = [110, 70, 40, 140, 90, 60, 80, 60]
        best = max(([rr.uniform(l, h) for l, h in zip(lo, hi)] for _ in range(800)), key=score)
        step = 10.0
        while step > 0.5:
            improved = False
            for i in range(8):
                for dlt in (step, -step):
                    q = list(best)
                    q[i] = max(lo[i], min(hi[i], q[i] + dlt))
                    if score(q) > score(best):
                        best, improved = q, True
            if not improved:
                step /= 2
        pb = arm.pose.bones["hand.R"]
        print("PROBE", [round(x) for x in best], round(score(best), 3), tuple(round(c, 2) for c in pb.head.lerp(pb.tail, 0.6)))

    import json
    for name, base, pos, xd, yd in json.loads(os.environ["COLLECTOR_PROBE"]):
        print("PROBE", name)
        fit({**REST, **{k: tuple(v) for k, v in base.items()}}, pos, xd, yd)
    sys.exit(0)

# Which way the turning page flips: it must travel over the top of the book (posed +Z world).
pm = pose_matrices(REST)
lp = pm["ledger_page"].to_3x3()
UP_LOCAL = lp.col[0]            # ledger X axis (out of the palm) in armature space
print("ledger up (should point up):", tuple(round(c, 2) for c in UP_LOCAL), "across:", tuple(round(c, 2) for c in lp.col[2]))
# Page lies on local +Z; rotating +Y (Z -> X) lifts it over the top when X points up.
FLIP = 180.0 if UP_LOCAL.z > 0 else -180.0

# Idle: 60f loop. Slow breathing; the head tilts as if listening; the ledger lifts a little.
action("idle", 60, {
    0: R({"chest": (0, 0, 0), "hips@loc": (0, 0, 0)}),
    30: R({"chest": (-2, 0, 1), "head": (9, 5, -4), "upper_arm.L": (-5, -17, -38), "upper_arm.R": (4, 0, -7), "hips@loc": (0, -0.005, 0)}),
    60: R({"chest": (0, 0, 0), "hips@loc": (0, 0, 0)}),
})

# Right-arm key poses below were fitted to hand targets (palm position and facing) offline.
def RA(ua, fa, hd):
    return {"upper_arm.R": ua, "forearm.R": fa, "hand.R": hd}


# Talk: 60f loop. The right hand opens palm-up toward the listener, then turns back to herself.
GEST_A = R({**RA((42, -27, 20), (83, 82, 0), (-18, 14, 0)), "chest": (0, -6, 0), "head": (2, -8, 4)})
GEST_B = R({**RA((27, -56, 12), (105, 57, 0), (0, 19, -22)), "chest": (2, 5, 0), "head": (10, 6, -3)})
action("talk", 60, {0: R({"head": (4, 0, 0)}), 12: GEST_A, 24: {**GEST_A, "head": (-2, -10, 5), "upper_arm.R": (46, -27, 14)},
                    38: GEST_B, 50: R({"head": (8, 3, 0), "upper_arm.R": (14, 0, -8), "forearm.R": (40, 0, 0)}), 60: R({"head": (4, 0, 0)})})

# Offer: 45f. Draws a slip from the ledger (frame 9), holds it out palm-up with a slight bow;
# it is taken at frame 32, and her hand returns.
TAKE = R({**RA((86, -33, -79), (70, -9, 0), (-60, -30, -27)), "chest": (4, 8, 0), "head": (14, 6, 0)})
HOLD = R({**RA((73, -41, -7), (48, 79, 0), (0, 26, 4)), "chest": (6, -4, 0), "spine": (6, 0, 0), "head": (12, 0, 0), "slip@scale": 1.0})
action("offer", 45, {0: R(), 7: TAKE, 9: {**TAKE, "slip@scale": 1.0}, 20: HOLD, 31: {**HOLD, "head": (14, 0, 0)}, 32: {**HOLD, "slip@scale": 0.001},
                     45: R()})

# Bow: 45f. A merchant's polite bow from the waist, right hand laid over the heart.
BOW = R({**RA((23, -4, 16), (132, -28, 0), (-4, 25, 45)), "spine": (16, 0, 0), "chest": (14, 0, 0), "neck": (6, 0, 0), "head": (10, 0, 0), "hips@loc": (0, 0, 0.02)})
action("bow", 45, {0: R(), 14: BOW, 30: {**BOW, "spine": (18, 0, 0)}, 45: R()})

# Turn page: 40f. The right hand reaches across to her left page and lays it over (flip 12-28);
# the sheet snaps back unseen at the end (both halves look the same).
REACH = R({**RA((98, -19, -57), (51, -58, 0), (-2, 0, -20)), "chest": (4, 10, 0), "head": (16, 8, 0)})
CROSS = R({**RA((75, -10, -78), (92, 5, 0), (0, 0, 60)), "chest": (4, 4, 0), "head": (16, 2, 0)})
LAY = R({**RA((43, -13, -43), (87, -43, 0), (-10, -27, -30)), "chest": (4, -2, 0), "head": (14, -4, 0)})
action("turn_page", 40, {
    0: R(), 10: REACH, 12: {**REACH, "ledger_page": (0, FLIP * 0.03, 0)}, 20: {**CROSS, "ledger_page": (0, FLIP * 0.5, 0)},
    28: {**LAY, "ledger_page": (0, FLIP, 0)}, 38: R({"ledger_page": (0, FLIP, 0)}),
    39: R({"ledger_page": (0, FLIP, 0), "ledger_page@scale": 0.001}), 40: R({"ledger_page": (0, 0, 0), "ledger_page@scale": 1.0}),
})

arm.animation_data.action = bpy.data.actions["idle"]
C.export_glb("assets/models/characters/collector/collector.glb", [arm] + meshes)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


print("collector tris:", sum(tris(o) for o in meshes), {o.name: tris(o) for o in meshes})
zs = [v.co.z for v in collector.data.vertices]
print("top: %.3f  lowest: %.3f  height: %.3f" % (max(zs), min(zs), max(zs) - min(zs)))
