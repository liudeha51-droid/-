"""Utsushimi (写身), the Mirror of the Empty Sanctum: in-house stylised model, rig and animations.

Output: assets/models/characters/utsushimi/utsushimi.glb

A tsukumogami born from the sacred mirror (goshintai) of the Hakurei Shrine's storehouse.
Her face is hidden behind a round bronze mirror; a larger mirror ring floats behind her
head like a halo, and small mirror shards orbit her hands. She hovers ~0.3 m off the floor.

Same conventions as build_reimu.py / build_story_characters.py:
Blender axes: Z up, she faces -Y, her left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
Bones that point forward (feet, face_mirror, mirror_crack, halo, hand shards) have their roll
aligned to up instead, so for them +X tips the tip up, Y spins about the forward axis.

Everything is modelled at the Former Shrine Maiden's adult proportions, then scaled to
~1.55 m and lifted 0.3 m so the bind pose already hovers. Pose-bone `hips@loc` is
(x, up, forward) in metres.

Mirror parts are separate skinned meshes (rigid to their own bones) so the game can find them:
  FaceMirror (bones face_mirror, mirror_crack), HaloMirror (halo),
  MirrorShard.L.1 / .L.2 / .R.1 / .R.2 (shard.* on hand.L / hand.R), MirrorShard.C (shard.C on chest).
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402

C.reset_scene()

SCALE = 0.917  # maiden-proportion model (1.69 m) -> 1.55 m
HOVER = 0.30
TO_WORLD = Matrix.Translation((0, 0, HOVER)) @ Matrix.Scale(SCALE, 4)

# ---------------------------------------------------------------- materials
M = {
    "skin": C.material("PorcelainSkin", (0.78, 0.76, 0.76), 0.3),
    "kosode": C.material("Kosode", (0.64, 0.63, 0.62), 0.8),
    "kosode_edge": C.material("KosodeEdge", (0.4, 0.37, 0.47), 0.7),
    "chihaya": C.material("Chihaya", (0.7, 0.73, 0.8), 0.6, emission=0.05),
    "hakama": C.material("ForgottenHakama", (0.3, 0.27, 0.37), 0.8),
    "hakama_dark": C.material("ForgottenHakamaDark", (0.19, 0.17, 0.25), 0.8),
    "hair": C.material("SilverHair", (0.56, 0.58, 0.66), 0.35, 0.15),
    "tabi": C.material("Tabi", (0.66, 0.66, 0.65), 0.85),
    "gold": C.material("FadedGoldCord", (0.66, 0.55, 0.32), 0.5, 0.3),
    "bronze": C.material("Bronze", (0.5, 0.35, 0.18), 0.38, 0.45),
    "bronze_dark": C.material("BronzeEngraving", (0.16, 0.1, 0.05), 0.6, 0.3),
    "glass": C.material("MirrorFace", (0.4, 0.52, 0.68), 0.08, 0.25, emission=0.3),
    "glass_edge": C.material("MirrorFaceEdge", (0.2, 0.26, 0.36), 0.1, 0.3, emission=0.2),
    "shine": C.material("MirrorShine", (0.95, 0.98, 1.0), 0.05, emission=1.6),
    "shard": C.material("ShardGlass", (0.5, 0.64, 0.84), 0.08, 0.25, emission=0.5),
    "crack": C.material("MirrorCrack", (0.05, 0.05, 0.07), 0.6),
}

# ---------------------------------------------------------------- skeleton (adult, maiden proportions)
MIRROR_C = Vector((0, -0.127, 1.57))   # face-mirror centre
MIRROR_R = 0.175                       # -> 0.32 m across after scaling
HALO_C = Vector((0, 0.215, 1.6))       # halo ring centre
HAND_PIVOT = {"L": Vector((0.315, -0.105, 0.715)), "R": Vector((-0.315, -0.105, 0.715))}

BONES = [
    ("root", (0, 0, 0), (0, 0, 0.15), None),
    ("hips", (0, 0, 0.96), (0, 0, 1.08), "root"),
    ("spine", (0, 0, 1.08), (0, 0, 1.22), "hips"),
    ("chest", (0, 0, 1.22), (0, 0, 1.4), "spine"),
    ("neck", (0, 0, 1.4), (0, 0, 1.48), "chest"),
    ("head", (0, 0, 1.48), (0, 0, 1.7), "neck"),
    ("face_mirror", tuple(MIRROR_C), tuple(MIRROR_C + Vector((0, -0.08, 0))), "head"),
    ("mirror_crack", tuple(MIRROR_C + Vector((0, -0.01, 0))), tuple(MIRROR_C + Vector((0, -0.06, 0))), "face_mirror"),
    ("halo", tuple(HALO_C), tuple(HALO_C + Vector((0, -0.1, 0))), "chest"),
    ("shard.C", (0, 0, 1.3), (0, 0, 1.4), "chest"),
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
    pv = HAND_PIVOT[s]
    for i in (1, 2):
        BONES.append((f"shard.{s}.{i}", tuple(pv), tuple(pv + Vector((0, -0.05, 0))), f"hand.{s}"))

FORWARD = {"face_mirror", "mirror_crack", "halo", "shard.L.1", "shard.L.2", "shard.R.1", "shard.R.2"}

arm_data = bpy.data.armatures.new("UtsushimiRig")
arm = bpy.data.objects.new("UtsushimiRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
C.activate(arm)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    if name.startswith("shoulder"):
        eb.align_roll(Vector((0, -1, 0)))
    elif name.startswith("foot") or name in FORWARD:
        eb.align_roll(Vector((0, 0, 1)))
    else:
        eb.align_roll(Vector((0, -1, 0)))
    if parent:
        eb.parent = arm_data.edit_bones[parent]
        eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
arm_data.display_type = "STICK"

BODY_BONES = [b[0] for b in BONES if b[0] not in ("root", "shard.C") and b[0] not in FORWARD and not b[0].startswith("shard")]


def P(name, t):
    b = arm.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


# ---------------------------------------------------------------- mesh helpers
def loft(name, rings_spec, seg, mat, pleats=0, pleat_amp=0.0):
    """Loft horizontal ellipse rings: [(center, rx, ry)], optionally pleated."""
    bm = bmesh.new()
    rings = []
    for r, (c, rx, ry) in enumerate(rings_spec):
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            w = 1.0 + pleat_amp * math.sin(a * pleats) * (r / max(1, len(rings_spec) - 1)) ** 0.5 if pleats else 1.0
            ring.append(bm.verts.new(Vector(c) + Vector((math.cos(a) * rx * w, math.sin(a) * ry * w, 0))))
        rings.append(ring)
    for r in range(len(rings) - 1):
        for k in range(seg):
            bm.faces.new((rings[r][k], rings[r][(k + 1) % seg], rings[r + 1][(k + 1) % seg], rings[r + 1][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat)


def lathe(name, profile, seg, mat, center, closed=False, facing=None, smooth=True):
    """Revolve a (radius, dy) profile about the Y axis through `center` (rings lie in XZ)."""
    bm = bmesh.new()
    center = Vector(center)
    rings = []
    for r, dy in profile:
        if r < 1e-6:
            rings.append([bm.verts.new(center + Vector((0, dy, 0)))])
        else:
            rings.append([bm.verts.new(center + Vector((math.cos(2 * math.pi * k / seg) * r, dy, math.sin(2 * math.pi * k / seg) * r))) for k in range(seg)])
    pairs = list(zip(rings[:-1], rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        if len(a) == 1:
            for k in range(seg):
                bm.faces.new((a[0], b[k], b[(k + 1) % seg]))
        elif len(b) == 1:
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[0]))
        else:
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if closed:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    elif facing is not None:
        for f in bm.faces:
            f.normal_update()
            if f.normal.dot(Vector(facing)) < 0:
                f.normal_flip()
    return C.new_object(name, bm, mat, smooth=smooth)


def disc(name, center, radius, sides, thick, mat, rot=Matrix(), edge_mat=None):
    """A flat polygonal disc (hexagon / round) lying in the XZ plane, facing -Y."""
    bm = bmesh.new()
    front, back = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides + (math.pi / 2 if sides == 6 else 0)
        p = Vector((math.cos(a) * radius, 0, math.sin(a) * radius))
        front.append(bm.verts.new(p + Vector((0, -thick / 2, 0))))
        back.append(bm.verts.new(p + Vector((0, thick / 2, 0))))
    bm.faces.new(front[::-1])
    bm.faces.new(back)
    sides_f = []
    for k in range(sides):
        sides_f.append(bm.faces.new((front[k], front[(k + 1) % sides], back[(k + 1) % sides], back[k])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.transform(Matrix.Translation(Vector(center)) @ rot)
    obj = C.new_object(name, bm, mat, smooth=False)
    if edge_mat is not None:
        obj.data.materials.append(edge_mat)
        for poly in obj.data.polygons:
            if len(poly.vertices) == 4:
                poly.material_index = 1
    return obj


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
    sub.levels = 2
    C.apply_modifiers(obj)

    for key in ("kosode", "skin", "tabi"):
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
    C.weight_by_bones(obj, arm, BODY_BONES, power=4.0)
    return obj


def build_hands():
    """Slender open porcelain hands: palm plate and five tapered fingers (rest: palm faces in)."""
    parts = []
    for s, sx in (("L", 1.0), ("R", -1.0)):
        b = arm.data.bones[f"hand.{s}"]
        down = (b.tail_local - b.head_local).normalized()
        base = P(f"hand.{s}", 0.05)
        palm = C.uv_sphere(f"Palm.{s}", 1.0, (0, 0, 0), (0.011, 0.028, 0.036), 12, 8, M["skin"])
        C.transform(palm, Matrix.Translation(base + down * 0.035) @ Matrix.Rotation(math.atan2(b.tail_local.y - b.head_local.y, -(b.tail_local.z - b.head_local.z)), 4, "X"))
        parts.append(palm)
        root = base + down * 0.062
        for i, (dy, ln) in enumerate(((-0.018, 0.052), (-0.006, 0.06), (0.006, 0.057), (0.017, 0.046))):
            a = root + Vector((0, dy, 0))
            spread = Vector((sx * 0.004, dy * 0.35, 0))
            tip = a + down * ln + spread
            mid = a.lerp(tip, 0.5) + Vector((-sx * 0.003, 0, 0))
            parts.append(C.tube("Finger", [a, mid, tip], [0.0075, 0.0065, 0.004], 6, M["skin"]))
        # Thumb from the front of the palm, angled forward-down.
        t0 = base + down * 0.03 + Vector((-sx * 0.004, -0.024, 0))
        t2 = t0 + Vector((-sx * 0.006, -0.022, -0.035))
        parts.append(C.tube("Thumb", [t0, t0.lerp(t2, 0.5), t2], [0.0085, 0.007, 0.0045], 6, M["skin"]))
        for p in parts[-6:]:
            C.rigid(p, f"hand.{s}")
    return parts


# ---------------------------------------------------------------- head and hair
def build_head():
    parts = []
    hc = Vector((0, 0, 1.565))
    head = C.uv_sphere("Head", 0.098, tuple(hc), (0.9, 0.98, 1.1), 24, 12, M["skin"])
    for v in head.data.vertices:
        dz = v.co.z - hc.z
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.11) * 0.3
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.03
    parts.append(head)
    cap = C.uv_sphere("HairCap", 0.107, (0, 0.008, 1.575), (0.95, 1.0, 1.08), 24, 12, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = [v for v in bm.verts if v.co.y < -0.03 and v.co.z < 1.61]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.005)
    parts.append(cap)
    # Straight, even bangs (a hime cut) - mostly hidden behind the mirror, read from the side.
    for i in range(7):
        x = -0.066 + i * 0.022
        top = Vector((x * 0.8, -0.085, 1.67))
        bottom = Vector((x * 1.1, -0.106 + abs(x) * 0.25, 1.59 + abs(x) * 0.3))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.01, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.018, 0.014, 0.003], 6, M["hair"], (1.0, 0.45)))
    # Hime-cut side curtains framing the face, cut straight at the jaw.
    for sx in (1.0, -1.0):
        pts = [Vector((sx * 0.092, -0.035, 1.64)), Vector((sx * 0.1, -0.05, 1.55)), Vector((sx * 0.1, -0.055, 1.47))]
        parts.append(C.tube("SideCurtain", pts, [0.03, 0.034, 0.034], 8, M["hair"], (0.45, 1.0), twist_up=Vector((0, -1, 0))))
    # Cords holding the face mirror: from its back knob, round the head to a knot at the back.
    for sx in (1.0, -1.0):
        pts = [MIRROR_C + Vector((sx * 0.02, 0.02, 0.0)), Vector((sx * 0.085, -0.075, 1.6)), Vector((sx * 0.107, 0.0, 1.61)), Vector((sx * 0.08, 0.09, 1.605)), Vector((sx * 0.012, 0.118, 1.6))]
        parts.append(C.tube("MirrorCord", pts, [0.005] * 5, 6, M["gold"]))
    parts.append(C.uv_sphere("CordKnot", 0.014, (0, 0.12, 1.6), (1.3, 0.8, 1.0), 10, 6, M["gold"]))
    for sx in (1.0, -1.0):
        a = Vector((sx * 0.01, 0.125, 1.595))
        parts.append(C.tube("CordTail", [a, a + Vector((sx * 0.012, 0.012, -0.09))], [0.004, 0.0035], 6, M["gold"]))
    for p in parts:
        C.rigid(p, "head")
    # The first cord segment follows the mirror so it stays attached when the mirror swings.
    return parts


def build_long_hair():
    parts = []
    back = [Vector((0, 0.06, 1.64)), Vector((0, 0.1, 1.53)), Vector((0, 0.135, 1.38)), Vector((0, 0.165, 1.2)), Vector((0, 0.2, 1.02)), Vector((0, 0.215, 0.92))]
    parts.append(C.tube("BackHair", back, [0.1, 0.125, 0.14, 0.15, 0.15, 0.14], 18, M["hair"], (1.0, 0.3), twist_up=Vector((0, -1, 0))))
    # Cut straight across, with only faint unevenness.
    for i in range(9):
        x = -0.12 + i * 0.03
        ln = 0.05 + (0.015 if i % 2 else 0.0)
        parts.append(C.tube("HairTip", [Vector((x, 0.215, 0.94)), Vector((x * 1.02, 0.22, 0.94 - ln))], [0.022, 0.012], 6, M["hair"], (1.0, 0.5), twist_up=Vector((0, -1, 0))))
    for sx in (1.0, -1.0):
        pts = [Vector((sx * 0.085, -0.03, 1.62)), Vector((sx * 0.108, -0.075, 1.5)), Vector((sx * 0.125, -0.105, 1.38)), Vector((sx * 0.13, -0.115, 1.25)), Vector((sx * 0.128, -0.12, 1.12)), Vector((sx * 0.126, -0.122, 1.06))]
        parts.append(C.tube("FrontLock", pts, [0.026, 0.03, 0.03, 0.028, 0.024, 0.018], 8, M["hair"], (1.0, 0.45), twist_up=Vector((0, -1, 0))))
    return parts


# ---------------------------------------------------------------- the mirrors
def build_face_mirror():
    parts = []
    c, R = MIRROR_C, MIRROR_R
    # Polished face: a shallow dome, bright in the middle, darker toward the rim for depth.
    parts.append(lathe("MirrorGlass", [(0.0, -0.1465), (0.05, -0.1455), (0.1, -0.1435)], 40, M["glass"], c, facing=(0, -1, 0)))
    parts.append(lathe("MirrorGlassEdge", [(0.1, -0.1435), (0.13, -0.1415), (0.152, -0.139)], 40, M["glass_edge"], c, facing=(0, -1, 0)))
    # Bronze rim: a raised lip round the glass, rolling over to a flat back.
    rim = [(0.15, -0.1385), (0.156, -0.1455), (0.166, -0.1475), (R, -0.141), (R + 0.002, -0.131), (R - 0.004, -0.121), (0.12, -0.119), (0.0, -0.118)]
    parts.append(lathe("MirrorRim", rim, 40, M["bronze"], c, facing=(0, -1, 0)))
    # Engraved line on the rim face and the back boss (chu) with its cord hole.
    parts.append(lathe("RimLine", [(0.163, -0.1478), (0.1665, -0.1478)], 40, M["bronze_dark"], c, facing=(0, -1, 0)))
    parts.append(C.uv_sphere("MirrorBoss", 0.022, tuple(c + Vector((0, 0.012, 0))), (1, 0.6, 1), 12, 6, M["bronze"]))
    # Sheen: two diagonal highlight streaks across the glass.
    for off, ln, w in ((-0.045, 0.1, 0.012), (-0.01, 0.06, 0.006)):
        bm = bmesh.new()
        d = Vector((math.cos(math.radians(40)), 0, math.sin(math.radians(40))))
        n = Vector((-d.z, 0, d.x))
        mid = c + n * off + Vector((0, -0.1475, 0)) + Vector((-0.015, 0, 0.03))
        a, b = mid - d * ln / 2, mid + d * ln / 2
        vs = [bm.verts.new(a - n * w / 2), bm.verts.new(b - n * w * 0.2), bm.verts.new(b + n * w * 0.2), bm.verts.new(a + n * w / 2)]
        bm.faces.new(vs)
        parts.append(C.new_object("MirrorShine", bm, M["shine"], smooth=False))
    # The thin crack she already carries: from the upper right rim toward the centre.
    y = -0.1475
    crack = [Vector((-0.15, y + 0.0055, 0.075)), Vector((-0.105, y + 0.0035, 0.045)), Vector((-0.085, y + 0.002, 0.05)), Vector((-0.045, y + 0.0005, 0.012)), Vector((-0.02, y, 0.0))]
    parts.append(C.tube("Crack", [c + p for p in crack], [0.0022, 0.002, 0.0018, 0.0014, 0.0008], 4, M["crack"]))
    parts.append(C.tube("CrackBranch", [c + crack[2], c + Vector((-0.07, y + 0.001, 0.09))], [0.0015, 0.0007], 4, M["crack"]))
    # Tassels of faded gold cord hanging from the lower rim.
    for sx in (1.0, -1.0):
        a = c + Vector((sx * 0.1, -0.13, -0.142))
        b = a + Vector((sx * 0.012, 0.0, -0.1))
        parts.append(C.tube("TasselCord", [a, a.lerp(b, 0.5), b], [0.004, 0.004, 0.004], 6, M["gold"]))
        parts.append(C.tube("Tassel", [b, b + Vector((0, 0, -0.012)), b + Vector((0, 0, -0.06))], [0.006, 0.011, 0.013], 8, M["gold"]))
    for p in parts:
        C.rigid(p, "face_mirror")

    # Phase-2 cracks: rigid to mirror_crack, parked just behind the glass until phase2 pushes
    # the bone forward by CRACK_PUSH (so they are hidden in every other action).
    deep = []
    yb = -0.1475 + CRACK_HIDE
    lines = [
        [(-0.02, 0.0), (0.03, -0.035), (0.055, -0.03), (0.1, -0.075), (0.125, -0.1)],
        [(-0.02, 0.0), (0.01, 0.05), (0.0, 0.085), (0.03, 0.14)],
        [(-0.02, 0.0), (-0.06, -0.04), (-0.085, -0.035), (-0.13, -0.075)],
        [(0.03, -0.035), (0.035, -0.09), (0.02, -0.13)],
        [(0.01, 0.05), (0.07, 0.07), (0.12, 0.06)],
    ]
    for ln in lines:
        pts = [c + Vector((x, yb + 0.004 * math.hypot(x, z) / 0.15, z)) for x, z in ln]
        radii = [0.0026 - 0.0016 * i / (len(pts) - 1) for i in range(len(pts))]
        deep.append(C.tube("DeepCrack", pts, radii, 4, M["crack"]))
    # A small star of light where the cracks meet.
    deep.append(C.uv_sphere("CrackCore", 0.006, tuple(c + Vector((-0.02, yb - 0.001, 0.0))), (1, 0.4, 1), 8, 4, M["shine"]))
    for p in deep:
        C.rigid(p, "mirror_crack")
    return parts + deep


def build_halo():
    parts = []
    c = HALO_C
    # Bronze ring with bevelled faces (closed profile), a polished inner inlay on both faces.
    ring = [(0.232, -0.004), (0.24, -0.012), (0.286, -0.012), (0.3, -0.005), (0.3, 0.006), (0.286, 0.013), (0.24, 0.013), (0.232, 0.005)]
    parts.append(lathe("HaloRing", ring, 64, M["bronze"], c, closed=True))
    for dy, face in ((-0.0128, (0, -1, 0)), (0.0138, (0, 1, 0))):
        parts.append(lathe("HaloInlay", [(0.245, dy), (0.268, dy)], 64, M["glass_edge"], c, facing=face, smooth=False))
        parts.append(lathe("HaloLine", [(0.276, dy), (0.279, dy)], 64, M["bronze_dark"], c, facing=face, smooth=False))
    # Engraved notches (24) on both faces and eight bosses with polished pips (8-fold symmetric).
    for k in range(24):
        a = 2 * math.pi * k / 24
        for dy in (-0.0128, 0.0138):
            pos = c + Vector((math.cos(a) * 0.2915, dy, math.sin(a) * 0.2915))
            parts.append(C.box("HaloNotch", (0.012, 0.002, 0.0035), tuple(pos), M["bronze_dark"], rot=(0, -math.degrees(a), 0)))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        pos = c + Vector((math.cos(a) * 0.3, 0.0005, math.sin(a) * 0.3))
        parts.append(C.uv_sphere("HaloBoss", 0.016, tuple(pos), (1, 1.0, 1), 10, 6, M["bronze"]))
        tip = c + Vector((math.cos(a) * 0.335, 0.0005, math.sin(a) * 0.335))
        parts.append(C.tube("HaloRay", [pos, tip], [0.009, 0.001], 6, M["bronze"]))
        for dy in (-0.012, 0.013):
            parts.append(C.uv_sphere("HaloPip", 0.0065, tuple(pos + Vector((0, dy, 0))), (1, 0.4, 1), 8, 4, M["glass"]))
    for p in parts:
        C.rigid(p, "halo")
    return parts


def build_shards():
    """Five small mirror shards, each its own mesh rigid to its own orbit bone."""
    shards = []
    specs = []
    for s, sx in (("L", 1.0), ("R", -1.0)):
        pv = HAND_PIVOT[s]
        specs.append((f"MirrorShard.{s}.1", f"shard.{s}.1", pv + Vector((sx * 0.085, 0, 0.035)), 0.04, 6, (8, 20 * sx, 15)))
        specs.append((f"MirrorShard.{s}.2", f"shard.{s}.2", pv + Vector((-sx * 0.07, 0, -0.06)), 0.032, 16, (-10, -15 * sx, 0)))
    specs.append(("MirrorShard.C", "shard.C", Vector((0.4, -0.05, 1.5)), 0.045, 6, (0, 35, 10)))
    for name, bone, pos, r, sides, rot in specs:
        obj = disc(name, pos, r, sides, 0.007, M["shard"], C.euler_matrix(rot), edge_mat=M["bronze"])
        # A tiny shine on the face so each shard catches the light.
        C.rigid(obj, bone)
        obj.name = name
        obj.data.name = name
        shards.append(obj)
    return shards


# ---------------------------------------------------------------- clothing
def build_outfit():
    parts = []
    # Kosode crossed collar (left over right) with a faded lilac-grey edge.
    for sx, zb in ((-1.0, 1.1), (1.0, 1.13)):
        pts = [Vector((-sx * 0.045, 0.045, 1.46)), Vector((-sx * 0.068, -0.02, 1.415)), Vector((-sx * 0.05, -0.074, 1.36)), Vector((0.0, -0.088, 1.26)), Vector((sx * 0.045, -0.082, zb))]
        parts.append(C.tube("KosodeCollar", pts, [0.012, 0.014, 0.014, 0.014, 0.012], 8, M["kosode_edge"], (1.0, 0.35)))
    for p in parts:
        C.weight_by_bones(p, arm, ["chest", "spine", "neck"], power=4.0)

    # Hakama: pleated waist wrap and two long flared legs; the hovering hem trails past the ankles.
    wrap = loft("HakamaWaist", [((0, 0.0, 1.12), 0.095, 0.078), ((0, 0.0, 1.05), 0.135, 0.108), ((0, 0.0, 0.93), 0.17, 0.138), ((0, 0.0, 0.84), 0.185, 0.152)], 32, M["hakama"], pleats=10, pleat_amp=0.04)
    C.solidify(wrap, 0.006)
    C.weight_by_bones(wrap, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    parts.append(wrap)
    for s, sx in (("L", 1.0), ("R", -1.0)):
        spec = []
        for z, rx, ry in ((0.99, 0.095, 0.115), (0.86, 0.12, 0.145), (0.7, 0.135, 0.16), (0.52, 0.145, 0.17), (0.32, 0.155, 0.178), (0.16, 0.165, 0.186), (0.1, 0.168, 0.19)):
            t = (0.99 - z) / 0.93
            spec.append(((sx * (0.058 + 0.042 * min(1.0, t * 3)), 0.012 * t, z), rx, ry))
        leg = loft(f"HakamaLeg.{s}", spec, 24, M["hakama"], pleats=7, pleat_amp=0.05)
        C.solidify(leg, 0.006)
        C.weight_by_bones(leg, arm, ["hips", f"thigh.{s}", f"shin.{s}"], power=3.0, keep=2)
        parts.append(leg)
    band = loft("HakamaBand", [((0, 0, 1.13), 0.098, 0.08), ((0, 0, 1.085), 0.115, 0.093)], 32, M["hakama_dark"])
    C.solidify(band, 0.006)
    C.weight_by_bones(band, arm, ["hips", "spine"], power=4.0)
    parts.append(band)
    tie = [C.uv_sphere("TieKnot", 0.02, (0, -0.1, 1.1), (1.3, 0.6, 0.8), 10, 6, M["hakama_dark"])]
    for sx in (1.0, -1.0):
        tie.append(C.tube("TieLoop", [Vector((0, -0.103, 1.1)), Vector((sx * 0.045, -0.105, 1.105))], [0.011, 0.016], 8, M["hakama_dark"], (1.0, 0.35)))
        tie.append(C.tube("TieEnd", [Vector((sx * 0.01, -0.105, 1.09)), Vector((sx * 0.028, -0.135, 0.95))], [0.011, 0.014], 6, M["hakama_dark"], (1.0, 0.3)))
    for p in tie:
        C.weight_by_bones(p, arm, ["hips", "spine"], power=4.0)
    parts += tie

    # Chihaya: a sheer, open-fronted overcoat from the shoulders to the upper thigh.
    rings = [((0, 0.005, 1.47), 0.062, 0.058), ((0, 0.0, 1.42), 0.15, 0.085), ((0, 0.0, 1.37), 0.2, 0.1), ((0, 0.0, 1.3), 0.155, 0.105),
             ((0, 0.0, 1.2), 0.14, 0.105), ((0, 0.0, 1.1), 0.16, 0.125), ((0, 0.0, 1.0), 0.19, 0.152), ((0, 0.0, 0.9), 0.218, 0.172),
             ((0, 0.0, 0.8), 0.238, 0.184), ((0, 0.0, 0.74), 0.246, 0.19)]
    chi = loft("Chihaya", rings, 40, M["chihaya"])
    bm = bmesh.new()
    bm.from_mesh(chi.data)
    OPEN = math.radians(20)
    kill = []
    for f in bm.faces:
        cc = f.calc_center_median()
        ang = math.atan2(cc.y, cc.x)
        if abs(ang + math.pi / 2) < OPEN and cc.z < 1.445:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(chi.data)
    bm.free()
    C.solidify(chi, 0.006)
    C.weight_by_bones(chi, arm, ["neck", "chest", "spine", "hips", "thigh.L", "thigh.R", "upper_arm.L", "upper_arm.R"], power=4.0, keep=3)
    parts.append(chi)
    # Lapel band: up the left front, round the back of the neck, down the right front.
    edge = []
    a_l, a_r = -math.pi / 2 + OPEN * 0.97, -math.pi / 2 - OPEN * 0.97
    for c, rx, ry in reversed(rings[1:]):
        edge.append(Vector(c) + Vector((math.cos(a_l) * (rx + 0.004), math.sin(a_l) * (ry + 0.004), 0)))
    c0, rx0, ry0 = rings[0]
    for k in range(9):
        a = a_l + (2 * math.pi - 2 * OPEN * 0.97) * k / 8
        edge.append(Vector(c0) + Vector((math.cos(a) * (rx0 + 0.006), math.sin(a) * (ry0 + 0.006), -0.005)))
    for c, rx, ry in rings[1:]:
        edge.append(Vector(c) + Vector((math.cos(a_r) * (rx + 0.004), math.sin(a_r) * (ry + 0.004), 0)))
    lapel = C.tube("ChihayaLapel", edge, [0.011] * len(edge), 6, M["chihaya"], (1.0, 0.5), cap=False)
    C.weight_by_bones(lapel, arm, ["neck", "chest", "spine", "hips", "thigh.L", "thigh.R"], power=4.0, keep=3)
    parts.append(lapel)
    # Faded gold cord tying the chihaya at the chest, a knot and two hanging ends.
    lz = 1.21
    pl = Vector((math.cos(a_l) * 0.142, math.sin(a_l) * 0.107, lz))
    pr = Vector((math.cos(a_r) * 0.142, math.sin(a_r) * 0.107, lz))
    cord = [C.tube("ChestCord", [pl, Vector((0, -0.112, lz - 0.004)), pr], [0.005, 0.005, 0.005], 6, M["gold"])]
    cord.append(C.uv_sphere("ChestKnot", 0.013, (0, -0.114, lz - 0.004), (1.3, 0.8, 1.0), 10, 6, M["gold"]))
    for sx in (1.0, -1.0):
        a = Vector((sx * 0.006, -0.116, lz - 0.01))
        cord.append(C.tube("ChestCordEnd", [a, a + Vector((sx * 0.012, -0.008, -0.06))], [0.004, 0.0035], 6, M["gold"]))
        cord.append(C.tube("ChestTassel", [a + Vector((sx * 0.012, -0.008, -0.06)), a + Vector((sx * 0.013, -0.009, -0.1))], [0.007, 0.01], 8, M["gold"]))
    for p in cord:
        C.weight_by_bones(p, arm, ["chest", "spine"], power=4.0)
    parts += cord

    # Long, wide chihaya sleeves (tamoto) that sag well below the wrist, gold cord at the cuff.
    for s in ("L", "R"):
        p0 = P(f"upper_arm.{s}", 0.08)
        p1 = P(f"forearm.{s}", 0.0)
        p2 = P(f"forearm.{s}", 1.0)
        d = (p2 - p1).normalized()
        pts = [p0, p0.lerp(p1, 0.5), p1, p1.lerp(p2, 0.5), p2 - d * 0.015]
        radii = [0.062, 0.1, 0.135, 0.165, 0.175]
        sleeve = C.tube(f"Sleeve.{s}", pts, radii, 16, M["chihaya"], (0.4, 1.0), cap=False, twist_up=Vector((0, -1, 0)))

        def sag(obj, amount=0.13):
            for v in obj.data.vertices:
                t = max(0.0, (p0.z - v.co.z) / (p0.z - p2.z))
                if v.co.y > 0.0:
                    v.co.z -= amount * t * (v.co.y / 0.175)

        sag(sleeve)
        C.solidify(sleeve, 0.006)
        C.weight_by_bones(sleeve, arm, [f"upper_arm.{s}", f"forearm.{s}", "chest"], power=4.0)
        cuff = C.tube(f"SleeveCord.{s}", [p2 - d * 0.024, p2 - d * 0.008], [0.1765, 0.1765], 16, M["gold"], (0.415, 1.02), cap=False, twist_up=Vector((0, -1, 0)))
        sag(cuff)
        C.solidify(cuff, 0.01)
        C.rigid(cuff, f"forearm.{s}")
        # Sode-kukuri: the sleeve cord's tassel hanging from the lowest corner of the bag.
        low = min(cuff.data.vertices, key=lambda v: v.co.z).co.copy()
        tas = [C.tube("SleeveTasselCord", [low, low + Vector((0, 0.0, -0.06))], [0.004, 0.004], 6, M["gold"]),
               C.tube("SleeveTassel", [low + Vector((0, 0, -0.06)), low + Vector((0, 0, -0.072)), low + Vector((0, 0, -0.12))], [0.006, 0.011, 0.013], 8, M["gold"])]
        for t in tas:
            C.rigid(t, f"forearm.{s}")
        parts += [sleeve, cuff] + tas
    return parts


# ---------------------------------------------------------------- assemble
CRACK_HIDE = 0.0075   # phase-2 cracks sit this far behind the glass surface...
CRACK_PUSH = (CRACK_HIDE + 0.0012) * SCALE  # ...and phase2 pushes them this far forward (metres)

body = build_body()
hands = build_hands()
head_parts = build_head()
hair = build_long_hair()
for p in hair:
    C.weight_by_bones(p, arm, ["head", "neck", "chest", "spine"], power=4.0)
outfit = build_outfit()
face_mirror_parts = build_face_mirror()
halo_parts = build_halo()
shards = build_shards()

# Scale everything to 1.55 m and lift into the hover, meshes and bones alike.
for o in [body] + hands + head_parts + hair + outfit + face_mirror_parts + halo_parts + shards:
    C.transform(o, TO_WORLD)
C.activate(arm)
bpy.ops.object.mode_set(mode="EDIT")
for eb in arm_data.edit_bones:
    roll = eb.roll
    eb.transform(TO_WORLD, scale=True, roll=False)
    eb.roll = roll
bpy.ops.object.mode_set(mode="OBJECT")

utsushimi = C.join([body] + hands + head_parts + hair + outfit, "Utsushimi")
face_mirror = C.join(face_mirror_parts, "FaceMirror")
halo = C.join(halo_parts, "HaloMirror")
meshes = [utsushimi, face_mirror, halo] + shards
for o in meshes:
    mod = o.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    o.parent = arm

# ---------------------------------------------------------------- animation
arm.animation_data_create()
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"


def action(name, frames, keys, loop=False):
    """keys: {frame: {bone: (rx, ry, rz) degrees | ("loc", (x, y, z))}}."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    used = set()
    for f in keys:
        used.update(keys[f].keys())
    for f in sorted(keys):
        pose = keys[f]
        for bone in used:
            pb = arm.pose.bones[bone.split("@")[0]]
            if bone.endswith("@loc"):
                pb.location = pose.get(bone, (0, 0, 0))
                pb.keyframe_insert("location", frame=f)
            else:
                pb.rotation_euler = [math.radians(a) for a in pose.get(bone, (0, 0, 0))]
                pb.keyframe_insert("rotation_euler", frame=f)
    act.frame_range = (0, frames)
    return act


