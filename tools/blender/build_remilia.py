"""Remilia Scarlet, the Scarlet Devil: in-house stylised model, rig and boss animations.

Output: assets/models/characters/remilia/remilia.glb

Same conventions as build_reimu.py / build_cirno.py, scaled to a ~1.3 m child
vampire (mob cap included).
Blender axes: Z up, the character faces -Y, her left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
The bat wings follow the same rule: wing.X / wing_tip.X swing forward (wrap)
with +X and back (fold) with -X; +Z raises the left wing, -Z the right.
She is a hovering boss: every action lifts her off the ground through hips@loc
(local Y of the hips bone is world up, local Z is forward).

Spear the Gungnir is exported as its own mesh node ("Gungnir"), skinned
rigidly to hand.R, so the game can show it only while it is summoned.
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
    "skin": C.material("RemiliaSkin", (0.97, 0.89, 0.88), 0.6),
    "hair": C.material("RemiliaHair", (0.60, 0.64, 0.86), 0.45),
    "pink": C.material("RemiliaDress", (0.95, 0.74, 0.80), 0.65),
    "pink_dark": C.material("RemiliaDressShade", (0.84, 0.56, 0.64), 0.7),
    "red": C.material("ScarletTrim", (0.60, 0.04, 0.10), 0.5),  # scarlet gone the colour of old wine
    "cap": C.material("MobCap", (0.97, 0.95, 0.97), 0.75),
    "shoe": C.material("RemiliaShoe", (0.38, 0.04, 0.08), 0.4),
    "membrane": C.material("WingMembrane", (0.16, 0.07, 0.15), 0.6),
    "wingbone": C.material("WingBone", (0.07, 0.04, 0.08), 0.5),
    "eye_white": C.material("RemiliaEyeWhite", (0.98, 0.96, 0.96), 0.3),
    "iris": C.material("RemiliaIris", (0.86, 0.05, 0.08), 0.2, emission=0.6),
    "pupil": C.material("RemiliaPupil", (0.22, 0.0, 0.03), 0.3),
    "shine": C.material("RemiliaEyeShine", (1.0, 1.0, 1.0), 0.1, emission=1.0),
    "line": C.material("RemiliaLine", (0.16, 0.06, 0.12), 0.6),
    "fang": C.material("RemiliaFang", (0.98, 0.97, 0.97), 0.3),
    "nail": C.material("RemiliaNail", (0.42, 0.03, 0.08), 0.35),
    "porcelain": C.material("Porcelain", (0.95, 0.94, 0.92), 0.25),
    "gold": C.material("RemiliaGold", (0.85, 0.66, 0.28), 0.3, 0.8),
    "tea": C.material("ColdTea", (0.30, 0.06, 0.08), 0.1),
    "gungnir": C.material("Gungnir", (0.85, 0.02, 0.06), 0.2, emission=1.6),
    "gungnir_core": C.material("GungnirCore", (1.0, 0.35, 0.30), 0.2, emission=2.0),
    "gungnir_glow": C.material("GungnirGlow", (0.9, 0.02, 0.06), 0.3, emission=1.0),
}
glow = M["gungnir_glow"]
glow.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.35
glow.blend_method = "BLEND"
if hasattr(glow, "surface_render_method"):
    glow.surface_render_method = "BLENDED"

# ---------------------------------------------------------------- skeleton
WING_ROOT = Vector((0.045, 0.10, 0.84))
WING_ELBOW = Vector((0.24, 0.165, 0.99))
WING_TIP = Vector((0.46, 0.225, 0.90))

BONES = [
    # name, head, tail, parent
    ("root", (0, 0, 0), (0, 0, 0.12), None),
    ("hips", (0, 0, 0.58), (0, 0, 0.66), "root"),
    ("spine", (0, 0, 0.66), (0, 0, 0.76), "hips"),
    ("chest", (0, 0, 0.76), (0, 0, 0.88), "spine"),
    ("neck", (0, 0, 0.88), (0, 0, 0.94), "chest"),
    ("head", (0, 0, 0.94), (0, 0, 1.18), "neck"),
]


def mx(v, sx):
    return Vector((v[0] * sx, v[1], v[2]))


for s, sx in (("L", 1.0), ("R", -1.0)):
    BONES += [
        (f"shoulder.{s}", (sx * 0.02, 0, 0.855), (sx * 0.095, 0, 0.855), "chest"),
        (f"upper_arm.{s}", (sx * 0.10, 0, 0.85), (sx * 0.15, 0.0, 0.69), f"shoulder.{s}"),
        (f"forearm.{s}", (sx * 0.15, 0, 0.69), (sx * 0.185, -0.02, 0.545), f"upper_arm.{s}"),
        (f"hand.{s}", (sx * 0.185, -0.02, 0.545), (sx * 0.197, -0.03, 0.475), f"forearm.{s}"),
        (f"thigh.{s}", (sx * 0.062, 0, 0.60), (sx * 0.066, 0, 0.33), "hips"),
        (f"shin.{s}", (sx * 0.066, 0, 0.33), (sx * 0.066, 0.01, 0.065), f"thigh.{s}"),
        (f"foot.{s}", (sx * 0.066, 0.01, 0.065), (sx * 0.066, -0.075, 0.018), f"shin.{s}"),
        (f"wing.{s}", tuple(mx(WING_ROOT, sx)), tuple(mx(WING_ELBOW, sx)), "chest"),
        (f"wing_tip.{s}", tuple(mx(WING_ELBOW, sx)), tuple(mx(WING_TIP, sx)), f"wing.{s}"),
    ]

arm_data = bpy.data.armatures.new("RemiliaRig")
arm = bpy.data.objects.new("RemiliaRig", arm_data)
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

BODY_BONES = [b[0] for b in BONES if b[0] != "root" and not b[0].startswith("wing")]


def P(name, t):
    b = arm.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


def spike(name, base, direction, length, width, thick, normal=Vector((0, 1, 0)), mat=None, mid=0.32, sides=6):
    """Faceted spike: flattened bipyramid from base along direction."""
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


def ring_strip(name, z_top, z_bot, r_top, r_bot, mat, seg=48, squash=0.84, wave=0.0, waves=10, center=(0, 0, 0), thick=0.005):
    """Open band between two elliptic rings (sash, hem trims, frills)."""
    bm = bmesh.new()
    top, bot = [], []
    cx, cy, _ = center
    for k in range(seg):
        a = 2 * math.pi * k / seg
        w = 1.0 + wave * math.sin(a * waves)
        top.append(bm.verts.new((cx + math.cos(a) * r_top * w, cy + math.sin(a) * r_top * w * squash, z_top)))
        bot.append(bm.verts.new((cx + math.cos(a) * r_bot * w, cy + math.sin(a) * r_bot * w * squash, z_bot)))
    for k in range(seg):
        bm.faces.new((top[k], top[(k + 1) % seg], bot[(k + 1) % seg], bot[k]))
    obj = C.new_object(name, bm, mat)
    C.solidify(obj, thick)
    return obj


# ---------------------------------------------------------------- body (skin modifier)
def build_body():
    verts, edges, radii = [], [], []

    def v(co, r):
        verts.append(co)
        radii.append(r)
        return len(verts) - 1

    pelvis = v((0, 0, 0.585), (0.08, 0.062))
    waist = v((0, 0, 0.68), (0.055, 0.045))
    chest = v((0, 0, 0.78), (0.064, 0.05))
    upper = v((0, 0, 0.845), (0.064, 0.047))
    neck_b = v((0, 0, 0.89), (0.027, 0.027))
    neck_t = v((0, 0, 0.965), (0.025, 0.025))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
    for sx in (1.0, -1.0):
        sh = v((sx * 0.098, 0, 0.848), (0.029, 0.029))
        el = v((sx * 0.15, 0, 0.69), (0.021, 0.021))
        wr = v((sx * 0.185, -0.02, 0.545), (0.016, 0.016))
        hd = v((sx * 0.195, -0.028, 0.49), (0.023, 0.016))
        hip = v((sx * 0.062, 0, 0.575), (0.049, 0.049))
        kn = v((sx * 0.066, 0, 0.33), (0.032, 0.032))
        an = v((sx * 0.066, 0.01, 0.07), (0.025, 0.025))
        toe = v((sx * 0.066, -0.07, 0.03), (0.03, 0.026))
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

    # Regions: red shoes, bare legs, pink dress bodice, skin arms, neck.
    order = ("shoe", "skin", "pink")
    for key in order:
        obj.data.materials.append(M[key])
    idx = {k: i for i, k in enumerate(order)}
    for poly in obj.data.polygons:
        c = poly.center
        if abs(c.x) > 0.105 or (abs(c.x) > 0.085 and c.z > 0.8):  # arms
            key = "skin"
        elif c.z > 0.875:
            key = "skin"
        elif c.z < 0.085:
            key = "shoe"
        elif c.z < 0.55:
            key = "skin"
        else:
            key = "pink"
        poly.material_index = idx[key]
        poly.use_smooth = True
    C.weight_by_bones(obj, arm, BODY_BONES, power=4.0)
    return obj


# ---------------------------------------------------------------- head
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

    # Red eyes with narrow vampire pupils; calm, slightly lidded, brows raised.
    for sx in (1.0, -1.0):
        base = Vector((sx * 0.043, -0.108, 1.036))
        turn = Matrix.Rotation(math.radians(-20 * sx), 4, "Z")
        for mat, size, off, lift, dx in (
            (M["eye_white"], (0.03, 0.03), 0.0, 0.0, 0.0),
            (M["iris"], (0.022, 0.027), -0.003, -0.003, 0.0),
            (M["pupil"], (0.005, 0.018), -0.005, -0.003, 0.0),
            (M["shine"], (0.006, 0.007), -0.007, 0.009, sx * 0.007),
        ):
            bm = bmesh.new()
            bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=1.0)
            m = Matrix.Translation(base + Vector((dx, off, lift))) @ turn @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Diagonal((size[0], size[1], 1, 1))
            bm.transform(m)
            parts.append(C.new_object("Eye", bm, mat, smooth=False))
        # Heavy upper lid (half-lidded, bored aristocrat) and a high, thin brow.
        parts.append(C.box("Lid", (0.042, 0.006, 0.006), (sx * 0.044, -0.11, 1.062), M["line"], (0, 6 * sx, -20 * sx)))
        parts.append(C.box("Lash", (0.008, 0.005, 0.004), (sx * 0.068, -0.103, 1.064), M["line"], (0, 30 * sx, -30 * sx)))
        parts.append(C.box("Brow", (0.03, 0.005, 0.0045), (sx * 0.046, -0.106, 1.094), M["line"], (0, 10 * sx, -20 * sx)))
    # A small knowing smirk, one fang.
    parts.append(C.box("Mouth", (0.02, 0.004, 0.003), (0.002, -0.098, 0.984), M["line"], (0, -8, 0)))
    parts.append(spike("Fang", (-0.006, -0.099, 0.983), (0, -0.2, -1), 0.012, 0.004, 0.002, Vector((0, -1, 0)), M["fang"], mid=0.1, sides=4))

    # Hair cap, open at the face.
    cap = C.uv_sphere("HairCap", 0.131, (0, 0.008, 1.062), (1.05, 1.0, 1.03), 32, 16, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = [v for v in bm.verts if v.co.y < -0.065 and v.co.z < 1.105]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.006)
    parts.append(cap)

    # Soft wavy bangs, parted slightly off-centre.
    for i in range(7):
        x = -0.086 + i * 0.0287
        top = Vector((x * 0.8, -0.088, 1.165))
        drop = 0.012 if i % 2 else 0.0
        bottom = Vector((x * 1.1 + (0.01 if x > 0 else -0.01), -0.117 + abs(x) * 0.2, 1.078 + abs(x) * 0.22 - drop))
        mid = top.lerp(bottom, 0.5) + Vector((0.012 * (1 if i % 2 else -1), -0.015, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.022, 0.017, 0.002], 8, M["hair"], (1.0, 0.45)))

    # Wavy side locks to the jaw, curling inward at the tips.
    for sx in (1.0, -1.0):
        for dz, fy in ((0.0, 0.0), (0.02, 0.04)):
            pts = [Vector((sx * 0.112, -0.03 + fy, 1.1 + dz)), Vector((sx * 0.128, -0.05 + fy, 1.03 + dz)),
                   Vector((sx * 0.118, -0.055 + fy, 0.975 + dz)), Vector((sx * 0.098, -0.07 + fy, 0.945 + dz))]
            parts.append(C.tube("Sidelock", pts, [0.027, 0.022, 0.016, 0.002], 8, M["hair"], (1.0, 0.5)))

    # Short back with outward-flicking wavy tips at the nape.
    back = [Vector((0, 0.07, 1.1)), Vector((0, 0.105, 1.01)), Vector((0, 0.095, 0.955))]
    parts.append(C.tube("BackHair", back, [0.127, 0.122, 0.092], 16, M["hair"], (1.0, 0.45)))
    for i in range(7):
        x = -0.1 + i * 0.0333
        flick = 1.3 if abs(x) > 0.06 else 1.12
        parts.append(C.tube("HairTip", [Vector((x, 0.1, 0.99)), Vector((x * 1.05, 0.118, 0.95)), Vector((x * flick, 0.112 + abs(x) * 0.25, 0.912 - (i % 2) * 0.02))],
                           [0.026, 0.02, 0.002], 8, M["hair"], (1.0, 0.5)))

    # White mob cap: puffed crown, ruffled brim, red ribbon band and side bow.
    CAPC = Vector((0, 0.018, 1.165))
    tilt = Matrix.Translation(CAPC) @ Matrix.Rotation(math.radians(-12), 4, "X")
    crown = C.uv_sphere("CapCrown", 1.0, (0, 0, 0), (0.148, 0.142, 0.092), 28, 12, M["cap"])
    for v in crown.data.vertices:
        # soft gathered folds on the crown
        a = math.atan2(v.co.y, v.co.x)
        v.co.x *= 1.0 + 0.04 * math.sin(a * 8)
        v.co.y *= 1.0 + 0.04 * math.sin(a * 8)
    C.transform(crown, tilt @ Matrix.Translation((0, 0, 0.02)))
    brim = ring_strip("CapBrim", 0.0, -0.022, 0.138, 0.172, M["cap"], seg=64, squash=0.97, wave=0.05, waves=16, thick=0.006)
    C.transform(brim, tilt)
    band = ring_strip("CapBand", 0.018, -0.002, 0.146, 0.146, M["red"], seg=40, squash=0.97, thick=0.008)
    C.transform(band, tilt)
    parts += [crown, brim, band]
    bow_at = tilt @ Vector((0.105, -0.1, 0.012))
    for k in (1.0, -1.0):
        lobe = C.uv_sphere("CapBowLobe", 1.0, (0, 0, 0), (0.034, 0.012, 0.022), 14, 7, M["red"])
        C.transform(lobe, Matrix.Translation(bow_at + Vector((k * 0.027, -0.008 * k, 0.004))) @ Matrix.Rotation(math.radians(-40), 4, "Z") @ Matrix.Rotation(math.radians(k * -18), 4, "Y"))
        parts.append(lobe)
    parts.append(C.uv_sphere("CapBowKnot", 0.012, tuple(bow_at + Vector((0, -0.004, 0))), (1, 0.8, 1), 10, 5, M["red"]))
    for k in (1.0, -1.0):
        parts.append(C.tube("CapBowTail", [bow_at, bow_at + Vector((0.01 + k * 0.012, -0.004, -0.035)), bow_at + Vector((0.018 + k * 0.02, 0.0, -0.06))],
                           [0.009, 0.011, 0.013], 8, M["red"], (1.0, 0.3)))

    for p in parts:
        C.rigid(p, "head")
    return parts


# ---------------------------------------------------------------- wings
def quad_curve(a, q, b, s):
    return a * (1 - s) ** 2 + q * 2 * s * (1 - s) + b * s * s


def build_wing(sx):
    """Bat wing: a scalloped membrane fanned from the wrist, with finger spars.
    One scallop is torn (the hollowing)."""
    R = mx(WING_ROOT, sx)
    E = mx(WING_ELBOW, sx)
    B = mx((0.045, 0.105, 0.735), sx)
    F = [mx(p, sx) for p in ((0.53, 0.225, 1.09), (0.585, 0.25, 0.87), (0.47, 0.245, 0.67), (0.27, 0.19, 0.575))]
    bone_w = "wing." + ("L" if sx > 0 else "R")
    tip_w = "wing_tip." + ("L" if sx > 0 else "R")

    # Boundary loop: root -> wrist -> top tip -> scallops between fingers -> body.
    loop = []
    for t in (0.0, 0.33, 0.66):
        loop.append(R.lerp(E, t))
    for t in (0.0, 0.33, 0.66):
        loop.append(E.lerp(F[0], t))
    chain = F + [B]
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        q = a.lerp(b, 0.5).lerp(E if i < 3 else R.lerp(E, 0.5), 0.42)
        loop.append(a)
        if i == 1:  # torn scallop: a ragged notch bitten into the membrane
            for s, pull in ((0.18, 0.0), (0.3, 0.0), (0.36, 0.22), (0.44, 0.05), (0.52, 0.16), (0.6, 0.0), (0.8, 0.0)):
                p = quad_curve(a, q, b, s)
                loop.append(p.lerp(E, pull))
        elif i == 2:
            for s, pull in ((0.25, 0.0), (0.45, 0.0), (0.55, 0.08), (0.62, 0.0), (0.8, 0.0)):
                p = quad_curve(a, q, b, s)
                loop.append(p.lerp(E, pull))
        else:
            for s in (0.25, 0.5, 0.75):
                loop.append(quad_curve(a, q, b, s))
    loop.append(B)
    loop.append(B.lerp(R, 0.5))

    centroid = sum(loop, Vector()) / len(loop)
    Cn = E.lerp(centroid, 0.55)
    bm = bmesh.new()
    cv = bm.verts.new(Cn)
    rings = []
    for t in (0.34, 0.67, 1.0):
        rings.append([bm.verts.new(Cn.lerp(p, t)) for p in loop])
    n = len(loop)
    for k in range(n):
        bm.faces.new((cv, rings[0][k], rings[0][(k + 1) % n]))
    for r in range(2):
        for k in range(n):
            bm.faces.new((rings[r][k], rings[r + 1][k], rings[r + 1][(k + 1) % n], rings[r][(k + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mem = C.new_object("WingMembrane", bm, M["membrane"])
    C.solidify(mem, 0.005)

    parts = [mem]
    # Leading-edge arm and finger spars.
    parts.append(C.tube("WingArm", [mx((0.018, 0.045, 0.83), sx), R, R.lerp(E, 0.5), E], [0.012, 0.013, 0.011, 0.012], 8, M["wingbone"]))
    parts.append(C.tube("WingFinger", [E, E.lerp(F[0], 0.5), F[0]], [0.01, 0.007, 0.002], 6, M["wingbone"]))
    for f in F[1:]:
        parts.append(C.tube("WingFinger", [E, E.lerp(f, 0.5), f], [0.008, 0.005, 0.0015], 6, M["wingbone"]))
    parts.append(spike("WingThumb", E, mx((0.25, -0.15, 1.0), sx), 0.045, 0.008, 0.006, Vector((0, -1, 0)), M["wingbone"], mid=0.25, sides=4))
    wing = C.join(parts, "Wing")
    C.weight_by_bones(wing, arm, ["chest", bone_w, tip_w], power=3.0, keep=2)
    return wing


# ---------------------------------------------------------------- outfit
def build_outfit():
    parts = []
    # Rounded pink collar with a red ribbon tie and brooch.
    collar = C.tube("Collar", [Vector((0, 0.0, 0.885)), Vector((0, 0.002, 0.86))], [0.035, 0.082], 24, M["pink_dark"])
    parts.append(collar)
    parts.append(C.uv_sphere("Brooch", 0.012, (0, -0.066, 0.852), (1.0, 0.6, 1.0), 12, 6, M["red"]))
    for sx in (1.0, -1.0):
        parts.append(C.tube("TieLoop", [Vector((0, -0.068, 0.855)), Vector((sx * 0.032, -0.064, 0.866)), Vector((sx * 0.046, -0.056, 0.85))], [0.008, 0.019, 0.006], 8, M["red"], (1.0, 0.35)))
        parts.append(C.tube("TieTail", [Vector((sx * 0.004, -0.066, 0.848)), Vector((sx * 0.014, -0.064, 0.8))], [0.01, 0.014], 8, M["red"], (1.0, 0.3)))
    # Red trim line down the bodice front.
    parts.append(C.box("BodiceTrim", (0.012, 0.004, 0.08), (0, -0.05, 0.765), M["red"], (-8, 0, 0)))
    for p in parts:
        C.rigid(p, "chest")

    # Knee-length flared skirt, soft pleats, red hem trim and a frill.
    bm = bmesh.new()
    seg, rings = 40, 7
    grid = []
    for r in range(rings + 1):
        t = r / rings
        z = 0.69 - t * 0.335
        rad = 0.064 + (0.212 - 0.064) * (t ** 0.8)
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            pleat = 1.0 + 0.06 * t * math.sin(a * 10)
            ring.append(bm.verts.new((math.cos(a) * rad * pleat, math.sin(a) * rad * pleat * 0.84, z)))
        grid.append(ring)
    for r in range(rings):
        for k in range(seg):
            bm.faces.new((grid[r][k], grid[r][(k + 1) % seg], grid[r + 1][(k + 1) % seg], grid[r + 1][k]))
    skirt = C.new_object("Skirt", bm, M["pink"])
    C.solidify(skirt, 0.007)
    trim = ring_strip("HemTrim", 0.385, 0.358, 0.197, 0.215, M["red"], seg=80, wave=0.06, waves=10, thick=0.006)
    frill = ring_strip("HemFrill", 0.36, 0.33, 0.212, 0.226, M["pink_dark"], seg=80, wave=0.07, waves=40, thick=0.005)
    for p in (skirt, trim, frill):
        C.weight_by_bones(p, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
        parts.append(p)

    # Red waist sash with a big bow at the back.
    sash = ring_strip("Sash", 0.708, 0.668, 0.07, 0.075, M["red"], seg=32, squash=0.84, thick=0.007)
    C.weight_by_bones(sash, arm, ["hips", "spine"], power=3.0, keep=2)
    bow = []
    for sx in (1.0, -1.0):
        lobe = C.uv_sphere("SashLobe", 1.0, (0, 0, 0), (0.058, 0.02, 0.04), 18, 9, M["red"])
        C.transform(lobe, Matrix.Translation((sx * 0.062, 0.088, 0.698)) @ Matrix.Rotation(math.radians(sx * 18), 4, "Y") @ Matrix.Rotation(math.radians(sx * 14), 4, "Z"))
        tail = C.tube("SashTail", [Vector((sx * 0.012, 0.085, 0.685)), Vector((sx * 0.04, 0.14, 0.55)), Vector((sx * 0.062, 0.185, 0.43))], [0.02, 0.026, 0.03], 10, M["red"], (1.0, 0.22))
        bow += [lobe, tail]
    bow.append(C.uv_sphere("SashKnot", 0.022, (0, 0.082, 0.69), (1.0, 0.8, 1.1), 14, 7, M["red"]))
    for p in bow:
        C.rigid(p, "hips")
    parts += [sash] + bow

    # The hollowed touch: a cracked porcelain teacup charm hanging from the sash.
    cup_parts = []
    top = Vector((0.052, -0.066, 0.672))
    cup = Vector((0.06, -0.094, 0.608))
    cup_parts.append(C.tube("CharmChain", [top, top.lerp(cup, 0.5) + Vector((0, -0.006, 0)), cup + Vector((0, 0, 0.022))], [0.0025, 0.0025, 0.0025], 5, M["gold"]))
    cup_parts.append(C.tube("Teacup", [cup + Vector((0, 0, -0.012)), cup + Vector((0, 0, 0.004)), cup + Vector((0, 0, 0.016))], [0.013, 0.019, 0.022], 14, M["porcelain"]))
    cup_parts.append(C.tube("CupRim", [cup + Vector((0, 0, 0.0155)), cup + Vector((0, 0, 0.0175))], [0.0225, 0.0225], 14, M["gold"]))
    cup_parts.append(C.tube("CupTea", [cup + Vector((0, 0, 0.012)), cup + Vector((0, 0, 0.0178))], [0.018, 0.018], 12, M["tea"]))
    cup_parts.append(C.tube("CupHandle", [cup + Vector((0.018, 0, 0.01)), cup + Vector((0.03, 0, 0.004)), cup + Vector((0.018, 0, -0.006))], [0.004, 0.004, 0.004], 5, M["porcelain"]))
    # Crack: a jagged dark seam down the front, and a chip out of the rim.
    crack = [(-0.004, 0.016), (0.001, 0.008), (-0.003, 0.002), (0.003, -0.005), (0.0, -0.011)]
    for (x0, z0), (x1, z1) in zip(crack, crack[1:]):
        a = cup + Vector((x0, -0.021, z0))
        b = cup + Vector((x1, -0.0185 if z1 < 0 else -0.0205, z1))
        cup_parts.append(C.tube("CupCrack", [a, b], [0.0015, 0.0015], 4, M["line"], cap=False))
    cup_parts.append(C.box("CupChip", (0.008, 0.008, 0.006), tuple(cup + Vector((-0.012, -0.016, 0.017))), M["tea"], (0, 0, 40)))
    for p in cup_parts:
        C.rigid(p, "hips")
    parts += cup_parts

    # Puffed short sleeves with a red ribbon cuff; small dark claws.
    for s in ("L", "R"):
        a, b = P(f"upper_arm.{s}", 0.0), P(f"upper_arm.{s}", 1.0)
        d = (b - a).normalized()
        pts = [a - d * 0.012, a + d * 0.03, a + d * 0.07, a + d * 0.1]
        sleeve = C.tube(f"Sleeve.{s}", pts, [0.028, 0.046, 0.042, 0.026], 14, M["pink"])
        cuff = C.tube(f"Cuff.{s}", [a + d * 0.09, a + d * 0.108], [0.03, 0.03], 14, M["red"])
        for p in (sleeve, cuff):
            C.rigid(p, f"upper_arm.{s}")
        parts += [sleeve, cuff]
        h0, h1 = P(f"hand.{s}", 0.0), P(f"hand.{s}", 1.0)
        hd = (h1 - h0).normalized()
        sx = 1.0 if s == "L" else -1.0
        for spread in (-0.4, 0.0, 0.4):
            base = h0.lerp(h1, 0.85) + Vector((spread * 0.022 * sx, -0.01 + abs(spread) * 0.01, 0))
            dd = (hd + Vector((spread * 0.25 * sx, -0.2, 0))).normalized()
            nail = spike(f"Nail.{s}", base, dd, 0.03, 0.005, 0.003, Vector((0, -1, 0)), M["nail"], mid=0.2, sides=4)
            C.rigid(nail, f"hand.{s}")
            parts.append(nail)
    return parts


# ---------------------------------------------------------------- Spear the Gungnir
def build_gungnir():
    """Summoned lance of scarlet light. Built in the rest pose of hand.R; the
    shaft runs along the hand's local forward axis (world -Y at rest)."""
    parts = []
    grip = P("hand.R", 0.45)
    d = Vector((0, -1.0, 0))
    butt, neck = grip - d * 0.42, grip + d * 0.95
    tip = neck + d * 0.34
    parts.append(C.tube("GungnirShaft", [butt, grip, neck], [0.01, 0.013, 0.012], 8, M["gungnir"]))
    parts.append(C.tube("GungnirCoreLine", [butt + d * 0.05, neck + d * 0.05], [0.005, 0.005], 6, M["gungnir_core"]))
    parts.append(spike("GungnirButt", butt, -d, 0.09, 0.02, 0.02, Vector((0, 0, 1)), M["gungnir"], mid=0.3, sides=6))
    # Long leaf blade with swept guard spikes.
    parts.append(spike("GungnirBlade", neck, d, 0.34, 0.042, 0.016, Vector((0, 0, 1)), M["gungnir"], mid=0.22, sides=6))
    parts.append(spike("GungnirEdge", neck + d * 0.02, d, 0.3, 0.018, 0.022, Vector((0, 0, 1)), M["gungnir_core"], mid=0.25, sides=4))
    for ang in (0, 90, 180, 270):
        side = Matrix.Rotation(math.radians(ang), 3, d) @ Vector((1, 0, 0))
        parts.append(spike("GungnirGuard", neck - d * 0.02, (side * 1.0 - d * 0.55), 0.13, 0.014, 0.006, d, M["gungnir"], mid=0.2, sides=4))
    # A thin wound spiral of light around the upper shaft.
    spiral = []
    for i in range(25):
        t = i / 24
        a = t * math.pi * 6
        spiral.append(grip.lerp(neck, t) + Vector((math.cos(a) * 0.026, 0, math.sin(a) * 0.026)))
    parts.append(C.tube("GungnirSpiral", spiral, [0.004] * len(spiral), 5, M["gungnir"]))
    # Soft glow sheath.
    parts.append(C.tube("GungnirGlow", [butt - d * 0.04, grip, neck, tip - d * 0.05], [0.02, 0.028, 0.034, 0.012], 8, M["gungnir_glow"]))
    spear = C.join(parts, "Gungnir")
    C.rigid(spear, "hand.R")
    return spear


