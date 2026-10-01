class_name Lever
extends Interactable
## A shrine mechanism: pulling it raises or lowers `door`.

@export var door: Node3D
@export var open_height := 3.0

var is_open := false
var _handle := MeshInstance3D.new()
var _closed_y := 0.0


func _ready() -> void:
	prompt = "Pull lever"
	interact_anim = &"interact"
	effect_time = 0.55
	var base := MeshInstance3D.new()
	var base_mesh := BoxMesh.new()
	base_mesh.size = Vector3(0.4, 0.8, 0.3)
	base.mesh = base_mesh
	base.position.y = 0.4
	add_child(base)
	var handle_mesh := CylinderMesh.new()
	handle_mesh.top_radius = 0.04
	handle_mesh.bottom_radius = 0.04
	handle_mesh.height = 0.7
	_handle.mesh = handle_mesh
	_handle.position = Vector3(0, 0.95, 0.1)
	_handle.rotation.x = -0.6
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.8, 0.1, 0.1)
	_handle.material_override = mat
	add_child(_handle)
	if door:
		_closed_y = door.position.y


func interact(player: Node) -> void:
	is_open = not is_open
	_handle.rotation.x = 0.6 if is_open else -0.6
	if door:
		var tw := create_tween()
		tw.tween_property(door, "position:y", _closed_y + (open_height if is_open else 0.0), 0.8) \
				.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	prompt = "Pull lever (close)" if is_open else "Pull lever"
	super.interact(player)
