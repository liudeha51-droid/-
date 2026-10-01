class_name TrainingDummy
extends CharacterBody3D
## A sparring target for testing every combat action.
##
## It telegraphs a strike every few seconds: an orange flash means it can be
## blocked or parried; every third strike flashes red and is unblockable (dodge
## it). Breaking its posture staggers it, which lets the player start a QTE
## finisher with the interact button.

signal hit_taken(damage: float)
signal staggered
signal defeated

enum Mode { IDLE, WINDUP, RECOVER, FLINCH, STAGGERED, FINISHER, DOWN }

@export var max_hp := 400.0
@export var max_poise := 80.0
@export var poise_regen := 18.0
@export var auto_attack := true
@export var attack_interval := 3.0
@export var attack_range := 2.8
@export var windup_time := 0.6
@export var damage := 12.0
@export var stagger_time := 4.0

var hp := 400.0
var poise := 80.0
var mode: Mode = Mode.IDLE
var mode_time := 0.0
var strikes := 0
var last_result: int = -1
var _next_unblockable := false
var _cooldown := 2.0
var _since_hit := 10.0
var _flash := 0.0
var _body_mat := StandardMaterial3D.new()
var _label := Label3D.new()

# Interactable interface (available while staggered).
var prompt := "Finisher (QTE)"
var radius := 2.4
var interact_anim: StringName = &""
var effect_time := 0.0


func _ready() -> void:
	add_to_group(&"enemy")
	add_to_group(&"interactable")
	hp = max_hp
	poise = max_poise
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.6
	shape.shape = capsule
	shape.position.y = 0.8
	add_child(shape)
	_body_mat.albedo_color = Color(0.55, 0.38, 0.22)
	var body := MeshInstance3D.new()
	var mesh := CapsuleMesh.new()
	mesh.radius = 0.35
	mesh.height = 1.6
	body.mesh = mesh
	body.material_override = _body_mat
	body.position.y = 0.8
	add_child(body)
	# An ofuda-style talisman marks the dummy's front.
	var tag := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.18, 0.4, 0.04)
	tag.mesh = box
	var tag_mat := StandardMaterial3D.new()
	tag_mat.albedo_color = Color(0.95, 0.92, 0.8)
	tag.material_override = tag_mat
	tag.position = Vector3(0, 1.1, 0.36)
	add_child(tag)
	_label.position.y = 2.0
	_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_label.font_size = 40
	_label.outline_size = 8
	add_child(_label)


func _physics_process(delta: float) -> void:
	mode_time += delta
	_since_hit += delta
	if _since_hit > 1.5 and mode != Mode.STAGGERED and mode != Mode.FINISHER:
		poise = minf(max_poise, poise + poise_regen * delta)
	var player := _player()
	match mode:
		Mode.IDLE:
			if player:
				_face(player.global_position, delta)
			_cooldown -= delta
			if auto_attack and _cooldown <= 0.0 and player and _in_range(player):
				start_attack()
		Mode.WINDUP:
			if mode_time >= windup_time:
				_strike(player)
		Mode.RECOVER:
			if mode_time >= 0.6:
				_set_mode(Mode.IDLE)
		Mode.FLINCH:
			if mode_time >= 0.3:
				_set_mode(Mode.IDLE)
		Mode.STAGGERED:
			if mode_time >= stagger_time:
				poise = max_poise
				_set_mode(Mode.IDLE)
		Mode.DOWN:
			if mode_time >= 3.0:
				hp = max_hp
				poise = max_poise
				_set_mode(Mode.IDLE)
	velocity.x = move_toward(velocity.x, 0.0, 12.0 * delta)
	velocity.z = move_toward(velocity.z, 0.0, 12.0 * delta)
	velocity.y = -1.0 if is_on_floor() else velocity.y - 24.0 * delta
	move_and_slide()
	_update_visuals(delta)


func reset(pos: Vector3) -> void:
	global_position = pos
	velocity = Vector3.ZERO
	rotation.y = 0.0
	hp = max_hp
	poise = max_poise
	strikes = 0
	last_result = -1
	_cooldown = attack_interval
	_set_mode(Mode.IDLE)


## Begins a telegraphed strike (also used by tests and scripted encounters).
func start_attack(unblockable := false) -> void:
	_next_unblockable = unblockable or (strikes % 3 == 2)
	_set_mode(Mode.WINDUP)