body = build_body()
parts = [body] + build_head() + build_outfit() + [build_wing(1.0), build_wing(-1.0)]
remilia = C.join(parts, "Remilia")
gungnir = build_gungnir()
for ob in (remilia, gungnir):
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    ob.parent = arm

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


H = 0.3  # hover height of the hips above the standing rest pose (m)


def W(x, z, tx=0.0, tz=0.0, y=0.0, ty=0.0):
    """Symmetric wing pose: x swings forward(+)/back(-), z raises(+)/lowers(-)."""
    return {"wing.L": (x, y, z), "wing.R": (x, -y, -z), "wing_tip.L": (tx, ty, tz), "wing_tip.R": (tx, -ty, -tz)}


# Hover rest: poised and upright, chin slightly up; the spear hand (R) holds
# the summoned lance upright at her side, the left hand relaxed, clawed.
REST = {
    "hips@loc": (0, H, 0),
    "chest": (-3, 0, 0), "head": (-3, 0, 0),
    "upper_arm.L": (5, 0, 14), "forearm.L": (30, 0, 0), "hand.L": (15, 0, 0),
    "upper_arm.R": (12, 60, -14), "forearm.R": (45, 0, 0), "hand.R": (0, 15, 0),
    "thigh.L": (12, 0, 3), "thigh.R": (4, 0, -3),
    "shin.L": (-26, 0, 0), "shin.R": (-12, 0, 0),
    "foot.L": (-40, 0, 0), "foot.R": (-40, 0, 0),
    **W(-18, 0, -5, 0),
}