SHARDS = ["shard.L.1", "shard.L.2", "shard.R.1", "shard.R.2", "shard.C"]
MIRROR_BONES = ["face_mirror", "mirror_crack", "halo"] + SHARDS
# Every action keys the mirror bones (the hidden phase-2 crack must be re-hidden everywhere).
DEFAULTS = {"face_mirror": (0, 0, 0), "face_mirror@loc": (0, 0, 0), "mirror_crack@loc": (0, 0, 0), "halo": (0, 0, 0), "halo@loc": (0, 0, 0)}
DEFAULTS.update({b: (0, 0, 0) for b in SHARDS})


def mirror_act(name, frames, keys, spins=None, loop=False):
    """action() with mirror-bone defaults; `spins` = {bone: (axis, total_deg)} spun linearly
    over the clip (seamless when the part is symmetric under total_deg)."""
    keys = {f: dict(p) for f, p in keys.items()}
    for f, pose in keys.items():
        for b, v in DEFAULTS.items():
            pose.setdefault(b, v)
        for b, (axis, total) in (spins or {}).items():
            r = list(pose.get(b, (0, 0, 0)))
            r[axis] += total * f / frames
            pose[b] = tuple(r)
    act = action(name, frames, keys, loop)
    if spins:
        for fc in act.fcurves:
            if any(f'"{b}"' in fc.data_path for b in spins) and "rotation" in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    return act


