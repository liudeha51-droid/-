class_name QteTrigger
extends Node3D
## Story QTE: walking into the barrier rift starts a button sequence.
## Success seals the rift; failure knocks Reimu back and hurts her.

signal resolved(success: bool)

@export var trigger_radius := 1.6
@export var sequence: Array[StringName] = [&"jump", &"attack_light", &"dodge"]
@export var step_window := 1.4
@export var fail_damage := 15.0
@export var rearm_time := 8.0

var armed := true
var sealed := false
var _ring := MeshInstance3D.new()
var _mat := StandardMaterial3D.new()


func _ready() -> void:
	var torus := TorusMesh.new()
	torus.inner_radius = trigger_radius - 0.12
	torus.outer_radius = trigger_radius
	_ring.mesh = torus
	_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_mat.albedo_color = Color(0.7, 0.2, 1.0)
	_ring.material_override = _mat
	_ring.position.y = 0.05
	add_child(_ring)
	for x in [-1.0, 1.0]:
		var post := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.1
		cyl.bottom_radius = 0.1
		cyl.height = 2.4
		post.mesh = cyl
		post.position = Vector3(x * trigger_radius, 1.2, 0)
		var red := StandardMaterial3D.new()
		red.albedo_color = Color(0.8, 0.1, 0.1)
		post.material_override = red
		add_child(post)
	var label := Label3D.new()
	label.text = "Barrier Rift"
	label.position.y = 2.7
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 48
	add_child(label)


func _physics_process(_delta: float) -> void:
	_ring.rotation.y += 0.02
	if not armed or sealed:
		return
	var player := get_tree().get_first_node_in_group(&"player") as Node3D
	if player == null:
		return
	var d := player.global_position - global_position
	if Vector2(d.x, d.z).length() <= trigger_radius and player.begin_story_qte(sequence, step_window, _on_done):
		armed = false


func _on_done(success: bool) -> void:
	var player := get_tree().get_first_node_in_group(&"player")
	if success:
		sealed = true
		_mat.albedo_color = Color(0.3, 0.8, 1.0)
	elif player:
		var info := HitInfo.new(self, fail_damage, 7.0)
		info.unblockable = true
		info.parryable = false
		info.heavy = true
		player.receive_hit(info)
		get_tree().create_timer(rearm_time).timeout.connect(func() -> void: armed = true)
	resolved.emit(success)
