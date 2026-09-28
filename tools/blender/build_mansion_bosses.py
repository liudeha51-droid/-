"""Scarlet Devil Mansion bosses: Hong Meiling and Sakuya Izayoi.

Outputs:
  assets/models/characters/meiling/meiling.glb
  assets/models/characters/sakuya/sakuya.glb

See data/bosses.json ("hong_meiling", "sakuya_izayoi") and docs/STORY_AND_CHARACTERS.md.
Both are canon characters who are "hollowing" as faith drains: they stay themselves,
with small, quiet signs of wear (a faded badge, a cracked watch, tired posture).

Same conventions as build_reimu.py:
Blender axes: Z up, characters face -Y, their left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
The adult rig, grounded() and action() come from build_story_characters.py.

Run:  python tools/blender/build_mansion_bosses.py [-- meiling|sakuya ...]
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402
import build_story_characters as SC  # noqa: E402
from build_story_characters import action, grounded, loft, start_animation, tri_count, P  # noqa: E402


# ================================================================ shared builders
def adult_bones(sh=0.17, hip=0.095):
    """The story characters' adult rig (~1.69 m before scaling), with shoulder / hip width."""
    bones = [
        ("root", (0, 0, 0), (0, 0, 0.15), None),
        ("hips", (0, 0, 0.96), (0, 0, 1.08), "root"),
        ("spine", (0, 0, 1.08), (0, 0, 1.22), "hips"),
        ("chest", (0, 0, 1.22), (0, 0, 1.4), "spine"),
        ("neck", (0, 0, 1.4), (0, 0, 1.48), "chest"),
        ("head", (0, 0, 1.48), (0, 0, 1.7), "neck"),
    ]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        bones += [
            (f"shoulder.{s}", (sx * 0.03, 0, 1.37), (sx * (sh - 0.02), 0, 1.37), "chest"),
            (f"upper_arm.{s}", (sx * sh, 0, 1.36), (sx * (sh + 0.07), 0.0, 1.08), f"shoulder.{s}"),
            (f"forearm.{s}", (sx * (sh + 0.07), 0, 1.08), (sx * (sh + 0.12), -0.03, 0.84), f"upper_arm.{s}"),
            (f"hand.{s}", (sx * (sh + 0.12), -0.03, 0.84), (sx * (sh + 0.14), -0.04, 0.75), f"forearm.{s}"),
            (f"thigh.{s}", (sx * hip, 0, 0.97), (sx * (hip + 0.005), 0, 0.52), "hips"),
            (f"shin.{s}", (sx * (hip + 0.005), 0, 0.52), (sx * (hip + 0.005), 0.01, 0.09), f"thigh.{s}"),
            (f"foot.{s}", (sx * (hip + 0.005), 0.01, 0.09), (sx * (hip + 0.005), -0.12, 0.02), f"shin.{s}"),
        ]
    return bones


def skin_body(arm, d, M, keys, rule):
    """Skin-modifier body. d: proportions; rule(bone_kind, center, bone_name) -> material key."""
    verts, edges, radii = [], [], []

    def v(co, r):
        verts.append(co)
        radii.append(r)
        return len(verts) - 1

    sh = d["sh"]
    hip = d["hip"]
    pelvis = v((0, 0, 0.95), (d["pelvis"], 0.09))
    waist = v((0, 0, 1.1), (d["waist"], 0.07))
    chest = v((0, 0, 1.26), (d["chest"], 0.085))
    upper = v((0, 0, 1.35), (d["chest"] - 0.004, 0.074))
    neck_b = v((0, 0, 1.41), (0.042, 0.042))
    neck_t = v((0, 0, 1.5), (0.034, 0.034))
    edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
    a = d.get("arm", 1.0)
    lg = d.get("leg", 1.0)
    for sx in (1.0, -1.0):
        s = v((sx * (sh - 0.01), 0, 1.365), (0.046 * a, 0.046 * a))
        el = v((sx * (sh + 0.07), 0, 1.08), (0.032 * a, 0.032 * a))
        wr = v((sx * (sh + 0.12), -0.03, 0.84), (0.024 * a, 0.024 * a))
        hd = v((sx * (sh + 0.135), -0.038, 0.765), (0.031 * a, 0.02 * a))
        hp = v((sx * hip, 0, 0.93), (0.075 * lg, 0.075 * lg))
        kn = v((sx * (hip + 0.005), 0, 0.52), (0.05 * lg, 0.05 * lg))
        an = v((sx * (hip + 0.005), 0.01, 0.1), (0.032, 0.032))
        toe = v((sx * (hip + 0.005), -0.1, 0.035), (0.036, 0.03))
        edges += [(upper, s), (s, el), (el, wr), (wr, hd), (pelvis, hp), (hp, kn), (kn, an), (an, toe)]

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

    names = [b.name for b in arm.data.bones if b.name != "root"]
    segs = {n: (arm.data.bones[n].head_local.copy(), arm.data.bones[n].tail_local.copy()) for n in names}
    for k in keys:
        obj.data.materials.append(M[k])
    for poly in obj.data.polygons:
        c = poly.center
        n = min(names, key=lambda n: C.seg_dist(c, *segs[n]))
        poly.material_index = keys.index(rule(n.split(".")[0], c, n))
        poly.use_smooth = True
    body_bones = [b for b in names]
    C.weight_by_bones(obj, arm, body_bones, power=4.0)
    return obj


def star_badge(name, center, r_out, r_in, mat, normal_rot=(0, 0, 0), chipped=None, thick=0.004):
    """Five-point star facing -Y. `chipped`: index of a worn-down point."""
    bm = bmesh.new()
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = r_out if k % 2 == 0 else r_in
        if chipped is not None and k == chipped * 2:
            r = r_out * 0.62
        pts.append(bm.verts.new((math.cos(a) * r, 0, math.sin(a) * r)))
    bm.faces.new(pts)
    obj = C.new_object(name, bm, mat, smooth=False)
    C.solidify(obj, thick)
    C.transform(obj, Matrix.Translation(Vector(center)) @ C.euler_matrix(normal_rot))
    return obj


def face(hc, M, lid_cut, iris_mat, lid_mat, brow_lift=0.0, brow_tilt=0.0, eye_z=-0.006, mouth_mat=None):
    """Head sphere, nose, mouth, eyes with upper lids. lid_cut: lid edge as a fraction of the
    eye's half-height (1.0 = lids fully open above the eye, 0.0 = half-closed)."""
    parts = []
    head = C.uv_sphere("Head", 0.1, tuple(hc), (0.92, 0.98, 1.1), 24, 14, M["skin"])
    for v in head.data.vertices:
        dz = v.co.z - hc.z
        if dz < 0:
            k = 1.0 - min(1.0, -dz / 0.11) * 0.3
            v.co.x *= k
            v.co.y = v.co.y * k - (1.0 - k) * 0.03
    parts.append(head)
    parts.append(C.uv_sphere("Nose", 0.008, tuple(hc + Vector((0, -0.096, -0.03))), (0.7, 0.8, 1.3), 8, 6, M["skin"]))
    parts.append(C.box("Mouth", (0.018, 0.004, 0.0025), tuple(hc + Vector((0, -0.089, -0.072))), mouth_mat or M["line"]))
    for sx in (1.0, -1.0):
        base = hc + Vector((sx * 0.036, -0.0905, eye_z))
        turn = Matrix.Rotation(math.radians(-20 * sx), 4, "Z")
        orient = Matrix.Translation(base) @ turn @ Matrix.Rotation(math.radians(90), 4, "X")

        def disc(mat, size, off, lift, dx=0.0, poly=None):
            bm = bmesh.new()
            if poly is None:
                bmesh.ops.create_circle(bm, cap_ends=True, segments=14, radius=1.0)
            else:
                bm.faces.new([bm.verts.new((x, y, 0)) for x, y in poly])
            m = orient @ Matrix.Translation((dx, lift, off)) @ Matrix.Diagonal((size[0], size[1], 1, 1))
            bm.transform(m)
            return C.new_object("Eye", bm, mat, smooth=False)

        ew = (0.019, 0.02)
        parts.append(disc(M["eye_white"], ew, 0.0, 0.0))
        parts.append(disc(iris_mat, (0.013, 0.017), 0.002, -0.002))
        parts.append(disc(M["pupil"], (0.006, 0.009), 0.0028, -0.003))
        parts.append(disc(M["shine"], (0.004, 0.0045), 0.0034, 0.006, dx=sx * 0.004))
        # Upper lid: the part of the eye above `lid_cut` is covered by skin.
        a0 = math.asin(max(-0.99, min(0.99, lid_cut)))
        arc = [(math.cos(a) * 1.15, math.sin(a) * 1.15) for a in [a0 + (math.pi - 2 * a0) * i / 10 for i in range(11)]]
        parts.append(disc(lid_mat, ew, 0.0042, 0.0, poly=arc))
        # Lash line along the lid edge, heavier at the outer corner.
        y = math.sin(a0) * 1.15 * ew[1]
        x = math.cos(a0) * 1.15 * ew[0]
        pa = orient @ Vector((-x * 1.05, y, 0.0046))
        pb = orient @ Vector((x * 1.05, y, 0.0046))
        outer, inner = (pa, pb) if (orient @ Vector((1, 0, 0)) - orient @ Vector((0, 0, 0))).x * sx < 0 else (pb, pa)
        parts.append(C.tube("Lash", [inner, inner.lerp(outer, 0.5) + Vector((0, 0, 0.0015)), outer], [0.0016, 0.0022, 0.0026], 5, M["line"]))
        # Brow.
        b0 = hc + Vector((sx * 0.016, -0.094, 0.028 + brow_lift))
        b1 = hc + Vector((sx * 0.056, -0.08, 0.03 + brow_lift + brow_tilt))
        parts.append(C.tube("Brow", [b0, b0.lerp(b1, 0.5) + Vector((0, -0.002, 0.004)), b1], [0.002, 0.0028, 0.0015], 5, M["brow"], (1.0, 0.5)))
    return parts