func is_unblockable_windup() -> bool:
	return mode == Mode.WINDUP and _next_unblockable


func _strike(player: Node3D) -> void:
	strikes += 1
	_cooldown = attack_interval
	last_result = -1
	_set_mode(Mode.RECOVER)
	if player == null or not _in_range(player):
		return
	var to := player.global_position - global_position
	to.y = 0.0
	if _forward().dot(to.normalized()) < 0.3:
		return
	var info := HitInfo.new(self, damage * (1.5 if _next_unblockable else 1.0), 5.0)
	info.unblockable = _next_unblockable
	info.parryable = not _next_unblockable
	info.heavy = _next_unblockable
	info.guard_damage = 20.0
	last_result = player.receive_hit(info)


func receive_hit(info: HitInfo) -> HitInfo.Result:
	if mode in [Mode.DOWN, Mode.FINISHER]:
		return HitInfo.Result.IGNORED
	_since_hit = 0.0
	_flash = 0.15
	hp = maxf(0.0, hp - info.damage)
	velocity += info.push_direction(self) * info.knockback
	hit_taken.emit(info.damage)
	if hp <= 0.0:
		_set_mode(Mode.DOWN)
		defeated.emit()
		return HitInfo.Result.HIT
	if mode != Mode.STAGGERED:
		poise -= info.poise_damage
		if poise <= 0.0:
			_stagger()
		elif mode != Mode.WINDUP or info.heavy:
			_set_mode(Mode.FLINCH)  # light hits do not interrupt a windup
	return HitInfo.Result.HIT


func on_parried(_by: Node) -> void:
	poise -= 50.0
	if poise <= 0.0:
		_stagger()
	else:
		_set_mode(Mode.FLINCH)


func _stagger() -> void:
	poise = 0.0
	_set_mode(Mode.STAGGERED)
	staggered.emit()


# --- finisher / interactable interface -------------------------------------
func can_interact(_player: Node) -> bool:
	return mode == Mode.STAGGERED


func begin_finisher(_player: Node) -> void:
	_set_mode(Mode.FINISHER)


func receive_finisher(amount: float) -> void:
	hp = maxf(0.0, hp - amount)
	_flash = 0.2
	hit_taken.emit(amount)


func end_finisher(success: bool) -> void:
	if hp <= 0.0:
		_set_mode(Mode.DOWN)
		defeated.emit()
	else:
		poise = max_poise if success else max_poise * 0.5
		_set_mode(Mode.IDLE)
		_cooldown = 1.0 if not success else attack_interval


# --- helpers ----------------------------------------------------------------
func _set_mode(m: Mode) -> void:
	mode = m
	mode_time = 0.0


func _player() -> Node3D:
	var p := get_tree().get_first_node_in_group(&"player")
	return p as Node3D


func _in_range(player: Node3D) -> bool:
	return global_position.distance_to(player.global_position) <= attack_range


func _forward() -> Vector3:
	return Vector3(sin(rotation.y), 0.0, cos(rotation.y))


func _face(point: Vector3, delta: float) -> void:
	var d := point - global_position
	if Vector2(d.x, d.z).length() > 0.05:
		rotation.y = rotate_toward(rotation.y, atan2(d.x, d.z), 4.0 * delta)


func _update_visuals(delta: float) -> void:
	_flash = maxf(0.0, _flash - delta)
	var c := Color(0.55, 0.38, 0.22)
	match mode:
		Mode.WINDUP:
			var pulse := 0.5 + 0.5 * sin(mode_time * 30.0)
			c = c.lerp(Color(1.0, 0.1, 0.1) if _next_unblockable else Color(1.0, 0.6, 0.1), pulse)
		Mode.STAGGERED:
			c = c.lerp(Color(0.6, 0.6, 1.0), 0.5 + 0.5 * sin(mode_time * 8.0))
		Mode.DOWN:
			c = Color(0.25, 0.2, 0.18)
	if _flash > 0.0:
		c = Color.WHITE
	_body_mat.albedo_color = c
	var status := {Mode.WINDUP: "!!" if _next_unblockable else "!", Mode.STAGGERED: "STAGGERED", Mode.DOWN: "DOWN"}
	_label.text = "%d / %d  %s" % [hp, max_hp, status.get(mode, "")]
	_label.modulate = Color(1, 0.4, 0.3) if mode == Mode.WINDUP else Color.WHITE