def with_rest(p):
    out = dict(REST)
    out.update(p)
    return out


def up(dy, fwd=0.0):
    return (0, H + dy, fwd)


# Idle: 60-frame hover with two slow, deep wing beats; the body rises on the downstroke.
action("idle", 60, {
    0: with_rest({**W(-18, 14, -5, 10)}),
    15: with_rest({"hips@loc": up(0.035), **W(-12, -14, 4, -12), "chest": (-4, 0, 0)}),
    30: with_rest({"hips@loc": up(0.02), **W(-18, 14, -5, 10), "thigh.L": (15, 0, 3), "shin.L": (-32, 0, 0)}),
    45: with_rest({"hips@loc": up(0.045), **W(-12, -14, 4, -12), "chest": (-4, 0, 0), "head": (-5, 0, 0)}),
    60: with_rest({**W(-18, 14, -5, 10)}),
}, loop=True)


# Fly: 20-frame loop, pitched forward, big full wing strokes, legs trailing.
def glide(dy, wz, wtz, wx):
    return {
        "hips@loc": up(dy),
        "hips": (30, 0, 0), "spine": (5, 0, 0), "chest": (3, 0, 0),
        "neck": (-8, 0, 0), "head": (-24, 0, 0),
        "upper_arm.L": (-30, 0, 18), "upper_arm.R": (-20, 0, -14),
        "forearm.L": (35, 0, 0), "forearm.R": (60, 0, 0), "hand.L": (-10, 0, 0), "hand.R": (0, 0, 0),
        "thigh.L": (-10, 0, 4), "thigh.R": (-16, 0, -4),
        "shin.L": (-40, 0, 0), "shin.R": (-50, 0, 0),
        "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
        **W(wx, wz, 0, wtz),
    }