def hair_cap(hc, M, open_z=0.045, r=0.108):
    cap = C.uv_sphere("HairCap", r, tuple(hc + Vector((0, 0.008, 0.01))), (0.95, 1.0, 1.08), 24, 14, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = [v for v in bm.verts if v.co.y < -0.03 and v.co.z < hc.z + open_z]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(cap.data)
    bm.free()
    C.solidify(cap, 0.005)
    return cap


def bangs(hc, M, xs, drops, depth=-0.085, top_z=0.105, base_z=0.045):
    parts = []
    for x, drop in zip(xs, drops):
        top = hc + Vector((x * 0.8, depth, top_z))
        bottom = hc + Vector((x * 1.1, -0.106 + abs(x) * 0.25, base_z - drop + abs(x) * 0.4))
        mid = top.lerp(bottom, 0.5) + Vector((0, -0.013, 0))
        parts.append(C.tube("Bang", [top, mid, bottom], [0.019, 0.015, 0.002], 7, M["hair"], (1.0, 0.45)))
    return parts


def braid(name, pts, r, mat, beads=8, tie_mat=None, bow=0.0):
    """A plait: alternating squashed beads along a polyline, tied off with a ribbon bow."""
    parts = []
    path = [Vector(p) for p in pts]
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    total = lengths[-1]

    def at(t):
        s = t * total
        for i in range(1, len(path)):
            if s <= lengths[i] or i == len(path) - 1:
                u = (s - lengths[i - 1]) / max(1e-6, lengths[i] - lengths[i - 1])
                return path[i - 1].lerp(path[i], min(1.0, u)), (path[i] - path[i - 1]).normalized()
    for i in range(beads):
        t = (i + 0.5) / beads
        c, d = at(t)
        side = d.cross(Vector((0, 1, 0))).normalized()
        rr = r * (1.0 - 0.35 * t)
        c = c + side * (rr * 0.25 * (1 if i % 2 else -1))
        b = C.uv_sphere(name, 1.0, (0, 0, 0), (rr, rr * 0.8, rr * 1.45), 8, 5, mat)
        rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        C.transform(b, Matrix.Translation(c) @ rot @ Matrix.Rotation(math.radians(22 if i % 2 else -22), 4, "Y"))
        parts.append(b)
    end, d = at(1.0)
    parts.append(C.tube(name + "Tip", [end - d * 0.005, end + d * 0.04], [r * 0.6, 0.002], 6, mat))
    if tie_mat is not None:
        knot = end - d * 0.004
        parts.append(C.uv_sphere(name + "Tie", r * 0.75, tuple(knot), (1.1, 1.1, 0.7), 8, 5, tie_mat))
        if bow > 0:
            for sx in (1.0, -1.0):
                lobe = C.uv_sphere(name + "Bow", 1.0, (0, 0, 0), (bow, bow * 0.35, bow * 0.6), 10, 6, tie_mat)
                C.transform(lobe, Matrix.Translation(knot + Vector((sx * bow * 0.9, -0.004, 0.002))) @ Matrix.Rotation(math.radians(sx * -18), 4, "Y"))
                parts.append(lobe)
                parts.append(C.tube(name + "BowTail", [knot, knot + Vector((sx * bow * 0.5, -0.006, -bow * 1.6))], [bow * 0.3, bow * 0.4], 6, tie_mat, (1.0, 0.3)))
    return parts


def panel_weights(obj, arm, top_z, bottom_z, side_split=True, max_leg=0.75):
    """Hanging cloth panel: hips at the top, blending into the thighs by the hem."""
    for n in ("hips", "thigh.L", "thigh.R"):
        obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)
    for v in obj.data.vertices:
        t = max(0.0, min(1.0, (top_z - v.co.z) / (top_z - bottom_z)))
        leg = max_leg * t ** 1.2
        if side_split:
            wl = 0.5 + max(-0.5, min(0.5, v.co.x / 0.09))
        else:
            wl = 0.5
        obj.vertex_groups["hips"].add([v.index], 1.0 - leg, "REPLACE")
        obj.vertex_groups["thigh.L"].add([v.index], leg * wl, "REPLACE")
        obj.vertex_groups["thigh.R"].add([v.index], leg * (1 - wl), "REPLACE")