def mirror_pose(pose):
    out = {}
    for k, v in pose.items():
        if k.endswith("@loc"):
            out[k] = v
            continue
        k2 = k.replace(".L", ".TMP").replace(".R", ".L").replace(".TMP", ".R")
        out[k2] = (v[0], -v[1], -v[2])
    return out


GROUND_POINTS = [("shin.L", "head", 0.05), ("shin.R", "head", 0.05), ("foot.L", "head", 0.06), ("foot.R", "head", 0.06), ("foot.L", "tail", 0.02), ("foot.R", "tail", 0.02)]


def grounded(pose):
    """Drop the hips so the lowest knee / ankle / toe rests on the floor (z = 0)."""
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    for bone, val in pose.items():
        if not bone.endswith("@loc"):
            arm.pose.bones[bone].rotation_euler = [math.radians(a) for a in val]
    lx, _, lz = pose.get("hips@loc", (0, 0, 0))
    arm.pose.bones["hips"].location = (lx, 0, lz)
    bpy.context.view_layer.update()
    drop = min(getattr(arm.pose.bones[b], end).z - h for b, end, h in GROUND_POINTS)
    out = dict(pose)
    out["hips@loc"] = (lx, -drop, lz)
    return out


# Hover rest: feet pointed and hanging, knees soft, sleeves held a little away, palms loose.
REST = {"thigh.L": (6, 0, 2), "thigh.R": (4, 0, -2), "shin.L": (-10, 0, 0), "shin.R": (-6, 0, 0), "foot.L": (-58, 0, 0), "foot.R": (-55, 0, 0),
        "upper_arm.L": (6, 0, 9), "upper_arm.R": (6, 0, -9), "forearm.L": (22, 0, 0), "forearm.R": (22, 0, 0), "hand.L": (6, 0, -4), "hand.R": (6, 0, 4),
        "head": (3, 0, 0)}


