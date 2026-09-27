class_name Toon
extends RefCounted
## Converts imported PBR materials to the project's stylised look: toon diffuse and
## specular bands plus an inverted-hull ink outline (docs/GAME_DESIGN.md §7-8).


static func outline_material(thickness: float, color := Color(0.04, 0.02, 0.03)) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color
	m.cull_mode = BaseMaterial3D.CULL_FRONT
	m.grow = true
	m.grow_amount = thickness
	return m


## Gives every surface of `mi` a toon copy of its material with the outline as next pass.
## Returns the new materials (callers use them for hit flashes).
static func apply(mi: MeshInstance3D, outline: Material) -> Array[StandardMaterial3D]:
	var out: Array[StandardMaterial3D] = []
	if mi.mesh == null:
		return out
	for i in mi.mesh.get_surface_count():
		var src := mi.get_active_material(i)
		var m: StandardMaterial3D
		if src is StandardMaterial3D:
			m = (src as StandardMaterial3D).duplicate()
		else:
			m = StandardMaterial3D.new()
		m.diffuse_mode = BaseMaterial3D.DIFFUSE_TOON
		m.specular_mode = BaseMaterial3D.SPECULAR_TOON
		m.rim_enabled = true
		m.rim = 0.35
		m.rim_tint = 0.6
		if outline:
			m.next_pass = outline
		mi.set_surface_override_material(i, m)
		out.append(m)
	return out
