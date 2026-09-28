"""Story characters: the Former Shrine Maiden and the Wayside God.

Outputs:
  assets/models/characters/former_maiden/former_maiden.glb
  assets/models/characters/wayside_god/wayside_god.glb

See docs/STORY_AND_CHARACTERS.md ("1. The Former Shrine Maiden", "2. The Wayside God").

Same conventions as build_reimu.py:
Blender axes: Z up, characters face -Y, their left side is +X (".L").
Every bone's local Z axis points forward (-Y) so poses read the same way:
  +X rotation = swing forward / bend forward, Y = twist, Z = side raise
  (+Z raises a left limb outward, -Z raises a right limb outward).
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector, noise

sys.path.insert(0, os.path.dirname(__file__))
import common as C  # noqa: E402

ARM = None  # the armature the helpers below act on


# ================================================================ shared rig / animation helpers
def build_armature(name, bones, forward_roll=()):
    """bones: (name, head, tail, parent). Bones listed in `forward_roll` point roughly
    forward, so their roll is aligned to up instead (like Reimu's feet)."""
    global ARM
    data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(arm)
    C.activate(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, head, tail, parent in bones:
        eb = data.edit_bones.new(bname)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        if bname.startswith("shoulder"):
            eb.align_roll(Vector((0, -1, 0)))
        elif bname.startswith("foot") or bname in forward_roll:
            eb.align_roll(Vector((0, 0, 1)))
        else:
            eb.align_roll(Vector((0, -1, 0)))
        if parent:
            eb.parent = data.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    data.display_type = "STICK"
    ARM = arm
    return arm


def P(name, t):
    b = ARM.data.bones[name]
    return b.head_local.lerp(b.tail_local, t)


# Ground contacts for auto-grounded poses: (bone, head/tail, minimum height).
GROUND_POINTS = [
    ("shin.L", "head", 0.055), ("shin.R", "head", 0.055),
    ("foot.L", "head", 0.07), ("foot.R", "head", 0.07),
    ("foot.L", "tail", 0.02), ("foot.R", "tail", 0.02),
]


def grounded(pose):
    """Drop (or lift) the hips so the lowest knee / ankle / toe rests on the floor."""
    arm = ARM
    arm.animation_data.action = None  # otherwise the active action overrides the pose
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    for bone, val in pose.items():
        if bone.endswith("@loc"):
            continue
        arm.pose.bones[bone].rotation_euler = [math.radians(a) for a in val]
    lx, _, lz = pose.get("hips@loc", (0, 0, 0))
    arm.pose.bones["hips"].location = (lx, 0, lz)
    bpy.context.view_layer.update()
    drop = min(getattr(arm.pose.bones[b], end).z - h for b, end, h in GROUND_POINTS)
    out = dict(pose)
    out["hips@loc"] = (lx, -drop, lz)
    return out


def action(name, frames, keys, loop=False):
    """keys: {frame: {bone: (rx, ry, rz) degrees | ("loc", (x, y, z))}}."""
    arm = ARM
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


def start_animation(arm):
    arm.animation_data_create()
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def loft(name, rings_spec, seg, mat, pleats=0, pleat_amp=0.0, cap=False):
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
    if cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C.new_object(name, bm, mat)


def roughen(obj, amp, freq, seed=0.0, keep_bottom=None):
    """Weathering: push vertices along their normals by low-frequency noise."""
    me = obj.data
    for v in me.vertices:
        if keep_bottom is not None and v.co.z < keep_bottom:
            continue
        n = noise.noise(v.co * freq + Vector((seed, seed * 0.7, seed * 1.3)))
        n2 = noise.noise(v.co * freq * 3.1 + Vector((seed, 0, 0)))
        v.co += v.normal * (n * amp + n2 * amp * 0.35)
    me.update()


def paper_strip(name, center, width, height, mat, rot_z=0.0, tilt_x=0.0, thick=0.002):
    obj = C.box(name, (width, thick, height), (0, 0, 0), mat)
    C.transform(obj, Matrix.Translation(Vector(center)) @ Matrix.Rotation(math.radians(rot_z), 4, "Z") @ Matrix.Rotation(math.radians(tilt_x), 4, "X"))
    return obj


# ================================================================ 1. the Former Shrine Maiden
def build_former_maiden():
    C.reset_scene()
    M = {
        "skin": C.material("PorcelainSkin", (0.86, 0.8, 0.77), 0.55),
        "kosode": C.material("FadedWhite", (0.6, 0.6, 0.58), 0.8),
        "hakama": C.material("FadedRed", (0.3, 0.14, 0.15), 0.8),
        "hakama_dark": C.material("FadedRedDark", (0.18, 0.06, 0.07), 0.8),
        "cord": C.material("FrayedCord", (0.55, 0.1, 0.1), 0.6),
        "hair": C.material("DullHair", (0.06, 0.055, 0.06), 0.55),
        "trim": C.material("GhostTrim", (0.78, 0.86, 0.95), 0.5, emission=0.7),
        "paper": C.material("Ofuda", (0.88, 0.85, 0.76), 0.85, emission=0.15),
        "ink": C.material("Ink", (0.28, 0.04, 0.05), 0.6),
        "blackink": C.material("BlackInk", (0.05, 0.04, 0.04), 0.6),
        "crack": C.material("Crack", (0.12, 0.1, 0.12), 0.6),
        "wood": C.material("OldWood", (0.25, 0.19, 0.14), 0.85),
        "tabi": C.material("Tabi", (0.72, 0.71, 0.68), 0.85),
        "straw": C.material("ZoriStraw", (0.45, 0.38, 0.27), 0.9),
        "shide": C.material("TornShide", (0.8, 0.78, 0.72), 0.85, emission=0.1),
        "metal": C.material("TarnishedCap", (0.4, 0.34, 0.26), 0.5, 0.6),
    }

    # ------------------------------------------------------------ skeleton (adult, ~1.68 m)
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
            (f"shoulder.{s}", (sx * 0.03, 0, 1.37), (sx * 0.15, 0, 1.37), "chest"),
            (f"upper_arm.{s}", (sx * 0.17, 0, 1.36), (sx * 0.24, 0.0, 1.08), f"shoulder.{s}"),
            (f"forearm.{s}", (sx * 0.24, 0, 1.08), (sx * 0.29, -0.03, 0.84), f"upper_arm.{s}"),
            (f"hand.{s}", (sx * 0.29, -0.03, 0.84), (sx * 0.31, -0.04, 0.75), f"forearm.{s}"),
            (f"thigh.{s}", (sx * 0.095, 0, 0.97), (sx * 0.1, 0, 0.52), "hips"),
            (f"shin.{s}", (sx * 0.1, 0, 0.52), (sx * 0.1, 0.01, 0.09), f"thigh.{s}"),
            (f"foot.{s}", (sx * 0.1, 0.01, 0.09), (sx * 0.1, -0.12, 0.02), f"shin.{s}"),
        ]
    arm = build_armature("FormerMaidenRig", bones)
    body_bones = [b[0] for b in bones if b[0] != "root"]

    # ------------------------------------------------------------ body (skin modifier)
    def build_body():
        verts, edges, radii = [], [], []

        def v(co, r):
            verts.append(co)
            radii.append(r)
            return len(verts) - 1

        pelvis = v((0, 0, 0.95), (0.125, 0.09))
        waist = v((0, 0, 1.1), (0.09, 0.072))
        chest = v((0, 0, 1.26), (0.112, 0.085))
        upper = v((0, 0, 1.35), (0.108, 0.074))
        neck_b = v((0, 0, 1.41), (0.042, 0.042))
        neck_t = v((0, 0, 1.5), (0.034, 0.034))
        edges += [(pelvis, waist), (waist, chest), (chest, upper), (upper, neck_b), (neck_b, neck_t)]
        for sx in (1.0, -1.0):
            sh = v((sx * 0.16, 0, 1.365), (0.046, 0.046))
            el = v((sx * 0.24, 0, 1.08), (0.032, 0.032))
            wr = v((sx * 0.29, -0.03, 0.84), (0.024, 0.024))
            hd = v((sx * 0.305, -0.038, 0.765), (0.031, 0.02))
            hip = v((sx * 0.095, 0, 0.93), (0.075, 0.075))
            kn = v((sx * 0.1, 0, 0.52), (0.05, 0.05))
            an = v((sx * 0.1, 0.01, 0.1), (0.032, 0.032))
            toe = v((sx * 0.1, -0.1, 0.035), (0.036, 0.03))
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

        # Kosode torso and sleeves-under, porcelain hands / neck, white tabi.
        for key in ("kosode", "skin", "tabi"):
            obj.data.materials.append(M[key])
        for poly in obj.data.polygons:
            c = poly.center
            if c.z < 0.16:
                poly.material_index = 2
            elif c.z > 1.405 or (abs(c.x) > 0.2 and c.z < 0.9):
                poly.material_index = 1
            else:
                poly.material_index = 0
            poly.use_smooth = True
        C.weight_by_bones(obj, arm, body_bones, power=4.0)
        return obj

    def build_head():
        parts = []
        hc = Vector((0, 0, 1.565))
        head = C.uv_sphere("Head", 0.1, tuple(hc), (0.92, 0.98, 1.1), 28, 14, M["skin"])
        # Adult jaw: a gentler taper than Reimu's.
        for v in head.data.vertices:
            dz = v.co.z - hc.z
            if dz < 0:
                k = 1.0 - min(1.0, -dz / 0.11) * 0.3
                v.co.x *= k
                v.co.y = v.co.y * k - (1.0 - k) * 0.03
        parts.append(head)
        parts.append(C.uv_sphere("Nose", 0.012, (0, -0.1, 1.54), (0.7, 0.9, 1.3), 8, 6, M["skin"]))
        parts.append(C.box("Mouth", (0.02, 0.004, 0.0025), (0, -0.088, 1.495), M["crack"]))

        # Porcelain cracks running down from under the eye veil.
        for sx in (1.0, -1.0):
            pts = [Vector((sx * 0.04, -0.089, 1.55)), Vector((sx * 0.047, -0.085, 1.525)), Vector((sx * 0.041, -0.083, 1.505)), Vector((sx * 0.05, -0.074, 1.48))]
            parts.append(C.tube("Crack", pts, [0.0022, 0.0018, 0.0015, 0.0008], 4, M["crack"]))
            parts.append(C.tube("CrackBranch", [pts[1], pts[1] + Vector((sx * 0.014, 0.004, -0.008))], [0.0015, 0.0006], 4, M["crack"]))

        # The veil: an ofuda band across the eyes, and talismans hanging over the face.
        bm = bmesh.new()
        seg, span = 22, math.radians(230)
        top, bot = [], []
        for k in range(seg + 1):
            a = -math.pi / 2 - span / 2 + span * k / seg
            for z, lst in ((1.592, top), (1.548, bot)):
                rx, ry = 0.0975, 0.104
                lst.append(bm.verts.new((math.cos(a) * rx, math.sin(a) * ry, z)))
        for k in range(seg):
            bm.faces.new((bot[k], bot[k + 1], top[k + 1], top[k]))
        band = C.new_object("VeilBand", bm, M["paper"])
        C.solidify(band, 0.003)
        parts.append(band)
        # Band knot and hanging tails at the back of the head.
        for sx in (1.0, -1.0):
            parts.append(paper_strip("VeilTail", (sx * 0.03, 0.11, 1.52), 0.03, 0.12, M["paper"], rot_z=sx * 12, tilt_x=-8))
        # Hanging talismans: a long central slip and two shorter ones.
        for x, h, rz, tilt in ((0.0, 0.14, 0, -4), (-0.042, 0.085, 22, -3), (0.044, 0.1, -20, -3)):
            zc = 1.575 - h / 2
            y = -0.108 if x == 0 else -0.098
            parts.append(paper_strip("Ofuda", (x, y, zc), 0.036, h, M["paper"], rot_z=rz, tilt_x=tilt))
            # Ink: a bold vertical stroke with a seal square.
            parts.append(paper_strip("OfudaInk", (x - math.sin(math.radians(rz)) * 0.0 , y - 0.0025, zc + 0.005), 0.006, h * 0.6, M["blackink"], rot_z=rz, tilt_x=tilt))
            parts.append(paper_strip("OfudaSeal", (x, y - 0.003, zc - h * 0.36), 0.016, 0.016, M["ink"], rot_z=rz, tilt_x=tilt))
        # Two brush strokes across the band itself.
        for x in (-0.045, 0.045):
            parts.append(paper_strip("BandInk", (x, -0.098 + abs(x) * 0.28, 1.57), 0.02, 0.005, M["ink"], rot_z=-x * 500))

        # Hair: cap open at the face, long uneven bangs, long loose back hair.
        cap = C.uv_sphere("HairCap", 0.108, (0, 0.008, 1.575), (0.95, 1.0, 1.08), 28, 14, M["hair"])
        bm = bmesh.new()
        bm.from_mesh(cap.data)
        kill = [v for v in bm.verts if v.co.y < -0.03 and v.co.z < 1.61]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        bm.to_mesh(cap.data)
        bm.free()
        C.solidify(cap, 0.005)
        parts.append(cap)
        for i in range(8):
            x = -0.07 + i * 0.02
            top = Vector((x * 0.8, -0.085, 1.67))
            drop = 0.02 if i % 3 == 1 else 0.0
            bottom = Vector((x * 1.1, -0.108 + abs(x) * 0.25, 1.595 - drop + abs(x) * 0.4))
            mid = top.lerp(bottom, 0.5) + Vector((0, -0.012, 0))
            parts.append(C.tube("Bang", [top, mid, bottom], [0.018, 0.014, 0.002], 8, M["hair"], (1.0, 0.45)))
        return parts

    def build_long_hair():
        """Long, loose hair; skinned so the crown follows the head and the ends the back."""
        parts = []
        back = [Vector((0, 0.06, 1.63)), Vector((0, 0.1, 1.52)), Vector((0, 0.12, 1.38)), Vector((0, 0.12, 1.2)), Vector((0, 0.115, 1.05))]
        parts.append(C.tube("BackHair", back, [0.1, 0.12, 0.13, 0.13, 0.11], 18, M["hair"], (1.0, 0.36), twist_up=Vector((0, -1, 0))))
        for i in range(7):
            x = -0.1 + i * 0.033
            ln = 0.1 + (0.05 if i % 2 else 0.0) + (0.03 if i == 3 else 0.0)
            parts.append(C.tube("HairTip", [Vector((x, 0.115, 1.1)), Vector((x * 1.08, 0.12, 1.1 - ln))], [0.028, 0.002], 8, M["hair"], (1.0, 0.45), twist_up=Vector((0, -1, 0))))
        # Locks falling in front of the shoulders.
        for sx in (1.0, -1.0):
            pts = [Vector((sx * 0.085, -0.03, 1.62)), Vector((sx * 0.1, -0.05, 1.5)), Vector((sx * 0.12, -0.06, 1.38)), Vector((sx * 0.13, -0.075, 1.24)), Vector((sx * 0.125, -0.085, 1.16))]
            parts.append(C.tube("FrontLock", pts, [0.03, 0.03, 0.028, 0.02, 0.002], 10, M["hair"], (1.0, 0.5), twist_up=Vector((0, -1, 0))))
            side = [Vector((sx * 0.095, 0.02, 1.6)), Vector((sx * 0.12, 0.04, 1.44)), Vector((sx * 0.14, 0.05, 1.3)), Vector((sx * 0.13, 0.07, 1.15))]
            parts.append(C.tube("SideHair", side, [0.035, 0.04, 0.035, 0.003], 10, M["hair"], (0.6, 1.0), twist_up=Vector((0, -1, 0))))
        # The ribbon is gone: only a frayed red cord loosely ties the hair at the nape.
        cord_c = Vector((0, 0.14, 1.36))
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=16, radius=1.0)
        ring = C.new_object("CordLoop", bm, M["cord"])
        C.transform(ring, Matrix.Translation(cord_c) @ Matrix.Diagonal((0.1, 0.05, 1, 1)))
        C.solidify(ring, 0.012)
        parts.append(ring)
        parts.append(C.uv_sphere("CordKnot", 0.012, tuple(cord_c + Vector((0.01, 0.04, 0))), (1.2, 1, 1), 8, 6, M["cord"]))
        for sx, ln in ((1.0, 0.1), (-0.4, 0.14)):
            a = cord_c + Vector((0.01, 0.045, 0))
            b = a + Vector((sx * 0.02, 0.012, -ln))
            parts.append(C.tube("CordEnd", [a, a.lerp(b, 0.5) + Vector((sx * 0.01, 0.005, 0)), b], [0.0045, 0.004, 0.0035], 6, M["cord"]))
            for j, (dx, dl) in enumerate(((-0.006, 0.025), (0.004, 0.035), (0.009, 0.018))):
                parts.append(C.tube("CordFray", [b, b + Vector((dx, 0.002 * j, -dl))], [0.0018, 0.0005], 4, M["cord"]))
        return parts

    def build_outfit():
        parts = []
        # Crossed kosode collar (left over right) with a faint ghostly edge.
        for sx, zb in ((-1.0, 1.1), (1.0, 1.13)):
            pts = [Vector((-sx * 0.05, 0.05, 1.46)), Vector((-sx * 0.075, -0.02, 1.415)), Vector((-sx * 0.055, -0.078, 1.36)), Vector((0.0, -0.092, 1.26)), Vector((sx * 0.05, -0.085, zb))]
            parts.append(C.tube("Collar", pts, [0.014, 0.016, 0.016, 0.016, 0.014], 8, M["trim"], (1.0, 0.35)))
        # Kosode chest volume (a front panel so the overlap reads).
        parts.append(C.tube("KosodeFold", [Vector((0.03, -0.082, 1.3)), Vector((0.06, -0.092, 1.2)), Vector((0.07, -0.08, 1.1))], [0.02, 0.02, 0.02], 8, M["kosode"], (1.0, 0.25)))
        for p in parts:
            C.weight_by_bones(p, arm, ["chest", "spine", "neck"], power=4.0)

        # Hakama: a pleated waist wrap and two wide pleated legs.
        wrap = loft("HakamaWaist", [((0, 0.0, 1.12), 0.1, 0.08), ((0, 0.0, 1.05), 0.14, 0.11), ((0, 0.0, 0.93), 0.175, 0.14), ((0, 0.0, 0.84), 0.19, 0.155)], 32, M["hakama"], pleats=10, pleat_amp=0.04)
        C.solidify(wrap, 0.006)
        C.weight_by_bones(wrap, arm, ["hips", "spine", "thigh.L", "thigh.R"], power=3.0, keep=3)
        parts.append(wrap)
        for s, sx in (("L", 1.0), ("R", -1.0)):
            spec = []
            for z, rx, ry in ((0.99, 0.1, 0.12), (0.86, 0.125, 0.15), (0.7, 0.14, 0.165), (0.52, 0.15, 0.175), (0.3, 0.16, 0.18), (0.1, 0.17, 0.19), (0.06, 0.172, 0.192)):
                t = (0.99 - z) / 0.93
                spec.append(((sx * (0.06 + 0.045 * min(1.0, t * 3)), 0.0, z), rx, ry))
            leg = loft(f"HakamaLeg.{s}", spec, 28, M["hakama"], pleats=7, pleat_amp=0.05)
            C.solidify(leg, 0.006)
            C.weight_by_bones(leg, arm, ["hips", f"thigh.{s}", f"shin.{s}"], power=3.0, keep=2)
            parts.append(leg)
        # Waist band and the front bow of the hakama ties; the stiff back board (koshi-ita).
        band = loft("HakamaBand", [((0, 0, 1.13), 0.103, 0.083), ((0, 0, 1.085), 0.12, 0.097)], 32, M["hakama_dark"])
        C.solidify(band, 0.006)
        C.weight_by_bones(band, arm, ["hips", "spine"], power=4.0)
        parts.append(band)
        tie = [C.uv_sphere("TieKnot", 0.022, (0, -0.105, 1.1), (1.3, 0.6, 0.8), 10, 6, M["hakama_dark"])]
        for sx in (1.0, -1.0):
            tie.append(C.tube("TieLoop", [Vector((0, -0.108, 1.1)), Vector((sx * 0.05, -0.11, 1.105))], [0.012, 0.018], 8, M["hakama_dark"], (1.0, 0.35)))
            tie.append(C.tube("TieEnd", [Vector((sx * 0.01, -0.11, 1.09)), Vector((sx * 0.03, -0.14, 0.94))], [0.012, 0.015], 6, M["hakama_dark"], (1.0, 0.3)))
        board = C.box("KoshiIta", (0.2, 0.02, 0.1), (0, 0.105, 1.1), M["hakama"], rot=(-8, 0, 0))
        for p in tie + [board]:
            C.weight_by_bones(p, arm, ["hips", "spine"], power=4.0)
        parts += tie + [board]

        # Kosode sleeves: flat, wide hanging sleeves (tamoto) with a ghostly cuff edge.
        for s in ("L", "R"):
            p0 = P(f"upper_arm.{s}", 0.1)
            p1 = P(f"forearm.{s}", 0.0)
            p2 = P(f"forearm.{s}", 1.0)
            d = (p2 - p1).normalized()
            pts = [p0, p0.lerp(p1, 0.5), p1, p1.lerp(p2, 0.5), p2 - d * 0.02]
            radii = [0.06, 0.085, 0.11, 0.13, 0.14]
            sleeve = C.tube(f"Sleeve.{s}", pts, radii, 16, M["kosode"], (0.42, 1.0), cap=False, twist_up=Vector((0, -1, 0)))
            # Let the sleeve bag sag below the arm line (towards +Y, behind the forearm, and down).
            for v in sleeve.data.vertices:
                t = max(0.0, (p0.z - v.co.z) / (p0.z - p2.z))
                if v.co.y > 0.0:
                    v.co.z -= 0.07 * t * (v.co.y / 0.14)
            C.solidify(sleeve, 0.006)
            C.weight_by_bones(sleeve, arm, [f"upper_arm.{s}", f"forearm.{s}", "chest"], power=4.0)
            cuff = C.tube(f"SleeveCuff.{s}", [p2 - d * 0.03, p2 - d * 0.012], [0.141, 0.141], 16, M["trim"], (0.44, 1.02), cap=False, twist_up=Vector((0, -1, 0)))
            for v in cuff.data.vertices:
                if v.co.y > 0.0:
                    v.co.z -= 0.07 * (v.co.y / 0.14)
            C.solidify(cuff, 0.008)
            C.rigid(cuff, f"forearm.{s}")
            parts += [sleeve, cuff]

        # Straw zori soles and thongs.
        for s, sx in (("L", 1.0), ("R", -1.0)):
            sole = C.box(f"Zori.{s}", (0.085, 0.22, 0.018), (sx * 0.1, -0.05, 0.009), M["straw"])
            C.rigid(sole, f"foot.{s}")
            parts.append(sole)
        return parts

    def build_gohei():
        """Cracked, ancient gohei wrapped in struck-out register pages, torn shide."""
        parts = []
        grip = P("hand.R", 0.4)
        d = Vector((0.08, -1.0, 0.5)).normalized()
        start = grip - d * 0.16
        crack_at = grip + d * 0.36
        end = grip + d * 0.74
        kink = (d + Vector((0.03, 0.0, 0.03))).normalized()
        parts.append(C.tube("GoheiStick", [start, crack_at - d * 0.006], [0.012, 0.0125], 8, M["wood"]))
        parts.append(C.tube("GoheiStickTop", [crack_at + kink * 0.006, crack_at + kink * 0.38], [0.012, 0.011], 8, M["wood"]))
        end = crack_at + kink * 0.38
        parts.append(C.tube("GoheiSplit", [crack_at - d * 0.03, crack_at + kink * 0.03], [0.009, 0.009], 6, M["crack"]))
        parts.append(C.uv_sphere("GoheiCap", 0.019, tuple(end), (1, 1, 1), 10, 6, M["metal"]))
        # Register pages wrapped round the shaft (inked, struck through).
        for tt, ln in ((0.15, 0.07), (0.28, 0.05)):
            a = crack_at + kink * (tt * 0.38 / 0.3)
            parts.append(C.tube("RegisterWrap", [a, a + kink * ln], [0.017, 0.016], 8, M["paper"]))
            parts.append(C.tube("RegisterStrike", [a + kink * ln * 0.2, a + kink * ln * 0.8], [0.0175, 0.0175], 8, M["blackink"], (1.0, 1.0)))
        # Torn zigzag shide: one long, one ripped short, one hanging by a scrap.
        for sx, count, lean in ((1.0, 6, 0.0), (-1.0, 3, 0.01), (0.3, 2, -0.01)):
            bm = bmesh.new()
            prev = None
            for i in range(count):
                z = -i * 0.045
                x = sx * (0.022 + (0.022 if i % 2 else 0.0))
                w = 0.018 if i < count - 1 else 0.012
                a = bm.verts.new(end + Vector((x - w + lean * i, 0.0, z)))
                b = bm.verts.new(end + Vector((x + w * (0.6 if i == count - 1 else 1.0), 0.004 * i, z - (0.012 if i == count - 1 else 0.0))))
                if prev:
                    bm.faces.new((prev[0], prev[1], b, a))
                prev = (a, b)
            shide = C.new_object("Shide", bm, M["shide"], smooth=False)
            C.solidify(shide, 0.003)
            parts.append(shide)
        for p in parts:
            C.rigid(p, "hand.R")
        return parts

    body = build_body()
    head_parts = build_head()
    for p in head_parts:
        C.rigid(p, "head")
    hair = build_long_hair()
    for p in hair:
        C.weight_by_bones(p, arm, ["head", "neck", "chest", "spine"], power=4.0)
    parts = [body] + head_parts + hair + build_outfit() + build_gohei()
    maiden = C.join(parts, "FormerMaiden")
    mod = maiden.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    maiden.parent = arm

    # ------------------------------------------------------------ animation
    start_animation(arm)

    # Rest: gohei held low, head a little bowed, heavy shoulders.
    REST = {"upper_arm.L": (3, 0, 5), "forearm.L": (10, 0, 0), "upper_arm.R": (12, 0, -4), "forearm.R": (32, 0, 0), "hand.R": (-18, 0, 0), "head": (8, 0, 0), "neck": (4, 0, 0)}

    def with_rest(p):
        out = dict(REST)
        out.update(p)
        return out

    # Idle: 60f loop. Slow, shallow breathing; the head drifts as if listening.
    action("idle", 60, {
        0: with_rest({"chest": (0, 0, 0), "hips@loc": (0, 0, 0)}),
        30: with_rest({"chest": (-2, 0, 1), "head": (5, 4, -2), "upper_arm.L": (2, 0, 7), "hips@loc": (0, -0.006, 0)}),
        60: with_rest({"chest": (0, 0, 0), "hips@loc": (0, 0, 0)}),
    }, loop=True)

    # Walk: 30f loop, slow and heavy. Left heel strikes at 0, right at 15.
    def walk_contact(s):
        return with_rest({
            "hips@loc": (0, -0.03, 0), "hips": (0, 5 * s, 2 * s), "spine": (6, 0, 0), "chest": (0, -6 * s, -2 * s), "head": (10, 4 * s, 0),
            "thigh.L": (20 * s, 0, 1), "thigh.R": (-20 * s, 0, -1),
            "shin.L": (-5 if s > 0 else -14, 0, 0), "shin.R": (-14 if s > 0 else -5, 0, 0),
            "foot.L": (12 if s > 0 else 0, 0, 0), "foot.R": (0 if s > 0 else 12, 0, 0),
            "upper_arm.L": (-10 * s, 0, 5), "upper_arm.R": (12 + 8 * s, 0, -4),
        })

    def walk_pass(s):
        # s = +1: the right leg swings through under a straight left.
        return with_rest({
            "hips@loc": (0, 0.0, 0), "hips": (0, 0, -3 * s), "spine": (7, 0, 0), "chest": (0, 0, 3 * s), "head": (11, 0, 0),
            "thigh.L": (-4 * s if s > 0 else 12, 0, 1), "thigh.R": (12 if s > 0 else 4, 0, -1),
            "shin.L": (-3 if s > 0 else -50, 0, 0), "shin.R": (-50 if s > 0 else -3, 0, 0),
            "foot.L": (0 if s > 0 else 10, 0, 0), "foot.R": (10 if s > 0 else 0, 0, 0),
        })

    action("walk", 30, {0: walk_contact(1), 8: walk_pass(1), 15: walk_contact(-1), 23: walk_pass(-1), 30: walk_contact(1)}, loop=True)

    # Strike 1: 20f. Wide right-to-left sweep, contact frame 9.
    WIND1 = {"chest": (0, -45, 0), "spine": (0, -18, 0), "upper_arm.R": (20, 0, -85), "forearm.R": (40, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (30, 0, 25), "thigh.R": (-10, 0, 0), "thigh.L": (15, 0, 0), "head": (5, 20, 0), "hips@loc": (0, -0.02, 0)}
    HIT1 = {"chest": (5, 35, 0), "spine": (5, 15, 0), "upper_arm.R": (85, 0, 20), "forearm.R": (5, 0, 0), "hand.R": (-70, 0, 0), "upper_arm.L": (-10, 0, 30), "thigh.R": (-12, 0, 0), "thigh.L": (28, 0, 0), "shin.L": (-14, 0, 0), "head": (5, -10, 0), "hips@loc": (0, -0.04, 0.03)}
    action("strike1", 20, {0: with_rest({}), 5: WIND1, 9: HIT1, 13: {**HIT1, "chest": (5, 45, 0)}, 20: with_rest({})})

    # Strike 2: 20f. Backhand left-to-right, contact frame 9.
    WIND2 = {"chest": (0, 38, 0), "spine": (0, 12, 0), "upper_arm.R": (70, 0, 35), "forearm.R": (80, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (10, 0, 30), "thigh.L": (15, 0, 0), "head": (5, -15, 0), "hips@loc": (0, -0.02, 0)}
    HIT2 = {"chest": (5, -40, 0), "spine": (5, -15, 0), "upper_arm.R": (80, 0, -70), "forearm.R": (5, 0, 0), "hand.R": (-70, 0, 0), "upper_arm.L": (20, 0, 20), "thigh.R": (22, 0, 0), "shin.R": (-12, 0, 0), "head": (5, 12, 0), "hips@loc": (0, -0.04, 0.03)}
    action("strike2", 20, {0: with_rest({}), 5: WIND2, 9: HIT2, 13: {**HIT2, "chest": (5, -48, 0)}, 20: with_rest({})})

    # Thrust: 24f. Draw back, then a straight lunge with the gohei, contact frame 12.
    WIND_T = {"chest": (-4, -28, 0), "spine": (0, -10, 0), "upper_arm.R": (-25, 0, -12), "forearm.R": (95, 0, 0), "hand.R": (-35, 0, 0), "upper_arm.L": (40, 0, 20), "forearm.L": (30, 0, 0), "thigh.L": (18, 0, 0), "shin.L": (-10, 0, 0), "thigh.R": (-8, 0, 0), "head": (6, 20, 0), "hips@loc": (0, -0.03, -0.04)}
    HIT_T = {"chest": (6, 18, 0), "spine": (8, 6, 0), "upper_arm.R": (82, 0, -4), "forearm.R": (4, 0, 0), "hand.R": (-78, 0, 0), "upper_arm.L": (-30, 0, 18), "forearm.L": (20, 0, 0), "thigh.L": (55, 0, 0), "shin.L": (-58, 0, 0), "foot.L": (5, 0, 0), "thigh.R": (-28, 0, 0), "shin.R": (-6, 0, 0), "foot.R": (22, 0, 0), "head": (-4, -8, 0), "hips@loc": (0, -0.1, 0.14)}
    action("thrust", 24, {0: with_rest({}), 7: WIND_T, 12: HIT_T, 16: HIT_T, 24: with_rest({})})

    # Seal cast: 36f. Hands gather into a seal, then push the barrier out; release frame 20.
    GATHER = {"upper_arm.L": (30, 40, 0), "forearm.L": (115, 0, 0), "hand.L": (20, 0, 20), "upper_arm.R": (30, -40, 0), "forearm.R": (115, 0, 0), "hand.R": (-75, -30, -30), "head": (16, 0, 0), "chest": (4, 0, 0)}
    CHARGE = {**GATHER, "head": (22, 0, 0), "spine": (6, 0, 0), "thigh.L": (12, 0, 0), "shin.L": (-18, 0, 0), "thigh.R": (6, 0, 0), "shin.R": (-18, 0, 0), "hips@loc": (0, -0.04, 0)}
    RELEASE = {"upper_arm.L": (82, 0, 28), "forearm.L": (6, 0, 0), "hand.L": (-65, 0, 0), "upper_arm.R": (78, 0, -30), "forearm.R": (6, 0, 0), "hand.R": (-70, 0, 0), "chest": (-6, 0, 0), "head": (-4, 0, 0), "thigh.L": (18, 0, 0), "shin.L": (-8, 0, 0), "thigh.R": (-10, 0, 0), "hips@loc": (0, -0.01, 0.05)}
    action("seal_cast", 36, {0: with_rest({}), 10: GATHER, 17: CHARGE, 20: RELEASE, 27: {**RELEASE, "chest": (-4, 0, 0)}, 36: with_rest({})})

    # Kneel: 40f. Steps down onto one knee, settles into seiza, joins hands in prayer.
    ONE_KNEE = grounded({"thigh.L": (78, 0, 0), "shin.L": (-80, 0, 0), "foot.L": (0, 0, 0), "thigh.R": (-8, 0, 0), "shin.R": (-95, 0, 0), "foot.R": (-40, 0, 0), "spine": (8, 0, 0), "head": (12, 0, 0), "upper_arm.L": (20, 0, 8), "forearm.L": (40, 0, 0), "upper_arm.R": (12, 0, -6), "forearm.R": (35, 0, 0), "hand.R": (-15, 0, 0)})
    SEIZA = {"thigh.L": (76, 0, 2), "thigh.R": (76, 0, -2), "shin.L": (-166, 0, 0), "shin.R": (-166, 0, 0), "foot.L": (-78, 0, 0), "foot.R": (-78, 0, 0), "spine": (4, 0, 0)}
    SEIZA_HANDS = grounded({**SEIZA, "upper_arm.L": (28, 0, 4), "forearm.L": (55, 0, 0), "upper_arm.R": (28, 0, -4), "forearm.R": (55, 0, 0), "hand.R": (-20, 0, 0), "head": (14, 0, 0)})
    PRAY = grounded({**SEIZA, "spine": (6, 0, 0), "chest": (4, 0, 0), "upper_arm.L": (20, 40, 0), "forearm.L": (110, 0, 0), "hand.L": (20, 0, 20), "upper_arm.R": (20, -40, 0), "forearm.R": (110, 0, 0), "hand.R": (-60, 0, -15), "neck": (8, 0, 0), "head": (24, 0, 0)})
    action("kneel", 40, {0: with_rest({"hips@loc": (0, 0, 0)}), 13: ONE_KNEE, 26: SEIZA_HANDS, 34: PRAY, 40: PRAY})

    # Hurt: 10f. A stiff recoil.
    action("hurt", 10, {0: with_rest({}), 3: {"spine": (-12, 0, 0), "chest": (-10, 6, 0), "head": (-18, 0, 0), "upper_arm.L": (18, 0, 38), "upper_arm.R": (24, 0, -34), "forearm.R": (30, 0, 0), "hand.R": (-20, 0, 0), "hips@loc": (0, 0.0, -0.05)}, 10: with_rest({})})

    # Death: 45f. Staggers, sinks to her knees, sits back and slumps (the game fades her).
    STAGGER = with_rest({"spine": (-8, 0, 0), "chest": (-6, 0, 0), "head": (-10, 0, 0), "upper_arm.L": (10, 0, 25), "upper_arm.R": (15, 0, -22), "thigh.R": (-10, 0, 0), "hips@loc": (0, 0, -0.04)})
    KNEES = grounded({"thigh.L": (8, 0, 3), "thigh.R": (8, 0, -3), "shin.L": (-95, 0, 0), "shin.R": (-95, 0, 0), "foot.L": (-55, 0, 0), "foot.R": (-55, 0, 0), "spine": (12, 0, 0), "chest": (6, 0, 0), "head": (25, 0, 0), "upper_arm.L": (6, 0, 12), "upper_arm.R": (10, 0, -10), "forearm.R": (25, 0, 0), "forearm.L": (15, 0, 0)})
    SLUMP = grounded({**SEIZA, "spine": (24, 0, 0), "chest": (18, 0, 4), "neck": (15, 0, 0), "head": (35, -10, 0), "upper_arm.L": (14, 0, 2), "forearm.L": (28, 0, 0), "upper_arm.R": (18, 0, -2), "forearm.R": (30, 0, 0), "hand.R": (10, 0, 0), "hand.L": (10, 0, 0)})
    action("death", 45, {0: with_rest({"hips@loc": (0, 0, 0)}), 6: STAGGER, 18: KNEES, 32: SLUMP, 45: SLUMP})

    arm.animation_data.action = bpy.data.actions["idle"]
    C.export_glb("assets/models/characters/former_maiden/former_maiden.glb", [arm, maiden])
    top = max(v.co.z for v in maiden.data.vertices)
    print("former_maiden tris:", tri_count(maiden), "height: %.3f" % top)


# ================================================================ 2. the Wayside God
def build_wayside_god():
    C.reset_scene()
    M = {
        "stone": C.material("WeatheredStone", (0.13, 0.13, 0.12), 0.95),
        "worn": C.material("WornStone", (0.2, 0.2, 0.19), 0.95),
        "slab": C.material("SlabStone", (0.08, 0.08, 0.075), 0.95),
        "carve": C.material("Carving", (0.03, 0.03, 0.03), 0.9),
        "moss": C.material("Moss", (0.1, 0.17, 0.04), 0.95),
        "moss_dark": C.material("MossDark", (0.05, 0.1, 0.03), 0.95),
        "bib": C.material("FadedBib", (0.3, 0.05, 0.045), 0.85),
        "straw": C.material("Straw", (0.42, 0.3, 0.15), 0.9),
        "straw_dark": C.material("StrawDark", (0.2, 0.13, 0.06), 0.9),
        "glow": C.material("LanternMoss", (0.95, 0.6, 0.25), 0.6, emission=0.8),
        "flame": C.material("SpiritFlame", (1.0, 0.55, 0.2), 0.3, emission=4.0),
    }

    bones = [
        ("root", (0, 0, 0), (0, 0, 0.1), None),
        ("hips", (0, 0, 0.06), (0, 0, 0.2), "root"),
        ("spine", (0, 0, 0.2), (0, 0, 0.36), "hips"),
        ("head.R", (-0.068, 0, 0.38), (-0.068, 0, 0.53), "spine"),  # the surviving figure
        ("head.L", (0.075, 0, 0.37), (0.075, 0, 0.51), "spine"),  # the half worn smooth
    ]
    for s, sx in (("L", 1.0), ("R", -1.0)):
        bones += [
            (f"arm.{s}", (sx * 0.135, -0.04, 0.34), (sx * 0.155, -0.1, 0.225), "spine"),
            (f"hand.{s}", (sx * 0.155, -0.1, 0.225), (sx * 0.05, -0.165, 0.205), f"arm.{s}"),
        ]
    arm = build_armature("WaysideGodRig", bones, forward_roll=("hand.L", "hand.R"))

    parts = []
    # Stout stone body: a squat egg with a flat underside, weathered by noise.
    body = C.uv_sphere("StoneBody", 1.0, (0, 0.005, 0.235), (0.19, 0.145, 0.2), 28, 16, M["stone"])
    for v in body.data.vertices:
        v.co.z = max(v.co.z, 0.055)
        # Broader at the base, narrowing to the shoulders.
        k = 1.0 + 0.12 * max(0.0, (0.25 - v.co.z) / 0.2)
        v.co.x *= k
        v.co.y *= k
    body.data.update()
    roughen(body, 0.014, 9.0, seed=1.0)
    C.weight_by_bones(body, arm, ["hips", "spine"], power=3.0)
    parts.append(body)

    # The two heads of the pair, merged into the one stone.
    head_r = C.uv_sphere("HeadSurvivor", 0.083, (-0.068, -0.01, 0.455), (1.0, 0.92, 1.02), 24, 12, M["stone"])
    roughen(head_r, 0.006, 12.0, seed=3.0)
    C.rigid(head_r, "head.R")
    head_l = C.uv_sphere("HeadWorn", 0.078, (0.075, 0.0, 0.438), (1.0, 0.95, 0.94), 20, 10, M["worn"])
    # Worn smooth and chipped: flatten the face, shave a slope off the crown.
    for v in head_l.data.vertices:
        if v.co.y < -0.035:
            v.co.y = -0.035 + (v.co.y + 0.035) * 0.45
        slope = 0.5 + (v.co.x - 0.075) * 0.6
        if v.co.z > slope:
            v.co.z = slope + (v.co.z - slope) * 0.4
    head_l.data.update()
    roughen(head_l, 0.004, 6.0, seed=5.0)
    C.rigid(head_l, "head.L")
    parts += [head_r, head_l]

    # A gentle, sad carved face on the survivor: closed eyes, sloping brows, a small mouth.
    face = []
    fx, fy, fz = -0.068, -0.086, 0.455
    for sx in (1.0, -1.0):
        ex = fx + sx * 0.03
        eye = [Vector((ex - 0.015, fy + 0.012 + abs(sx * 0.0), fz - 0.002)), Vector((ex, fy + 0.002, fz - 0.009)), Vector((ex + 0.015, fy + 0.012, fz - 0.002))]
        face.append(C.tube("ClosedEye", eye, [0.0032, 0.0035, 0.0032], 5, M["carve"]))
        # Brows lift towards the middle: a sad slope.
        inner = Vector((fx + sx * 0.012, fy + 0.004, fz + 0.03))
        outer = Vector((fx + sx * 0.044, fy + 0.02, fz + 0.016))
        face.append(C.tube("Brow", [inner, outer], [0.003, 0.0022], 5, M["carve"]))
    mouth = [Vector((fx - 0.013, fy + 0.008, fz - 0.043)), Vector((fx, fy + 0.002, fz - 0.039)), Vector((fx + 0.013, fy + 0.008, fz - 0.043))]
    face.append(C.tube("Mouth", mouth, [0.0025, 0.003, 0.0025], 5, M["carve"]))
    for p in face:
        C.rigid(p, "head.R")
    parts += face
    # The worn half keeps only a faint crease where its face used to be.
    ghost = C.tube("WornCrease", [Vector((0.06, -0.071, 0.44)), Vector((0.075, -0.073, 0.437)), Vector((0.09, -0.07, 0.44))], [0.0018, 0.002, 0.0015], 4, M["stone"])
    C.rigid(ghost, "head.L")
    parts.append(ghost)

    # Small straw hat (kasa) on the survivor, tipped a little.
    bm = bmesh.new()
    seg = 24
    apex = bm.verts.new((0, 0, 0.055))
    rim = [bm.verts.new((math.cos(2 * math.pi * k / seg) * 0.11, math.sin(2 * math.pi * k / seg) * 0.11, 0.0)) for k in range(seg)]
    lip = [bm.verts.new((math.cos(2 * math.pi * k / seg) * 0.118, math.sin(2 * math.pi * k / seg) * 0.118, -0.008)) for k in range(seg)]
    for k in range(seg):
        bm.faces.new((apex, rim[k], rim[(k + 1) % seg]))
        bm.faces.new((rim[k], lip[k], lip[(k + 1) % seg], rim[(k + 1) % seg]))
    hat = C.new_object("Kasa", bm, M["straw"])
    C.solidify(hat, 0.006)
    hat_m = Matrix.Translation((-0.07, -0.005, 0.525)) @ Matrix.Rotation(math.radians(-10), 4, "Y") @ Matrix.Rotation(math.radians(-6), 4, "X")
    C.transform(hat, hat_m)
    rings = []
    for r in (0.035, 0.07, 0.1):
        ring = C.tube("KasaRing", [Vector((0, 0, 0)), Vector((0, 0, 0.004))], [r, r], 24, M["straw_dark"], cap=False)
        C.transform(ring, hat_m @ Matrix.Translation((0, 0, 0.056 * (1 - r / 0.11) + 0.003)))
        C.solidify(ring, 0.003)
        rings.append(ring)
    hat_knot = C.uv_sphere("KasaKnob", 0.01, (0, 0, 0), (1, 1, 1), 8, 6, M["straw_dark"])
    C.transform(hat_knot, hat_m @ Matrix.Translation((0, 0, 0.058)))
    for p in [hat, hat_knot] + rings:
        C.rigid(p, "head.R")
    parts += [hat, hat_knot] + rings

    # Faded red bib (yodarekake), tied under the survivor's chin, with a frayed hem.
    bm = bmesh.new()
    cols, rows = 10, 5
    grid = []
    for r in range(rows + 1):
        t = r / rows
        z = 0.385 - t * 0.14
        half = 0.07 + t * 0.045
        row = []
        for c in range(cols + 1):
            u = -1 + 2 * c / cols
            x = -0.045 + u * half
            # Wrap onto the body surface (ellipse in XY), slightly proud of it.
            bz = (z - 0.235) / 0.2
            k = math.sqrt(max(0.05, 1.0 - bz * bz))
            ex, ey = 0.19 * k * 1.03 + 0.012, 0.145 * k * 1.03 + 0.012
            xn = max(-0.98, min(0.98, x / ex))
            y = -ey * math.sqrt(1.0 - xn * xn)
            fray = (0.006 if (c % 2) else -0.004) if r == rows else 0.0
            row.append(bm.verts.new((x, y - 0.004 * t, z + fray)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    bib = C.new_object("Yodarekake", bm, M["bib"])
    C.solidify(bib, 0.004)
    tie = C.tube("BibTie", [Vector((-0.12, -0.055, 0.39)), Vector((-0.045, -0.105, 0.39)), Vector((0.03, -0.055, 0.39))], [0.006, 0.006, 0.006], 6, M["bib"])
    for p in (bib, tie):
        C.weight_by_bones(p, arm, ["spine", "hips"], power=4.0)
    parts += [bib, tie]

    # Moss: soft lumps on the worn head, the shoulders and the foot of the stone.
    moss = []
    for i, (c, r, sc, mat) in enumerate((
        ((0.085, 0.01, 0.49), 0.05, (1.2, 1.1, 0.45), "moss"),
        ((0.15, 0.03, 0.33), 0.04, (1.0, 1.3, 0.5), "moss_dark"),
        ((-0.16, 0.05, 0.3), 0.035, (1.0, 1.2, 0.5), "moss"),
        ((0.02, 0.1, 0.4), 0.05, (1.4, 0.8, 0.6), "moss_dark"),
        ((0.12, -0.08, 0.08), 0.045, (1.3, 0.8, 0.5), "moss"),
        ((-0.1, 0.12, 0.08), 0.05, (1.4, 1.0, 0.5), "moss_dark"),
    )):
        m = C.uv_sphere("Moss", r, c, sc, 12, 6, M[mat])
        roughen(m, r * 0.25, 30.0, seed=i * 2.0)
        bone = "head.L" if i == 0 else ("spine" if c[2] > 0.25 else "hips")
        C.rigid(m, bone)
        moss.append(m)
    parts += moss

    # Stubby stone arms folded over the belly; hands of moss and lantern light.
    for s, sx in (("L", 1.0), ("R", -1.0)):
        a0, a1 = P(f"arm.{s}", 0.0), P(f"arm.{s}", 1.0)
        limb = C.tube(f"Arm.{s}", [a0 + Vector((-sx * 0.01, 0.02, 0.01)), a0.lerp(a1, 0.5), a1], [0.03, 0.036, 0.032], 12, M["stone"])
        elbow = C.uv_sphere(f"Elbow.{s}", 0.032, tuple(a1), (1, 1, 1), 12, 6, M["stone"])
        C.rigid(elbow, f"arm.{s}")
        parts.append(elbow)
        roughen(limb, 0.004, 14.0, seed=7.0 + sx)
        C.weight_by_bones(limb, arm, [f"arm.{s}", "spine"], power=4.0)
        fore = C.tube(f"Forearm.{s}", [a1, P(f"hand.{s}", 0.7)], [0.03, 0.026], 12, M["stone"])
        C.weight_by_bones(fore, arm, [f"hand.{s}", f"arm.{s}"], power=4.0)
        hand = C.uv_sphere(f"MossHand.{s}", 0.03, tuple(P(f"hand.{s}", 0.95)), (1.1, 1.0, 0.8), 12, 6, M["moss"])
        roughen(hand, 0.006, 40.0, seed=11.0 + sx)
        core = C.uv_sphere(f"LanternCore.{s}", 0.017, tuple(P(f"hand.{s}", 0.95) + Vector((0, -0.018, 0.006))), (1, 1, 1), 10, 6, M["glow"])
        for p in (hand, core):
            C.rigid(p, f"hand.{s}")
        parts += [limb, fore, hand, core]

    # Pedestal slab with a small niche that holds the spirit flame.
    slab = C.uv_sphere("Pedestal", 1.0, (0, 0.0, 0.03), (0.24, 0.2, 0.035), 20, 8, M["slab"])
    for v in slab.data.vertices:
        v.co.z = max(v.co.z, 0.0)
    slab.data.update()
    roughen(slab, 0.008, 10.0, seed=13.0, keep_bottom=0.002)
    niche = C.box("Niche", (0.06, 0.03, 0.03), (0.0, -0.19, 0.035), M["carve"])
    flame = C.uv_sphere("SpiritFlame", 0.014, (0.0, -0.205, 0.07), (1.0, 1.0, 2.0), 10, 8, M["flame"])
    for v in flame.data.vertices:
        if v.co.z > 0.07:
            k = 1.0 - (v.co.z - 0.07) / 0.03
            v.co.x *= max(0.1, k)
            v.co.y = -0.205 + (v.co.y + 0.205) * max(0.1, k)
    flame.data.update()
    for p in (slab, niche, flame):
        C.rigid(p, "root")
    parts += [slab, niche, flame]

    god = C.join(parts, "WaysideGod")
    mod = god.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    god.parent = arm

    # ------------------------------------------------------------ animation
    start_animation(arm)

    # Idle: 60f loop. The survivor leans very slightly towards its worn half.
    action("idle", 60, {
        0: {"spine": (0, 0, 0), "head.R": (4, 0, -3), "head.L": (0, 0, 0), "hips@loc": (0, 0, 0)},
        30: {"spine": (2, 0, -1.5), "head.R": (7, 4, -6), "head.L": (1, 0, 1), "hips@loc": (0, -0.004, 0)},
        60: {"spine": (0, 0, 0), "head.R": (4, 0, -3), "head.L": (0, 0, 0), "hips@loc": (0, 0, 0)},
    }, loop=True)

    # Bow: 30f. A slow bow of the whole stone, hands pressed together.
    BOW = {"hips": (8, 0, 0), "spine": (20, 0, 0), "head.R": (20, 0, 0), "head.L": (14, 0, 0), "arm.L": (-10, 0, 0), "arm.R": (-10, 0, 0), "hips@loc": (0, -0.01, 0.01)}
    action("bow", 30, {0: {}, 12: BOW, 20: BOW, 30: {}})

    # Speak: 30f loop. The moss-and-lantern hands open outwards; the head nods softly.
    def speak(ph):
        s = 1 if ph == 0 else -1
        return {
            "arm.L": (50, 0, 8 + 4 * s), "hand.L": (-15, -25, 12 + 5 * s),
            "arm.R": (45 + 10 * s, 0, -8), "hand.R": (-20, 25, -12),
            "spine": (-3, 3 * s, 0), "head.R": (2 + 5 * (1 - s), 5 * s, -4), "head.L": (0, 0, 2),
        }
    action("speak", 30, {0: speak(0), 8: {**speak(0), "head.R": (10, 2, -4)}, 15: speak(1), 23: {**speak(1), "head.R": (0, -2, -4)}, 30: speak(0)}, loop=True)

    # Fade: 60f. It sags, the heads fall together, and it sinks into the earth.
    SAG = {"spine": (14, 0, 0), "head.R": (22, 0, -14), "head.L": (10, 0, 10), "arm.L": (-15, 0, -5), "arm.R": (-15, 0, 5), "hips@loc": (0, -0.03, 0)}
    SUNK = {"hips": (6, 0, 2), "spine": (22, 0, -3), "head.R": (30, 0, -20), "head.L": (14, 0, 16), "arm.L": (-25, 0, -8), "arm.R": (-25, 0, 8), "hips@loc": (0, -0.03, 0), "root@loc": (0, -0.22, 0)}
    action("fade", 60, {0: {}, 18: SAG, 40: {**SAG, "root@loc": (0, -0.08, 0)}, 60: SUNK})

    arm.animation_data.action = bpy.data.actions["idle"]
    C.export_glb("assets/models/characters/wayside_god/wayside_god.glb", [arm, god])
    top = max(v.co.z for v in god.data.vertices)
    print("wayside_god tris:", tri_count(god), "height: %.3f" % top)


if __name__ == "__main__":
    which = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["maiden", "god"]
    if "maiden" in which:
        build_former_maiden()
    if "god" in which:
        build_wayside_god()