def R(p=None, **kw):
    out = dict(REST)
    out.update(p or {})
    return out


HAND_SPIN = {"shard.L.1": (1, 360), "shard.L.2": (1, 360), "shard.R.1": (1, -360), "shard.R.2": (1, -360), "shard.C": (1, 360), "halo": (1, 45)}

# Idle: 60f loop. A slow hover bob; the halo turns an eighth, shards circle each hand once.
mirror_act("idle", 60, {
    0: R({"hips@loc": (0, 0, 0), "chest": (0, 0, 0)}),
    30: R({"hips@loc": (0, 0.03, 0), "chest": (-2, 0, 1), "head": (5, 3, -2), "upper_arm.L": (4, 0, 11), "upper_arm.R": (4, 0, -11), "face_mirror": (-2, 0, 0), "foot.L": (-62, 0, 0)}),
    60: R({"hips@loc": (0, 0, 0), "chest": (0, 0, 0)}),
}, spins=HAND_SPIN, loop=True)

# Float move: 20f loop. Leans into the glide; sleeves, legs and hair trail behind.
def glide(ph):
    s = 1 if ph == 0 else -1
    return R({
        "hips@loc": (0, 0.0 if ph == 0 else 0.018, 0), "hips": (4, 0, 0), "spine": (3, 2 * s, 0), "chest": (2, 0, 0), "head": (-10, 0, 0),
        "thigh.L": (-16 + 3 * s, 0, 2), "thigh.R": (-16 - 3 * s, 0, -2), "shin.L": (-18, 0, 0), "shin.R": (-15, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
        "upper_arm.L": (-24 + 4 * s, 0, 14), "upper_arm.R": (-24 - 4 * s, 0, -14), "forearm.L": (18, 0, 0), "forearm.R": (18, 0, 0),
        "face_mirror": (4, 0, 0), "halo": (-6, 0, 0), "halo@loc": (0, 0, -0.02),
        "shard.L.1": (0, 25 * s, 0), "shard.L.2": (0, 25 * s, 0), "shard.R.1": (0, -25 * s, 0), "shard.R.2": (0, -25 * s, 0), "shard.C": (0, 30 * s, 0),
    })


mirror_act("float_move", 20, {0: glide(0), 10: glide(1), 20: glide(0)}, loop=True)

# Reflect stance: 30f loop. Both hands raised, open, palms forward; the face-mirror tilted up.
# The shards whirl round the hands (a full turn per loop), the halo turns an eighth.
def ward(ph):
    s = 1 if ph == 0 else -1
    left = {"upper_arm.L": (40, -30, 0), "forearm.L": (90, 0, 0), "hand.L": (0, -135, 30)}
    return R({
        **left, **mirror_pose(left),
        "hips@loc": (0, 0.012 * (1 - s), 0), "spine": (-4, 0, 0), "chest": (-4, 0, 0), "head": (-6, 0, 0), "neck": (-3, 0, 0),
        "face_mirror": (14 + 2 * s, 0, 0), "halo@loc": (0, 0.01, -0.01),
        "thigh.L": (10, 0, 2), "thigh.R": (-6, 0, -2), "shin.L": (-18, 0, 0),
    })


mirror_act("reflect_stance", 30, {0: ward(0), 15: ward(1), 30: ward(0)}, spins={**HAND_SPIN, "shard.C": (1, 180)}, loop=True)

# Strike: 20f. The right sleeve sweeps from wide right across to the left; contact frame 9.
WIND = R({"chest": (0, -38, 0), "spine": (0, -16, 0), "head": (4, 16, 0), "upper_arm.R": (25, 0, -95), "forearm.R": (35, 0, 0), "hand.R": (-20, 0, 0),
          "upper_arm.L": (25, 0, 22), "forearm.L": (40, 0, 0), "hips@loc": (0, 0.03, 0.02), "thigh.R": (-12, 0, 0), "face_mirror": (0, 0, -5)})
HIT = R({"chest": (4, 38, 0), "spine": (4, 16, 0), "head": (2, -12, 0), "upper_arm.R": (84, 0, 25), "forearm.R": (8, 0, 0), "hand.R": (-30, 0, 0),
         "upper_arm.L": (-15, 0, 30), "forearm.L": (20, 0, 0), "hips@loc": (0, -0.02, 0.1), "thigh.L": (-18, 0, 0), "thigh.R": (-10, 0, 0), "face_mirror": (0, 0, 6),
         "shard.R.1": (0, -120, 0), "shard.R.2": (0, -120, 0)})
FOLLOW = {**HIT, "chest": (4, 48, 0), "upper_arm.R": (78, 0, 40), "shard.R.1": (0, -160, 0), "shard.R.2": (0, -160, 0)}
mirror_act("strike", 20, {0: R(), 5: WIND, 9: HIT, 13: FOLLOW, 20: R()})

# Cast: 12f. Draws the right hand back, then pushes it out palm-first; release frame 6.
CAST_DRAW = R({"upper_arm.R": (20, 0, -30), "forearm.R": (110, 60, 0), "hand.R": (-20, 0, 0), "chest": (0, -22, 0), "head": (0, 10, 0), "hips@loc": (0, 0.01, -0.02)})
CAST_PUSH = R({"upper_arm.R": (84, 0, -6), "forearm.R": (8, 70, 0), "hand.R": (-60, 0, 0), "chest": (0, 18, 0), "spine": (4, 6, 0), "head": (0, -8, 0), "hips@loc": (0, 0, 0.05),
               "shard.R.1": (0, -90, 0), "shard.R.2": (0, -90, 0), "face_mirror": (4, 0, 0)})
mirror_act("cast", 12, {0: R(), 3: CAST_DRAW, 6: CAST_PUSH, 8: CAST_PUSH, 12: R()})

# Spell: 30f. Arms spread wide; the halo rises, tilts toward the foe and spins.
GATHER = R({"upper_arm.L": (40, 30, 10), "upper_arm.R": (40, -30, -10), "forearm.L": (95, 0, 0), "forearm.R": (95, 0, 0), "head": (6, 0, 0), "chest": (6, 0, 0), "hips@loc": (0, -0.02, 0),
            "halo@loc": (0, 0.03, 0)})
SPREAD = R({"upper_arm.L": (20, 0, 100), "upper_arm.R": (20, 0, -100), "forearm.L": (10, -60, 0), "forearm.R": (10, 60, 0), "hand.L": (-20, 0, 0), "hand.R": (-20, 0, 0),
            "chest": (-10, 0, 0), "spine": (-4, 0, 0), "head": (-14, 0, 0), "hips@loc": (0, 0.07, 0), "halo@loc": (0, 0.14, -0.02), "face_mirror": (10, 0, 0)})
mirror_act("spell", 30, {0: R(), 8: GATHER, 16: SPREAD, 24: {**SPREAD, "hips@loc": (0, 0.08, 0)}, 30: R()},
           spins={"halo": (1, 180), "shard.L.1": (1, 360), "shard.L.2": (1, 360), "shard.R.1": (1, -360), "shard.R.2": (1, -360), "shard.C": (1, 180)})

# Hurt: 10f. Knocked back; the face-mirror swings on its cords.
action_hurt = mirror_act("hurt", 10, {0: R(), 3: R({"spine": (-12, 0, 0), "chest": (-10, 6, 0), "head": (-16, 0, 0), "upper_arm.L": (18, 0, 40), "upper_arm.R": (22, 0, -36),
                                                      "forearm.L": (40, 0, 0), "forearm.R": (40, 0, 0), "hips@loc": (0, 0.02, -0.08), "face_mirror": (18, 0, 6), "halo": (8, 0, 0),
                                                      "thigh.L": (18, 0, 0), "thigh.R": (14, 0, 0), "shin.L": (-25, 0, 0)}),
                                        6: R({"face_mirror": (-8, 0, -3), "head": (4, 0, 0), "hips@loc": (0, 0.01, -0.03)}), 10: R()})

# Phase 2: 30f. She jerks, the face-mirror cracks further (frame 8) and she opens outward.
CRACKED = {"mirror_crack@loc": (0, CRACK_PUSH, 0)}
JOLT = R({"head": (-22, 0, 8), "neck": (-8, 0, 0), "chest": (-10, 0, 0), "spine": (-6, 0, 0), "upper_arm.L": (30, 0, 30), "upper_arm.R": (30, 0, -30),
          "forearm.L": (95, 0, 0), "forearm.R": (95, 0, 0), "hand.L": (-30, 0, 0), "hand.R": (-30, 0, 0), "face_mirror": (10, 0, 10), "hips@loc": (0, 0.04, -0.03)})
OPEN_P = R({"head": (10, 0, -10), "neck": (6, 0, 0), "chest": (-6, 0, 0), "upper_arm.L": (40, 0, 55), "upper_arm.R": (40, 0, -55), "forearm.L": (25, -40, 0), "forearm.R": (25, 40, 0),
            "hand.L": (-25, 0, 0), "hand.R": (-25, 0, 0), "face_mirror": (-6, 0, -8), "hips@loc": (0, 0.06, 0), "halo": (0, 0, 8), "halo@loc": (0, 0.03, 0)})
mirror_act("phase2", 30, {0: R(), 7: {**JOLT, "face_mirror": (4, 0, 4)}, 8: {**JOLT, **CRACKED}, 18: {**OPEN_P, **CRACKED}, 30: {**OPEN_P, **CRACKED, "head": (12, 0, -12)}},
           spins={"halo": (1, 45), "shard.L.1": (1, 180), "shard.L.2": (1, 180), "shard.R.1": (1, -180), "shard.R.2": (1, -180)})

# Death: 45f. The hover fails: she sinks, kneels in seiza, and the face-mirror tips down and
# hangs from its cords, showing its reflection to the floor. Shards and halo drop and still.
STAGGER = R({"spine": (-8, 0, 0), "chest": (-6, 0, 0), "head": (-12, 0, 0), "upper_arm.L": (12, 0, 28), "upper_arm.R": (15, 0, -24), "face_mirror": (12, 0, 0), "hips@loc": (0, -0.04, -0.04)})
SINK = grounded({"thigh.L": (40, 0, 3), "thigh.R": (38, 0, -3), "shin.L": (-100, 0, 0), "shin.R": (-100, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
                 "spine": (10, 0, 0), "chest": (6, 0, 0), "head": (20, 0, 0), "upper_arm.L": (6, 0, 14), "upper_arm.R": (8, 0, -12), "forearm.L": (20, 0, 0), "forearm.R": (20, 0, 0)})
SINK["hips@loc"] = (0, SINK["hips@loc"][1] + 0.05, 0)
SEIZA = {"thigh.L": (80, 0, 3), "thigh.R": (80, 0, -3), "shin.L": (-165, 0, 0), "shin.R": (-165, 0, 0), "foot.L": (-60, 0, 0), "foot.R": (-60, 0, 0)}
KNEEL = grounded({**SEIZA, "spine": (16, 0, 0), "chest": (12, 0, 0), "neck": (14, 0, 0), "head": (30, 0, 0),
                  "upper_arm.L": (15, 0, 2), "upper_arm.R": (15, 0, -2), "forearm.L": (88, 0, 0), "forearm.R": (88, 0, 0), "hand.L": (0, -20, 0), "hand.R": (0, 20, 0)})
KNEEL["hips@loc"] = (0, KNEEL["hips@loc"][1] + 0.04, 0)  # a spirit: she settles just above the boards
DROPPED = {"face_mirror": (-58, 0, 0), "face_mirror@loc": (0, 0.07, -0.03), "halo": (-14, 0, 6), "halo@loc": (0, -0.1, -0.03),
           "shard.L.1": (0, 40, 0), "shard.R.1": (0, -40, 0), "shard.C": (0, 70, 0)}
mirror_act("death", 45, {0: R({"hips@loc": (0, 0, 0)}), 6: STAGGER, 20: {**SINK, "face_mirror": (-20, 0, 0), "halo@loc": (0, -0.04, 0)}, 32: {**KNEEL, **DROPPED, "face_mirror": (-70, 0, 0)},
                         45: {**KNEEL, **DROPPED}})

arm.animation_data.action = bpy.data.actions["idle"]
C.export_glb("assets/models/characters/utsushimi/utsushimi.glb", [arm] + meshes)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


print("utsushimi tris:", sum(tris(o) for o in meshes), {o.name: tris(o) for o in meshes})
zs = [(o.matrix_world @ v.co).z for o in [utsushimi] for v in o.data.vertices]
print("body top: %.3f  lowest: %.3f  height: %.3f" % (max(zs), min(zs), max(zs) - min(zs)))
print("mirror top: %.3f" % max(v.co.z for v in face_mirror.data.vertices), "halo top: %.3f" % max(v.co.z for v in halo.data.vertices))
