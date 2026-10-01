class_name CameraRig
extends Node3D
## Orbit camera that follows a target. Mouse (captured on click) or right
## stick to look around; Esc releases the mouse.

@export var target: Node3D
@export var height := 1.35
@export var distance := 4.2
@export var mouse_sensitivity := 0.0025
@export var stick_speed := 2.6
@export var follow_speed := 10.0

var pitch := -0.25
var _pivot: Node3D
var _arm: SpringArm3D
var camera: Camera3D


func _ready() -> void:
	top_level = true
	_pivot = Node3D.new()
	add_child(_pivot)
	_arm = SpringArm3D.new()
	_arm.spring_length = distance
	_arm.margin = 0.2
	_pivot.add_child(_arm)
	camera = Camera3D.new()
	camera.fov = 60.0
	camera.position.z = distance
	_arm.add_child(camera)
	camera.current = true
	if target:
		global_position = target.global_position + Vector3.UP * height
		if target is CollisionObject3D:
			_arm.add_excluded_object(target.get_rid())


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventKey and event.pressed and event.physical_keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotation.y -= event.relative.x * mouse_sensitivity
		pitch -= event.relative.y * mouse_sensitivity


func _process(delta: float) -> void:
	var look := Input.get_vector(&"camera_left", &"camera_right", &"camera_up", &"camera_down")
	rotation.y -= look.x * stick_speed * delta
	pitch -= look.y * stick_speed * delta
	pitch = clampf(pitch, -1.2, 0.6)
	_pivot.rotation.x = pitch
	if target:
		var goal := target.global_position + Vector3.UP * height
		global_position = global_position.lerp(goal, minf(1.0, follow_speed * delta))
