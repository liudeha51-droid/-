class_name PickupItem
extends Interactable
## A healing charm (stored, used with "use_item") or a faith orb (fills the
## burst meter immediately). Respawns after `respawn_time` seconds when > 0.

@export_enum("healing_charm", "faith_orb") var kind := "healing_charm"
@export var respawn_time := 20.0

var _mesh := MeshInstance3D.new()
var _light := OmniLight3D.new()


func _ready() -> void:
	interact_anim = &"pickup"
	effect_time = 0.4
	prompt = "Pick up healing charm" if kind == "healing_charm" else "Take faith orb"
	var mat := StandardMaterial3D.new()
	mat.emission_enabled = true
	if kind == "healing_charm":
		var box := BoxMesh.new()
		box.size = Vector3(0.14, 0.28, 0.03)
		_mesh.mesh = box
		mat.albedo_color = Color(0.95, 0.95, 0.85)
		mat.emission = Color(0.4, 1.0, 0.5)
	else:
		var orb := SphereMesh.new()
		orb.radius = 0.14
		orb.height = 0.28
		_mesh.mesh = orb
		mat.albedo_color = Color(1.0, 0.5, 0.3)
		mat.emission = Color(1.0, 0.4, 0.2)
	_mesh.material_override = mat
	_mesh.position.y = 0.5
	add_child(_mesh)
	_light.position.y = 0.5
	_light.omni_range = 1.5
	_light.light_color = mat.emission
	add_child(_light)


func _process(delta: float) -> void:
	_mesh.rotation.y += 2.0 * delta
	_mesh.position.y = 0.5 + 0.06 * sin(Time.get_ticks_msec() * 0.003)


func interact(player: Node) -> void:
	if kind == "healing_charm":
		player.add_item("healing_charm")
	else:
		player.add_burst(35.0)
	super.interact(player)
	_set_available(false)
	if respawn_time > 0.0:
		get_tree().create_timer(respawn_time).timeout.connect(_set_available.bind(true))


func _set_available(on: bool) -> void:
	enabled = on
	visible = on