action("fly", 20, {0: glide(0.0, 32, 20, -30), 5: glide(0.03, 0, 0, -15), 10: glide(0.05, -32, -24, -5), 15: glide(0.02, 0, 0, -20), 20: glide(0.0, 32, 20, -30)}, loop=True)

# Claw: 18 frames. Left hand rakes right-to-left across the body; contact frame 8.
CL_WIND = with_rest({"hips@loc": up(0.03, -0.04), "chest": (-6, 40, 0), "spine": (0, 15, 0), "head": (5, -25, 0),
                     "upper_arm.L": (-30, 0, 80), "forearm.L": (45, 0, 0), "hand.L": (-30, 0, 0),
                     **W(-30, 20, -10, 15)})
CL_HIT = with_rest({"hips@loc": up(0.0, 0.16), "hips": (10, 0, 0), "chest": (8, -40, 0), "spine": (5, -16, 0), "head": (0, 20, 0),
                    "upper_arm.L": (85, 0, -25), "forearm.L": (8, 0, 0), "hand.L": (-15, 0, 0),
                    "thigh.L": (25, 0, 6), "shin.L": (-50, 0, 0), "thigh.R": (-5, 0, -6), "shin.R": (-40, 0, 0),
                    **W(-5, -15, 5, -10)})
action("claw", 18, {0: with_rest({}), 5: CL_WIND, 8: CL_HIT, 11: {**CL_HIT, "chest": (8, -50, 0), "upper_arm.L": (75, 0, -40)}, 18: with_rest({})})