def cloth_panel(name, mat, z_top, z_bot, w_top, w_bot, y_top, y_bot, curve=0.03, cols=10, rows=8, jag=0.0, back=False):
    """A slightly curved hanging panel (front: -Y, back: +Y)."""
    bm = bmesh.new()
    grid = []
    sgn = 1.0 if back else -1.0
    for r in range(rows + 1):
        t = r / rows
        z = z_top + (z_bot - z_top) * t
        w = w_top + (w_bot - w_top) * t ** 0.8
        y = y_top + (y_bot - y_top) * t
        row = []
        for c in range(cols + 1):
            u = -1.0 + 2.0 * c / cols
            zz = z
            if r == rows and jag:
                zz += jag * (1 if c % 2 else -0.4)
            row.append(bm.verts.new((u * w, sgn * (y + curve * (1 - u * u)), zz)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat)


def scale_rig(arm, objs, k):
    """Uniform rescale of the armature and meshes (weights / rolls are kept)."""
    C.activate(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in arm.data.edit_bones:
        eb.head = eb.head * k
        eb.tail = eb.tail * k
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in objs:
        C.transform(o, Matrix.Scale(k, 4))


def finish(name, arm, parts):
    obj = C.join(parts, name)
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm
    return obj


def base_materials():
    return {
        "eye_white": C.material("EyeWhite", (0.93, 0.92, 0.9), 0.3),
        "pupil": C.material("Pupil", (0.04, 0.04, 0.06), 0.2),
        "shine": C.material("EyeShine", (1.0, 1.0, 1.0), 0.1, emission=0.8),
        "line": C.material("Line", (0.12, 0.06, 0.06), 0.6),
    }


# ================================================================ 1. Hong Meiling
def build_meiling():
    C.reset_scene()
    M = base_materials()
    M.update({
        "skin": C.material("Skin", (0.98, 0.82, 0.72), 0.6),
        "lid": C.material("Eyelid", (0.9, 0.72, 0.64), 0.6),
        "hair": C.material("RedHair", (0.6, 0.1, 0.08), 0.5),
        "brow": C.material("RedBrow", (0.42, 0.07, 0.05), 0.6),
        "iris": C.material("IrisBlueGrey", (0.22, 0.36, 0.5), 0.2),
        "green": C.material("DressGreen", (0.13, 0.38, 0.22), 0.7),
        "green_dk": C.material("DressGreenDark", (0.06, 0.2, 0.12), 0.7),
        "hat": C.material("HatGreen", (0.12, 0.34, 0.2), 0.75),
        "trouser": C.material("Trousers", (0.84, 0.83, 0.78), 0.85),
        "cuff": C.material("CuffWhite", (0.88, 0.87, 0.82), 0.7),
        "shoe": C.material("Slipper", (0.08, 0.07, 0.07), 0.5),
        "badge": C.material("FadedBadge", (0.58, 0.55, 0.44), 0.7, 0.3),
        "badge_dk": C.material("BadgeWorn", (0.3, 0.29, 0.25), 0.8),
        "ribbon": C.material("BraidRibbon", (0.07, 0.16, 0.1), 0.6),
        "qi": C.material("FaintQi", (0.7, 0.55, 0.45), 0.6, emission=0.25),
    })

    bones = adult_bones(sh=0.175, hip=0.1)
    arm = SC.build_armature("MeilingRig", bones)
    hc = Vector((0, 0, 1.565))

    def rule(kind, c, n):
        if kind in ("head", "neck"):
            return "skin"
        if kind in ("forearm", "hand"):
            return "skin"
        if kind == "foot" or (kind == "shin" and c.z < 0.13):
            return "shoe"
        if kind == "shin" or (kind == "thigh" and c.z < 0.74):
            return "trouser"
        return "green"

    body = skin_body(arm, {"sh": 0.175, "hip": 0.1, "pelvis": 0.128, "waist": 0.09, "chest": 0.116, "arm": 1.08, "leg": 1.05}, M,
                     ["green", "skin", "trouser", "shoe"], rule)

    # ------------------------------------------------------------ head
    head = face(hc, M, lid_cut=0.18, iris_mat=M["iris"], lid_mat=M["lid"], brow_lift=0.004, brow_tilt=-0.004)
    head.append(hair_cap(hc, M))
    head += bangs(hc, M, [-0.075, -0.052, -0.03, -0.01, 0.012, 0.034, 0.056, 0.078], [0.0, 0.02, 0.0, 0.03, 0.01, 0.025, 0.0, 0.0])
    # Longer side locks framing the face.
    for sx in (1.0, -1.0):
        pts = [hc + Vector((sx * 0.08, -0.05, 0.07)), hc + Vector((sx * 0.094, -0.07, 0.0)), hc + Vector((sx * 0.092, -0.068, -0.07)), hc + Vector((sx * 0.085, -0.06, -0.11))]
        head.append(C.tube("SideLock", pts, [0.022, 0.022, 0.016, 0.002], 8, M["hair"], (1.0, 0.5), twist_up=Vector((0, -1, 0))))
    # Beret-style cap with the star badge (faded, one point worn away).
    hat_m = Matrix.Translation(hc + Vector((0.0, 0.004, 0.118))) @ Matrix.Rotation(math.radians(-6), 4, "X") @ Matrix.Rotation(math.radians(4), 4, "Y")
    crown = C.uv_sphere("Beret", 1.0, (0, 0, 0), (0.122, 0.118, 0.052), 24, 10, M["hat"])
    C.transform(crown, hat_m @ Matrix.Translation((0, 0, 0.012)))
    band = loft("BeretBand", [((0, 0, -0.012), 0.101, 0.105), ((0, 0, 0.014), 0.106, 0.11)], 24, M["green_dk"])
    C.solidify(band, 0.004)
    C.transform(band, hat_m)
    head += [crown, band]
    star_c = hat_m @ Vector((0, -0.114, 0.004))
    head.append(star_badge("StarBadge", star_c, 0.024, 0.01, M["badge"], normal_rot=(-8, 0, 0), chipped=2))
    disc = C.tube("BadgeCore", [star_c + Vector((0, -0.002, 0)), star_c + Vector((0, -0.004, 0))], [0.0065, 0.0065], 10, M["badge_dk"])
    head.append(disc)
    for p in head:
        C.rigid(p, "head")

    # ------------------------------------------------------------ long hair and braids
    hair = []
    back = [hc + Vector((0, 0.06, 0.07)), hc + Vector((0, 0.1, -0.04)), hc + Vector((0, 0.125, -0.2)), hc + Vector((0, 0.13, -0.4)), hc + Vector((0, 0.12, -0.6))]
    hair.append(C.tube("BackHair", back, [0.1, 0.125, 0.14, 0.14, 0.12], 16, M["hair"], (1.0, 0.33), twist_up=Vector((0, -1, 0))))
    for i in range(7):
        x = -0.105 + i * 0.035
        ln = 0.1 + (0.05 if i % 2 else 0.0) + (0.04 if i == 3 else 0.0)
        a = hc + Vector((x, 0.12, -0.55))
        hair.append(C.tube("HairTip", [a, a + Vector((x * 0.1, 0.004, -ln))], [0.03, 0.002], 7, M["hair"], (1.0, 0.45), twist_up=Vector((0, -1, 0))))
    for sx in (1.0, -1.0):
        side = [hc + Vector((sx * 0.095, 0.02, 0.04)), hc + Vector((sx * 0.12, 0.05, -0.1)), hc + Vector((sx * 0.13, 0.08, -0.3)), hc + Vector((sx * 0.12, 0.1, -0.48))]
        hair.append(C.tube("SideHair", side, [0.035, 0.04, 0.035, 0.003], 9, M["hair"], (0.6, 1.0), twist_up=Vector((0, -1, 0))))
        pts = [hc + Vector((sx * 0.09, -0.035, -0.02)), hc + Vector((sx * 0.11, -0.05, -0.11)), hc + Vector((sx * 0.13, -0.075, -0.22)), hc + Vector((sx * 0.135, -0.095, -0.33))]
        hair += braid("Braid", pts, 0.02, M["hair"], beads=9, tie_mat=M["ribbon"], bow=0.018)
    for p in hair:
        C.weight_by_bones(p, arm, ["head", "neck", "chest", "spine"], power=4.0)

    # ------------------------------------------------------------ outfit
    parts = []
    # Mandarin collar, the diagonal cheongsam flap and knot buttons.
    collar = loft("Collar", [((0, 0.0, 1.405), 0.05, 0.048), ((0, 0.003, 1.455), 0.045, 0.043)], 20, M["green"])
    C.solidify(collar, 0.006)
    collar_trim = loft("CollarTrim", [((0, 0.003, 1.452), 0.046, 0.044), ((0, 0.003, 1.462), 0.046, 0.044)], 20, M["cuff"])
    C.solidify(collar_trim, 0.004)
    flap = [Vector((0.0, -0.05, 1.415)), Vector((-0.04, -0.09, 1.37)), Vector((-0.085, -0.095, 1.32)), Vector((-0.11, -0.07, 1.26))]
    front = [collar, collar_trim, C.tube("Flap", flap, [0.007, 0.007, 0.007, 0.006], 6, M["green_dk"])]
    for p in (flap[0].lerp(flap[1], 0.4), flap[1].lerp(flap[2], 0.5), flap[3]):
        front.append(C.uv_sphere("KnotButton", 0.009, tuple(p + Vector((0, -0.006, 0))), (1.2, 0.8, 1.0), 8, 5, M["green_dk"]))
        front.append(C.tube("Frog", [p + Vector((-0.016, -0.006, 0)), p + Vector((0.016, -0.006, 0))], [0.004, 0.004], 5, M["green_dk"]))
    for p in front:
        C.weight_by_bones(p, arm, ["chest", "neck"], power=4.0)
    parts += front
    # Waist sash knot (dark green).
    sash = loft("Sash", [((0, 0, 1.06), 0.1, 0.082), ((0, 0, 1.1), 0.097, 0.078)], 24, M["green_dk"])
    C.solidify(sash, 0.006)
    C.weight_by_bones(sash, arm, ["hips", "spine"], power=4.0)
    parts.append(sash)

    # Front and back skirt panels of the dress; the side slits show the trousers.
    for back_side in (False, True):
        pan = cloth_panel("DressPanel", M["green"], 1.0, 0.4, 0.12, 0.15, 0.112, 0.14, curve=0.03, back=back_side, rows=9)
        C.solidify(pan, 0.006)
        panel_weights(pan, arm, 0.98, 0.4, max_leg=0.9)
        hem = cloth_panel("PanelHem", M["green_dk"], 0.43, 0.4, 0.148, 0.151, 0.137, 0.141, curve=0.03, back=back_side, rows=1)
        C.solidify(hem, 0.009)
        panel_weights(hem, arm, 0.98, 0.4, max_leg=0.9)
        parts += [pan, hem]

    # Sleeves: full green sleeves with white cuffs; the right one torn at the elbow.
    for s in ("L", "R"):
        p0 = P(f"upper_arm.{s}", 0.0) + Vector((0, 0, 0.02))
        p1 = P(f"forearm.{s}", 0.0)
        p2 = P(f"forearm.{s}", 1.0)
        d1 = (p1 - p0).normalized()
        d2 = (p2 - p1).normalized()
        if s == "L":
            pts = [p0 - d1 * 0.01, p0.lerp(p1, 0.5), p1, p1.lerp(p2, 0.5), p2 - d2 * 0.015]
            radii = [0.05, 0.048, 0.04, 0.038, 0.04]
        else:
            pts = [p0 - d1 * 0.01, p0.lerp(p1, 0.5), p1, p1 + d2 * 0.05]
            radii = [0.05, 0.048, 0.041, 0.043]
        sleeve = C.tube(f"Sleeve.{s}", pts, radii, 14, M["green"], cap=False)
        if s == "R":
            # Ragged edge: the end ring zigzags back up the arm.
            end = pts[-1]
            for v in sleeve.data.vertices:
                if (v.co - end).length < 0.06 and (v.co - end).dot(d2) > -0.01:
                    ang = math.atan2(v.co.y - end.y, v.co.x - end.x)
                    v.co -= d2 * (0.012 + 0.018 * (0.5 + 0.5 * math.sin(ang * 5.0)) + 0.01 * math.sin(ang * 13.0))
        C.solidify(sleeve, 0.005)
        C.weight_by_bones(sleeve, arm, [f"upper_arm.{s}", f"forearm.{s}", f"shoulder.{s}"], power=4.0)
        parts.append(sleeve)
        if s == "L":
            cuff = C.tube("Cuff.L", [p2 - d2 * 0.04, p2 - d2 * 0.012], [0.043, 0.044], 14, M["cuff"], cap=False)
            C.solidify(cuff, 0.006)
            C.rigid(cuff, "forearm.L")
            parts.append(cuff)
        else:
            # A strip of bandage wraps the bare forearm below the tear.
            w0, w1 = P("forearm.R", 0.55), P("forearm.R", 0.8)
            wrap = C.tube("Wrap.R", [w0, w1], [0.03, 0.027], 10, M["cuff"])
            C.rigid(wrap, "forearm.R")
            parts.append(wrap)
    # Qi-glow wristbands (faint): a hint of the rainbow at her fists.
    for s in ("L", "R"):
        w = P(f"hand.{s}", 0.0)
        d = (P(f"hand.{s}", 1.0) - w).normalized()
        band = C.tube(f"QiBand.{s}", [w - d * 0.012, w + d * 0.004], [0.027, 0.027], 10, M["qi"])
        C.rigid(band, f"forearm.{s}")
        parts.append(band)
    model_parts = [body] + head + hair + parts
    K = 1.72 / 1.69
    scale_rig(arm, model_parts, K)
    meiling = finish("Meiling", arm, model_parts)

    # ------------------------------------------------------------ animation
    start_animation(arm)

    # Fighting stance: left foot forward, knees soft, left palm guarding, right fist chambered.
    STANCE = {
        "hips": (0, 12, 0), "spine": (4, -8, 0), "chest": (2, -6, 0), "neck": (0, 0, 0), "head": (4, 4, 0),
        "thigh.L": (32, 0, 6), "shin.L": (-38, 0, 0), "foot.L": (4, 0, 0),
        "thigh.R": (-14, 0, -10), "shin.R": (-26, 0, 0), "foot.R": (8, 0, 0),
        "upper_arm.L": (48, 0, 12), "forearm.L": (72, 0, 0), "hand.L": (-25, 0, 0),
        "upper_arm.R": (-8, 0, -16), "forearm.R": (105, 0, 0), "hand.R": (0, 0, 0),
    }

    def st(p, ground=True):
        out = dict(STANCE)
        out.update(p)
        return grounded(out) if ground else out

    IDLE_A = st({})
    IDLE_B = st({"chest": (-1, -6, 0), "spine": (3, -8, 0), "head": (8, 4, 1), "upper_arm.L": (46, 0, 13), "forearm.L": (70, 0, 0), "shin.L": (-42, 0, 0), "shin.R": (-30, 0, 0), "thigh.L": (34, 0, 6)})
    action("idle", 60, {0: IDLE_A, 30: IDLE_B, 60: IDLE_A}, loop=True)

    # Walk: 32f loop, guard kept up. Left heel strikes at 0, right at 16.
    GUARD = {"spine": (6, 0, 0), "chest": (0, 0, 0), "upper_arm.L": (40, 0, 10), "forearm.L": (80, 0, 0), "hand.L": (-20, 0, 0), "upper_arm.R": (-4, 0, -14), "forearm.R": (100, 0, 0), "head": (2, 0, 0)}

    def walk_contact(s):
        return grounded({**GUARD, "hips": (0, 6 * s, 0), "chest": (0, -8 * s, 0),
                         "thigh.L": (24 * s, 0, 2), "thigh.R": (-24 * s, 0, -2),
                         "shin.L": (-6 if s > 0 else -18, 0, 0), "shin.R": (-18 if s > 0 else -6, 0, 0),
                         "foot.L": (14 if s > 0 else -8, 0, 0), "foot.R": (-8 if s > 0 else 14, 0, 0)})

    def walk_pass(s):
        return grounded({**GUARD, "hips": (0, 0, -2 * s),
                         "thigh.L": (-2 if s > 0 else 30, 0, 2), "thigh.R": (30 if s > 0 else -2, 0, -2),
                         "shin.L": (-4 if s > 0 else -60, 0, 0), "shin.R": (-60 if s > 0 else -4, 0, 0),
                         "foot.L": (0, 0, 0), "foot.R": (0, 0, 0)})

    action("walk", 32, {0: walk_contact(1), 8: walk_pass(1), 16: walk_contact(-1), 24: walk_pass(-1), 32: walk_contact(1)}, loop=True)

    # Palm strike ("Rising Palm"): 20f, contact f9. Step in, right palm drives up and forward.
    PS_WIND = st({"hips": (0, 20, 0), "spine": (8, -18, 0), "chest": (4, -20, 0), "upper_arm.R": (-25, 0, -18), "forearm.R": (110, 0, 0), "hand.R": (-40, 0, 0),
                  "upper_arm.L": (70, 0, 5), "forearm.L": (40, 0, 0), "thigh.L": (38, 0, 6), "shin.L": (-55, 0, 0), "thigh.R": (-10, 0, -10), "shin.R": (-40, 0, 0), "foot.R": (10, 0, 0)})
    PS_HIT = st({"hips": (0, -10, 0), "spine": (-2, 12, 0), "chest": (-6, 22, 0), "head": (-4, -10, 0),
                 "upper_arm.R": (96, 0, 4), "forearm.R": (10, 0, 0), "hand.R": (-78, 0, 0),
                 "upper_arm.L": (-25, 0, 20), "forearm.L": (95, 0, 0), "hand.L": (0, 0, 0),
                 "thigh.L": (52, 0, 4), "shin.L": (-58, 0, 0), "foot.L": (6, 0, 0), "thigh.R": (-32, 0, -6), "shin.R": (-6, 0, 0), "foot.R": (-18, 0, 0),
                 "hips@loc": (0, 0, 0.12)})
    PS_HOLD = {**PS_HIT, "chest": (-8, 26, 0)}
    action("palm_strike", 20, {0: st({}), 5: PS_WIND, 9: PS_HIT, 12: PS_HOLD, 20: st({})})

    # Kick combo: 30f. Left front snap kick (contact f9), then a right roundhouse (contact f20).
    K1_WIND = st({"spine": (-4, -8, 0), "thigh.L": (75, 0, 4), "shin.L": (-100, 0, 0), "foot.L": (-30, 0, 0), "thigh.R": (-4, 0, -6), "shin.R": (-18, 0, 0), "foot.R": (6, 0, 0), "upper_arm.L": (40, 0, 20), "forearm.L": (90, 0, 0)})
    K1_HIT = st({"spine": (-14, -6, 0), "chest": (-4, -4, 0), "head": (14, 4, 0), "thigh.L": (98, 0, 2), "shin.L": (-8, 0, 0), "foot.L": (-40, 0, 0), "thigh.R": (-6, 0, -6), "shin.R": (-10, 0, 0), "foot.R": (8, 0, 0),
                 "upper_arm.L": (30, 0, 30), "forearm.L": (80, 0, 0), "upper_arm.R": (10, 0, -30), "forearm.R": (90, 0, 0), "hips@loc": (0, 0, 0.06)})
    K2_WIND = st({"hips": (0, -20, 0), "spine": (0, -20, 0), "chest": (0, -15, 0), "head": (0, 30, 0), "thigh.L": (36, 0, 4), "shin.L": (-30, 0, 0), "foot.L": (6, 0, 0),
                  "thigh.R": (-20, 0, -8), "shin.R": (-40, 0, 0), "foot.R": (0, 0, 0), "upper_arm.L": (60, 0, 40), "forearm.L": (60, 0, 0), "upper_arm.R": (20, 0, -40), "forearm.R": (80, 0, 0), "hips@loc": (0, 0, 0.1)})
    K2_HIT = st({"hips": (0, 30, 10), "spine": (-4, -10, -14), "chest": (-4, -20, -8), "head": (6, -25, 10),
                 "thigh.L": (6, -30, 10), "shin.L": (-16, 0, 0), "foot.L": (8, 0, 0),
                 "thigh.R": (25, 0, -88), "shin.R": (-6, 0, 0), "foot.R": (-30, 0, 0),
                 "upper_arm.L": (30, 0, 70), "forearm.L": (40, 0, 0), "upper_arm.R": (40, 0, -20), "forearm.R": (100, 0, 0), "hips@loc": (0, 0, 0.12)})
    K2_FOLLOW = {**K2_HIT, "hips": (0, 50, 10), "thigh.R": (35, 0, -75), "shin.R": (-30, 0, 0)}
    action("kick_combo", 30, {0: st({}), 5: K1_WIND, 9: K1_HIT, 12: K1_HIT, 15: K2_WIND, 20: K2_HIT, 23: K2_FOLLOW, 30: st({})})

    # Rising kick ("Earth Dragon"): 24f, contact f11. Crouch, spring up, right leg drives skyward.
    RK_CROUCH = st({"spine": (18, 0, 0), "chest": (8, 0, 0), "head": (-10, 0, 0), "thigh.L": (70, 0, 8), "shin.L": (-100, 0, 0), "foot.L": (12, 0, 0),
                    "thigh.R": (20, 0, -10), "shin.R": (-95, 0, 0), "foot.R": (-20, 0, 0), "upper_arm.L": (-30, 0, 20), "forearm.L": (40, 0, 0), "upper_arm.R": (-35, 0, -20), "forearm.R": (40, 0, 0)})
    RK_HIT = {"spine": (-18, 0, 0), "chest": (-10, 0, 0), "head": (20, 0, 0), "neck": (4, 0, 0),
              "thigh.R": (150, 0, -4), "shin.R": (-4, 0, 0), "foot.R": (-40, 0, 0),
              "thigh.L": (55, 0, 8), "shin.L": (-110, 0, 0), "foot.L": (-30, 0, 0),
              "upper_arm.L": (40, 0, 60), "forearm.L": (30, 0, 0), "upper_arm.R": (-20, 0, -55), "forearm.R": (30, 0, 0), "hips@loc": (0, 0.32, 0.1)}
    RK_PEAK = {**RK_HIT, "thigh.R": (160, 0, -4), "hips@loc": (0, 0.36, 0.12)}
    RK_LAND = st({"spine": (14, 0, 0), "thigh.L": (60, 0, 8), "shin.L": (-80, 0, 0), "thigh.R": (10, 0, -10), "shin.R": (-70, 0, 0), "foot.R": (-10, 0, 0), "upper_arm.L": (50, 0, 30), "upper_arm.R": (20, 0, -30), "forearm.R": (80, 0, 0), "hips@loc": (0, 0, 0.1)})
    action("rising_kick", 24, {0: st({}), 6: RK_CROUCH, 11: RK_HIT, 14: RK_PEAK, 18: RK_LAND, 24: st({})})

    # Qi burst: 30f, release f16. Sink into a horse stance, gather at the hip, push both palms out.
    HORSE = {"hips": (0, 0, 0), "spine": (6, 0, 0), "thigh.L": (30, 0, 22), "shin.L": (-55, 0, 0), "foot.L": (20, 0, -10), "thigh.R": (30, 0, -22), "shin.R": (-55, 0, 0), "foot.R": (20, 0, 10)}
    QB_GATHER = grounded({**HORSE, "chest": (0, 25, 0), "head": (6, -20, 0), "upper_arm.L": (40, 0, -30), "forearm.L": (110, 0, 0), "hand.L": (-20, 0, 0),
                          "upper_arm.R": (-20, 0, -10), "forearm.R": (100, 0, 0), "hand.R": (-40, 0, 0)})
    QB_CHARGE = grounded({**QB_GATHER, "spine": (10, 0, 0), "chest": (2, 30, 0), "thigh.L": (36, 0, 24), "thigh.R": (36, 0, -24), "shin.L": (-66, 0, 0), "shin.R": (-66, 0, 0)})
    QB_RELEASE = grounded({**HORSE, "spine": (2, 0, 0), "chest": (-6, -6, 0), "head": (-6, 0, 0),
                           "upper_arm.L": (84, 0, -10), "forearm.L": (6, 0, 0), "hand.L": (-75, 0, 0),
                           "upper_arm.R": (84, 0, 10), "forearm.R": (6, 0, 0), "hand.R": (-75, 0, 0), "hips@loc": (0, 0, 0.06)})
    action("qi_burst", 30, {0: st({}), 8: QB_GATHER, 13: QB_CHARGE, 16: QB_RELEASE, 22: QB_RELEASE, 30: st({})})

    # Stagger (poise broken): 30f. Knocked back, guard gone, head swimming; recovers her stance.
    SG_HIT = st({"spine": (-14, 6, 0), "chest": (-10, 8, 0), "head": (-20, 10, 0), "upper_arm.L": (20, 0, 40), "forearm.L": (30, 0, 0), "upper_arm.R": (25, 0, -45), "forearm.R": (30, 0, 0),
                 "thigh.L": (20, 0, 6), "shin.L": (-20, 0, 0), "thigh.R": (-25, 0, -10), "shin.R": (-35, 0, 0), "hips@loc": (0, 0, -0.1)})
    SG_SLUMP = st({"spine": (22, 0, 4), "chest": (14, 0, 0), "neck": (10, 0, 0), "head": (24, -8, 0), "upper_arm.L": (10, 0, 6), "forearm.L": (20, 0, 0), "upper_arm.R": (14, 0, -6), "forearm.R": (24, 0, 0),
                   "thigh.L": (30, 0, 8), "shin.L": (-50, 0, 0), "thigh.R": (-6, 0, -10), "shin.R": (-40, 0, 0), "hips@loc": (0, 0, -0.12)})
    action("stagger", 30, {0: st({}), 3: SG_HIT, 10: SG_SLUMP, 22: {**SG_SLUMP, "head": (28, -4, 0)}, 30: st({})})

    # Hurt: 12f. A sharp flinch, guard snaps back up.
    action("hurt", 12, {0: st({}), 3: st({"spine": (-10, 8, 0), "chest": (-10, 6, 0), "head": (-18, 6, 0), "upper_arm.L": (30, 0, 35), "forearm.L": (50, 0, 0), "upper_arm.R": (20, 0, -30), "hips@loc": (0, 0, -0.05)}), 12: st({})})

    # Death: 40f. She sinks to her knees, sits back and her head nods forward, as if dozing at her post.
    SEIZA = {"thigh.L": (76, 0, 4), "thigh.R": (76, 0, -4), "shin.L": (-166, 0, 0), "shin.R": (-166, 0, 0), "foot.L": (-78, 0, 0), "foot.R": (-78, 0, 0)}
    D_KNEE = grounded({"thigh.L": (80, 0, 4), "shin.L": (-80, 0, 0), "foot.L": (0, 0, 0), "thigh.R": (-8, 0, -4), "shin.R": (-95, 0, 0), "foot.R": (-40, 0, 0), "spine": (14, 0, 0), "head": (16, 0, 0),
                       "upper_arm.L": (20, 0, 8), "forearm.L": (40, 0, 0), "upper_arm.R": (14, 0, -8), "forearm.R": (35, 0, 0)})
    D_SIT = grounded({**SEIZA, "spine": (6, 0, 0), "chest": (2, 0, 0), "head": (10, 0, 0), "upper_arm.L": (24, 0, 2), "forearm.L": (55, 0, 0), "upper_arm.R": (24, 0, -2), "forearm.R": (55, 0, 0)})
    D_DOZE = grounded({**SEIZA, "spine": (16, 0, 2), "chest": (10, 0, 2), "neck": (14, 0, 0), "head": (30, 6, 4), "upper_arm.L": (20, 0, 0), "forearm.L": (50, 0, 0), "upper_arm.R": (20, 0, 0), "forearm.R": (50, 0, 0)})
    action("death", 40, {0: st({}), 6: st({"spine": (-8, 0, 0), "head": (-12, 0, 0), "hips@loc": (0, 0, -0.03)}), 16: D_KNEE, 28: D_SIT, 36: D_DOZE, 40: D_DOZE})

    arm.animation_data.action = bpy.data.actions["idle"]
    C.export_glb("assets/models/characters/meiling/meiling.glb", [arm, meiling])
    top = max(v.co.z for v in meiling.data.vertices)
    print("meiling tris:", tri_count(meiling), "height: %.3f" % top)


# ================================================================ 2. Sakuya Izayoi
def knife(name, grip, d, M, blade=0.16, handle=0.05):
    """A thin throwing knife: handle behind `grip`, blade along `d`, flat faces towards -Y."""
    d = d.normalized()
    w = d.cross(Vector((0, 1, 0)))
    if w.length < 1e-3:
        w = Vector((1, 0, 0))
    w.normalize()
    ref = w.cross(d)
    parts = [
        C.tube(name + "Handle", [grip - d * handle * 0.6, grip + d * handle * 0.4], [0.0075, 0.0085], 6, M["knife_grip"]),
        C.tube(name + "Guard", [grip + d * handle * 0.4, grip + d * (handle * 0.4 + 0.006)], [0.013, 0.013], 6, M["knife"], (1.0, 0.4), twist_up=ref),
        C.tube(name + "Blade", [grip + d * handle * 0.45, grip + d * (handle * 0.45 + blade * 0.6), grip + d * (handle * 0.45 + blade)], [0.014, 0.012, 0.0008], 6, M["knife"], (1.0, 0.18), twist_up=ref),
    ]
    return parts


def build_sakuya():
    C.reset_scene()
    M = base_materials()
    M.update({
        "skin": C.material("Skin", (0.97, 0.84, 0.77), 0.6),
        "lid": C.material("Eyelid", (0.88, 0.72, 0.68), 0.6),
        "tired": C.material("TiredShadow", (0.72, 0.6, 0.62), 0.7),
        "hair": C.material("SilverHair", (0.74, 0.75, 0.8), 0.45),
        "brow": C.material("SilverBrow", (0.5, 0.5, 0.56), 0.6),
        "iris": C.material("IrisBlue", (0.18, 0.3, 0.62), 0.2),
        "blue": C.material("MaidBlue", (0.14, 0.2, 0.42), 0.7),
        "blue_dk": C.material("MaidBlueDark", (0.07, 0.1, 0.24), 0.7),
        "white": C.material("MaidWhite", (0.9, 0.9, 0.92), 0.75),
        "frill": C.material("Frill", (0.95, 0.95, 0.96), 0.8),
        "ribbon": C.material("GreenRibbon", (0.1, 0.42, 0.24), 0.55),
        "stocking": C.material("Stocking", (0.86, 0.86, 0.88), 0.7),
        "shoe": C.material("Shoe", (0.07, 0.06, 0.07), 0.35),
        "knife": C.material("KnifeSilver", (0.86, 0.88, 0.92), 0.3, 0.45),
        "knife_grip": C.material("KnifeGrip", (0.15, 0.13, 0.16), 0.5),
        "watch": C.material("WatchSilver", (0.8, 0.8, 0.82), 0.35, 0.45),
        "dial": C.material("WatchDial", (0.9, 0.88, 0.8), 0.4),
        "crack": C.material("Crack", (0.1, 0.09, 0.1), 0.6),
        "leather": C.material("Holster", (0.2, 0.12, 0.08), 0.6),
    })

    bones = adult_bones(sh=0.16, hip=0.092)
    arm = SC.build_armature("SakuyaRig", bones)
    hc = Vector((0, 0, 1.565))

    def rule(kind, c, n):
        if kind in ("head", "neck"):
            return "skin"
        if kind in ("forearm", "hand"):
            return "skin"
        if kind == "upper_arm":
            return "skin" if c.z < 1.23 else "white"
        if kind == "foot" or (kind == "shin" and c.z < 0.125):
            return "shoe"
        if kind in ("thigh", "shin"):
            return "stocking"
        return "blue"

    body = skin_body(arm, {"sh": 0.16, "hip": 0.092, "pelvis": 0.122, "waist": 0.082, "chest": 0.108, "arm": 0.95, "leg": 0.98}, M,
                     ["blue", "skin", "white", "stocking", "shoe"], rule)

    # ------------------------------------------------------------ head
    head = face(hc, M, lid_cut=0.5, iris_mat=M["iris"], lid_mat=M["lid"], brow_lift=0.0, brow_tilt=0.002)
    # Faint tired shadows under the eyes.
    for sx in (1.0, -1.0):
        c = hc + Vector((sx * 0.038, -0.088, -0.03))
        sh = C.uv_sphere("UnderEye", 1.0, (0, 0, 0), (0.016, 0.003, 0.004), 8, 4, M["tired"])
        C.transform(sh, Matrix.Translation(c) @ Matrix.Rotation(math.radians(-20 * sx), 4, "Z"))
        head.append(sh)
    head.append(hair_cap(hc, M, open_z=0.05, r=0.11))
    # Bob: a shell round the back and sides, open at the face, ending at the jaw.
    bob = C.uv_sphere("Bob", 0.118, tuple(hc + Vector((0, 0.01, 0.0))), (1.0, 1.0, 1.08), 24, 14, M["hair"])
    bm = bmesh.new()
    bm.from_mesh(bob.data)
    kill = [v for v in bm.verts if (v.co.y < -0.045 and v.co.z < hc.z + 0.05) or v.co.z < hc.z - 0.085]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(bob.data)
    bm.free()
    for v in bob.data.vertices:
        # Flare the lower edge out and in a touch, like a cut bob.
        if v.co.z < hc.z - 0.02:
            t = (hc.z - 0.02 - v.co.z) / 0.065
            v.co.x *= 1.0 + 0.1 * t
            v.co.y = v.co.y * (1.0 + 0.05 * t)
    C.solidify(bob, 0.006)
    head.append(bob)
    # Jagged strand tips along the back and sides of the bob.
    for i in range(11):
        a = math.radians(-160 + i * 32)
        base = hc + Vector((math.cos(a) * 0.118, 0.01 + math.sin(a) * 0.115, -0.06))
        if base.y < -0.05:
            continue
        head.append(C.tube("BobTip", [base, base + Vector((math.cos(a) * 0.008, math.sin(a) * 0.008, -0.045 - (0.015 if i % 2 else 0)))], [0.022, 0.002], 6, M["hair"], (1.0, 0.45), twist_up=Vector((0, 0, 1))))
    head += bangs(hc, M, [-0.07, -0.046, -0.024, -0.004, 0.018, 0.04, 0.064], [0.0, 0.015, 0.035, 0.05, 0.02, 0.01, 0.0])
    # Side locks and the two braids with green ribbons.
    for sx in (1.0, -1.0):
        pts = [hc + Vector((sx * 0.082, -0.05, 0.06)), hc + Vector((sx * 0.096, -0.066, -0.01)), hc + Vector((sx * 0.094, -0.064, -0.07)), hc + Vector((sx * 0.09, -0.058, -0.1))]
        head.append(C.tube("SideLock", pts, [0.02, 0.021, 0.015, 0.002], 8, M["hair"], (1.0, 0.5), twist_up=Vector((0, -1, 0))))
        bp = [hc + Vector((sx * 0.1, -0.035, -0.0)), hc + Vector((sx * 0.106, -0.05, -0.08)), hc + Vector((sx * 0.104, -0.058, -0.16))]
        head += braid("Braid", bp, 0.013, M["hair"], beads=7, tie_mat=M["ribbon"], bow=0.016)
    # Maid headdress: a frilled white band over the crown.
    tilt = math.radians(28)
    U = Vector((0, -math.sin(tilt), math.cos(tilt)))
    X = Vector((1, 0, 0))
    bm = bmesh.new()
    inner, outer = [], []
    n = 26
    for i in range(n + 1):
        a = math.radians(-78 + 156 * i / n)
        dirv = X * math.sin(a) + U * math.cos(a)
        inner.append(bm.verts.new(hc + Vector((0, 0.01, 0.01)) + dirv * 0.112))
        rr = 0.137 + (0.01 if i % 2 else 0.0)
        outer.append(bm.verts.new(hc + Vector((0, 0.01, 0.01)) + dirv * rr + Vector((0, -0.006, 0))))
    for i in range(n):
        bm.faces.new((inner[i], inner[i + 1], outer[i + 1], outer[i]))
    frill = C.new_object("Headdress", bm, M["frill"])
    C.solidify(frill, 0.006)
    base_band = C.tube("HeaddressBand", [hc + Vector((0, 0.01, 0.01)) + (X * math.sin(math.radians(a)) + U * math.cos(math.radians(a))) * 0.114 for a in range(-78, 79, 12)], [0.007] * 14, 6, M["frill"])
    head += [frill, base_band]
    for p in head:
        C.rigid(p, "head")

    # ------------------------------------------------------------ outfit
    parts = []
    # White collar, green bow at the throat.
    collar = loft("Collar", [((0, 0.0, 1.4), 0.052, 0.05), ((0, 0.004, 1.44), 0.047, 0.045)], 20, M["white"])
    C.solidify(collar, 0.006)
    front = [collar]
    for sx in (1.0, -1.0):
        flap = C.tube("CollarFlap", [Vector((sx * 0.012, -0.05, 1.41)), Vector((sx * 0.055, -0.06, 1.37))], [0.018, 0.024], 8, M["white"], (1.0, 0.3), twist_up=Vector((0, -1, 0)))
        lobe = C.uv_sphere("NeckBow", 1.0, (0, 0, 0), (0.022, 0.008, 0.014), 10, 6, M["ribbon"])
        C.transform(lobe, Matrix.Translation((sx * 0.022, -0.068, 1.395)) @ Matrix.Rotation(math.radians(sx * -15), 4, "Y"))
        front += [flap, lobe]
    front.append(C.uv_sphere("NeckKnot", 0.009, (0, -0.07, 1.395), (1, 0.8, 1), 8, 5, M["ribbon"]))
    # White blouse front under the blue bodice, with a row of buttons.
    front.append(C.tube("Blouse", [Vector((0, -0.075, 1.38)), Vector((0, -0.092, 1.28)), Vector((0, -0.08, 1.14))], [0.03, 0.036, 0.024], 10, M["white"], (1.0, 0.3), twist_up=Vector((0, -1, 0))))
    for z in (1.33, 1.27, 1.21):
        front.append(C.uv_sphere("Button", 0.006, (0, -0.101 + abs(z - 1.28) * 0.12, z), (1, 0.6, 1), 6, 4, M["blue_dk"]))
    for p in front:
        C.weight_by_bones(p, arm, ["chest", "neck", "spine"], power=4.0)
    parts += front

    # Puffed short sleeves with blue cuffs.
    for s, sx in (("L", 1.0), ("R", -1.0)):
        p0 = P(f"upper_arm.{s}", 0.0) + Vector((0, 0, 0.01))
        p1 = P(f"upper_arm.{s}", 0.42)
        puff = C.tube(f"Puff.{s}", [p0 + (p1 - p0) * 0.04, p0.lerp(p1, 0.35), p1], [0.04, 0.066, 0.046], 14, M["white"])
        cuff = C.tube(f"PuffCuff.{s}", [p1 - (p1 - p0).normalized() * 0.006, p1 + (p1 - p0).normalized() * 0.01], [0.044, 0.044], 14, M["blue"], cap=False)
        C.solidify(cuff, 0.005)
        C.weight_by_bones(puff, arm, [f"upper_arm.{s}", f"shoulder.{s}"], power=4.0)
        C.rigid(cuff, f"upper_arm.{s}")
        parts += [puff, cuff]

    # Skirt: flared blue to just above the knee, with a white petticoat frill.
    skirt = loft("Skirt", [((0, 0.0, 1.08), 0.088, 0.074), ((0, 0.0, 1.0), 0.13, 0.108), ((0, 0.0, 0.88), 0.2, 0.17), ((0, 0.0, 0.74), 0.25, 0.215), ((0, 0.0, 0.62), 0.28, 0.24)], 40, M["blue"], pleats=10, pleat_amp=0.06)
    C.solidify(skirt, 0.007)
    C.weight_by_bones(skirt, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    pet = loft("Petticoat", [((0, 0.0, 0.66), 0.268, 0.232), ((0, 0.0, 0.595), 0.295, 0.256)], 48, M["frill"], pleats=24, pleat_amp=0.04)
    C.solidify(pet, 0.005)
    C.weight_by_bones(pet, arm, ["hips", "thigh.L", "thigh.R"], power=3.0, keep=3)
    parts += [skirt, pet]
    # Waist apron with a frilled hem, and the big bow at the back.
    apron = cloth_panel("Apron", M["white"], 1.075, 0.66, 0.08, 0.17, 0.087, 0.255, curve=0.04, rows=8)
    C.solidify(apron, 0.005)
    frl = cloth_panel("ApronFrill", M["frill"], 0.672, 0.63, 0.172, 0.182, 0.258, 0.27, curve=0.04, rows=1, cols=20, jag=0.008)
    C.solidify(frl, 0.004)
    band = loft("ApronBand", [((0, 0, 1.075), 0.09, 0.077), ((0, 0, 1.105), 0.087, 0.074)], 24, M["white"])
    C.solidify(band, 0.005)
    for p in (apron, frl):
        C.weight_by_bones(p, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
    C.weight_by_bones(band, arm, ["hips", "spine"], power=4.0)
    parts += [apron, frl, band]
    bow_c = Vector((0, 0.09, 1.09))
    bow = [C.uv_sphere("BackKnot", 0.018, tuple(bow_c), (1, 0.8, 1), 8, 5, M["white"])]
    for sx in (1.0, -1.0):
        lobe = C.uv_sphere("BackBow", 1.0, (0, 0, 0), (0.07, 0.018, 0.04), 12, 6, M["white"])
        C.transform(lobe, Matrix.Translation(bow_c + Vector((sx * 0.062, 0.006, 0.01))) @ Matrix.Rotation(math.radians(sx * -14), 4, "Y"))
        tail = C.tube("BackBowTail", [bow_c, bow_c + Vector((sx * 0.04, 0.02, -0.08)), bow_c + Vector((sx * 0.06, 0.03, -0.2))], [0.018, 0.024, 0.03], 8, M["white"], (1.0, 0.25), twist_up=Vector((0, 1, 0)))
        bow += [lobe, tail]
    for p in bow:
        C.weight_by_bones(p, arm, ["hips", "spine"], power=4.0)
    parts += bow

    # Knife holster round the left thigh, just under the hem.
    hz = 0.6
    hp = P("thigh.L", (0.97 - hz) / 0.45)
    strap = C.tube("Holster", [hp + Vector((0, 0, 0.012)), hp - Vector((0, 0, 0.012))], [0.062, 0.062], 14, M["leather"])
    C.rigid(strap, "thigh.L")
    parts.append(strap)
    for i, a in enumerate((-35, -10, 15)):
        dirv = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0))
        g = hp + dirv * 0.064 + Vector((0, 0, 0.02))
        for kp in knife("HolsterKnife", g, Vector((0, 0, -1)), M, blade=0.0, handle=0.05)[:2]:
            C.rigid(kp, "thigh.L")
            parts.append(kp)

    # Knives fanned in the right hand.
    grip = P("hand.R", 0.55)
    hd = (P("hand.R", 1.0) - P("hand.R", 0.0)).normalized()
    knives = []
    for a in (-24, 0, 24):
        d = Matrix.Rotation(math.radians(a), 3, "Y") @ hd
        knives += knife("Knife", grip + Vector((0, -0.01, 0)), d, M)
    for p in knives:
        C.rigid(p, "hand.R")
    parts += knives

    # The pocket watch, in the left palm, face cracked; its chain loops over the fingers.
    # Built facing -Y with the stem up, then turned so the face looks out of the palm (-X)
    # and the stem points to the fingertips.
    wc = Vector((0, 0, 0))
    watch = []
    case = C.tube("WatchCase", [wc + Vector((0, 0.006, 0)), wc + Vector((0, -0.006, 0))], [0.03, 0.03], 16, M["watch"], twist_up=Vector((0, 0, 1)))
    dial = C.tube("WatchDial", [wc + Vector((0, -0.006, 0)), wc + Vector((0, -0.0075, 0))], [0.025, 0.025], 16, M["dial"], twist_up=Vector((0, 0, 1)))
    stem = C.tube("WatchStem", [wc + Vector((0, 0, 0.03)), wc + Vector((0, 0, 0.042))], [0.005, 0.005], 6, M["watch"])
    bow_ring = C.tube("WatchBow", [wc + Vector((-0.007, 0, 0.045)), wc + Vector((0, 0, 0.05)), wc + Vector((0.007, 0, 0.045))], [0.0025, 0.0025, 0.0025], 5, M["watch"])
    watch += [case, dial, stem, bow_ring]
    f = wc + Vector((0, -0.008, 0))
    for hand_d, ln in ((Vector((0.2, 0, 1)), 0.016), (Vector((-1, 0, 0.3)), 0.011)):
        watch.append(C.tube("WatchHand", [f, f + hand_d.normalized() * ln], [0.0016, 0.001], 4, M["crack"]))
    # The crack: a jagged line across the glass.
    cr = [f + Vector((-0.022, -0.0005, 0.01)), f + Vector((-0.008, -0.0005, 0.002)), f + Vector((0.002, -0.0005, 0.008)), f + Vector((0.021, -0.0005, -0.012))]
    watch.append(C.tube("WatchCrack", cr, [0.0013, 0.0016, 0.0013, 0.0008], 4, M["crack"]))
    watch.append(C.tube("WatchCrack2", [cr[1], cr[1] + Vector((0.004, -0.0005, -0.016))], [0.0012, 0.0006], 4, M["crack"]))
    chain_pts = [wc + Vector((0, 0, 0.05)), wc + Vector((0.01, -0.01, 0.075)), wc + Vector((0.03, 0.0, 0.07)), wc + Vector((0.035, 0.01, 0.03)), wc + Vector((0.03, 0.01, -0.02)), wc + Vector((0.025, 0.005, -0.06))]
    watch.append(C.tube("WatchChain", chain_pts, [0.0022] * 6, 5, M["watch"]))
    # Face direction in rest space, solved so the face tilts up towards her in the idle pose
    # and turns to the front when she holds the watch out in time_stop.
    wf = Vector((-0.587, -0.735, -0.339)).normalized()
    wz = (Vector((0, 0, -1)) - wf * Vector((0, 0, -1)).dot(wf)).normalized()
    wy = -wf
    wx = wy.cross(wz)
    palm = Matrix.Translation(P("hand.L", 0.55) + wf * 0.024) @ Matrix((wx, wy, wz)).transposed().to_4x4()
    for p in watch:
        C.transform(p, palm)
        C.rigid(p, "hand.L")
    parts += watch

    model_parts = [body] + head + parts
    K = 1.65 / 1.69
    scale_rig(arm, model_parts, K)
    sakuya = finish("Sakuya", arm, model_parts)

    # ------------------------------------------------------------ animation
    start_animation(arm)

    # Rest: upright but tired. Head bowed a little, knives low, the watch cradled at the waist.
    REST = {"spine": (3, 0, 0), "chest": (4, 0, 0), "neck": (6, 0, 0), "head": (8, -4, 2),
            "upper_arm.L": (-4, 30, -2), "forearm.L": (88, 0, 0), "hand.L": (-10, -70, 0),
            "upper_arm.R": (4, 0, -10), "forearm.R": (12, 0, 0), "hand.R": (0, 0, 0),
            "thigh.L": (4, 0, 2), "thigh.R": (-2, 0, -3), "shin.L": (-6, 0, 0)}

    def rp(p, ground=True):
        out = dict(REST)
        out.update(p)
        return grounded(out) if ground else out

    action("idle", 60, {0: rp({}), 30: rp({"chest": (1, 0, 1), "head": (12, -2, 3), "neck": (8, 0, 0), "upper_arm.R": (6, 0, -12)}), 60: rp({})}, loop=True)

    def walk_contact(s):
        return grounded({**REST, "hips": (0, 5 * s, 0), "chest": (4, -6 * s, 0),
                         "thigh.L": (22 * s, 0, 1), "thigh.R": (-22 * s, 0, -1),
                         "shin.L": (-5 if s > 0 else -16, 0, 0), "shin.R": (-16 if s > 0 else -5, 0, 0),
                         "foot.L": (12 if s > 0 else -6, 0, 0), "foot.R": (-6 if s > 0 else 12, 0, 0),
                         "upper_arm.R": (-14 * s + 2, 0, -8)})

    def walk_pass(s):
        return grounded({**REST, "hips": (0, 0, -2 * s),
                         "thigh.L": (-2 if s > 0 else 26, 0, 1), "thigh.R": (26 if s > 0 else -2, 0, -1),
                         "shin.L": (-4 if s > 0 else -52, 0, 0), "shin.R": (-52 if s > 0 else -4, 0, 0),
                         "foot.L": (0, 0, 0), "foot.R": (0, 0, 0), "upper_arm.R": (2, 0, -8)})

    action("walk", 32, {0: walk_contact(1), 8: walk_pass(1), 16: walk_contact(-1), 24: walk_pass(-1), 32: walk_contact(1)}, loop=True)

    # Knife throw: 15f, release f7. Sidearm flick from behind the hip.
    KT_WIND = rp({"hips": (0, -10, 0), "chest": (0, -30, 0), "head": (0, 25, 0), "upper_arm.R": (-20, 0, -50), "forearm.R": (70, 0, 0), "hand.R": (-20, 0, 0), "thigh.R": (-10, 0, -6), "thigh.L": (14, 0, 2), "shin.L": (-10, 0, 0)})
    KT_REL = rp({"hips": (0, 10, 0), "chest": (2, 22, 0), "head": (-2, -20, 0), "neck": (0, 0, 0), "upper_arm.R": (86, 0, -4), "forearm.R": (2, 0, 0), "hand.R": (-60, 0, 0), "thigh.L": (24, 0, 2), "shin.L": (-16, 0, 0), "thigh.R": (-14, 0, -4), "foot.R": (-10, 0, 0), "hips@loc": (0, 0, 0.05)})
    KT_FOLLOW = {**KT_REL, "upper_arm.R": (78, 0, 20), "chest": (2, 30, 0), "hand.R": (-30, 0, 0)}
    action("knife_throw", 15, {0: rp({}), 4: KT_WIND, 7: KT_REL, 10: KT_FOLLOW, 15: rp({})})

    # Knife fan: 20f, release f10. Arm sweeps across the body and flings the fan out wide.
    KF_WIND = rp({"chest": (0, -35, 0), "spine": (4, -10, 0), "head": (0, 30, 0), "upper_arm.R": (45, -60, 0), "forearm.R": (90, 0, 0), "hand.R": (-20, 0, 0), "thigh.L": (10, 0, 4), "thigh.R": (-8, 0, -8), "shin.L": (-20, 0, 0), "shin.R": (-20, 0, 0)})
    KF_REL = rp({"chest": (0, 20, 0), "spine": (2, 10, 0), "head": (-4, -15, 0), "neck": (0, 0, 0), "upper_arm.R": (40, 0, -75), "forearm.R": (4, 0, 0), "hand.R": (-40, 0, 0), "upper_arm.L": (30, 0, 20), "forearm.L": (70, 0, 0), "thigh.L": (18, 0, 6), "thigh.R": (-10, 0, -10), "shin.L": (-12, 0, 0), "hips@loc": (0, 0, 0.03)})
    action("knife_fan", 20, {0: rp({}), 6: KF_WIND, 10: KF_REL, 14: {**KF_REL, "upper_arm.R": (32, 0, -88)}, 20: rp({})})

    # Slash: 18f, contact f8. A short lunge and a rising-to-falling diagonal cut.
    SL_WIND = rp({"hips": (0, -15, 0), "chest": (-4, -25, 0), "head": (-4, 20, 0), "upper_arm.R": (130, 0, -35), "forearm.R": (40, 0, 0), "hand.R": (-20, 0, 0), "upper_arm.L": (20, 0, 10),
                  "thigh.L": (20, 0, 4), "shin.L": (-24, 0, 0), "thigh.R": (-6, 0, -6), "shin.R": (-20, 0, 0)})
    SL_HIT = rp({"hips": (0, 15, 0), "spine": (10, 8, 0), "chest": (10, 25, 0), "head": (-10, -15, 0), "neck": (0, 0, 0), "upper_arm.R": (60, 0, 30), "forearm.R": (10, 0, 0), "hand.R": (-40, 0, 0),
                 "upper_arm.L": (-20, 0, 30), "forearm.L": (60, 0, 0), "thigh.L": (52, 0, 4), "shin.L": (-55, 0, 0), "foot.L": (6, 0, 0), "thigh.R": (-30, 0, -4), "shin.R": (-6, 0, 0), "foot.R": (-18, 0, 0), "hips@loc": (0, 0, 0.14)})
    action("slash", 18, {0: rp({}), 5: SL_WIND, 8: SL_HIT, 11: {**SL_HIT, "upper_arm.R": (45, 0, 40)}, 18: rp({})})

    # Time stop: 36f, stop at f18. She straightens, raises the watch, and the moment holds.
    TS_RAISE = rp({"spine": (0, 0, 0), "chest": (-2, 0, 0), "neck": (0, 0, 0), "head": (0, 0, 0), "upper_arm.L": (55, 10, -6), "forearm.L": (60, 0, 0), "hand.L": (-15, 0, 0), "upper_arm.R": (10, 0, -30), "forearm.R": (20, 0, 0)})
    TS_STOP = rp({"spine": (-3, 0, 0), "chest": (-4, 0, 0), "neck": (-2, 0, 0), "head": (-6, 0, 0), "upper_arm.L": (85, -20, -10), "forearm.L": (10, 0, 0), "hand.L": (-20, 45, 40),
                  "upper_arm.R": (20, 0, -70), "forearm.R": (8, 0, 0), "hand.R": (-20, 0, 0), "thigh.L": (6, 0, 4), "thigh.R": (-4, 0, -6)})
    action("time_stop", 36, {0: rp({}), 10: TS_RAISE, 18: TS_STOP, 28: TS_STOP, 36: rp({})})

    # Teleport out / in: 10f each, poses only (the game hides / shows her on the last / first frame).
    TP_TUCK = rp({"hips": (0, 40, 0), "spine": (14, 10, 0), "chest": (6, 10, 0), "head": (10, -30, 0), "upper_arm.L": (20, 0, -20), "forearm.L": (110, 0, 0),
                  "upper_arm.R": (30, 0, 25), "forearm.R": (120, 0, 0), "thigh.L": (40, 0, 4), "shin.L": (-70, 0, 0), "thigh.R": (35, 0, -4), "shin.R": (-70, 0, 0)})
    action("teleport_out", 10, {0: rp({}), 4: rp({"hips": (0, 15, 0), "chest": (2, 5, 0), "upper_arm.R": (30, 0, 10), "forearm.R": (80, 0, 0), "thigh.L": (20, 0, 2), "shin.L": (-35, 0, 0), "thigh.R": (18, 0, -2), "shin.R": (-35, 0, 0)}), 10: TP_TUCK})
    TP_OPEN = rp({"hips": (0, -10, 0), "spine": (-2, 0, 0), "chest": (-4, -8, 0), "head": (-2, 10, 0), "upper_arm.R": (60, 0, -60), "forearm.R": (10, 0, 0), "hand.R": (-30, 0, 0),
                  "thigh.L": (18, 0, 6), "shin.L": (-24, 0, 0), "thigh.R": (-6, 0, -8), "shin.R": (-20, 0, 0)})
    action("teleport_in", 10, {0: TP_TUCK, 5: TP_OPEN, 10: rp({})})

    # Hurt: 12f.
    action("hurt", 12, {0: rp({}), 3: rp({"spine": (-10, 6, 0), "chest": (-8, 8, 0), "head": (-16, 8, 0), "neck": (0, 0, 0), "upper_arm.L": (20, 0, 20), "upper_arm.R": (20, 0, -40), "forearm.R": (40, 0, 0), "hips@loc": (0, 0, -0.05)}), 12: rp({})})

    # Death: 40f. She kneels, holds the watch to her chest and bows her head, sitting back on her heels.
    SEIZA = {"thigh.L": (76, 0, 3), "thigh.R": (76, 0, -3), "shin.L": (-166, 0, 0), "shin.R": (-166, 0, 0), "foot.L": (-78, 0, 0), "foot.R": (-78, 0, 0)}
    D_STEP = rp({"spine": (-6, 0, 0), "head": (-8, 0, 0), "neck": (0, 0, 0), "upper_arm.R": (10, 0, -25), "thigh.R": (-8, 0, -4), "hips@loc": (0, 0, -0.04)})
    D_KNEE = grounded({"thigh.L": (78, 0, 3), "shin.L": (-80, 0, 0), "foot.L": (0, 0, 0), "thigh.R": (-8, 0, -3), "shin.R": (-95, 0, 0), "foot.R": (-40, 0, 0), "spine": (10, 0, 0), "head": (14, 0, 0),
                       "upper_arm.L": (30, 0, -10), "forearm.L": (110, 0, 0), "hand.L": (0, 40, 0), "upper_arm.R": (10, 0, -10), "forearm.R": (20, 0, 0)})
    D_SIT = grounded({**SEIZA, "spine": (10, 0, 0), "chest": (6, 0, 0), "neck": (8, 0, 0), "head": (20, 0, 0), "upper_arm.L": (24, 0, -18), "forearm.L": (125, 0, 0), "hand.L": (0, 50, 0),
                      "upper_arm.R": (20, 0, 10), "forearm.R": (70, 0, 0), "hand.R": (0, 0, 0)})
    D_BOW = grounded({**D_SIT, "spine": (12, 0, 0), "chest": (7, 0, 0), "neck": (10, 0, 0), "head": (24, 0, 0)})
    action("death", 40, {0: rp({}), 6: D_STEP, 16: D_KNEE, 28: D_SIT, 36: D_BOW, 40: D_BOW})

    arm.animation_data.action = bpy.data.actions["idle"]
    C.export_glb("assets/models/characters/sakuya/sakuya.glb", [arm, sakuya])
    top = max(v.co.z for v in sakuya.data.vertices)
    print("sakuya tris:", tri_count(sakuya), "height: %.3f" % top)


if __name__ == "__main__":
    which = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["meiling", "sakuya"]
    if "meiling" in which:
        build_meiling()
    if "sakuya" in which:
        build_sakuya()
