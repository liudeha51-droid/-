"""The Faithless: in-house stylised enemy models, rigs and combat animations.

Outputs:
  assets/models/characters/faithless/hollow_fairy.glb   (~0.9 m hovering fairy)
  assets/models/characters/faithless/tengu_scout.glb    (~1.6 m masked crow-tengu)

Same conventions as build_reimu.py:
Blender axes: Z up, characters face -Y, their left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
Wing bones follow the same rule: +Z lifts a left wing, -Z lifts a right one.
"""
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402

FPS = 30


# ================================================================ shared helpers
def make_rig(name, bones):
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    C.activate(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, head, tail, parent in bones:
        eb = arm_data.edit_bones.new(bname)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        if bname.startswith("foot") or bname.startswith("shoulder"):
            eb.align_roll(Vector((0, 0, 1)) if bname.startswith("foot") else Vector((0, -1, 0)))
        else:
            eb.align_roll(Vector((0, -1, 0)))
        if parent:
            eb.parent = arm_data.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.data.display_type = "STICK"
    arm.animation_data_create()
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def bone_point(arm, name, t):
    b = arm.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


def make_action(arm):
    def action(name, frames, keys, loop=False):
        """keys: {frame: {bone: (rx, ry, rz) degrees | bone@loc: (x, y, z) | bone@scale: (x, y, z)}}."""
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        for pb in arm.pose.bones:
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
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
                elif bone.endswith("@scale"):
                    pb.scale = pose.get(bone, (1, 1, 1))
                    pb.keyframe_insert("scale", frame=f)
                else:
                    pb.rotation_euler = [math.radians(a) for a in pose.get(bone, (0, 0, 0))]
                    pb.keyframe_insert("rotation_euler", frame=f)
        act.frame_range = (0, frames)
        return act
    return action


def skin_body(name, verts, edges, root, arm, bone_names, assign, mats, power=4.0):
    """verts: [(co, (rx, ry))]. assign(poly_center) -> material index."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([v[0] for v in verts], edges, [])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    for i, (_, r) in enumerate(verts):
        obj.data.skin_vertices[0].data[i].radius = r
    obj.data.skin_vertices[0].data[root].use_root = True
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 2
    C.apply_modifiers(obj)
    for m in mats:
        obj.data.materials.append(m)
    for poly in obj.data.polygons:
        poly.material_index = assign(poly.center)
        poly.use_smooth = True
    C.weight_by_bones(obj, arm, bone_names, power=power)
    return obj


class Graph:
    def __init__(self):
        self.verts, self.edges = [], []

    def v(self, co, r):
        self.verts.append((co, r if isinstance(r, tuple) else (r, r)))
        return len(self.verts) - 1

    def chain(self, *ids):
        for a, b in zip(ids, ids[1:]):
            self.edges.append((a, b))


class Surface:
    """Ray-casts onto a mesh from the front (-Y) so decals hug a curved face."""

    def __init__(self, obj):
        self.bvh = BVHTree.FromPolygons([v.co.copy() for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])

    def hit(self, x, z, off=0.0015):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector((x, -2.0, z)), Vector((0, 1, 0)))
        if loc is None:
            return None, None
        if nrm.y > 0:
            nrm = -nrm
        return loc + nrm * off, nrm


def disc(name, center, normal, size, mat, segments=16):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=segments, radius=1.0)
    rot = normal.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm.transform(Matrix.Translation(center) @ rot @ Matrix.Diagonal((size[0], size[1], 1, 1)))
    return C.new_object(name, bm, mat, smooth=False)


def decal_line(name, surf, pts2d, radius, mat, off=0.0015):
    pts = [surf.hit(x, z, off)[0] for x, z in pts2d]
    pts = [p for p in pts if p is not None]
    return C.tube(name, pts, [radius] * len(pts), 4, mat)


def flare(name, z_top, z_bot, r_top, r_bot, mat, seg=40, rings=6, a0=0.0, a1=2 * math.pi,
          yscale=0.86, pleats=0.0, jag=0.0, seed=1, yoff=0.0, power=0.8):
    """A conical skirt (or partial panel when a0..a1 is not a full turn) with a torn hem."""
    rng = random.Random(seed)
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    cols = seg if full else seg + 1
    tear = []
    for k in range(cols):
        base = rng.random() ** 1.6 * jag
        tear.append(base * (1.0 if k % 3 else 0.35))
    bm = bmesh.new()
    grid = []
    for r in range(rings + 1):
        t = r / rings
        rad = r_top + (r_bot - r_top) * (t ** power)
        ring = []
        for k in range(cols):
            a = a0 + (a1 - a0) * k / (seg if full else seg)
            z = z_top - t * (z_top - z_bot - tear[k])
            p = 1.0 + pleats * t * math.sin(a * 12)
            ring.append(bm.verts.new((math.cos(a) * rad * p, math.sin(a) * rad * p * yscale + yoff, z)))
        grid.append(ring)
    for r in range(rings):
        for k in range(seg):
            k2 = (k + 1) % cols
            bm.faces.new((grid[r][k], grid[r][k2], grid[r + 1][k2], grid[r + 1][k]))
    return C.new_object(name, bm, mat)


def jag_tube_end(obj, segments, amp, seed):
    """Tear the last ring of an uncapped C.tube: random lifts give a ragged hem."""
    rng = random.Random(seed)
    n = len(obj.data.vertices)
    for k in range(segments):
        v = obj.data.vertices[n - segments + k]
        v.co.z += rng.random() ** 1.5 * amp * (1.0 if k % 2 else 0.4)


def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def finish(parts, name, arm, path):
    body = C.join(parts, name)
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    body.parent = arm
    arm.animation_data.action = bpy.data.actions["idle"]
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    C.export_glb(path, [arm, body])
    zs = [v.co.z for v in body.data.vertices]
    print(f"{name}: tris {tri_count(body)}, height {max(zs) - min(zs):.3f} (z {min(zs):.3f}..{max(zs):.3f})")
    for act in bpy.data.actions:
        print(f"  {act.name}: {int(act.frame_range[1])} frames")


# ================================================================ hollow fairy
def build_fairy():
    C.reset_scene()
    M = {
        "skin": C.material("PorcelainSkin", (0.80, 0.78, 0.77), 0.45),
        "dress": C.material("FadedDress", (0.16, 0.18, 0.25), 0.8),
        "apron": C.material("GreyApron", (0.5, 0.49, 0.46), 0.85),
        "hair": C.material("AshHair", (0.36, 0.36, 0.38), 0.6),
        "shoe": C.material("Shoe", (0.07, 0.06, 0.07), 0.5),
        "socket": C.material("EmptyEye", (0.015, 0.015, 0.02), 0.9),
        "glow": C.material("PaleGlow", (0.78, 0.86, 0.95), 0.2, emission=1.2),
        "crack": C.material("Crack", (0.2, 0.19, 0.2), 0.8),
        "vein": C.material("WingVein", (0.42, 0.45, 0.5), 0.5),
    }
    wing = C.material("WingMembrane", (0.72, 0.78, 0.86), 0.15, emission=0.15)
    wing.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.38
    wing.use_backface_culling = False
    M["wing"] = wing

    bones = [
        ("root", (0, 0, 0), (0, 0, 0.1), None),
        ("hips", (0, 0, 0.40), (0, 0, 0.47), "root"),
        ("spine", (0, 0, 0.47), (0, 0, 0.54), "hips"),
        ("chest", (0, 0, 0.54), (0, 0, 0.63), "spine"),
        ("neck", (0, 0, 0.63), (0, 0, 0.67), "chest"),
        ("head", (0, 0, 0.67), (0, 0, 0.87), "neck"),
    ]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        bones += [
            (f"shoulder.{s}", (sx * 0.02, 0, 0.605), (sx * 0.075, 0, 0.605), "chest"),
            (f"upper_arm.{s}", (sx * 0.08, 0, 0.60), (sx * 0.125, 0, 0.47), f"shoulder.{s}"),
            (f"forearm.{s}", (sx * 0.125, 0, 0.47), (sx * 0.15, -0.02, 0.35), f"upper_arm.{s}"),
            (f"hand.{s}", (sx * 0.15, -0.02, 0.35), (sx * 0.16, -0.025, 0.29), f"forearm.{s}"),
            (f"thigh.{s}", (sx * 0.05, 0, 0.41), (sx * 0.055, 0, 0.22), "hips"),
            (f"shin.{s}", (sx * 0.055, 0, 0.22), (sx * 0.055, 0.005, 0.045), f"thigh.{s}"),
            (f"foot.{s}", (sx * 0.055, 0.005, 0.045), (sx * 0.055, -0.06, 0.012), f"shin.{s}"),
            (f"wing.{s}", (sx * 0.025, 0.05, 0.585), (sx * 0.14, 0.09, 0.67), "chest"),
        ]
    arm = make_rig("HollowFairyRig", bones)
    body_bones = [b[0] for b in bones if b[0] != "root" and not b[0].startswith("wing")]
    P = lambda n, t: bone_point(arm, n, t)  # noqa: E731

    # ---- body
    g = Graph()
    pelvis = g.v((0, 0, 0.40), (0.066, 0.052))
    waist = g.v((0, 0, 0.47), (0.05, 0.04))
    chest = g.v((0, 0, 0.55), (0.06, 0.046))
    upper = g.v((0, 0, 0.60), (0.056, 0.042))
    neck_b = g.v((0, 0, 0.63), 0.024)
    neck_t = g.v((0, 0, 0.69), 0.021)
    g.chain(pelvis, waist, chest, upper, neck_b, neck_t)
    for sx in (1.0, -1.0):
        sh = g.v((sx * 0.075, 0, 0.598), 0.026)
        el = g.v((sx * 0.125, 0, 0.47), 0.017)
        wr = g.v((sx * 0.15, -0.02, 0.35), 0.013)
        hd = g.v((sx * 0.157, -0.023, 0.315), (0.017, 0.012))
        hip = g.v((sx * 0.048, 0, 0.39), 0.04)
        kn = g.v((sx * 0.055, 0, 0.22), 0.026)
        an = g.v((sx * 0.055, 0.005, 0.05), 0.018)
        toe = g.v((sx * 0.055, -0.05, 0.02), (0.022, 0.017))
        g.chain(upper, sh, el, wr, hd)
        g.chain(pelvis, hip, kn, an, toe)

    def body_mat(c):
        if c.z < 0.035:
            return 3
        if c.z < 0.38 and abs(c.x) < 0.1:
            return 2  # bare legs
        if c.z > 0.625 or (abs(c.x) > 0.085 and c.z < 0.56) or abs(c.x) > 0.1:
            return 2
        return 0
    body = skin_body("Body", g.verts, g.edges, pelvis, arm, body_bones, body_mat,
                     [M["dress"], M["apron"], M["skin"], M["shoe"]])
    parts = [body]

    # Thin claw-like fingers.
    for s, sx in (("L", 1.0), ("R", -1.0)):
        base = P(f"hand.{s}", 0.55)
        for i, dy in enumerate((-0.012, 0.0, 0.012)):
            tip = base + Vector((sx * 0.005, dy - 0.02, -0.055 + abs(dy) * 0.8))
            mid = base.lerp(tip, 0.5) + Vector((sx * 0.004, dy * 0.3, 0))
            f = C.tube("Finger", [base + Vector((0, dy * 0.6, 0.01)), mid, tip], [0.006, 0.005, 0.0012], 6, M["skin"])
            C.rigid(f, f"hand.{s}")
            parts.append(f)

    # ---- head: porcelain face, empty eyes, cracks
    hc = Vector((0, 0, 0.77))
    head = C.uv_sphere("Head", 0.1, tuple(hc), (1.0, 0.95, 1.04), 28, 14, M["skin"])
    for v in head.data.vertices:
        dz = v.co.z - hc.z
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.105) * 0.36
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.04
    face = Surface(head)
    hp = [head]
    for sx in (1.0, -1.0):
        c, n = face.hit(sx * 0.037, 0.768, 0.0015)
        hp.append(disc("EyeSocket", c, n, (0.021, 0.027), M["socket"]))
        c2, _ = face.hit(sx * 0.035, 0.771, 0.003)
        hp.append(disc("EyeGlow", c2, n, (0.0045, 0.006), M["glow"], 10))
        # a faint stain running down from each eye
        hp.append(decal_line("Tear", face, [(sx * 0.036, 0.743), (sx * 0.038, 0.73), (sx * 0.036, 0.72)], 0.0014, M["socket"]))
    c, n = face.hit(0.0, 0.715, 0.0012)
    hp.append(C.tube("Mouth", [c + Vector((-0.011, 0, 0.002)), c, c + Vector((0.011, 0, 0.002))], [0.0016] * 3, 4, M["crack"]))
    # Porcelain cracks across the face.
    hp.append(decal_line("Crack", face, [(0.02, 0.84), (0.028, 0.815), (0.022, 0.8), (0.034, 0.785)], 0.0014, M["crack"]))
    hp.append(decal_line("Crack", face, [(-0.055, 0.75), (-0.045, 0.738), (-0.05, 0.725), (-0.035, 0.712)], 0.0014, M["crack"]))
    hp.append(decal_line("Crack", face, [(0.024, 0.8), (0.012, 0.79)], 0.0012, M["crack"]))

    # Hair: dull ash cap, ragged bangs, short uneven back hair.
    cap = C.uv_sphere("HairCap", 0.109, (0, 0.008, 0.782), (1.03, 1.0, 1.05), 28, 14, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.03 and v.co.z < 0.82], context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.005)
    hp.append(cap)
    rng = random.Random(7)
    for i in range(7):
        x = -0.075 + i * 0.025
        top = Vector((x * 0.8, -0.075, 0.855))
        drop = 0.03 + rng.random() * 0.045
        bottom = Vector((x * 1.1, -0.102 + abs(x) * 0.2, 0.83 - drop + abs(x) * 0.25))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.012, 0))
        hp.append(C.tube("Bang", [top, mid, bottom], [0.018, 0.013, 0.002], 6, M["hair"], (1.0, 0.45)))
    for sx in (1.0, -1.0):
        pts = [Vector((sx * 0.088, -0.035, 0.81)), Vector((sx * 0.1, -0.045, 0.73)), Vector((sx * 0.098, -0.04, 0.66))]
        hp.append(C.tube("Sidelock", pts, [0.024, 0.02, 0.002], 8, M["hair"], (1.0, 0.55)))
    back = [Vector((0, 0.05, 0.82)), Vector((0, 0.085, 0.74)), Vector((0, 0.075, 0.67))]
    hp.append(C.tube("BackHair", back, [0.1, 0.1, 0.07], 14, M["hair"], (1.0, 0.45)))
    for i in range(6):
        x = -0.07 + i * 0.028
        hp.append(C.tube("HairTip", [Vector((x, 0.08, 0.7)), Vector((x * 1.15, 0.085, 0.63 - (i % 2) * 0.03 - rng.random() * 0.02))], [0.022, 0.002], 6, M["hair"], (1.0, 0.5)))
    # A limp stray strand on top.
    hp.append(C.tube("Ahoge", [Vector((0.01, -0.02, 0.885)), Vector((0.03, -0.03, 0.905)), Vector((0.055, -0.045, 0.89))], [0.008, 0.006, 0.001], 6, M["hair"], (1.0, 0.4)))
    # Broken maid headband: an arc over the head with a gap torn out of it.
    band = []
    for i in range(12):
        a = math.radians(15 + i * 12.5)
        if 7 <= i <= 8:
            continue
        band.append((i, Vector((math.cos(a) * 0.112, -0.012, 0.785 + math.sin(a) * 0.112))))
    runs, cur = [], []
    for i, p in band:
        if cur and i != cur[-1][0] + 1:
            runs.append(cur)
            cur = []
        cur.append((i, p))
    runs.append(cur)
    for run in runs:
        pts = [p for _, p in run]
        hp.append(C.tube("Headband", pts, [0.012] * len(pts), 6, M["apron"], (0.5, 1.0), twist_up=Vector((0, 1, 0))))
    for p in hp:
        C.rigid(p, "head")
    parts += hp

    # ---- outfit
    collar = C.tube("Collar", [Vector((0, 0.0, 0.64)), Vector((0, 0.0, 0.615))], [0.03, 0.05], 14, M["apron"])
    C.rigid(collar, "chest")
    bow = C.uv_sphere("BackBow", 0.02, (0, 0.05, 0.47), (1.6, 0.6, 0.9), 12, 6, M["apron"])
    C.rigid(bow, "spine")
    parts += [collar, bow]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        puff = C.uv_sphere("Puff", 0.033, tuple(P(f"upper_arm.{s}", 0.2)), (1.0, 1.0, 1.0), 12, 7, M["dress"])
        cuff = C.tube("Cuff", [P(f"upper_arm.{s}", 0.36), P(f"upper_arm.{s}", 0.44)], [0.024, 0.024], 10, M["apron"])
        C.rigid(puff, f"upper_arm.{s}")
        C.rigid(cuff, f"upper_arm.{s}")
        parts += [puff, cuff]

    skirt = flare("Skirt", 0.49, 0.25, 0.05, 0.155, M["dress"], seg=40, rings=6, pleats=0.06, jag=0.07, seed=3)
    C.solidify(skirt, 0.005)
    C.weight_by_bones(skirt, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    apron = flare("Apron", 0.47, 0.285, 0.056, 0.15, M["apron"], seg=10, rings=5,
                  a0=-math.pi / 2 - 0.75, a1=-math.pi / 2 + 0.75, jag=0.06, seed=11, pleats=0.06, yscale=0.9)
    C.solidify(apron, 0.004)
    C.weight_by_bones(apron, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    parts += [skirt, apron]

    # ---- cracked insect wings (two panes a side), translucent, rigid to the wing bones
    def wing_pane(root, side, ang, length, width, seed, bite):
        rng = random.Random(seed)
        a = math.radians(ang)
        d = Vector((side * math.cos(a), 0, math.sin(a)))
        perp = Vector((-side * math.sin(a), 0, math.cos(a)))

        def to3d(u, v):
            p = root + d * u + perp * v
            p.y = root.y + 0.35 * abs(p.x - root.x) + 0.1 * abs(p.z - root.z)
            return p
        outline = []
        n = 28
        for i in range(n):
            s = 2 * math.pi * i / n
            u = length * (1 - math.cos(s)) / 2
            v = width / 2 * math.sin(s) * min(1.0, 0.25 + 1.3 * u / length)
            if bite[0] <= i <= bite[1]:
                v *= 0.35 + 0.35 * ((i - bite[0]) % 2) + rng.random() * 0.1
            outline.append((u, v))
        bm = bmesh.new()
        vs = [bm.verts.new(to3d(u, v)) for u, v in outline]
        bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        out = [C.new_object("Wing", bm, M["wing"], smooth=False)]
        # Veins: a spine and branches; cracks: zigzags running in from the torn edge.
        vein = [to3d(length * t, 0.0) for t in (0.02, 0.4, 0.9)]
        out.append(C.tube("Vein", vein, [0.0022, 0.0018, 0.001], 4, M["vein"]))
        for t, sgn in ((0.3, 1), (0.5, -1), (0.65, 1), (0.8, -1)):
            u = length * t
            vmax = width / 2 * min(1.0, 0.25 + 1.3 * t) * 0.8
            out.append(C.tube("Vein", [to3d(u, 0), to3d(u + length * 0.1, sgn * vmax)], [0.0014, 0.0008], 4, M["vein"]))
        mid = (bite[0] + bite[1]) // 2
        u0, v0 = outline[mid]
        crack = [to3d(u0, v0)]
        for k in range(1, 4):
            crack.append(to3d(u0 * (1 - 0.12 * k) + rng.uniform(-0.01, 0.01), v0 * (1 - 0.3 * k) + (0.012 if k % 2 else -0.012)))
        out.append(C.tube("WingCrack", crack, [0.0016] * len(crack), 4, M["crack"]))
        return out

    for s, sx in (("L", 1.0), ("R", -1.0)):
        root = Vector((sx * 0.025, 0.05, 0.585))
        panes = wing_pane(root, sx, 38, 0.3, 0.1, 21 if s == "L" else 22, (16, 20) if s == "L" else (5, 8))
        panes += wing_pane(root + Vector((0, 0, -0.02)), sx, -28, 0.2, 0.07, 31 if s == "L" else 32, (4, 6) if s == "L" else (17, 20))
        for p in panes:
            C.rigid(p, f"wing.{s}")
        parts += panes

    # ---- animation
    action = make_action(arm)
    REST = {
        "spine": (12, 0, 0), "chest": (20, 0, 0), "neck": (8, 0, 0), "head": (-16, 4, 7),
        "shoulder.L": (8, 0, -6), "shoulder.R": (8, 0, 6),
        "upper_arm.L": (10, 0, 7), "upper_arm.R": (14, 0, -6), "forearm.L": (18, 0, 0), "forearm.R": (22, 0, 0),
        "thigh.L": (16, 0, 2), "thigh.R": (8, 0, -3), "shin.L": (-30, 0, 0), "shin.R": (-18, 0, 0),
        "foot.L": (-30, 0, 0), "foot.R": (-25, 0, 0),
        "wing.L": (0, 0, 0), "wing.R": (0, 0, 0), "hips@loc": (0, 0.10, 0),
    }

    def rest(p=None, bob=0.0, flap=0.0):
        out = dict(REST)
        out["hips@loc"] = (0, 0.10 + bob, 0)
        out["wing.L"] = (0, 0, flap)
        out["wing.R"] = (0, 0, -flap)
        out.update(p or {})
        return out

    def flutter(f, amp=16, lo=-6):
        return amp if (f // 2) % 2 == 0 else lo

    # Idle: 40 frames. Hovering bob, wing flutter, and a head twitch that skips the rhythm.
    keys = {}
    for f in range(0, 41, 2):
        ph = 2 * math.pi * f / 40
        p = rest({"chest": (20 + 2 * math.sin(ph), 0, 0)}, bob=0.02 * math.sin(ph), flap=flutter(f))
        if f in (24, 26):
            p["head"] = (-16, 12, 18)
        keys[f] = p
    action("idle", 40, keys, loop=True)

    # Fly: 20 frames. Leaning into the flight, limbs trailing, faster wider wingbeats.
    keys = {}
    for f in range(0, 21, 2):
        ph = 2 * math.pi * f / 20
        fl = 26 if (f // 2) % 2 == 0 else -14
        keys[f] = {
            "hips": (38, 0, 0), "spine": (4, 0, 0), "chest": (6, 0, 0), "neck": (-10, 0, 0), "head": (-30, 3, 5),
            "shoulder.L": (0, 0, -4), "shoulder.R": (0, 0, 4),
            "upper_arm.L": (-40, 0, 12), "upper_arm.R": (-40, 0, -12), "forearm.L": (25, 0, 0), "forearm.R": (25, 0, 0),
            "thigh.L": (-8 + 6 * math.sin(ph), 0, 3), "thigh.R": (-2 - 6 * math.sin(ph), 0, -3),
            "shin.L": (-35, 0, 0), "shin.R": (-25, 0, 0), "foot.L": (-40, 0, 0), "foot.R": (-40, 0, 0),
            "wing.L": (-12, 0, fl), "wing.R": (-12, 0, -fl), "hips@loc": (0, 0.16 + 0.015 * math.sin(ph), 0),
        }
    action("fly", 20, keys, loop=True)

    # Claw: 18 frames. Right-hand diagonal rake, contact at frame 8.
    WIND = {"chest": (0, -30, 0), "spine": (-4, -10, 0), "head": (-18, -8, 10),
            "upper_arm.R": (120, 0, -45), "forearm.R": (45, 0, 0), "hand.R": (-20, 0, 0),
            "upper_arm.L": (-15, 0, 20), "forearm.L": (30, 0, 0)}
    HIT = {"chest": (20, 30, 0), "spine": (14, 12, 0), "head": (-18, 10, 5),
           "upper_arm.R": (60, 0, 28), "forearm.R": (8, 0, 0), "hand.R": (20, 0, 0),
           "upper_arm.L": (10, 0, 30), "forearm.L": (25, 0, 0)}
    action("claw", 18, {
        0: rest(flap=8),
        4: rest(WIND, bob=0.02, flap=24),
        8: rest({**HIT, "hips@loc": (0, 0.08, 0.1)}, flap=-10),
        11: rest({**HIT, "chest": (24, 38, 0), "upper_arm.R": (45, 0, 38), "hips@loc": (0, 0.08, 0.1)}, flap=10),
        18: rest(flap=8),
    })

    # Shoot: 12 frames. Left hand gathers at the chest, then flicks a bullet forward at frame 6.
    GATHER = {"upper_arm.L": (45, 0, -15), "forearm.L": (110, 0, 0), "hand.L": (-10, 0, 0), "chest": (6, 18, 0), "head": (-14, 12, 16)}
    RELEASE = {"upper_arm.L": (88, 0, 4), "forearm.L": (2, 0, 0), "hand.L": (-25, 0, 0), "chest": (10, -15, 0), "head": (-18, -4, 4)}
    action("shoot", 12, {
        0: rest(flap=8),
        3: rest(GATHER, flap=18),
        6: rest(RELEASE, bob=0.01, flap=-8),
        8: rest(RELEASE, flap=12),
        12: rest(flap=8),
    })

    # Hurt: 10 frames. Jolted backwards, head snaps, wings flare.
    action("hurt", 10, {
        0: rest(flap=8),
        2: rest({"spine": (-14, 0, 0), "chest": (-14, 0, 0), "head": (-30, -15, -12),
                 "upper_arm.L": (20, 0, 40), "upper_arm.R": (20, 0, -40), "hips@loc": (0, 0.14, -0.06)}, flap=34),
        5: rest({"spine": (-4, 0, 0), "head": (-16, -6, -4), "hips@loc": (0, 0.12, -0.04)}, flap=14),
        10: rest(flap=8),
    })

    # Death: 30 frames. Stiffens, the hover gives out, she drops, folds onto her side and
    # the wings crumble away.
    CURL = {"hips": (12, 0, 82), "spine": (18, 0, 0), "chest": (18, 0, 0), "head": (15, 0, -10),
            "thigh.L": (70, 0, 5), "thigh.R": (80, 0, -5), "shin.L": (-100, 0, 0), "shin.R": (-110, 0, 0),
            "foot.L": (-20, 0, 0), "foot.R": (-20, 0, 0),
            "upper_arm.L": (50, 0, 10), "upper_arm.R": (70, 0, -5), "forearm.L": (60, 0, 0), "forearm.R": (80, 0, 0),
            "wing.L": (-40, 0, -30), "wing.R": (-40, 0, 30)}
    action("death", 30, {
        0: rest(flap=8),
        4: rest({"spine": (-12, 0, 0), "chest": (-10, 0, 0), "head": (-35, 0, 0), "upper_arm.L": (30, 0, 50),
                 "upper_arm.R": (30, 0, -50), "hips@loc": (0, 0.14, 0), "wing.L@scale": (1, 1, 1), "wing.R@scale": (1, 1, 1)}, flap=35),
        11: rest({"spine": (10, 0, 0), "chest": (20, 0, 0), "head": (20, 0, 0), "thigh.L": (40, 0, 0),
                  "thigh.R": (30, 0, 0), "shin.L": (-70, 0, 0), "shin.R": (-60, 0, 0), "hips@loc": (0, -0.05, 0),
                  "wing.L@scale": (1, 1, 1), "wing.R@scale": (1, 1, 1)}, flap=-20),
        18: {**CURL, "hips@loc": (0, -0.26, 0.0), "wing.L@scale": (0.8, 0.8, 0.8), "wing.R@scale": (0.8, 0.8, 0.8)},
        22: {**CURL, "hips": (14, 0, 86), "hips@loc": (0, -0.29, 0.0), "wing.L@scale": (0.55, 0.3, 0.55), "wing.R@scale": (0.55, 0.3, 0.55)},
        30: {**CURL, "hips": (14, 0, 88), "head": (25, 0, -15), "hips@loc": (0, -0.3, 0.0),
             "wing.L@scale": (0.05, 0.05, 0.05), "wing.R@scale": (0.05, 0.05, 0.05)},
    })

    finish(parts, "HollowFairy", arm, "assets/models/characters/faithless/hollow_fairy.glb")


# ================================================================ masked tengu scout
def build_tengu():
    C.reset_scene()
    M = {
        "garb": C.material("RaggedGarb", (0.06, 0.06, 0.07), 0.85),
        "garb2": C.material("Wraps", (0.14, 0.13, 0.14), 0.9),
        "skin": C.material("PaleSkin", (0.7, 0.66, 0.62), 0.6),
        "mask": C.material("PaperMask", (0.9, 0.88, 0.83), 0.8),
        "ink": C.material("FadedInk", (0.6, 0.59, 0.56), 0.9),
        "hair": C.material("CrowHair", (0.035, 0.035, 0.045), 0.5),
        "feather": C.material("Feather", (0.03, 0.03, 0.04), 0.45),
        "tokin": C.material("FadedRed", (0.3, 0.09, 0.09), 0.7),
        "pom": C.material("GreyPom", (0.55, 0.53, 0.5), 0.95),
        "steel": C.material("Steel", (0.55, 0.56, 0.6), 0.35, 0.8),
        "wood": C.material("Geta", (0.2, 0.14, 0.1), 0.7),
        "leaf": C.material("FanLeaf", (0.17, 0.21, 0.15), 0.7),
        "sash": C.material("Sash", (0.28, 0.12, 0.12), 0.8),
        "cord": C.material("Cord", (0.1, 0.1, 0.1), 0.8),
    }
    bones = [
        ("root", (0, 0, 0), (0, 0, 0.15), None),
        ("hips", (0, 0, 0.86), (0, 0, 0.98), "root"),
        ("spine", (0, 0, 0.98), (0, 0, 1.10), "hips"),
        ("chest", (0, 0, 1.10), (0, 0, 1.26), "spine"),
        ("neck", (0, 0, 1.26), (0, 0, 1.33), "chest"),
        ("head", (0, 0, 1.33), (0, 0, 1.58), "neck"),
        ("wing.L", (0.06, 0.09, 1.2), (0.24, 0.17, 1.37), "chest"),
        ("wing_tip.L", (0.24, 0.17, 1.37), (0.44, 0.23, 1.3), "wing.L"),
    ]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        bones += [
            (f"shoulder.{s}", (sx * 0.03, 0, 1.23), (sx * 0.15, 0, 1.23), "chest"),
            (f"upper_arm.{s}", (sx * 0.16, 0, 1.22), (sx * 0.24, 0, 0.98), f"shoulder.{s}"),
            (f"forearm.{s}", (sx * 0.24, 0, 0.98), (sx * 0.3, -0.03, 0.77), f"upper_arm.{s}"),
            (f"hand.{s}", (sx * 0.3, -0.03, 0.77), (sx * 0.32, -0.04, 0.68), f"forearm.{s}"),
            (f"thigh.{s}", (sx * 0.095, 0, 0.87), (sx * 0.1, 0, 0.49), "hips"),
            (f"shin.{s}", (sx * 0.1, 0, 0.49), (sx * 0.1, 0.01, 0.14), f"thigh.{s}"),
            (f"foot.{s}", (sx * 0.1, 0.01, 0.14), (sx * 0.1, -0.1, 0.09), f"shin.{s}"),
        ]
    arm = make_rig("TenguScoutRig", bones)
    body_bones = [b[0] for b in bones if b[0] != "root" and not b[0].startswith("wing")]
    P = lambda n, t: bone_point(arm, n, t)  # noqa: E731

    # ---- body
    g = Graph()
    pelvis = g.v((0, 0, 0.86), (0.115, 0.088))
    waist = g.v((0, 0, 0.98), (0.092, 0.072))
    chest = g.v((0, 0, 1.12), (0.118, 0.084))
    upper = g.v((0, 0, 1.21), (0.12, 0.078))
    neck_b = g.v((0, 0, 1.26), 0.05)
    neck_t = g.v((0, 0, 1.35), 0.043)
    g.chain(pelvis, waist, chest, upper, neck_b, neck_t)
    for sx in (1.0, -1.0):
        sh = g.v((sx * 0.155, 0, 1.215), 0.048)
        el = g.v((sx * 0.24, 0, 0.98), 0.035)
        wr = g.v((sx * 0.3, -0.03, 0.77), 0.027)
        hd = g.v((sx * 0.315, -0.037, 0.7), (0.034, 0.024))
        hip = g.v((sx * 0.092, 0, 0.84), 0.075)
        kn = g.v((sx * 0.1, 0, 0.49), 0.05)
        an = g.v((sx * 0.1, 0.01, 0.15), 0.034)
        toe = g.v((sx * 0.1, -0.075, 0.1), (0.036, 0.03))
        g.chain(upper, sh, el, wr, hd)
        g.chain(pelvis, hip, kn, an, toe)

    def body_mat(c):
        if c.z < 0.4 and abs(c.x) < 0.2:
            return 1  # leg wraps / tabi
        if c.z > 1.28:
            return 2
        if c.z < 0.8 and abs(c.x) > 0.25:
            return 2  # hands
        return 0
    body = skin_body("Body", g.verts, g.edges, pelvis, arm, body_bones, body_mat, [M["garb"], M["garb2"], M["skin"]])
    parts = [body]

    # ---- head, newspaper mask, crow hair, tokin
    hc = Vector((0, 0, 1.46))
    head = C.uv_sphere("Head", 0.108, tuple(hc), (1.0, 0.97, 1.08), 24, 12, M["skin"])
    hp = [head]
    mask = C.uv_sphere("Mask", 0.118, (0, -0.004, 1.455), (0.97, 1.0, 1.1), 28, 16, M["mask"])
    bm = bmesh.new()
    bm.from_mesh(mask.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -0.035 or v.co.z > 1.555 or v.co.z < 1.34], context="VERTS")
    bm.to_mesh(mask.data)
    bm.free()
    surf = Surface(mask)
    C.solidify(mask, 0.006)
    hp.append(mask)
    # Blank newspaper: an empty headline box, column rules, faint unreadable lines.
    for pts in ([(-0.06, 1.525), (0.06, 1.525)], [(-0.06, 1.492), (0.06, 1.492)], [(-0.06, 1.525), (-0.06, 1.492)], [(0.06, 1.525), (0.06, 1.492)]):
        hp.append(decal_line("Headline", surf, pts, 0.0022, M["ink"], 0.0045))
    for x in (-0.022, 0.022):
        hp.append(decal_line("Column", surf, [(x, 1.475), (x, 1.37)], 0.0015, M["ink"], 0.0045))
    for i, z in enumerate((1.465, 1.448, 1.431, 1.414, 1.397)):
        for x0, x1 in ((-0.068, -0.03), (-0.014, 0.014), (0.03, 0.062 - 0.012 * (i % 2))):
            hp.append(decal_line("Text", surf, [(x0, z), (x1, z)], 0.0012, M["ink"], 0.004))
    for sx in (1.0, -1.0):
        hp.append(C.tube("MaskCord", [Vector((sx * 0.105, -0.04, 1.47)), Vector((sx * 0.115, 0.03, 1.475)), Vector((sx * 0.07, 0.1, 1.48))], [0.005] * 3, 5, M["cord"]))

    cap = C.uv_sphere("HairCap", 0.118, (0, 0.012, 1.47), (1.02, 1.0, 1.06), 24, 12, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.03 and v.co.z < 1.53], context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.006)
    hp.append(cap)
    rng = random.Random(5)
    for i in range(5):
        x = -0.08 + i * 0.04
        hp.append(C.tube("Tuft", [Vector((x * 0.8, -0.02, 1.575)), Vector((x * 1.3, -0.07 + abs(x) * 0.3, 1.6 + rng.random() * 0.012))], [0.022, 0.002], 6, M["hair"], (1.0, 0.45)))
    for i in range(7):
        a = math.radians(-60 + i * 20)
        base = Vector((math.sin(a) * 0.09, 0.07 + math.cos(a) * 0.03, 1.44))
        tip = base + Vector((math.sin(a) * 0.05, 0.05 + rng.random() * 0.03, -0.1 - rng.random() * 0.05))
        hp.append(C.tube("HairSpike", [base, tip], [0.03, 0.002], 6, M["hair"], (1.0, 0.5)))
    tok = C.tube("Tokin", [Vector((0, -0.035, 1.565)), Vector((0, -0.045, 1.615))], [0.04, 0.03], 6, M["tokin"])
    hp.append(tok)
    for sx in (1.0, -1.0):
        hp.append(C.tube("TokinCord", [Vector((sx * 0.035, -0.04, 1.57)), Vector((sx * 0.1, -0.02, 1.47)), Vector((sx * 0.08, -0.06, 1.35))], [0.003] * 3, 4, M["cord"]))
    for p in hp:
        C.rigid(p, "head")
    parts += hp

    # ---- garb: cross collar, pompoms, sash, ragged trousers, sleeves, tabards, geta
    for sx in (1.0, -1.0):
        col = C.tube("Collar", [Vector((sx * 0.055, -0.04, 1.29)), Vector((sx * 0.02, -0.085, 1.2)), Vector((-sx * 0.02, -0.09, 1.1))], [0.02, 0.02, 0.02], 6, M["garb2"], (1.0, 0.4))
        C.rigid(col, "chest")
        parts.append(col)
    for z in (1.19, 1.1):
        pom = C.uv_sphere("Pompom", 0.026, (0, -0.1 if z > 1.15 else -0.095, z), (1, 0.8, 1), 10, 6, M["pom"])
        C.rigid(pom, "chest")
        parts.append(pom)
    sash = C.tube("Sash", [Vector((0, 0, 0.95)), Vector((0, 0, 0.9))], [0.1, 0.108], 16, M["sash"], (1.0, 0.8))
    C.rigid(sash, "hips")
    knot = C.tube("SashTail", [Vector((0.06, -0.085, 0.92)), Vector((0.08, -0.1, 0.82)), Vector((0.07, -0.1, 0.72))], [0.02, 0.022, 0.018], 6, M["sash"], (1.0, 0.35))
    C.weight_by_bones(knot, arm, ["hips", "thigh.L"], power=3.0)
    parts += [sash, knot]

    for s, sx in (("L", 1.0), ("R", -1.0)):
        a, b = P(f"thigh.{s}", 0.0) + Vector((0, 0, 0.04)), P(f"shin.{s}", 0.0)
        c = P(f"shin.{s}", 0.45)
        tr = C.tube(f"Trouser.{s}", [a, a.lerp(b, 0.5), b, c], [0.088, 0.085, 0.078, 0.085], 12, M["garb"], cap=False)
        jag_tube_end(tr, 12, 0.08, 40 + int(sx))
        C.solidify(tr, 0.006)
        C.weight_by_bones(tr, arm, ["hips", f"thigh.{s}", f"shin.{s}"], power=4.0)
        parts.append(tr)

        p0, p1, p2 = P(f"upper_arm.{s}", 0.1), P(f"forearm.{s}", 0.0), P(f"forearm.{s}", 0.7)
        sl = C.tube(f"Sleeve.{s}", [p0, p0.lerp(p1, 0.5), p1, p2], [0.058, 0.06, 0.068, 0.085], 12, M["garb"], cap=False)
        jag_tube_end(sl, 12, 0.05, 60 + int(sx))
        C.solidify(sl, 0.006)
        C.weight_by_bones(sl, arm, [f"upper_arm.{s}", f"forearm.{s}"], power=4.0)
        parts.append(sl)

        f = P(f"foot.{s}", 0.5)
        base = C.box("GetaBase", (0.085, 0.2, 0.022), (f.x, f.y - 0.005, 0.071), M["wood"])
        tooth = C.box("GetaTooth", (0.07, 0.03, 0.062), (f.x, f.y - 0.01, 0.03), M["wood"])
        strap = C.tube("GetaStrap", [Vector((f.x - 0.035, f.y + 0.02, 0.085)), Vector((f.x, f.y - 0.07, 0.115)), Vector((f.x + 0.035, f.y + 0.02, 0.085))], [0.006] * 3, 4, M["sash"])
        for o in (base, tooth, strap):
            C.rigid(o, f"foot.{s}")
        parts += [base, tooth, strap]

    for side, yoff, seed in (("front", -1, 70), ("back", 1, 71)):
        mid = -math.pi / 2 if side == "front" else math.pi / 2
        tab = flare("Tabard." + side, 0.93, 0.6, 0.112, 0.15, M["garb"], seg=8, rings=4, a0=mid - 0.6, a1=mid + 0.6, jag=0.14, seed=seed, yscale=0.85)
        C.solidify(tab, 0.005)
        C.weight_by_bones(tab, arm, ["hips", "thigh.L", "thigh.R"], power=3.0, keep=3)
        parts.append(tab)

    # Short ragged mantle over the shoulders.
    mantle = flare("Mantle", 1.3, 1.08, 0.06, 0.2, M["garb"], seg=28, rings=4, jag=0.07, seed=80, yscale=0.72, power=0.5)
    C.solidify(mantle, 0.006)
    C.weight_by_bones(mantle, arm, ["chest", "neck", "shoulder.L", "shoulder.R"], power=3.0, keep=3)
    parts.append(mantle)

    # ---- the single tattered wing (left) and a broken stump (right)
    A, B, Cc = Vector((0.06, 0.09, 1.2)), Vector((0.24, 0.17, 1.37)), Vector((0.44, 0.23, 1.3))
    wing_parts = {"wing.L": [], "wing_tip.L": []}
    bone_arm = C.tube("WingArm", [A, B, Cc], [0.03, 0.022, 0.01], 8, M["feather"])
    C.weight_by_bones(bone_arm, arm, ["wing.L", "wing_tip.L"], power=6.0)
    parts.append(bone_arm)
    normal = (Cc - A).cross(Vector((0, 0, -1))).normalized()
    rng = random.Random(9)
    n = 13
    for i in range(n):
        t = i / (n - 1)
        if i in (5, 9):
            continue  # missing feathers
        base = A.lerp(B, t * 2) if t < 0.5 else B.lerp(Cc, (t - 0.5) * 2)
        d = Vector((0.1, 0.2, -1.0)).lerp(Vector((0.9, 0.3, -0.45)), t).normalized()
        length = 0.22 + 0.3 * t
        if i in (3, 7, 11):
            length *= 0.55  # snapped
        tip = base + d * length
        mid = base.lerp(tip, 0.5) + normal * 0.01
        fth = C.tube("Feather", [base, mid, tip], [0.03, 0.038, 0.005 if i not in (3, 7, 11) else 0.03], 6, M["feather"], (1.0, 0.14), twist_up=normal)
        wing_parts["wing.L" if t < 0.45 else "wing_tip.L"].append(fth)
        if i % 2 == 0:
            cov_tip = base + d * length * 0.45 + normal * 0.012
            cov = C.tube("Covert", [base + normal * 0.012, cov_tip], [0.04, 0.012], 6, M["feather"], (1.0, 0.18), twist_up=normal)
            wing_parts["wing.L" if t < 0.45 else "wing_tip.L"].append(cov)
    for bname, objs in wing_parts.items():
        for o in objs:
            C.rigid(o, bname)
        parts += objs
    stump_root = Vector((-0.06, 0.09, 1.2))
    st = [C.tube("Stump", [stump_root, stump_root + Vector((-0.08, 0.05, 0.06))], [0.03, 0.018], 8, M["feather"])]
    for k in range(3):
        b = stump_root + Vector((-0.05 - 0.01 * k, 0.04, 0.04))
        st.append(C.tube("StumpFeather", [b, b + Vector((-0.03 - 0.02 * k, 0.03, -0.08 - 0.03 * k))], [0.02, 0.006], 6, M["feather"], (1.0, 0.25), twist_up=Vector((0, 1, 0))))
    for o in st:
        C.rigid(o, "chest")
    parts += st

    # ---- weapons: tanto (right hand), feather-leaf fan (left hand)
    grip = P("hand.R", 0.4)
    d = Vector((0.05, -1.0, 0.25)).normalized()
    wp = [
        C.tube("Hilt", [grip - d * 0.06, grip + d * 0.05], [0.014, 0.014], 6, M["cord"]),
        C.tube("Guard", [grip + d * 0.05, grip + d * 0.058], [0.026, 0.026], 8, M["steel"], (1.0, 0.6)),
        C.tube("Blade", [grip + d * 0.058, grip + d * 0.24, grip + d * 0.36], [0.018, 0.016, 0.001], 6, M["steel"], (0.22, 1.0), twist_up=Vector((0, 0, 1))),
    ]
    for o in wp:
        C.rigid(o, "hand.R")
    parts += wp

    fgrip = P("hand.L", 0.4)
    fd = Vector((-0.05, -0.6, 1.0)).normalized()
    fan_top = fgrip + fd * 0.12
    fan = [C.tube("FanHandle", [fgrip - fd * 0.05, fan_top], [0.011, 0.011], 6, M["wood"])]
    fside = fd.cross(Vector((1, 0, 0))).normalized()
    for k in range(7):
        ang = math.radians(-65 + k * 21.7)
        ldir = (fd * math.cos(ang) + fside * math.sin(ang)).normalized()
        L = 0.15 - abs(k - 3) * 0.015
        fan.append(C.tube("FanLobe", [fan_top, fan_top + ldir * L * 0.55, fan_top + ldir * L], [0.012, 0.03, 0.004], 6, M["leaf"], (1.0, 0.15), twist_up=Vector((1, 0, 0))))
    for o in fan:
        C.rigid(o, "hand.L")
    parts += fan

    # ---- animation
    action = make_action(arm)
    REST = {
        "spine": (10, 0, 0), "chest": (6, 0, 0), "head": (-12, 0, 0),
        "upper_arm.R": (18, 0, -10), "forearm.R": (45, 0, 0), "hand.R": (-20, 0, 0),
        "upper_arm.L": (10, 0, 12), "forearm.L": (30, 0, 0),
        "thigh.L": (14, 0, 3), "thigh.R": (4, 0, -3), "shin.L": (-24, 0, 0), "shin.R": (-12, 0, 0),
        "foot.L": (10, 0, 0), "foot.R": (8, 0, 0), "hips@loc": (0, -0.015, 0),
        "wing.L": (0, 0, 0), "wing_tip.L": (0, 0, 0),
    }

    def with_rest(p=None):
        out = dict(REST)
        out.update(p or {})
        return out

    # Idle: 60 frames. Slow breathing, a crow-like head cock, a ruffle of the wing.
    action("idle", 60, {
        0: with_rest(),
        20: with_rest({"chest": (3, 0, 0), "wing.L": (0, 0, 6), "wing_tip.L": (0, 0, -8)}),
        34: with_rest({"chest": (4, 0, 0), "head": (-12, 0, 0)}),
        37: with_rest({"chest": (4, 0, 0), "head": (-8, 18, -16)}),
        48: with_rest({"chest": (3, 0, 0), "head": (-8, 18, -16)}),
        52: with_rest({"chest": (2, 0, 0)}),
        60: with_rest(),
    }, loop=True)

    # Run: 20 frames. Low forward lean, blade trailing, wing tucked.
    def run_pose(ph):
        s = 1 if ph == 0 else -1
        return {
            "hips@loc": (0, -0.04 if ph == 0 else -0.01, 0),
            "hips": (0, 8 * s, 0), "spine": (22, 0, 0), "chest": (6, -10 * s, 0), "head": (-22, 6 * s, 0),
            "thigh.L": (48 * s, 0, 3), "thigh.R": (-48 * s, 0, -3),
            "shin.L": (-15 if s > 0 else -85, 0, 0), "shin.R": (-85 if s > 0 else -15, 0, 0),
            "foot.L": (0, 0, 0), "foot.R": (0, 0, 0),
            "upper_arm.L": (-40 * s + 5, 0, 14), "forearm.L": (55, 0, 0),
            "upper_arm.R": (-35, 0, -18), "forearm.R": (30, 0, 0), "hand.R": (-30, 0, 0),
            "wing.L": (-15, 0, -10), "wing_tip.L": (0, 0, -25),
        }
    action("run", 20, {0: run_pose(0), 5: {**run_pose(0), "hips@loc": (0, 0.0, 0)}, 10: run_pose(1),
                       15: {**run_pose(1), "hips@loc": (0, 0.0, 0)}, 20: run_pose(0)}, loop=True)

    # Slash: 18 frames. Right-to-left horizontal cut with the tanto, contact at frame 8.
    WIND = {"chest": (0, -45, 0), "spine": (6, -15, 0), "head": (-12, 20, 0),
            "upper_arm.R": (25, 0, -80), "forearm.R": (50, 0, 0), "hand.R": (-60, 0, 0),
            "upper_arm.L": (35, 0, 25), "thigh.R": (-10, 0, -3), "thigh.L": (22, 0, 3), "shin.L": (-30, 0, 0),
            "wing.L": (0, 0, 8)}
    HIT = {"chest": (8, 38, 0), "spine": (12, 15, 0), "head": (-18, -20, 0),
           "upper_arm.R": (85, 0, 20), "forearm.R": (5, 0, 0), "hand.R": (-70, 0, 0),
           "upper_arm.L": (-15, 0, 35), "thigh.R": (-12, 0, -3), "thigh.L": (35, 0, 3), "shin.L": (-25, 0, 0),
           "hips@loc": (0, -0.04, 0.1), "wing.L": (10, 0, 14), "wing_tip.L": (0, 0, 10)}
    action("slash", 18, {0: with_rest(), 4: with_rest(WIND), 8: with_rest(HIT),
                         11: with_rest({**HIT, "chest": (8, 48, 0)}), 18: with_rest()})

    # Gust: 20 frames. Fan raised overhead, wing spread, swept forward; the wind leaves at frame 10.
    RAISE = {"chest": (-10, 25, 0), "spine": (-6, 8, 0), "head": (-10, -10, 0),
             "upper_arm.L": (165, 0, 20), "forearm.L": (40, 0, 0), "hand.L": (-20, 0, 0),
             "upper_arm.R": (10, 0, -30), "thigh.R": (22, 0, -3), "thigh.L": (-5, 0, 3),
             "wing.L": (-20, 0, 45), "wing_tip.L": (0, 0, 25), "hips@loc": (0, 0.01, -0.03)}
    SWEEP = {"chest": (18, -25, 0), "spine": (12, -8, 0), "head": (-22, 10, 0),
             "upper_arm.L": (65, 0, -5), "forearm.L": (5, 0, 0), "hand.L": (30, 0, 0),
             "upper_arm.R": (0, 0, -35), "thigh.R": (30, 0, -3), "shin.R": (-30, 0, 0), "thigh.L": (-10, 0, 3),
             "wing.L": (-12, 0, 18), "wing_tip.L": (0, 0, 5), "hips@loc": (0, -0.04, 0.08)}
    action("gust", 20, {0: with_rest(), 6: with_rest(RAISE), 10: with_rest(SWEEP),
                        14: with_rest({**SWEEP, "upper_arm.L": (50, 0, -10)}), 20: with_rest()})

    # Hurt: 10 frames. Snap back, wing jerks open.
    action("hurt", 10, {0: with_rest(), 2: {"spine": (-15, 0, 0), "chest": (-15, 0, 0), "head": (-25, 0, 0),
                                            "upper_arm.L": (20, 0, 45), "upper_arm.R": (20, 0, -45),
                                            "wing.L": (-10, 0, 35), "wing_tip.L": (0, 0, 20), "hips@loc": (0, 0, 0.05)},
                        10: with_rest()})

    # Death: 30 frames. Knees give, then collapse backwards; the wing falls limp.
    action("death", 30, {
        0: with_rest(),
        8: {"spine": (20, 0, 0), "head": (25, 0, 0), "thigh.L": (60, 0, 0), "thigh.R": (60, 0, 0),
            "shin.L": (-100, 0, 0), "shin.R": (-100, 0, 0), "foot.L": (-25, 0, 0), "foot.R": (-25, 0, 0),
            "hips@loc": (0, -0.25, 0), "wing.L": (-10, 0, 20)},
        14: {"hips": (-40, 0, 5), "spine": (5, 0, 0), "head": (5, 10, 0), "thigh.L": (55, 0, 5), "thigh.R": (50, 0, -5),
             "shin.L": (-70, 0, 0), "shin.R": (-65, 0, 0), "upper_arm.L": (15, 0, 40), "upper_arm.R": (15, 0, -35),
             "foot.L": (-20, 0, 0), "foot.R": (-20, 0, 0), "hips@loc": (0, -0.38, 0.08), "wing.L": (10, 0, 22)},
        20: {"hips": (-75, 0, 10), "spine": (-10, 0, 0), "head": (-20, 20, 0), "thigh.L": (40, 0, 10),
             "thigh.R": (25, 0, -10), "shin.L": (-40, 0, 0), "shin.R": (-30, 0, 0), "upper_arm.L": (10, 0, 70),
             "upper_arm.R": (10, 0, -60), "hips@loc": (0, -0.66, 0.16), "wing.L": (25, 0, 25), "wing_tip.L": (0, 0, -5)},
        30: {"hips": (-88, 0, 10), "spine": (-5, 0, 0), "head": (-15, 30, 0), "thigh.L": (15, 0, 10),
             "thigh.R": (5, 0, -10), "shin.L": (-25, 0, 0), "shin.R": (-10, 0, 0), "upper_arm.L": (0, 0, 80),
             "upper_arm.R": (0, 0, -70), "hips@loc": (0, -0.7, 0.2), "wing.L": (35, 0, 20), "wing_tip.L": (0, 0, -8)},
    })

    finish(parts, "TenguScout", arm, "assets/models/characters/faithless/tengu_scout.glb")


if __name__ == "__main__":
    which = sys.argv[-1] if sys.argv[-1] in ("fairy", "tengu") else "all"
    if which in ("fairy", "all"):
        build_fairy()
    if which in ("tengu", "all"):
        build_tengu()
