extends Node3D
## Training ground that exercises every action: open floor for locomotion,
## stepped platforms and a tower gap for jumping and gliding, two sparring
## dummies, pickups, a lever-operated gate and a barrier rift (story QTE).

const PLAYER_SCRIPT := preload("res://player/player.gd")

var player: Player
var camera_rig: CameraRig
var hud: Hud
var dummy: TrainingDummy
var passive_dummy: TrainingDummy
var lever: Lever
var gate: Node3D
var rift: QteTrigger
var charm: PickupItem
var orb: PickupItem


func _ready() -> void:
	_environment()
	_box(Vector3(0, -0.5, 0), Vector3(60, 1, 60), Color(0.36, 0.42, 0.33))  # ground
	# Stepped platforms (single jump, double jump) and a tall tower to glide off.
	_box(Vector3(10, 0.6, 4), Vector3(3, 1.2, 3), Color(0.55, 0.5, 0.45))
	_box(Vector3(10, 1.5, 8), Vector3(3, 3.0, 3), Color(0.55, 0.5, 0.45))
	_box(Vector3(10, 3.0, 13), Vector3(3, 6.0, 3), Color(0.5, 0.45, 0.42))
	_box(Vector3(10, 2.25, 22), Vector3(3, 4.5, 3), Color(0.5, 0.45, 0.42))
	# Shrine wall with a gate operated by a lever.
	_box(Vector3(-13, 2, -14), Vector3(10, 4, 0.6), Color(0.7, 0.68, 0.62))
	_box(Vector3(-1, 2, -14), Vector3(6, 4, 0.6), Color(0.7, 0.68, 0.62))
	gate = _box(Vector3(-6, 2, -14), Vector3(4, 4, 0.4), Color(0.75, 0.15, 0.12))

	player = PLAYER_SCRIPT.new()
	player.name = "Player"
	add_child(player)
	camera_rig = CameraRig.new()
	camera_rig.target = player
	add_child(camera_rig)
	player.camera_rig = camera_rig

	dummy = TrainingDummy.new()
	dummy.name = "Dummy"
	dummy.position = Vector3(0, 0, -6)
	add_child(dummy)
	passive_dummy = TrainingDummy.new()
	passive_dummy.name = "PassiveDummy"
	passive_dummy.auto_attack = false
	passive_dummy.position = Vector3(5, 0, -6)
	add_child(passive_dummy)

	lever = Lever.new()
	lever.door = gate
	lever.position = Vector3(-9, 0, -12.5)
	add_child(lever)
	charm = _pickup("healing_charm", Vector3(-4, 0, 4))
	_pickup("healing_charm", Vector3(-5.5, 0, 4))
	orb = _pickup("faith_orb", Vector3(-4, 0, 7))
	rift = QteTrigger.new()
	rift.position = Vector3(-12, 0, 6)
	add_child(rift)

	hud = Hud.new()
	add_child(hud)
	hud.bind(player)


func _pickup(kind: String, pos: Vector3) -> PickupItem:
	var p := PickupItem.new()
	p.kind = kind
	p.position = pos
	add_child(p)
	return p


func _box(pos: Vector3, size: Vector3, color: Color) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	var mesh := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mesh.mesh = bm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mesh.material_override = mat
	body.add_child(mesh)
	add_child(body)
	return body


func _environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var mat := ProceduralSkyMaterial.new()
	mat.sky_top_color = Color(0.35, 0.5, 0.8)
	mat.sky_horizon_color = Color(0.85, 0.75, 0.7)
	sky.sky_material = mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -30, 0)
	sun.shadow_enabled = true
	add_child(sun)
