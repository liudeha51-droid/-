"""Reimu Hakurei: in-house stylised model, rig and combat animations.

Output: assets/models/characters/reimu/reimu.glb

Blender axes: Z up, the character faces -Y, her left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
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

# ---------------------------------------------------------------- materials
M = {
    "skin": C.material("Skin", (1.0, 0.82, 0.72), 0.6),
    "red": C.material("Red", (0.62, 0.03, 0.05), 0.55),
    "white": C.material("White", (0.92, 0.9, 0.86), 0.7),
    "hair": C.material("Hair", (0.09, 0.05, 0.04), 0.45),
    "yellow": C.material("Yellow", (0.95, 0.72, 0.15), 0.5),
    "shoe": C.material("Shoe", (0.16, 0.08, 0.05), 0.4),
    "sock": C.material("Sock", (0.85, 0.84, 0.8), 0.8),
    "eye_white": C.material("EyeWhite", (0.97, 0.96, 0.95), 0.3),
    "iris": C.material("Iris", (0.35, 0.06, 0.06), 0.2),
    "shine": C.material("EyeShine", (1.0, 1.0, 1.0), 0.1, emission=1.0),
    "line": C.material("Line", (0.12, 0.05, 0.05), 0.6),
    "wood": C.material("Wood", (0.42, 0.26, 0.13), 0.7),
    "paper": C.material("Paper", (0.97, 0.96, 0.92), 0.8),
    "gold": C.material("Gold", (0.95, 0.72, 0.25), 0.3, 0.8),
}

# ---------------------------------------------------------------- skeleton
BONES = [
    # name, head, tail, parent
    ("root", (0, 0, 0), (0, 0, 0.15), None),
    ("hips", (0, 0, 0.80), (0, 0, 0.92), "root"),
    ("spine", (0, 0, 0.92), (0, 0, 1.04), "hips"),
    ("chest", (0, 0, 1.04), (0, 0, 1.19), "spine"),
    ("neck", (0, 0, 1.19), (0, 0, 1.26), "chest"),
    ("head", (0, 0, 1.26), (0, 0, 1.52), "neck"),
]
for s, sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"shoulder.{s}", (sx * 0.03, 0, 1.16), (sx * 0.13, 0, 1.16), "chest"),
        (f"upper_arm.{s}", (sx * 0.14, 0, 1.15), (sx * 0.22, 0.0, 0.93), f"shoulder.{s}"),
        (f"forearm.{s}", (sx * 0.22, 0, 0.93), (sx * 0.28, -0.03, 0.73), f"upper_arm.{s}"),
        (f"hand.{s}", (sx * 0.28, -0.03, 0.73), (sx * 0.30, -0.04, 0.64), f"forearm.{s}"),
        (f"thigh.{s}", (sx * 0.085, 0, 0.82), (sx * 0.09, 0, 0.46), "hips"),
        (f"shin.{s}", (sx * 0.09, 0, 0.46), (sx * 0.09, 0.01, 0.08), f"thigh.{s}"),
        (f"foot.{s}", (sx * 0.09, 0.01, 0.08), (sx * 0.09, -0.1, 0.02), f"shin.{s}"),
    ]

arm_data = bpy.data.armatures.new("ReimuRig")
arm = bpy.data.objects.new("ReimuRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
C.activate(arm)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent in BONES:
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    if name.startswith("foot") or name.startswith("shoulder"):
        eb.align_roll(Vector((0, 0, 1)) if name.startswith("foot") else Vector((0, -1, 0)))
    else:
        eb.align_roll(Vector((0, -1, 0)))
    if parent:
        eb.parent = arm_data.edit_bones[parent]
        eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
arm.data.display_type = "STICK"

BODY_BONES = [b[0] for b in BONES if b[0] != "root"]


def P(name, t):
    b = arm.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


# ---------------------------------------------------------------- body (skin modifier)
def build_body():
    verts, edges, radii = [], [], []

    def v(co, r):
        verts.append(co)
        radii.append(r)
        return len(verts) - 1

    pelvis = v((0, 0, 0.80), (0.115, 0.085))
    waist = v((0, 0, 0.93), (0.078, 0.062))
    chest = v((0, 0, 1.07), (0.095, 0.072))
    upper = v((0, 0, 1.15), (0.09, 0.066))
    neck_b = v((0, 0, 1.2), (0.04, 0.04))
    neck_t = v((0, 0, 1.28), (0.034, 0.034))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
    for sx in (1.0, -1.0):
        sh = v((sx * 0.13, 0, 1.155), (0.042, 0.042))
        el = v((sx * 0.22, 0, 0.93), (0.03, 0.03))
        wr = v((sx * 0.28, -0.03, 0.73), (0.023, 0.023))
        hd = v((sx * 0.30, -0.04, 0.655), (0.03, 0.022))
        hip = v((sx * 0.085, 0, 0.78), (0.068, 0.068))
        kn = v((sx * 0.09, 0, 0.46), (0.045, 0.045))
        an = v((sx * 0.09, 0.01, 0.09), (0.03, 0.03))
        toe = v((sx * 0.09, -0.09, 0.035), (0.034, 0.03))
        edges += [(upper, sh), (sh, el), (el, wr), (wr, hd), (pelvis, hip), (hip, kn), (kn, an), (an, toe)]

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

    # Per-face materials by region: red top, skin arms/neck, socks and shoes.
    for key in ("red", "skin", "sock", "shoe"):
        obj.data.materials.append(M[key])
    for poly in obj.data.polygons:
        c = poly.center
        if c.z < 0.075:
            poly.material_index = 3
        elif c.z < 0.72:
            poly.material_index = 2
        elif abs(c.x) > 0.115 or c.z > 1.19:
            poly.material_index = 1
        else:
            poly.material_index = 0
        poly.use_smooth = True
    C.weight_by_bones(obj, arm, BODY_BONES, power=4.0)
    return obj


def build_head():
    parts = []
    head = C.uv_sphere("Head", 0.125, (0, 0, 1.375), (1.0, 0.97, 1.06), 32, 16, M["skin"])
    # Anime jaw: taper the lower half towards a small chin.
    for v in head.data.vertices:
        dz = v.co.z - 1.375
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.13) * 0.38
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.05
    parts.append(head)

    # Eyes: layered discs on the face (white, iris, shine), slightly turned outward.
    for sx in (1.0, -1.0):
        base = Vector((sx * 0.046, -0.117, 1.37))
        turn = Matrix.Rotation(math.radians(-18 * sx), 4, "Z")
        for mat, size, off, lift in ((M["eye_white"], (0.03, 0.036), 0.0, 0.0), (M["iris"], (0.022, 0.03), -0.003, -0.002), (M["shine"], (0.008, 0.009), -0.005, 0.01)):
            bm = bmesh.new()
            bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=1.0)
            m = Matrix.Translation(base + Vector((sx * 0.004 if mat is M["shine"] else 0, off, lift))) @ turn @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Diagonal((size[0], size[1], 1, 1))
            bm.transform(m)
            parts.append(C.new_object("Eye", bm, mat, smooth=False))
    parts.append(C.box("Mouth", (0.018, 0.004, 0.003), (0, -0.112, 1.305), M["line"]))

    # Hair cap: back and top of the head, open at the face.
    cap = C.uv_sphere("HairCap", 0.136, (0, 0.01, 1.385), (1.02, 1.0, 1.05), 32, 16, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = [v for v in bm.verts if v.co.y < -0.035 and v.co.z < 1.43]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.006)
    parts.append(cap)

    # Bangs: tapered, flattened strands across the forehead.
    for i in range(7):
        x = -0.09 + i * 0.03
        top = Vector((x * 0.8, -0.1, 1.48))
        bottom = Vector((x * 1.05, -0.128 + abs(x) * 0.15, 1.36 + abs(x) * 0.25 - (0.015 if i % 2 else 0)))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.012, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.022, 0.016, 0.002], 8, M["hair"], (1.0, 0.45)))

    # Sidelocks with Reimu's white hair tubes and red ribbons.
    for sx in (1.0, -1.0):
        pts = [Vector((sx * 0.105, -0.05, 1.42)), Vector((sx * 0.125, -0.07, 1.3)), Vector((sx * 0.13, -0.075, 1.16)), Vector((sx * 0.125, -0.07, 1.02))]
        parts.append(C.tube("Sidelock", pts, [0.03, 0.026, 0.022, 0.003], 10, M["hair"], (1.0, 0.55)))
        parts.append(C.tube("HairTube", [Vector((sx * 0.13, -0.075, 1.22)), Vector((sx * 0.13, -0.075, 1.12))], [0.03, 0.028], 12, M["white"]))
        for z in (1.21, 1.13):
            parts.append(C.tube("TubeRibbon", [Vector((sx * 0.13, -0.075, z + 0.006)), Vector((sx * 0.13, -0.075, z - 0.006))], [0.033, 0.033], 12, M["red"]))

    # Back hair: a broad tapered sheet down to the shoulder blades, with jagged tips.
    back = [Vector((0, 0.07, 1.4)), Vector((0, 0.11, 1.26)), Vector((0, 0.1, 1.1)), Vector((0, 0.1, 0.98))]
    parts.append(C.tube("BackHair", back, [0.13, 0.13, 0.11, 0.05], 16, M["hair"], (1.0, 0.42)))
    for i in range(5):
        x = -0.08 + i * 0.04
        parts.append(C.tube("HairTip", [Vector((x, 0.1, 1.04)), Vector((x * 1.1, 0.105, 0.9 - (i % 2) * 0.04))], [0.03, 0.002], 8, M["hair"], (1.0, 0.5)))

    # The bow: red lobes with white frilled edges, a knot and two tails.
    for sx in (1.0, -1.0):
        lobe = C.uv_sphere("BowLobe", 1.0, (0, 0, 0), (0.12, 0.035, 0.085), 20, 10, M["red"])
        C.transform(lobe, Matrix.Translation((sx * 0.12, 0.07, 1.53)) @ Matrix.Rotation(math.radians(sx * -22), 4, "Y"))
        # Frill shares the lobe's centre but is wider and thinner, so only its rim shows.
        frill = C.uv_sphere("BowFrill", 1.0, (0, 0, 0), (0.134, 0.022, 0.098), 20, 10, M["white"])
        C.transform(frill, Matrix.Translation((sx * 0.121, 0.07, 1.53)) @ Matrix.Rotation(math.radians(sx * -22), 4, "Y"))
        tail = C.tube("BowTail", [Vector((sx * 0.02, 0.085, 1.5)), Vector((sx * 0.06, 0.1, 1.42)), Vector((sx * 0.08, 0.11, 1.34))], [0.028, 0.03, 0.036], 10, M["red"], (1.0, 0.25))
        parts += [lobe, frill, tail]
    parts.append(C.uv_sphere("BowKnot", 0.035, (0, 0.08, 1.51), (1.0, 0.8, 1.0), 16, 8, M["red"]))

    for p in parts:
        C.rigid(p, "head")
    return parts


def build_outfit():
    parts = []
    # Collar and yellow ascot.
    collar = C.tube("Collar", [Vector((0, 0, 1.215)), Vector((0, 0, 1.185))], [0.052, 0.07], 20, M["white"])
    ascot = C.uv_sphere("Ascot", 0.024, (0, -0.07, 1.165), (1.0, 0.6, 0.8), 12, 6, M["yellow"])
    for sx in (1.0, -1.0):
        parts.append(C.tube("AscotLoop", [Vector((0, -0.075, 1.165)), Vector((sx * 0.045, -0.075, 1.15))], [0.012, 0.022], 8, M["yellow"], (1.0, 0.4)))
    parts.append(C.tube("AscotTail", [Vector((0, -0.075, 1.15)), Vector((0.005, -0.085, 1.07))], [0.014, 0.022], 8, M["yellow"], (1.0, 0.35)))
    parts += [collar, ascot]
    for p in parts:
        C.rigid(p, "chest")

    # Skirt: pleated flare from the waist to below the knee, frilled hem.
    bm = bmesh.new()
    seg, rings = 48, 8
    grid = []
    for r in range(rings + 1):
        t = r / rings
        z = 0.93 - t * 0.5
        rad = 0.082 + (0.3 - 0.082) * (t ** 0.8)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            pleat = 1.0 + 0.07 * t * math.sin(a * 12)
            ring.append(bm.verts.new((math.cos(a) * rad * pleat, math.sin(a) * rad * pleat * 0.86, z)))
        grid.append(ring)
    for r in range(rings):
        for k in range(seg):
            bm.faces.new((grid[r][k], grid[r][(k + 1) % seg], grid[r + 1][(k + 1) % seg], grid[r + 1][k]))
    skirt = C.new_object("Skirt", bm, M["red"])
    C.solidify(skirt, 0.008)
    C.weight_by_bones(skirt, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    hem = []
    bm = bmesh.new()
    seg2 = 96
    top, bot = [], []
    for k in range(seg2):
        a = 2 * math.pi * k / seg2
        w = 1.0 + 0.07 * math.sin(a * 12) + 0.03 * math.sin(a * 48)
        top.append(bm.verts.new((math.cos(a) * 0.3 * w, math.sin(a) * 0.3 * w * 0.86, 0.435)))
        bot.append(bm.verts.new((math.cos(a) * 0.325 * w, math.sin(a) * 0.325 * w * 0.86, 0.39)))
    for k in range(seg2):
        bm.faces.new((top[k], top[(k + 1) % seg2], bot[(k + 1) % seg2], bot[k]))
    frill = C.new_object("SkirtFrill", bm, M["white"])
    C.solidify(frill, 0.006)
    C.weight_by_bones(frill, arm, ["hips", "thigh.L", "thigh.R"], power=3.0, keep=3)
    parts += [skirt, frill]

    # Detached bell sleeves with red trim.
    for s in ("L", "R"):
        p0 = P(f"upper_arm.{s}", 0.3)
        p1 = P(f"forearm.{s}", 0.0)
        p2 = P(f"forearm.{s}", 1.0)
        d = (p2 - p1).normalized()
        pts = [p0, p0.lerp(p1, 0.5), p1, p1.lerp(p2, 0.5), p2, p2 + d * 0.06]
        radii = [0.046, 0.048, 0.052, 0.066, 0.085, 0.095]
        sleeve = C.tube(f"Sleeve.{s}", pts, radii, 16, M["white"], cap=False)
        C.solidify(sleeve, 0.006)
        C.weight_by_bones(sleeve, arm, [f"upper_arm.{s}", f"forearm.{s}"], power=4.0)
        trim = C.tube(f"SleeveTrim.{s}", [p0 - (p1 - p0).normalized() * 0.005, p0 + (p1 - p0).normalized() * 0.02], [0.052, 0.052], 16, M["red"])
        C.rigid(trim, f"upper_arm.{s}")
        parts += [sleeve, trim]
    return parts


def build_gohei():
    parts = []
    grip = P("hand.R", 0.35)
    d = Vector((0.1, -1.0, 0.45)).normalized()
    start, end = grip - d * 0.14, grip + d * 0.66
    parts.append(C.tube("GoheiStick", [start, end], [0.011, 0.011], 8, M["wood"]))
    parts.append(C.uv_sphere("GoheiCap", 0.02, tuple(end), (1, 1, 1), 12, 6, M["gold"]))
    # Zigzag paper streamers (shide) hanging from the tip.
    for sx in (1.0, -1.0):
        bm = bmesh.new()
        prev = None
        for i in range(6):
            z = -i * 0.05
            x = sx * (0.025 + (0.025 if i % 2 else 0.0))
            a = bm.verts.new(end + Vector((x - 0.02, 0.0, z)))
            b = bm.verts.new(end + Vector((x + 0.02, 0.0, z)))
            if prev:
                bm.faces.new((prev[0], prev[1], b, a))
            prev = (a, b)
        shide = C.new_object("Shide", bm, M["paper"], smooth=False)
        C.solidify(shide, 0.004)
        parts.append(shide)
    for p in parts:
        C.rigid(p, "hand.R")
    return parts


body = build_body()
parts = [body] + build_head() + build_outfit() + build_gohei()
reimu = C.join(parts, "Reimu")
mod = reimu.modifiers.new("Armature", "ARMATURE")
mod.object = arm
reimu.parent = arm

# ---------------------------------------------------------------- animation
FPS = 30
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


def mirror(pose):
    out = {}
    for k, v in pose.items():
        if k.endswith("@loc"):
            out[k] = v
            continue
        if ".L" in k:
            k2 = k.replace(".L", ".R")
        elif ".R" in k:
            k2 = k.replace(".R", ".L")
        else:
            k2 = k
        out[k2] = (v[0], -v[1], -v[2])
    return out


# Rest carries the gohei low and forward; arms relaxed slightly outward.
REST = {"upper_arm.L": (5, 0, 8), "upper_arm.R": (15, 0, -6), "forearm.R": (35, 0, 0), "forearm.L": (10, 0, 0), "hand.R": (-20, 0, 0)}


def with_rest(p):
    out = dict(REST)
    out.update(p)
    return out


# Idle: breathing, a slow sway, gohei ready.
action("idle", 60, {
    0: with_rest({"chest": (0, 0, 0), "head": (-2, 0, 0), "hips@loc": (0, 0, 0)}),
    30: with_rest({"chest": (-3, 0, 1), "head": (1, 2, 0), "upper_arm.L": (3, 0, 10), "hips@loc": (0, -0.008, 0)}),
    60: with_rest({"chest": (0, 0, 0), "head": (-2, 0, 0), "hips@loc": (0, 0, 0)}),
}, loop=True)

# Run cycle: 20 frames, arms counter-swing, forward lean.
def run_pose(ph):
    s = 1 if ph == 0 else -1
    return {
        "hips@loc": (0, -0.03 if ph == 0 else 0.0, 0),
        "hips": (0, 8 * s, 0),
        "spine": (12, 0, 0),
        "chest": (4, -10 * s, 0),
        "head": (-10, 6 * s, 0),
        "thigh.L": (45 * s, 0, 3),
        "thigh.R": (-45 * s, 0, -3),
        "shin.L": (-15 if s > 0 else -80, 0, 0),
        "shin.R": (-80 if s > 0 else -15, 0, 0),
        "foot.L": (0, 0, 0),
        "upper_arm.L": (-40 * s, 0, 12),
        "forearm.L": (60, 0, 0),
        "upper_arm.R": (30 * s + 15, 0, -10),
        "forearm.R": (60, 0, 0),
        "hand.R": (-25, 0, 0),
    }


action("run", 20, {0: run_pose(0), 5: {**run_pose(0), "hips@loc": (0, 0.01, 0)}, 10: run_pose(1), 15: {**run_pose(1), "hips@loc": (0, 0.01, 0)}, 20: run_pose(0)}, loop=True)

# Dodge roll: 15 frames (0.5 s). Tuck, full forward rotation around the hips, stand.
TUCK = {"spine": (35, 0, 0), "chest": (25, 0, 0), "head": (30, 0, 0), "thigh.L": (110, 0, 5), "thigh.R": (110, 0, -5), "shin.L": (-130, 0, 0), "shin.R": (-130, 0, 0), "upper_arm.L": (60, 0, 20), "upper_arm.R": (60, 0, -20), "forearm.L": (100, 0, 0), "forearm.R": (100, 0, 0)}
action("roll", 15, {
    0: with_rest({}),
    2: {**TUCK, "hips": (40, 0, 0), "hips@loc": (0, -0.22, 0)},
    6: {**TUCK, "hips": (170, 0, 0), "hips@loc": (0, -0.3, 0.0)},
    10: {**TUCK, "hips": (300, 0, 0), "hips@loc": (0, -0.25, 0)},
    13: {**with_rest({"spine": (15, 0, 0)}), "hips": (360, 0, 0), "hips@loc": (0, -0.08, 0)},
    15: with_rest({"hips": (360, 0, 0)}),
})

# Attack 1: 15 frames (0.5 s). Right-to-left horizontal sweep, contact ~frame 5 (0.17 s).
WIND1 = {"chest": (0, -40, 0), "spine": (0, -15, 0), "upper_arm.R": (20, 0, -85), "forearm.R": (40, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (30, 0, 25), "thigh.R": (-10, 0, 0), "thigh.L": (15, 0, 0)}
HIT1 = {"chest": (5, 35, 0), "spine": (5, 15, 0), "upper_arm.R": (85, 0, 20), "forearm.R": (5, 0, 0), "hand.R": (-70, 0, 0), "upper_arm.L": (-10, 0, 30), "thigh.R": (-10, 0, 0), "thigh.L": (25, 0, 0), "shin.L": (-10, 0, 0)}
action("attack1", 15, {0: with_rest({}), 2: WIND1, 5: HIT1, 8: {**HIT1, "chest": (5, 45, 0)}, 15: with_rest({})})

# Attack 2: 15 frames. Backhand left-to-right, contact ~frame 5.
WIND2 = {"chest": (0, 35, 0), "spine": (0, 12, 0), "upper_arm.R": (70, 0, 35), "forearm.R": (80, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (10, 0, 30), "thigh.L": (15, 0, 0)}
HIT2 = {"chest": (5, -40, 0), "spine": (5, -15, 0), "upper_arm.R": (80, 0, -70), "forearm.R": (5, 0, 0), "hand.R": (-70, 0, 0), "upper_arm.L": (20, 0, 20), "thigh.R": (20, 0, 0), "shin.R": (-10, 0, 0)}
action("attack2", 15, {0: with_rest({}), 2: WIND2, 5: HIT2, 8: {**HIT2, "chest": (5, -48, 0)}, 15: with_rest({})})

# Attack 3: 22 frames (0.72 s). Overhead two-handed smash, contact ~frame 9 (0.3 s).
WIND3 = {"spine": (-15, 0, 0), "chest": (-15, 0, 0), "head": (-10, 0, 0), "upper_arm.R": (175, 0, -10), "forearm.R": (30, 0, 0), "hand.R": (-40, 0, 0), "upper_arm.L": (165, 0, 15), "forearm.L": (40, 0, 0), "thigh.L": (25, 0, 0), "thigh.R": (-15, 0, 0), "hips@loc": (0, 0.02, 0)}
HIT3 = {"spine": (25, 0, 0), "chest": (20, 0, 0), "head": (10, 0, 0), "upper_arm.R": (70, 0, 10), "forearm.R": (5, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (70, 0, -15), "forearm.L": (10, 0, 0), "thigh.L": (45, 0, 0), "shin.L": (-40, 0, 0), "thigh.R": (-25, 0, 0), "hips@loc": (0, -0.08, -0.06)}
action("attack3", 22, {0: with_rest({}), 6: WIND3, 9: HIT3, 14: HIT3, 22: with_rest({})})

# Hurt: 10 frames. Snap back, arms out.
action("hurt", 10, {0: with_rest({}), 2: {"spine": (-15, 0, 0), "chest": (-15, 0, 0), "head": (-25, 0, 0), "upper_arm.L": (20, 0, 45), "upper_arm.R": (20, 0, -45), "hips@loc": (0, 0, 0.05)}, 10: with_rest({})})

# Death: 30 frames. Knees give, then collapse backwards.
action("death", 30, {
    0: with_rest({}),
    8: {"spine": (20, 0, 0), "head": (25, 0, 0), "thigh.L": (60, 0, 0), "thigh.R": (60, 0, 0), "shin.L": (-100, 0, 0), "shin.R": (-100, 0, 0), "hips@loc": (0, -0.3, 0)},
    20: {"hips": (-75, 0, 10), "spine": (-10, 0, 0), "head": (-20, 20, 0), "thigh.L": (40, 0, 10), "thigh.R": (25, 0, -10), "shin.L": (-40, 0, 0), "shin.R": (-30, 0, 0), "upper_arm.L": (10, 0, 70), "upper_arm.R": (10, 0, -60), "hips@loc": (0, -0.62, 0.15)},
    30: {"hips": (-88, 0, 10), "spine": (-5, 0, 0), "head": (-15, 30, 0), "thigh.L": (15, 0, 10), "thigh.R": (5, 0, -10), "shin.L": (-25, 0, 0), "shin.R": (-10, 0, 0), "upper_arm.L": (0, 0, 80), "upper_arm.R": (0, 0, -70), "hips@loc": (0, -0.66, 0.2)},
})

# Heal: 30 frames (1.0 s). Lift the gourd (left hand) to the mouth and drink.
DRINK = {"upper_arm.L": (70, 0, -15), "forearm.L": (120, 0, 0), "head": (-25, 0, 0), "chest": (-8, 0, 0)}
action("heal", 30, {0: with_rest({}), 8: with_rest(DRINK), 20: with_rest({**DRINK, "head": (-30, 0, 0)}), 30: with_rest({})})

# Ofuda cast: 9 frames (0.3 s). Left hand throws forward.
action("cast", 9, {0: with_rest({}), 3: with_rest({"upper_arm.L": (70, 0, 30), "forearm.L": (90, 0, 0), "chest": (0, 25, 0)}), 5: with_rest({"upper_arm.L": (90, 0, -5), "forearm.L": (0, 0, 0), "chest": (0, -15, 0)}), 9: with_rest({})})

# Spell card: 27 frames (0.9 s). Arms up to gather, then open wide.
action("spell", 27, {
    0: with_rest({}),
    8: {"upper_arm.L": (160, 0, 20), "upper_arm.R": (160, 0, -20), "forearm.L": (20, 0, 0), "forearm.R": (20, 0, 0), "head": (-15, 0, 0), "chest": (-10, 0, 0)},
    16: {"upper_arm.L": (60, 0, 80), "upper_arm.R": (60, 0, -80), "head": (-5, 0, 0), "chest": (-5, 0, 0), "hips@loc": (0, 0.03, 0)},
    27: with_rest({}),
})

arm.animation_data.action = bpy.data.actions["idle"]
C.export_glb("assets/models/characters/reimu/reimu.glb", [arm, reimu])
print("tris:", sum(len(p.vertices) - 2 for p in reimu.data.polygons))
