class_name CameraRig
extends Node3D
## Third-person orbit camera with Souls-style lock-on and screen shake.

const MOUSE_SENS := 0.0028
const STICK_SENS := 2.6
const PITCH_MIN := -1.2
const PITCH_MAX := 0.45

var yaw := 0.0
var pitch := -0.28
var follow: Node3D
var lock_target: Node3D
var spring: SpringArm3D
var camera: Camera3D
var _shake := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	top_level = true
	spring = SpringArm3D.new()
	spring.spring_length = 4.4
	spring.margin = 0.25
	spring.collision_mask = 1
	var probe := SphereShape3D.new()
	probe.radius = 0.25
	spring.shape = probe
	add_child(spring)
	camera = Camera3D.new()
	camera.fov = 62.0
	camera.far = 400.0
	spring.add_child(camera)
	camera.make_current()


func attach(target: CharacterBody3D) -> void:
	follow = target
	spring.add_excluded_object(target.get_rid())
	global_position = target.global_position + Vector3(0, 1.5, 0)


func shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and lock_target == null:
		yaw -= event.relative.x * MOUSE_SENS
		pitch = clampf(pitch - event.relative.y * MOUSE_SENS, PITCH_MIN, PITCH_MAX)


func _process(delta: float) -> void:
	if follow == null:
		return
	var look := Input.get_vector("look_left", "look_right", "look_up", "look_down")
	if lock_target and is_instance_valid(lock_target):
		var d := lock_target.global_position - follow.global_position
		d.y = 0.0
		if d.length() > 0.1:
			yaw = lerp_angle(yaw, atan2(-d.x, -d.z), 1.0 - exp(-8.0 * delta))
		pitch = lerpf(pitch, -0.36, 1.0 - exp(-5.0 * delta))
	else:
		yaw -= look.x * STICK_SENS * delta
		pitch = clampf(pitch - look.y * STICK_SENS * delta, PITCH_MIN, PITCH_MAX)
	rotation = Vector3(pitch, yaw, 0.0)
	var goal := follow.global_position + Vector3(0, 1.6, 0)
	global_position = global_position.lerp(goal, 1.0 - exp(-14.0 * delta))

	_shake = maxf(0.0, _shake - delta * 2.5)
	camera.h_offset = _rng.randf_range(-1.0, 1.0) * _shake * 0.3
	camera.v_offset = _rng.randf_range(-1.0, 1.0) * _shake * 0.3


## Direction the camera faces on the ground plane.
func flat_forward() -> Vector3:
	return Vector3(-sin(yaw), 0.0, -cos(yaw))
