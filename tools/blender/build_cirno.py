"""Cirno, the Ice Fairy: in-house stylised model, rig and boss animations.

Output: assets/models/characters/cirno/cirno.glb

Same conventions as build_reimu.py, scaled to a ~1.25 m child fairy.
Blender axes: Z up, the character faces -Y, her left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
She is a hovering boss: every action lifts her off the ground through hips@loc
(local Y of the hips bone is world up, local Z is forward).
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
    "skin": C.material("CirnoSkin", (0.93, 0.84, 0.86), 0.6),
    "frost": C.material("Frostbite", (0.66, 0.78, 0.93), 0.35),
    "blue": C.material("Dress", (0.10, 0.25, 0.68), 0.6),
    "white": C.material("Blouse", (0.90, 0.92, 0.95), 0.7),
    "red": C.material("Ribbon", (0.62, 0.04, 0.07), 0.5),
    "hair": C.material("CirnoHair", (0.42, 0.68, 0.93), 0.45),
    "bow": C.material("Bow", (0.05, 0.10, 0.42), 0.5),
    "shoe": C.material("CirnoShoe", (0.10, 0.10, 0.18), 0.4),
    "bloomers": C.material("Bloomers", (0.85, 0.88, 0.92), 0.8),
    "eye_white": C.material("CirnoEyeWhite", (0.95, 0.97, 1.0), 0.3),
    "iris": C.material("CirnoIris", (0.08, 0.38, 0.92), 0.2, emission=0.35),
    "shine": C.material("CirnoEyeShine", (1.0, 1.0, 1.0), 0.1, emission=1.0),
    "line": C.material("CirnoLine", (0.10, 0.08, 0.16), 0.6),
    "fang": C.material("Fang", (0.97, 0.97, 1.0), 0.3),
    "ice": C.material("Ice", (0.45, 0.88, 1.0), 0.08, emission=0.6),
}
ice = M["ice"]
bsdf = ice.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Alpha"].default_value = 0.72
ice.blend_method = "BLEND"
if hasattr(ice, "surface_render_method"):
    ice.surface_render_method = "BLENDED"

# ---------------------------------------------------------------- skeleton
BONES = [
    # name, head, tail, parent
    ("root", (0, 0, 0), (0, 0, 0.12), None),
    ("hips", (0, 0, 0.58), (0, 0, 0.66), "root"),
    ("spine", (0, 0, 0.66), (0, 0, 0.76), "hips"),
    ("chest", (0, 0, 0.76), (0, 0, 0.88), "spine"),
    ("neck", (0, 0, 0.88), (0, 0, 0.94), "chest"),
    ("head", (0, 0, 0.94), (0, 0, 1.18), "neck"),
]
for s, sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"shoulder.{s}", (sx * 0.02, 0, 0.855), (sx * 0.095, 0, 0.855), "chest"),
        (f"upper_arm.{s}", (sx * 0.10, 0, 0.85), (sx * 0.15, 0.0, 0.69), f"shoulder.{s}"),
        (f"forearm.{s}", (sx * 0.15, 0, 0.69), (sx * 0.185, -0.02, 0.545), f"upper_arm.{s}"),
        (f"hand.{s}", (sx * 0.185, -0.02, 0.545), (sx * 0.197, -0.03, 0.475), f"forearm.{s}"),
        (f"thigh.{s}", (sx * 0.062, 0, 0.60), (sx * 0.066, 0, 0.33), "hips"),
        (f"shin.{s}", (sx * 0.066, 0, 0.33), (sx * 0.066, 0.01, 0.065), f"thigh.{s}"),
        (f"foot.{s}", (sx * 0.066, 0.01, 0.065), (sx * 0.066, -0.075, 0.018), f"shin.{s}"),
    ]

arm_data = bpy.data.armatures.new("CirnoRig")
arm = bpy.data.objects.new("CirnoRig", arm_data)
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

    pelvis = v((0, 0, 0.585), (0.082, 0.064))
    waist = v((0, 0, 0.68), (0.058, 0.047))
    chest = v((0, 0, 0.78), (0.067, 0.052))
    upper = v((0, 0, 0.845), (0.066, 0.048))
    neck_b = v((0, 0, 0.89), (0.029, 0.029))
    neck_t = v((0, 0, 0.965), (0.026, 0.026))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
    for sx in (1.0, -1.0):
        sh = v((sx * 0.098, 0, 0.848), (0.03, 0.03))
        el = v((sx * 0.15, 0, 0.69), (0.022, 0.022))
        wr = v((sx * 0.185, -0.02, 0.545), (0.017, 0.017))
        hd = v((sx * 0.195, -0.028, 0.49), (0.024, 0.017))
        hip = v((sx * 0.062, 0, 0.575), (0.05, 0.05))
        kn = v((sx * 0.066, 0, 0.33), (0.034, 0.034))
        an = v((sx * 0.066, 0.01, 0.07), (0.027, 0.027))
        toe = v((sx * 0.066, -0.07, 0.03), (0.032, 0.027))
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

    # Regions: shoes, bare legs (frost-bitten knees), bloomers, blue bodice,
    # white blouse top, skin arms/neck with frost-bitten hands.
    order = ("shoe", "skin", "frost", "bloomers", "blue", "white")
    for key in order:
        obj.data.materials.append(M[key])
    idx = {k: i for i, k in enumerate(order)}
    for poly in obj.data.polygons:
        c = poly.center
        if abs(c.x) > 0.105 or (abs(c.x) > 0.085 and c.z > 0.8):  # arms
            key = "frost" if c.z < 0.53 else "skin"
        elif c.z > 0.875:
            key = "skin"
        elif c.z < 0.085:
            key = "shoe"
        elif c.z < 0.55:
            knee = abs(c.z - 0.335) < 0.022 and c.y < -0.02 and abs(abs(c.x) - 0.066) < 0.016
            key = "frost" if knee else "skin"
        elif c.z < 0.63:
            key = "bloomers"
        elif c.z > 0.825:
            key = "white"
        else:
            key = "blue"
        poly.material_index = idx[key]
        poly.use_smooth = True
    C.weight_by_bones(obj, arm, BODY_BONES, power=4.0)
    return obj


def crystal(name, base, direction, length, width, thick, normal=Vector((0, 1, 0)), mat=None, mid=0.32, sides=6):
    """Faceted ice shard: flattened bipyramid from base along direction."""
    d = Vector(direction).normalized()
    n = (normal - d * normal.dot(d)).normalized()
    w = d.cross(n).normalized()
    bm = bmesh.new()
    b = bm.verts.new(Vector(base))
    tip = bm.verts.new(Vector(base) + d * length)
    ring = []
    c = Vector(base) + d * length * mid
    for k in range(sides):
        a = 2 * math.pi * k / sides
        ring.append(bm.verts.new(c + w * math.cos(a) * width + n * math.sin(a) * thick))
    for k in range(sides):
        bm.faces.new((b, ring[(k + 1) % sides], ring[k]))
        bm.faces.new((ring[k], ring[(k + 1) % sides], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat, smooth=False)


def build_head():
    parts = []
    HC = Vector((0, 0, 1.05))
    head = C.uv_sphere("Head", 0.12, tuple(HC), (1.0, 0.95, 1.02), 32, 16, M["skin"])
    for v in head.data.vertices:
        dz = v.co.z - HC.z
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.125) * 0.36
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.045
    parts.append(head)

    # Big blue eyes, slightly narrowed at the top for a feral glare.
    for sx in (1.0, -1.0):
        base = Vector((sx * 0.043, -0.108, 1.038))
        turn = Matrix.Rotation(math.radians(-20 * sx), 4, "Z")
        for mat, size, off, lift, dx in (
            (M["eye_white"], (0.03, 0.033), 0.0, 0.0, 0.0),
            (M["iris"], (0.022, 0.029), -0.003, -0.002, 0.0),
            (M["line"], (0.009, 0.016), -0.005, -0.002, 0.0),
            (M["shine"], (0.007, 0.008), -0.007, 0.011, sx * 0.006),
        ):
            bm = bmesh.new()
            bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=1.0)
            m = Matrix.Translation(base + Vector((dx, off, lift))) @ turn @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Diagonal((size[0], size[1], 1, 1))
            bm.transform(m)
            parts.append(C.new_object("Eye", bm, mat, smooth=False))
        # Angry upper lid line and brow, low on the inner side.
        parts.append(C.box("Lid", (0.038, 0.006, 0.008), (sx * 0.044, -0.11, 1.066), M["line"], (0, -14 * sx, -20 * sx)))
        parts.append(C.box("Brow", (0.03, 0.006, 0.005), (sx * 0.046, -0.106, 1.088), M["line"], (0, -22 * sx, -20 * sx)))
    parts.append(C.box("Mouth", (0.022, 0.004, 0.003), (0, -0.098, 0.985), M["line"]))
    fang = crystal("Fang", (0.008, -0.1, 0.985), (0, -0.2, -1), 0.011, 0.004, 0.002, Vector((0, -1, 0)), M["fang"], mid=0.1, sides=4)
    parts.append(fang)

    # Hair cap, open at the face.
    cap = C.uv_sphere("HairCap", 0.131, (0, 0.008, 1.062), (1.04, 1.0, 1.03), 32, 16, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = [v for v in bm.verts if v.co.y < -0.065 and v.co.z < 1.105]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.006)
    parts.append(cap)

    # Choppy bangs.
    for i in range(7):
        x = -0.084 + i * 0.028
        top = Vector((x * 0.8, -0.085, 1.165))
        bottom = Vector((x * 1.08, -0.118 + abs(x) * 0.18, 1.075 + abs(x) * 0.2 - (0.014 if i % 2 else 0)))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.013, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.021, 0.016, 0.002], 8, M["hair"], (1.0, 0.45)))

    # Short side locks framing the cheeks.
    for sx in (1.0, -1.0):
        for dz, fy in ((0.0, 0.0), (0.02, 0.035)):
            pts = [Vector((sx * 0.112, -0.03 + fy, 1.1 + dz)), Vector((sx * 0.122, -0.05 + fy, 1.02 + dz)), Vector((sx * 0.112, -0.055 + fy, 0.955 + dz))]
            parts.append(C.tube("Sidelock", pts, [0.026, 0.02, 0.002], 8, M["hair"], (1.0, 0.5)))

    # Short back: a tapered sheet with outward-flicking tips at the nape.
    back = [Vector((0, 0.07, 1.1)), Vector((0, 0.105, 1.01)), Vector((0, 0.095, 0.955))]
    parts.append(C.tube("BackHair", back, [0.125, 0.12, 0.09], 16, M["hair"], (1.0, 0.45)))
    for i in range(6):
        x = -0.09 + i * 0.036
        flick = 1.25 if abs(x) > 0.06 else 1.1
        parts.append(C.tube("HairTip", [Vector((x, 0.1, 0.99)), Vector((x * flick, 0.105 + abs(x) * 0.2, 0.915 - (i % 2) * 0.025))], [0.026, 0.002], 8, M["hair"], (1.0, 0.5)))

    # The big dark-blue bow on the back of the head.
    for sx in (1.0, -1.0):
        lobe = C.uv_sphere("BowLobe", 1.0, (0, 0, 0), (0.12, 0.035, 0.085), 20, 10, M["bow"])
        C.transform(lobe, Matrix.Translation((sx * 0.115, 0.075, 1.2)) @ Matrix.Rotation(math.radians(sx * -24), 4, "Y"))
        tail = C.tube("BowTail", [Vector((sx * 0.02, 0.09, 1.17)), Vector((sx * 0.055, 0.115, 1.09)), Vector((sx * 0.075, 0.125, 1.02))], [0.024, 0.027, 0.032], 10, M["bow"], (1.0, 0.25))
        parts += [lobe, tail]
    parts.append(C.uv_sphere("BowKnot", 0.034, (0, 0.085, 1.185), (1.0, 0.8, 1.0), 16, 8, M["bow"]))

    for p in parts:
        C.rigid(p, "head")
    return parts


WING_ROOT = Vector((0.035, 0.085, 0.805))
WINGS = [  # (direction, length, width) for the left side; mirrored for the right
    ((1.0, 0.35, 0.75), 0.26, 0.04),
    ((1.0, 0.45, 0.12), 0.31, 0.046),
    ((1.0, 0.35, -0.45), 0.24, 0.038),
]


def build_outfit():
    parts = []
    # White rounded collar and red neck ribbon.
    collar = C.tube("Collar", [Vector((0, 0.0, 0.885)), Vector((0, 0.002, 0.862))], [0.037, 0.083], 24, M["white"])
    parts.append(collar)
    knot = C.uv_sphere("RibbonKnot", 0.014, (0, -0.068, 0.858), (1.0, 0.7, 1.0), 12, 6, M["red"])
    parts.append(knot)
    for sx in (1.0, -1.0):
        parts.append(C.tube("RibbonLoop", [Vector((0, -0.07, 0.858)), Vector((sx * 0.035, -0.066, 0.866)), Vector((sx * 0.05, -0.058, 0.852))], [0.008, 0.02, 0.006], 8, M["red"], (1.0, 0.35)))
        parts.append(C.tube("RibbonTail", [Vector((sx * 0.004, -0.07, 0.852)), Vector((sx * 0.018, -0.07, 0.8))], [0.01, 0.015], 8, M["red"], (1.0, 0.3)))

    # Six ice-crystal wings, three per side, floating off the back.
    for sx in (1.0, -1.0):
        for i, (d, length, width) in enumerate(WINGS):
            d = Vector((d[0] * sx, d[1], d[2])).normalized()
            base = Vector((WING_ROOT.x * sx, WING_ROOT.y, WING_ROOT.z)) + d * 0.02
            parts.append(crystal(f"Wing{i}", base, d, length, width, 0.012, Vector((0, 1, 0)), ice))
    for p in parts:
        C.rigid(p, "chest")

    # Pinafore skirt: flared, soft pleats, above the knee.
    bm = bmesh.new()
    seg, rings = 40, 7
    grid = []
    for r in range(rings + 1):
        t = r / rings
        z = 0.69 - t * 0.31
        rad = 0.066 + (0.215 - 0.066) * (t ** 0.8)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            pleat = 1.0 + 0.06 * t * math.sin(a * 10)
            ring.append(bm.verts.new((math.cos(a) * rad * pleat, math.sin(a) * rad * pleat * 0.84, z)))
        grid.append(ring)
    for r in range(rings):
        for k in range(seg):
            bm.faces.new((grid[r][k], grid[r][(k + 1) % seg], grid[r + 1][(k + 1) % seg], grid[r + 1][k]))
    skirt = C.new_object("Skirt", bm, M["blue"])
    C.solidify(skirt, 0.007)
    C.weight_by_bones(skirt, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    # White petticoat edge peeking under the hem.
    bm = bmesh.new()
    seg2 = 80
    top, bot = [], []
    for k in range(seg2):
        a = 2 * math.pi * k / seg2
        w = 1.0 + 0.06 * math.sin(a * 10) + 0.025 * math.sin(a * 40)
        top.append(bm.verts.new((math.cos(a) * 0.2 * w, math.sin(a) * 0.2 * w * 0.84, 0.4)))
        bot.append(bm.verts.new((math.cos(a) * 0.212 * w, math.sin(a) * 0.212 * w * 0.84, 0.37)))
    for k in range(seg2):
        bm.faces.new((top[k], top[(k + 1) % seg2], bot[(k + 1) % seg2], bot[k]))
    frill = C.new_object("Petticoat", bm, M["white"])
    C.solidify(frill, 0.005)
    C.weight_by_bones(frill, arm, ["hips", "thigh.L", "thigh.R"], power=3.0, keep=3)
    parts += [skirt, frill]

    # Puffed short sleeves with a blue cuff band; ice claws on both hands.
    for s in ("L", "R"):
        a, b = P(f"upper_arm.{s}", 0.0), P(f"upper_arm.{s}", 1.0)
        d = (b - a).normalized()
        pts = [a - d * 0.012, a + d * 0.03, a + d * 0.07, a + d * 0.1]
        sleeve = C.tube(f"Sleeve.{s}", pts, [0.028, 0.044, 0.04, 0.026], 14, M["white"])
        C.rigid(sleeve, f"upper_arm.{s}")
        cuff = C.tube(f"Cuff.{s}", [a + d * 0.09, a + d * 0.105], [0.029, 0.029], 14, M["blue"])
        C.rigid(cuff, f"upper_arm.{s}")
        parts += [sleeve, cuff]
        h0, h1 = P(f"hand.{s}", 0.0), P(f"hand.{s}", 1.0)
        hd = (h1 - h0).normalized()
        sx = 1.0 if s == "L" else -1.0
        for k, (spread, ln) in enumerate(((-0.35, 0.07), (0.0, 0.085), (0.35, 0.07))):
            base = h0.lerp(h1, 0.75) + Vector((0, -0.012, 0)) + Vector((spread * 0.03 * sx, spread * -0.02, 0))
            dd = (hd + Vector((0, -0.25 + abs(spread) * 0.2, 0)) + Vector((spread * 0.4 * sx, 0, 0))).normalized()
            claw = crystal(f"Claw.{s}", base, dd, ln, 0.009, 0.005, Vector((0, -1, 0)), ice, mid=0.25, sides=4)
            C.rigid(claw, f"hand.{s}")
            parts.append(claw)
    return parts


body = build_body()
parts = [body] + build_head() + build_outfit()
cirno = C.join(parts, "Cirno")
mod = cirno.modifiers.new("Armature", "ARMATURE")
mod.object = arm
cirno.parent = arm

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


H = 0.35  # hover height of the hips above the standing rest pose (m)

# Hover rest: arms loose and slightly out, clawed hands forward, legs dangling
# with toes pointed.
REST = {
    "hips@loc": (0, H, 0),
    "upper_arm.L": (8, 0, 16), "upper_arm.R": (8, 0, -16),
    "forearm.L": (25, 0, 0), "forearm.R": (25, 0, 0),
    "hand.L": (10, 0, 0), "hand.R": (10, 0, 0),
    "thigh.L": (22, 0, 4), "thigh.R": (8, 0, -4),
    "shin.L": (-38, 0, 0), "shin.R": (-22, 0, 0),
    "foot.L": (-35, 0, 0), "foot.R": (-35, 0, 0),
    "head": (6, 0, 0),
}


def with_rest(p):
    out = dict(REST)
    out.update(p)
    return out


def up(dy, fwd=0.0):
    return (0, H + dy, fwd)


# Idle: 60-frame hover bob, the legs trail the bob slightly.
action("idle", 60, {
    0: with_rest({}),
    15: with_rest({"hips@loc": up(0.03), "chest": (-2, 0, 0), "thigh.L": (18, 0, 4), "shin.L": (-32, 0, 0), "thigh.R": (5, 0, -4), "shin.R": (-18, 0, 0), "upper_arm.L": (6, 0, 20), "upper_arm.R": (6, 0, -20)}),
    30: with_rest({"hips@loc": up(0.045), "chest": (-3, 0, 0), "head": (3, 0, 0), "thigh.L": (20, 0, 4), "shin.L": (-40, 0, 0), "thigh.R": (6, 0, -4), "shin.R": (-26, 0, 0)}),
    45: with_rest({"hips@loc": up(0.015), "chest": (0, 0, 0), "thigh.L": (25, 0, 4), "shin.L": (-44, 0, 0), "thigh.R": (10, 0, -4), "shin.R": (-28, 0, 0), "upper_arm.L": (10, 0, 13), "upper_arm.R": (10, 0, -13)}),
    60: with_rest({}),
}, loop=True)


# Float move: 20-frame glide loop, whole body pitched forward, legs trailing.
def glide(dy, sway):
    return {
        "hips@loc": up(dy),
        "hips": (28, sway * 3, 0),
        "spine": (6, 0, 0),
        "chest": (4, -sway * 4, 0),
        "head": (-24, sway * 3, 0),
        "neck": (-8, 0, 0),
        "upper_arm.L": (-35, 0, 22), "upper_arm.R": (-35, 0, -22),
        "forearm.L": (30, 0, 0), "forearm.R": (30, 0, 0),
        "hand.L": (-20, 0, 0), "hand.R": (-20, 0, 0),
        "thigh.L": (-8 + sway * 6, 0, 5), "thigh.R": (-14 - sway * 6, 0, -5),
        "shin.L": (-35 - sway * 8, 0, 0), "shin.R": (-45 + sway * 8, 0, 0),
        "foot.L": (-45, 0, 0), "foot.R": (-45, 0, 0),
    }


action("float_move", 20, {0: glide(0.0, 1), 5: glide(0.025, 0), 10: glide(0.0, -1), 15: glide(0.025, 0), 20: glide(0.0, 1)}, loop=True)

# Swing: 24 frames. Right ice-claw sweeps right-to-left; contact at frame 10.
SW_WIND = {"hips@loc": up(0.03, -0.04), "chest": (-5, -45, 0), "spine": (0, -18, 0), "head": (5, 30, 0),
           "upper_arm.R": (-35, 0, -85), "forearm.R": (45, 0, 0), "hand.R": (-35, 0, 0),
           "upper_arm.L": (40, 0, 30), "forearm.L": (60, 0, 0),
           "thigh.L": (35, 0, 6), "shin.L": (-70, 0, 0), "thigh.R": (0, 0, -8), "shin.R": (-30, 0, 0), "foot.L": (-35, 0, 0), "foot.R": (-35, 0, 0)}
SW_HIT = {"hips@loc": up(0.0, 0.14), "hips": (10, 0, 0), "chest": (8, 40, 0), "spine": (5, 16, 0), "head": (0, -20, 0),
          "upper_arm.R": (85, 0, 25), "forearm.R": (8, 0, 0), "hand.R": (-15, 0, 0),
          "upper_arm.L": (-25, 0, 35), "forearm.L": (40, 0, 0),
          "thigh.L": (-5, 0, 6), "shin.L": (-40, 0, 0), "thigh.R": (30, 0, -6), "shin.R": (-50, 0, 0), "foot.L": (-40, 0, 0), "foot.R": (-35, 0, 0)}
action("swing", 24, {0: with_rest({}), 6: SW_WIND, 10: SW_HIT, 14: {**SW_HIT, "chest": (8, 50, 0), "upper_arm.R": (75, 0, 40)}, 24: with_rest({})})

# Dash: 15 frames. Coil, then lunge head-first with claws forward (frames 5-10).
DASH_COIL = {"hips@loc": up(0.04, -0.06), "hips": (-8, 0, 0), "spine": (18, 0, 0), "chest": (15, 0, 0), "head": (-5, 0, 0),
             "upper_arm.L": (-40, 0, 25), "upper_arm.R": (-40, 0, -25), "forearm.L": (60, 0, 0), "forearm.R": (60, 0, 0),
             "thigh.L": (65, 0, 5), "thigh.R": (60, 0, -5), "shin.L": (-110, 0, 0), "shin.R": (-105, 0, 0), "foot.L": (-40, 0, 0), "foot.R": (-40, 0, 0)}
DASH_LUNGE = {"hips@loc": up(-0.02, 0.2), "hips": (50, 0, 0), "spine": (5, 0, 0), "chest": (0, 0, 0), "neck": (-15, 0, 0), "head": (-35, 0, 0),
              "upper_arm.L": (110, 0, 12), "upper_arm.R": (110, 0, -12), "forearm.L": (15, 0, 0), "forearm.R": (15, 0, 0), "hand.L": (-25, 0, 0), "hand.R": (-25, 0, 0),
              "thigh.L": (-10, 0, 6), "thigh.R": (-18, 0, -6), "shin.L": (-25, 0, 0), "shin.R": (-35, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0)}
action("dash", 15, {0: with_rest({}), 4: DASH_COIL, 6: DASH_LUNGE, 10: {**DASH_LUNGE, "hips@loc": up(-0.01, 0.24)}, 15: with_rest({})})

# Cast: 12 frames. Right hand winds back and flings a bullet; release at frame 6.
action("cast", 12, {
    0: with_rest({}),
    4: with_rest({"chest": (-4, -30, 0), "spine": (0, -10, 0), "upper_arm.R": (-50, 0, -45), "forearm.R": (90, 0, 0), "hand.R": (30, 0, 0), "upper_arm.L": (30, 0, 25)}),
    6: with_rest({"chest": (6, 22, 0), "spine": (2, 8, 0), "upper_arm.R": (95, 0, -10), "forearm.R": (5, 0, 0), "hand.R": (-20, 0, 0), "upper_arm.L": (-10, 0, 25), "hips@loc": up(0.0, 0.04)}),
    12: with_rest({}),
})

# Spell: 30 frames. Gather (arms crossed, knees up), then burst wide open at
# frame 16 for the spell-card declaration, hold to 24.
SPELL_OPEN = {"hips@loc": up(0.1), "spine": (-8, 0, 0), "chest": (-14, 0, 0), "neck": (-5, 0, 0), "head": (-12, 0, 0),
              "upper_arm.L": (35, 0, 88), "upper_arm.R": (35, 0, -88), "forearm.L": (8, 0, 0), "forearm.R": (8, 0, 0), "hand.L": (-25, 0, 0), "hand.R": (-25, 0, 0),
              "thigh.L": (12, 0, 14), "thigh.R": (6, 0, -14), "shin.L": (-25, 0, 0), "shin.R": (-20, 0, 0), "foot.L": (-45, 0, 0), "foot.R": (-45, 0, 0)}
action("spell", 30, {
    0: with_rest({}),
    10: {"hips@loc": up(0.0), "spine": (18, 0, 0), "chest": (12, 0, 0), "head": (18, 0, 0),
         "upper_arm.L": (75, 0, -12), "upper_arm.R": (75, 0, 12), "forearm.L": (95, 0, 0), "forearm.R": (95, 0, 0),
         "thigh.L": (70, 0, 3), "thigh.R": (65, 0, -3), "shin.L": (-110, 0, 0), "shin.R": (-105, 0, 0), "foot.L": (-40, 0, 0), "foot.R": (-40, 0, 0)},
    16: SPELL_OPEN,
    24: {**SPELL_OPEN, "chest": (-10, 0, 0), "upper_arm.L": (40, 0, 84), "upper_arm.R": (40, 0, -84)},
    30: with_rest({}),
})

# Hurt: 10 frames. Knocked back in the air, arms flung.
action("hurt", 10, {
    0: with_rest({}),
    2: with_rest({"hips@loc": up(0.05, -0.1), "hips": (-12, 0, 0), "spine": (-15, 0, 0), "chest": (-15, 0, 0), "head": (-25, 0, 0),
                  "upper_arm.L": (25, 0, 50), "upper_arm.R": (25, 0, -50), "forearm.L": (50, 0, 0), "forearm.R": (50, 0, 0),
                  "thigh.L": (40, 0, 6), "thigh.R": (30, 0, -6), "shin.L": (-60, 0, 0), "shin.R": (-50, 0, 0)}),
    10: with_rest({}),
})

# Death: 40 frames. Jolt, the hover gives out, she drops to her knees on the
# ground by frame 24 and slumps into a crumpled heap.
KNEEL = {"hips@loc": (0, -0.3, -0.02), "hips": (-5, 0, 0), "spine": (30, 0, 0), "chest": (15, 0, 0), "head": (30, 0, 0),
         "thigh.L": (18, 0, 6), "thigh.R": (12, 0, -6), "shin.L": (-110, 0, 0), "shin.R": (-105, 0, 0), "foot.L": (-60, 0, 0), "foot.R": (-60, 0, 0),
         "upper_arm.L": (30, 0, 14), "upper_arm.R": (30, 0, -14), "forearm.L": (30, 0, 0), "forearm.R": (30, 0, 0)}
HEAP = {"hips@loc": (0.03, -0.36, 0.02), "hips": (-5, 0, -12), "spine": (40, 0, 10), "chest": (35, 10, 8), "neck": (15, 0, 0), "head": (30, 25, 15),
        "thigh.L": (70, 0, 20), "thigh.R": (80, 0, -10), "shin.L": (-155, 0, 0), "shin.R": (-150, 0, 0), "foot.L": (-65, 0, 0), "foot.R": (-65, 0, 0),
        "upper_arm.L": (25, 0, 10), "upper_arm.R": (45, 0, -25), "forearm.L": (40, 0, 0), "forearm.R": (60, 0, 0), "hand.L": (10, 0, 0), "hand.R": (20, 0, 0)}
action("death", 40, {
    0: with_rest({}),
    5: with_rest({"hips@loc": up(0.06, -0.05), "spine": (-18, 0, 0), "chest": (-20, 0, 0), "head": (-30, 0, 0),
                  "upper_arm.L": (20, 0, 55), "upper_arm.R": (20, 0, -55), "forearm.L": (10, 0, 0), "forearm.R": (10, 0, 0)}),
    14: with_rest({"hips@loc": up(-0.12), "spine": (10, 0, 0), "head": (15, 0, 0), "upper_arm.L": (-20, 0, 40), "upper_arm.R": (-20, 0, -40),
                   "thigh.L": (10, 0, 4), "thigh.R": (5, 0, -4), "shin.L": (-40, 0, 0), "shin.R": (-35, 0, 0)}),
    22: KNEEL,
    32: {**HEAP, "head": (25, 20, 12), "hips@loc": (0.03, -0.35, 0.02)},
    40: HEAP,
})

# Phase 2: 30 frames. Curl up, then a rage roar with arms and wings flung
# back at frame 14, hold with a tremble, settle by 30.
ROAR = {"hips@loc": up(0.12), "hips": (0, 0, 0), "spine": (-6, 0, 0), "chest": (-14, 0, 0), "neck": (0, 0, 0), "head": (2, 0, 0),
        "upper_arm.L": (-25, 0, 65), "upper_arm.R": (-25, 0, -65), "forearm.L": (35, 0, 0), "forearm.R": (35, 0, 0), "hand.L": (-30, 0, 0), "hand.R": (-30, 0, 0),
        "thigh.L": (-10, 0, 14), "thigh.R": (-10, 0, -14), "shin.L": (-30, 0, 0), "shin.R": (-30, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0)}
action("phase2", 30, {
    0: with_rest({}),
    7: {"hips@loc": up(-0.03), "hips": (5, 0, 0), "spine": (25, 0, 0), "chest": (20, 0, 0), "head": (20, 0, 0),
        "upper_arm.L": (45, 0, -8), "upper_arm.R": (45, 0, 8), "forearm.L": (125, 0, 0), "forearm.R": (125, 0, 0),
        "thigh.L": (75, 0, 4), "thigh.R": (70, 0, -4), "shin.L": (-120, 0, 0), "shin.R": (-115, 0, 0), "foot.L": (-40, 0, 0), "foot.R": (-40, 0, 0)},
    14: ROAR,
    18: {**ROAR, "chest": (-19, 3, 0), "head": (-25, -4, 0)},
    22: {**ROAR, "chest": (-24, -3, 0), "head": (-20, 4, 0)},
    30: with_rest({}),
})

arm.animation_data.action = bpy.data.actions["idle"]
C.export_glb("assets/models/characters/cirno/cirno.glb", [arm, cirno])
print("tris:", sum(len(p.vertices) - 2 for p in cirno.data.polygons))
bb = [cirno.matrix_world @ v.co for v in cirno.data.vertices]
print("height: %.3f" % (max(v.z for v in bb) - min(v.z for v in bb)))