# Gungnir throw: 30 frames. Rise, draw the lance back overhead, hurl it at
# frame 18 with the wings snapping forward, follow through.
TH_DRAW = with_rest({"hips@loc": up(0.1, -0.05), "hips": (-5, 0, 0), "spine": (-8, -15, 0), "chest": (-12, -30, 0), "head": (0, 30, 0),
                     "upper_arm.R": (-150, -30, -20), "forearm.R": (120, 0, 0), "hand.R": (50, -15, 0),
                     "upper_arm.L": (70, 0, 30), "forearm.L": (10, 0, 0), "hand.L": (-20, 0, 0),
                     "thigh.L": (35, 0, 6), "shin.L": (-70, 0, 0), "thigh.R": (-15, 0, -4), "shin.R": (-30, 0, 0),
                     **W(-40, 25, -20, 20)})
TH_REL = with_rest({"hips@loc": up(0.06, 0.1), "hips": (12, 0, 0), "spine": (10, 12, 0), "chest": (10, 25, 0), "head": (-10, -20, 0),
                    "upper_arm.R": (-20, 0, -12), "forearm.R": (10, 0, 0), "hand.R": (10, 45, -10),
                    "upper_arm.L": (-20, 0, 35), "forearm.L": (30, 0, 0),
                    "thigh.L": (-10, 0, 6), "shin.L": (-40, 0, 0), "thigh.R": (35, 0, -6), "shin.R": (-60, 0, 0),
                    **W(20, -10, 20, -10)})
