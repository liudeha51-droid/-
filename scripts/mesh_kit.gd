class_name MeshKit
extends RefCounted
## Helpers for building placeholder geometry from primitives.
## Everything in the prototype is procedural so that final 3D models can be
## dropped in later without touching gameplay code (see docs/GAME_DESIGN.md).

static var _mat_cache := {}


static func mat(color: Color, emission_energy := 0.0, roughness := 0.8, metallic := 0.0, alpha := 1.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(color.r, color.g, color.b, alpha)
	m.roughness = roughness
	m.metallic = metallic
	if emission_energy > 0.0:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = emission_energy
	if alpha < 1.0:
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	return m


## Unshaded glowing material, cached by color. Used for danmaku bullets.
static func glow(color: Color, energy := 3.0) -> StandardMaterial3D:
	var key := "%s|%s" % [color.to_html(), energy]
	if _mat_cache.has(key):
		return _mat_cache[key]
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = energy
	_mat_cache[key] = m
	return m


static func add(parent: Node3D, mesh: Mesh, material: Material, pos := Vector3.ZERO, rot_deg := Vector3.ZERO, scl := Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = material
	mi.position = pos
	mi.rotation_degrees = rot_deg
	mi.scale = scl
	parent.add_child(mi)
	return mi


static func box(size: Vector3) -> BoxMesh:
	var m := BoxMesh.new()
	m.size = size
	return m


static func sphere(radius: float, height := -1.0, segments := 24) -> SphereMesh:
	var m := SphereMesh.new()
	m.radius = radius
	m.height = radius * 2.0 if height < 0.0 else height
	m.radial_segments = segments
	m.rings = segments / 2
	return m


static func cylinder(top: float, bottom: float, height: float, segments := 24) -> CylinderMesh:
	var m := CylinderMesh.new()
	m.top_radius = top
	m.bottom_radius = bottom
	m.height = height
	m.radial_segments = segments
	return m


static func capsule(radius: float, height: float) -> CapsuleMesh:
	var m := CapsuleMesh.new()
	m.radius = radius
	m.height = height
	return m


static func prism(size: Vector3) -> PrismMesh:
	var m := PrismMesh.new()
	m.size = size
	return m


## Static collider with an optional visible mesh.
static func solid_box(parent: Node3D, size: Vector3, pos: Vector3, material: Material = null, rot_deg := Vector3.ZERO) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	body.rotation_degrees = rot_deg
	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = size
	shape.shape = box_shape
	body.add_child(shape)
	if material:
		add(body, box(size), material)
	parent.add_child(body)
	return body


static func solid_cylinder(parent: Node3D, radius: float, height: float, pos: Vector3, material: Material = null) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = radius
	cyl.height = height
	shape.shape = cyl
	body.add_child(shape)
	if material:
		add(body, cylinder(radius, radius, height), material)
	parent.add_child(body)
	return body
