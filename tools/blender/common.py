"""Shared helpers for the in-house Blender asset scripts.

Run any build script with Blender 4.2+ (GUI install or the `bpy` Python module):

    blender --background --python tools/blender/build_reimu.py
    python tools/blender/build_reimu.py        # with `pip install bpy==4.2.0`

Everything is generated from code so the assets are reproducible, reviewable in
diffs, and fully owned by the project (no third-party bases).
"""
import math
import os

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    return scene


def material(name, color, roughness=0.7, metallic=0.0, emission=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission > 0.0:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def new_object(name, bm, mat=None, smooth=True):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = smooth
    return obj


def activate(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def apply_modifiers(obj):
    activate(obj)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def solidify(obj, thickness):
    mod = obj.modifiers.new("Solidify", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 0.0
    apply_modifiers(obj)


def subdivide(obj, levels=1):
    mod = obj.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    apply_modifiers(obj)


def uv_sphere(name, radius, center, scale=(1, 1, 1), segments=24, rings=12, mat=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(center)
    return new_object(name, bm, mat)


def tube(name, points, radii, segments=12, mat=None, scale_xy=(1.0, 1.0), cap=True, twist_up=Vector((0, 0, 1))):
    """Loft rings of `radii` along a polyline; optional flattening per ring."""
    bm = bmesh.new()
    rings = []
    n = len(points)
    for i, p in enumerate(points):
        p = Vector(p)
        d = (Vector(points[min(i + 1, n - 1)]) - Vector(points[max(i - 1, 0)])).normalized()
        ref = twist_up if abs(d.dot(twist_up)) < 0.95 else Vector((1, 0, 0))
        side = d.cross(ref).normalized()
        up = side.cross(d).normalized()
        r = radii[i]
        ring = []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            off = side * math.cos(a) * r * scale_xy[0] + up * math.sin(a) * r * scale_xy[1]
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(segments):
            a, b = rings[i][k], rings[i][(k + 1) % segments]
            c, d2 = rings[i + 1][(k + 1) % segments], rings[i + 1][k]
            bm.faces.new((a, b, c, d2))
    if cap:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            if len(ring) >= 3:
                f = bm.faces.new(ring[::-1] if flip else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mat)


def box(name, size, center, mat=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(Vector(center)) @ euler_matrix(rot) @ Matrix.Diagonal((*size, 1.0))
    bm.transform(m)
    return new_object(name, bm, mat, smooth=False)


def euler_matrix(rot_deg):
    from mathutils import Euler
    return Euler([math.radians(a) for a in rot_deg], "XYZ").to_matrix().to_4x4()


def transform(obj, matrix):
    obj.data.transform(matrix)
    obj.data.update()


def join(objects, name):
    activate(objects[0])
    for o in objects:
        o.select_set(True)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def weight_by_bones(obj, arm, bone_names, power=6.0, keep=2):
    """Skin weights from distance to bone segments (a simple heat-weight stand-in)."""
    segs = {}
    for name in bone_names:
        b = arm.data.bones[name]
        segs[name] = (b.head_local.copy(), b.tail_local.copy())
    groups = {n: (obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)) for n in bone_names}
    for v in obj.data.vertices:
        ws = []
        for name, (a, b) in segs.items():
            d = seg_dist(v.co, a, b)
            ws.append((1.0 / (d ** power + 1e-12), name))
        ws.sort(reverse=True)
        ws = ws[:keep]
        total = sum(w for w, _ in ws)
        for w, name in ws:
            groups[name].add([v.index], w / total, "REPLACE")


def rigid(obj, bone_name):
    g = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
    g.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")


def export_glb(path, objects=None):
    path = os.path.join(REPO, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.view_layer.update()
    if objects is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objects)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=objects is not None,
        export_apply=True,
        export_yup=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
    )
    print("exported", path)