action("gungnir_throw", 30, {0: with_rest({}), 8: TH_DRAW, 14: {**TH_DRAW, "chest": (-14, -38, 0), "upper_arm.R": (-160, -30, -22)},
                             18: TH_REL, 22: {**TH_REL, "upper_arm.R": (40, 0, -10), "hand.R": (-40, 0, 0)}, 30: with_rest({})})

# Gungnir thrust: 24 frames. Coil with the lance level at the hip, lunge at frame 12.
TR_COIL = with_rest({"hips@loc": up(0.03, -0.08), "hips": (-5, 0, 0), "spine": (5, -15, 0), "chest": (5, -20, 0), "head": (-5, 25, 0),
                     "upper_arm.R": (-35, 0, -20), "forearm.R": (80, 0, 0), "hand.R": (-20, -30, 0),
                     "upper_arm.L": (40, 0, 30), "forearm.L": (40, 0, 0),
                     "thigh.L": (45, 0, 6), "shin.L": (-80, 0, 0), "thigh.R": (10, 0, -4), "shin.R": (-40, 0, 0),
                     **W(-45, 20, -25, 15)})
TR_HIT = with_rest({"hips@loc": up(-0.02, 0.3), "hips": (22, 0, 0), "spine": (5, 12, 0), "chest": (0, 18, 0), "neck": (-8, 0, 0), "head": (-18, -20, 0),
                    "upper_arm.R": (45, 0, -8), "forearm.R": (15, 0, 0), "hand.R": (-20, 60, 10),
                    "upper_arm.L": (-40, 0, 40), "forearm.L": (20, 0, 0), "hand.L": (-20, 0, 0),
                    "thigh.L": (-15, 0, 6), "shin.L": (-30, 0, 0), "thigh.R": (-5, 0, -6), "shin.R": (-60, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
                    **W(-50, -10, -20, -15)})
action("gungnir_thrust", 24, {0: with_rest({}), 7: TR_COIL, 12: TR_HIT, 16: {**TR_HIT, "hips@loc": up(-0.02, 0.33)}, 24: with_rest({})})

# Bat scatter: 20 frames. The wings wrap around her like a cloak (8-10), then
# burst open at frame 12 as she scatters into bats; reform by 20.
WRAP = with_rest({"hips@loc": up(0.0), "spine": (12, 0, 0), "chest": (10, 0, 0), "head": (15, 0, 0),
                  "upper_arm.L": (40, 0, -15), "upper_arm.R": (40, 0, 15), "forearm.L": (110, 0, 0), "forearm.R": (95, 0, 0),
                  "thigh.L": (40, 0, 3), "thigh.R": (35, 0, -3), "shin.L": (-70, 0, 0), "shin.R": (-65, 0, 0),
                  **W(95, -5, 80, -10)})
BURST = with_rest({"hips@loc": up(0.08), "spine": (-8, 0, 0), "chest": (-12, 0, 0), "head": (-10, 0, 0),
                   "upper_arm.L": (10, 0, 80), "upper_arm.R": (10, 0, -80), "forearm.L": (10, 0, 0), "forearm.R": (10, 0, 0), "hand.L": (-25, 0, 0), "hand.R": (-25, 0, 0),
                   "thigh.L": (5, 0, 10), "thigh.R": (0, 0, -10), "shin.L": (-20, 0, 0), "shin.R": (-15, 0, 0),
                   **W(-5, 30, 0, 25)})
action("bat_scatter", 20, {0: with_rest({}), 6: WRAP, 10: {**WRAP, "hips@loc": up(-0.02), **W(100, -8, 88, -12)}, 12: BURST, 15: {**BURST, **W(-10, 20, -5, 15)}, 20: with_rest({})})

# Spell: 30 frames. Draws herself up, one hand to her chest, then flings arms
# and wings wide for the declaration at frame 16, holds to 24.
SP_OPEN = with_rest({"hips@loc": up(0.12), "spine": (-6, 0, 0), "chest": (-12, 0, 0), "neck": (-4, 0, 0), "head": (-12, 0, 0),
                     "upper_arm.L": (30, 0, 95), "upper_arm.R": (20, 0, -100), "forearm.L": (5, 0, 0), "forearm.R": (15, 0, 0), "hand.L": (-30, 0, 0), "hand.R": (-20, 0, 0),
                     "thigh.L": (8, 0, 8), "thigh.R": (2, 0, -8), "shin.L": (-20, 0, 0), "shin.R": (-10, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
                     **W(0, 35, 5, 25)})
action("spell", 30, {
    0: with_rest({}),
    10: with_rest({"hips@loc": up(0.04), "chest": (4, 0, 0), "head": (10, 0, 0),
                   "upper_arm.L": (40, 0, -8), "forearm.L": (120, 0, 0), "hand.L": (20, 0, 0),
                   **W(-45, -15, -25, -10)}),
    16: SP_OPEN,
    24: {**SP_OPEN, "chest": (-9, 0, 0), "upper_arm.L": (35, 0, 90), **W(0, 30, 5, 20)},
    30: with_rest({}),
})

# Hurt: 10 frames. Knocked back in the air, wings flinch forward.
action("hurt", 10, {
    0: with_rest({}),
    2: with_rest({"hips@loc": up(0.04, -0.1), "hips": (-12, 0, 0), "spine": (-14, 0, 0), "chest": (-14, 0, 0), "head": (-25, 8, 0),
                  "upper_arm.L": (25, 0, 45), "upper_arm.R": (25, 0, -40), "forearm.L": (50, 0, 0), "forearm.R": (70, 0, 0),
                  "thigh.L": (40, 0, 6), "thigh.R": (30, 0, -6), "shin.L": (-60, 0, 0), "shin.R": (-50, 0, 0),
                  **W(15, -15, 20, -15)}),
    10: with_rest({}),
})

# Phase 2: 30 frames. Blood-moon rage: curls in, wings folded, then throws
# head, arms and wings fully open at frame 14, trembles, settles by 30.
ROAR = with_rest({"hips@loc": up(0.14), "spine": (-8, 0, 0), "chest": (-16, 0, 0), "neck": (-4, 0, 0), "head": (-4, 0, 0),
                  "upper_arm.L": (-25, 0, 70), "upper_arm.R": (-25, 0, -70), "forearm.L": (40, 0, 0), "forearm.R": (40, 0, 0), "hand.L": (-35, 0, 0), "hand.R": (-35, 0, 0),
                  "thigh.L": (-10, 0, 12), "thigh.R": (-10, 0, -12), "shin.L": (-30, 0, 0), "shin.R": (-30, 0, 0), "foot.L": (-50, 0, 0), "foot.R": (-50, 0, 0),
                  **W(-5, 42, 10, 30)})
action("phase2", 30, {
    0: with_rest({}),
    7: with_rest({"hips@loc": up(-0.03), "hips": (5, 0, 0), "spine": (22, 0, 0), "chest": (18, 0, 0), "head": (20, 0, 0),
                  "upper_arm.L": (45, 0, -8), "upper_arm.R": (45, 0, 8), "forearm.L": (120, 0, 0), "forearm.R": (110, 0, 0),
                  "thigh.L": (70, 0, 4), "thigh.R": (65, 0, -4), "shin.L": (-115, 0, 0), "shin.R": (-110, 0, 0),
                  **W(-55, -25, -35, -20)}),
    14: ROAR,
    18: {**ROAR, "chest": (-20, 3, 0), "head": (-22, -4, 0), **W(-2, 45, 12, 32)},
    22: {**ROAR, "chest": (-23, -3, 0), "head": (-18, 4, 0), **W(-8, 40, 8, 28)},
    30: with_rest({}),
})

# Death: 45 frames. Jolt, the hover fails, she drops to her knees on the
# ground by frame 26 and slumps sideways; the wings sag and fold over her.
KNEEL = {"hips@loc": (0, -0.3, -0.02), "hips": (-5, 0, 0), "spine": (25, 0, 0), "chest": (15, 0, 0), "head": (28, 0, 0),
         "thigh.L": (18, 0, 6), "thigh.R": (12, 0, -6), "shin.L": (-110, 0, 0), "shin.R": (-105, 0, 0), "foot.L": (-60, 0, 0), "foot.R": (-60, 0, 0),
         "upper_arm.L": (30, 0, 14), "upper_arm.R": (30, 0, -14), "forearm.L": (30, 0, 0), "forearm.R": (30, 0, 0), "hand.R": (-30, 60, -10),
         **W(-35, -30, -25, -25)}
HEAP = {"hips@loc": (0.03, -0.36, 0.02), "hips": (-5, 0, -12), "spine": (28, 0, 10), "chest": (22, 10, 8), "neck": (15, 0, 0), "head": (28, 25, 15),
        "thigh.L": (70, 0, 20), "thigh.R": (80, 0, -10), "shin.L": (-155, 0, 0), "shin.R": (-150, 0, 0), "foot.L": (-65, 0, 0), "foot.R": (-65, 0, 0),
        "upper_arm.L": (25, 0, 10), "upper_arm.R": (45, 0, -25), "forearm.L": (40, 0, 0), "forearm.R": (60, 0, 0), "hand.L": (10, 0, 0), "hand.R": (0, 90, 0),
        "wing.L": (25, 0, -80), "wing.R": (15, 0, 75), "wing_tip.L": (30, 0, -55), "wing_tip.R": (20, 0, 60)}
action("death", 45, {
    0: with_rest({}),
    5: with_rest({"hips@loc": up(0.06, -0.05), "spine": (-18, 0, 0), "chest": (-20, 0, 0), "head": (-30, 0, 0),
                  "upper_arm.L": (20, 0, 55), "upper_arm.R": (20, 0, -55), "forearm.L": (10, 0, 0), "forearm.R": (10, 0, 0),
                  **W(0, 35, 5, 25)}),
    15: with_rest({"hips@loc": up(-0.12), "spine": (10, 0, 0), "head": (15, 0, 0), "upper_arm.L": (-20, 0, 40), "upper_arm.R": (-20, 0, -40),
                   "thigh.L": (10, 0, 4), "thigh.R": (5, 0, -4), "shin.L": (-40, 0, 0), "shin.R": (-35, 0, 0),
                   **W(-10, 20, 0, 15)}),
    26: KNEEL,
    36: {**HEAP, "head": (24, 20, 12), "hips@loc": (0.03, -0.35, 0.02), "wing.L": (15, 0, -70), "wing.R": (8, 0, 65)},
    45: HEAP,
})

arm.animation_data.action = bpy.data.actions["idle"]
C.export_glb("assets/models/characters/remilia/remilia.glb", [arm, remilia, gungnir])
tris = sum(len(p.vertices) - 2 for ob in (remilia, gungnir) for p in ob.data.polygons)
print("tris:", tris, "(body %d, gungnir %d)" % (sum(len(p.vertices) - 2 for p in remilia.data.polygons), sum(len(p.vertices) - 2 for p in gungnir.data.polygons)))
bb = [remilia.matrix_world @ v.co for v in remilia.data.vertices]
print("height: %.3f" % (max(v.z for v in bb) - min(v.z for v in bb)))
