class_name Kit
extends RefCounted
## Loads the in-house Misty Lake environment kit (tools/blender/build_misty_lake_kit.py).
## Callers keep a primitive fallback so the level still builds without the assets.

const DIR := "res://assets/models/environment/misty_lake/%s.glb"

static var _cache := {}


static func has(asset: String) -> bool:
	return ResourceLoader.exists(DIR % asset)


static func place(parent: Node3D, asset: String, pos: Vector3, yaw := 0.0, scale := 1.0) -> Node3D:
	if not has(asset):
		return null
	if not _cache.has(asset):
		_cache[asset] = load(DIR % asset)
	var node: Node3D = (_cache[asset] as PackedScene).instantiate()
	parent.add_child(node)
	node.position = pos
	node.rotation.y = yaw
	node.scale = Vector3.ONE * scale
	return node
