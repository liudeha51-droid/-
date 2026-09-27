class_name Shrine
extends Node3D
## Wayside shrine: the checkpoint ("bonfire"). Praying refills HP and gourds,
## sets the respawn point, and resets the area (the boss, if not yet beaten).

signal prayed

const RADIUS := 2.6
var player: Player
var hud: Hud
var _flame: OmniLight3D


func _ready() -> void:
	var wood := MeshKit.mat(Color(0.35, 0.2, 0.12), 0.0, 0.9)
	var roof := MeshKit.mat(Color(0.18, 0.16, 0.16), 0.0, 0.7)
	var red := MeshKit.mat(Color(0.8, 0.12, 0.1), 0.0, 0.6)
	var stone := MeshKit.mat(Color(0.5, 0.5, 0.5), 0.0, 0.95)
	MeshKit.solid_box(self, Vector3(1.8, 0.3, 1.4), Vector3(0, 0.15, 0), stone)
	MeshKit.add(self, MeshKit.box(Vector3(1.2, 1.0, 0.9)), wood, Vector3(0, 0.8, 0.1))
	MeshKit.add(self, MeshKit.prism(Vector3(1.8, 0.6, 1.4)), roof, Vector3(0, 1.6, 0.1))
	# Donation box, the Hakurei Shrine's eternal hope.
	MeshKit.add(self, MeshKit.box(Vector3(0.7, 0.4, 0.4)), wood, Vector3(0, 0.5, -0.65))
	MeshKit.add(self, MeshKit.box(Vector3(0.72, 0.04, 0.42)), MeshKit.mat(Color(0.9, 0.75, 0.3), 0.3, 0.4, 0.5), Vector3(0, 0.72, -0.65))
	# Small torii in front.
	for side in [-1.0, 1.0]:
		MeshKit.add(self, MeshKit.cylinder(0.06, 0.07, 1.8), red, Vector3(0.75 * side, 0.9, -1.5))
	MeshKit.add(self, MeshKit.box(Vector3(2.0, 0.1, 0.16)), red, Vector3(0, 1.85, -1.5))
	MeshKit.add(self, MeshKit.box(Vector3(1.6, 0.07, 0.1)), red, Vector3(0, 1.6, -1.5))
	# Sacred rope with paper streamers.
	MeshKit.add(self, MeshKit.cylinder(0.05, 0.05, 1.3), MeshKit.mat(Color(0.85, 0.8, 0.6)), Vector3(0, 1.28, -0.4), Vector3(0, 0, 90))
	for i in 3:
		MeshKit.add(self, MeshKit.box(Vector3(0.06, 0.22, 0.01)), MeshKit.mat(Color(1, 1, 1), 0.3), Vector3(-0.4 + i * 0.4, 1.1, -0.4))
	_flame = OmniLight3D.new()
	_flame.light_color = Color(1.0, 0.7, 0.4)
	_flame.light_energy = 2.0
	_flame.omni_range = 7.0
	_flame.shadow_enabled = true
	_flame.position = Vector3(0, 1.2, -1.0)
	add_child(_flame)


func player_in_range() -> bool:
	return player != null and player.global_position.distance_to(global_position) < RADIUS


func _process(_delta: float) -> void:
	_flame.light_energy = 2.0 + sin(Time.get_ticks_msec() * 0.009) * 0.25
	if hud == null or player == null:
		return
	var near := player_in_range() and not player.is_dead()
	hud.set_prompt("[F] Pray at the shrine" if near else "")
	if near and Input.is_action_just_pressed("interact"):
		pray()


func pray() -> void:
	player.rest()
	Sfx.play("rest", 0.0, -4.0)
	Fx.burst(get_parent(), global_position + Vector3(0, 1.2, -1.0), Color(1.0, 0.85, 0.5), 40, 2.5, 1.2, 0.07)
	hud.big_message("御参り", "Prayed at the shrine. Health and gourds restored.", Color(1.0, 0.85, 0.55), 1.5)
	prayed.emit()
