class_name Player
extends CharacterBody3D
## Third-person action controller for Reimu.
##
## One explicit state machine drives every action. Each state owns its
## movement, animation, and which inputs may interrupt it:
##   Movement      IDLE / MOVE (slow walk, walk, run) -> SKID (sudden stop), DASH, DODGE (i-frames)
##   Jumping       AIR (jump, coyote time, variable height, double jump) -> GLIDE
##   Offense       ATTACK (light chain, heavy, charged, dash and aerial attacks) and CHARGE
##   Defense       GUARD (hold to block, tap right before a hit to parry) -> PARRY
##   Stun          HURT (flinch), STAGGER (heavy hit / guard break) -> RECOVER (tech roll)
##   Special       BURST (overload mode), QTE (finisher and story prompts), ITEM, INTERACT
##
## Attack recovery can be cancelled into a dodge, jump or dash from each
## attack's "cancel" time. Earlier presses are buffered and fire on that frame.

signal health_changed(hp: float, max_hp: float)
signal guard_changed(value: float, max_value: float)
signal burst_changed(value: float, active: bool)
signal items_changed(items: Dictionary)
signal state_changed(state_name: String)
signal prompt_changed(text: String)
signal perfect_evade
signal died

enum State { IDLE, MOVE, SKID, DASH, DODGE, AIR, GLIDE, ATTACK, CHARGE, GUARD, PARRY,
		HURT, STAGGER, RECOVER, BURST, QTE, ITEM, INTERACT, DEAD }

const MODEL_SCENE := preload("res://characters/reimu/reimu.glb")
const EXTRA_ANIMS := preload("res://characters/reimu/reimu_extra_anims.res")
const BUFFERED: Array[StringName] = [&"jump", &"dodge", &"dash", &"attack_light", &"attack_heavy",
		&"guard", &"interact", &"use_item", &"burst"]

## Attack table. Times are animation seconds:
##   active  window in which the hit lands
##   cancel  recovery starts; queued combo inputs and dodge/jump/dash cancels fire here
##   chain   window in which a light/heavy press queues next_light / next_heavy
##   reach   hit centre distance in front of Reimu; radius is the hit sphere size
const ATTACKS := {
	"light1": {"anim": &"attack1", "damage": 8.0, "active": [0.12, 0.28], "cancel": 0.3, "chain": [0.1, 0.48],
			"next_light": "light2", "next_heavy": "heavy", "lunge": 2.5, "reach": 1.0, "radius": 1.1,
			"knockback": 1.0, "poise": 12.0},
	"light2": {"anim": &"attack2", "damage": 9.0, "active": [0.12, 0.28], "cancel": 0.3, "chain": [0.1, 0.48],
			"next_light": "light3", "next_heavy": "ofuda_burst", "lunge": 2.5, "reach": 1.0, "radius": 1.1,
			"knockback": 1.0, "poise": 12.0},
	"light3": {"anim": &"attack3", "damage": 15.0, "active": [0.2, 0.42], "cancel": 0.5, "lunge": 3.5,
			"reach": 1.1, "radius": 1.3, "knockback": 5.0, "poise": 28.0, "heavy": true},
	"ofuda_burst": {"anim": &"cast", "damage": 12.0, "active": [0.08, 0.22], "cancel": 0.24, "reach": 2.6,
			"radius": 1.5, "knockback": 3.0, "poise": 18.0, "speed": 0.8},
	"heavy": {"anim": &"heavy_attack", "damage": 22.0, "active": [0.48, 0.75], "cancel": 0.8, "lunge": 4.0,
			"reach": 1.2, "radius": 1.4, "knockback": 6.0, "poise": 40.0, "heavy": true},
	"charged": {"anim": &"spell", "damage": 18.0, "active": [0.3, 0.6], "cancel": 0.7, "reach": 0.0,
			"radius": 2.2, "knockback": 7.0, "poise": 45.0, "heavy": true},
	"dash_attack": {"anim": &"dash_attack", "damage": 14.0, "active": [0.08, 0.32], "cancel": 0.38,
			"lunge": 8.0, "reach": 1.0, "radius": 1.2, "knockback": 4.0, "poise": 22.0},
	"air1": {"anim": &"air_attack1", "damage": 8.0, "active": [0.12, 0.28], "cancel": 0.3, "chain": [0.1, 0.48],
			"next_light": "air2", "next_heavy": "air_slam", "reach": 1.0, "radius": 1.2, "knockback": 1.0,
			"poise": 10.0, "air": true},
	"air2": {"anim": &"air_attack2", "damage": 11.0, "active": [0.2, 0.42], "cancel": 0.5, "chain": [0.25, 0.6],
			"next_heavy": "air_slam", "reach": 1.0, "radius": 1.3, "knockback": 4.0, "poise": 18.0, "air": true},
	"air_slam": {"anim": &"air_slam", "damage": 20.0, "active": [0.0, 0.0], "cancel": 0.45, "reach": 0.0,
			"radius": 2.4, "knockback": 6.0, "poise": 35.0, "heavy": true, "air": true},
}

@export_group("Movement")
@export var slow_walk_speed := 1.1
@export var walk_speed := 2.2
@export var run_speed := 5.6
@export var ground_accel := 30.0
@export var ground_decel := 36.0
@export var turn_speed := 14.0
## Releasing or reversing the stick above this speed triggers a skid.
@export var skid_min_speed := 4.2
@export var skid_decel := 16.0
@export var dash_speed := 13.0
@export var dash_time := 0.22
@export var dash_cooldown := 0.3
@export var dodge_speed := 9.0
@export var dodge_time := 0.5
## Invulnerable between these dodge times (seconds).
@export var dodge_iframes := Vector2(0.03, 0.34)
@export var dodge_recovery := 0.36

@export_group("Jumping")
@export var gravity := 24.0
@export var jump_velocity := 8.6
@export var air_jump_velocity := 8.0
@export var max_air_jumps := 1
@export var coyote_time := 0.12
## Upward velocity is multiplied by this when jump is released early.
@export var jump_cut := 0.45
@export var air_accel := 14.0
@export var max_fall_speed := 30.0
@export var glide_fall_speed := 1.6
@export var glide_speed := 4.8

@export_group("Combat")
@export var max_hp := 100.0
@export var max_guard := 60.0
@export var guard_regen := 20.0
@export var parry_window := 0.18
## Holding heavy longer than this starts a charged attack.
@export var charge_threshold := 0.3
@export var charge_max := 1.2
## Pressing dodge/jump inside this window of a stun performs a tech recovery.
@export var tech_window := Vector2(0.12, 0.5)
@export var heal_amount := 40.0

@export_group("Burst")
@export var burst_duration := 12.0
@export var burst_damage_mult := 1.6
@export var burst_speed_mult := 1.25
@export var burst_anim_mult := 1.2

var state: State = State.IDLE
var state_time := 0.0
var hp := 100.0
var guard_points := 60.0
var burst_meter := 0.0
var burst_active := false
var burst_time_left := 0.0
var items := {"healing_charm": 0}
var walk_toggled := false
var gait: StringName = &"run"
var air_jumps_left := 1
var attack_id := ""
var camera_rig: Node3D
var spawn_point := Vector3.ZERO
var auto_respawn := true

var visual: Node3D
var model: Node3D
var anim: AnimationPlayer
var aura: OmniLight3D
var sparks: CPUParticles3D

var _clock := 0.0
var _pressed := {}
var _used := {}
var _atk: Dictionary = {}
var _atk_time := 0.0
var _hit_targets: Array = []
var _queued_attack := ""
var _charge_level := 0.0
var _slam_landed := false
var _coyote := 0.0
var _jump_cut_done := false
var _glide_hold := 0.0
var _air_dash_ready := true
var _dash_dir := Vector3.FORWARD
var _dash_end_time := -10.0
var _dodge_dir := Vector3.FORWARD
var _skid_dir := Vector3.ZERO
var _guard_started := -10.0
var _guard_broken := false
var _last_block := -10.0
var _stun_length := 0.0
var _iframes := 0.0
var _hitstop := 0.0
var _speed_before_hitstop := 1.0
var _burst_fired := false
var _item_applied := false
var _interact_target: Node3D
var _interact_done := false
var _interact_len := 0.0
var _prompt := ""
var _qte_target: Node3D
var _qte_hits: Array = []
var _qte_story_cb := Callable()


func _ready() -> void:
	add_to_group(&"player")
	hp = max_hp
	guard_points = max_guard
	air_jumps_left = max_air_jumps
	spawn_point = global_position
	floor_snap_length = 0.35
	_build()
	play_anim(&"idle", 0.0)


func _build() -> void:
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.28
	capsule.height = 1.5
	shape.shape = capsule
	shape.position.y = 0.75
	add_child(shape)
	visual = Node3D.new()
	visual.name = "Visual"
	add_child(visual)
	model = MODEL_SCENE.instantiate()
	visual.add_child(model)
	anim = model.get_node("AnimationPlayer")
	anim.add_animation_library(&"x", EXTRA_ANIMS)
	aura = OmniLight3D.new()
	aura.position.y = 1.0
	aura.light_color = Color(1.0, 0.35, 0.25)
	aura.omni_range = 3.5
	aura.light_energy = 0.0
	add_child(aura)
	sparks = CPUParticles3D.new()
	sparks.position.y = 0.9
	sparks.emitting = false
	sparks.amount = 40
	sparks.lifetime = 0.8
	sparks.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	sparks.emission_sphere_radius = 0.6
	sparks.direction = Vector3.UP
	sparks.spread = 30.0
	sparks.gravity = Vector3(0, 1.5, 0)
	sparks.initial_velocity_min = 0.5
	sparks.initial_velocity_max = 1.5
	sparks.scale_amount_min = 0.03
	sparks.scale_amount_max = 0.06
	var spark_mesh := SphereMesh.new()
	spark_mesh.radius = 0.5
	spark_mesh.height = 1.0
	var spark_mat := StandardMaterial3D.new()
	spark_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	spark_mat.albedo_color = Color(1.0, 0.75, 0.4)
	spark_mesh.material = spark_mat
	sparks.mesh = spark_mesh
	add_child(sparks)


# ================================================================== frame loop
func _physics_process(delta: float) -> void:
	_clock += delta
	_poll_input()
	_tick_resources(delta)
	if _hitstop > 0.0:
		_hitstop -= delta
		if _hitstop <= 0.0:
			anim.speed_scale = _speed_before_hitstop
		return
	state_time += delta
	_iframes = maxf(_iframes - delta, 0.0)
	match state:
		State.IDLE, State.MOVE: _st_ground(delta)
		State.SKID: _st_skid(delta)
		State.DASH: _st_dash(delta)
		State.DODGE: _st_dodge(delta)
		State.AIR: _st_air(delta)
		State.GLIDE: _st_glide(delta)
		State.ATTACK: _st_attack(delta)
		State.CHARGE: _st_charge(delta)
		State.GUARD: _st_guard(delta)
		State.PARRY: _st_parry(delta)
		State.HURT, State.STAGGER: _st_stun(delta)
		State.RECOVER: _st_recover(delta)
		State.BURST: _st_burst(delta)
		State.QTE: _st_qte(delta)
		State.ITEM: _st_item(delta)
		State.INTERACT: _st_interact(delta)
		State.DEAD: _st_dead(delta)
	move_and_slide()
	_update_prompt()


func _enter(s: State) -> void:
	state = s
	state_time = 0.0
	state_changed.emit(state_name())


func state_name() -> String:
	return State.keys()[state]


# ================================================================ input helpers
func _poll_input() -> void:
	for a in BUFFERED:
		if Input.is_action_just_pressed(a):
			_pressed[a] = _clock
	if Input.is_action_just_pressed(&"walk_toggle"):
		walk_toggled = not walk_toggled


## Drops every buffered press, so buttons used for QTE prompts or pressed
## while dead do not fire as actions afterwards.
func clear_input_buffer() -> void:
	_used = _pressed.duplicate()


## True once per press if `action` was pressed within the last `window` seconds.
func _consume(action: StringName, window := 0.15) -> bool:
	var t: float = _pressed.get(action, -100.0)
	if _clock - t <= window and t > _used.get(action, -100.0):
		_used[action] = t
		return true
	return false


## Camera-relative movement input; length is the stick tilt (0..1).
func input_direction() -> Vector3:
	var v := Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")
	var yaw := camera_rig.rotation.y if camera_rig else 0.0
	return Vector3(v.x, 0.0, v.y).rotated(Vector3.UP, yaw)


func facing() -> Vector3:
	return Vector3(sin(visual.rotation.y), 0.0, cos(visual.rotation.y))


func face_towards(point: Vector3) -> void:
	var d := point - global_position
	d.y = 0.0
	if d.length() > 0.01:
		_face(d.normalized(), 0.0, true)


func _face(dir: Vector3, delta: float, instant := false) -> void:
	var target := atan2(dir.x, dir.z)
	visual.rotation.y = target if instant else rotate_toward(visual.rotation.y, target, turn_speed * delta)


func _horizontal() -> Vector3:
	return Vector3(velocity.x, 0.0, velocity.z)


func _set_horizontal(hv: Vector3) -> void:
	velocity.x = hv.x
	velocity.z = hv.z


func _apply_gravity(delta: float, scale := 1.0) -> void:
	if is_on_floor() and velocity.y <= 0.0:
		velocity.y = -1.0
	else:
		velocity.y = maxf(velocity.y - gravity * scale * delta, -max_fall_speed)


func _brake(delta: float, rate := -1.0) -> void:
	_set_horizontal(_horizontal().move_toward(Vector3.ZERO, (ground_decel if rate < 0.0 else rate) * delta))


# ================================================================== animation
func _anim_name(clip: StringName) -> StringName:
	return clip if anim.has_animation(clip) else StringName("x/" + clip)


## Plays `clip` (built-in or generated). Re-requesting the playing clip only
## updates its speed unless `restart` is set.
func play_anim(clip: StringName, blend := 0.12, speed := 1.0, restart := false) -> void:
	var n := _anim_name(clip)
	if _hitstop <= 0.0:
		anim.speed_scale = speed * _anim_mult()
	if anim.current_animation == n and anim.is_playing():
		if restart:
			anim.seek(0.0, true)
		return
	anim.play(n, blend)


func current_anim() -> StringName:
	return StringName(String(anim.current_animation).trim_prefix("x/"))


func is_anim(clip: StringName) -> bool:
	return anim.is_playing() and anim.current_animation == _anim_name(clip)


func anim_length(clip: StringName) -> float:
	return anim.get_animation(_anim_name(clip)).length


func _anim_mult() -> float:
	return burst_anim_mult if burst_active else 1.0


func _speed_mult() -> float:
	return burst_speed_mult if burst_active else 1.0


func start_hitstop(duration: float) -> void:
	if _hitstop <= 0.0:
		_speed_before_hitstop = anim.speed_scale
	anim.speed_scale = 0.0
	_hitstop = maxf(_hitstop, duration)


# ============================================================ ground movement
func _gait_for(tilt: float) -> StringName:
	if Input.is_action_pressed(&"slow_walk") or tilt < 0.4:
		return &"slow_walk"
	if walk_toggled or tilt < 0.75:
		return &"walk"
	return &"run"


func gait_speed(g: StringName) -> float:
	var base: float = {&"slow_walk": slow_walk_speed, &"walk": walk_speed}.get(g, run_speed)
	return base * _speed_mult()


func _st_ground(delta: float) -> void:
	if not is_on_floor():
		_coyote = coyote_time
		_enter_air()
		return
	_reset_air()
	if _try_ground_actions():
		return
	var dir := input_direction()
	var tilt := minf(dir.length(), 1.0)
	var hv := _horizontal()
	var speed := hv.length()
	if tilt > 0.05:
		var wish := dir.normalized()
		# Reversing at speed plants the feet first (skid turn).
		if state == State.MOVE and speed > skid_min_speed and hv.dot(wish) < -0.5 * speed:
			_start_skid(wish)
			return
		gait = _gait_for(tilt)
		hv = hv.move_toward(wish * gait_speed(gait), ground_accel * delta)
		_face(wish, delta)
		if state != State.MOVE:
			_enter(State.MOVE)
		play_anim(gait, 0.18, clampf(hv.length() / gait_speed(gait), 0.5, 1.3))
	else:
		# Letting go of the stick at a run is a sudden stop.
		if state == State.MOVE and speed > skid_min_speed:
			_start_skid(Vector3.ZERO)
			return
		hv = hv.move_toward(Vector3.ZERO, ground_decel * delta)
		if state != State.IDLE:
			_enter(State.IDLE)
		if not is_anim(&"land"):
			play_anim(&"idle", 0.2)
	_set_horizontal(hv)
	_apply_gravity(delta)


## Shared by every grounded, actionable state. Returns true if a new action began.
func _try_ground_actions() -> bool:
	if _consume(&"burst") and can_burst():
		_start_burst()
	elif _consume(&"jump"):
		_jump()
	elif _consume(&"dodge"):
		_start_dodge()
	elif _consume(&"dash") and _dash_ready():
		_start_dash()
	elif _consume(&"attack_light"):
		_start_attack("dash_attack" if _clock - _dash_end_time < 0.25 else "light1")
	elif _consume(&"attack_heavy"):
		_enter(State.CHARGE)
		_charge_level = 0.0
	elif Input.is_action_pressed(&"guard") and not _guard_broken:
		_enter_guard()
	elif _consume(&"interact") and _interact_target != null:
		_start_interact()
	elif _consume(&"use_item") and can_use_item():
		_enter(State.ITEM)
		_item_applied = false
		play_anim(&"heal", 0.1, 1.0, true)
	else:
		return false
	return true


func _start_skid(new_dir: Vector3) -> void:
	_skid_dir = new_dir
	_enter(State.SKID)
	play_anim(&"sudden_stop", 0.06, 1.0, true)


func _st_skid(delta: float) -> void:
	_brake(delta, skid_decel)
	_apply_gravity(delta)
	if not is_on_floor():
		_enter_air()
		return
	if state_time > 0.12 and _try_ground_actions():
		return
	var dir := input_direction()
	if dir.length() > 0.3:
		_skid_dir = dir.normalized()
	if state_time >= 0.45 or (state_time > 0.3 and _horizontal().length() < 0.05):
		if _skid_dir != Vector3.ZERO:
			_face(_skid_dir, 0.0, true)
		_enter(State.IDLE)


func _dash_ready() -> bool:
	return _clock - _dash_end_time > dash_cooldown and (is_on_floor() or _air_dash_ready)


func _start_dash() -> void:
	var dir := input_direction()
	_dash_dir = dir.normalized() if dir.length() > 0.1 else facing()
	_face(_dash_dir, 0.0, true)
	if not is_on_floor():
		_air_dash_ready = false
	_enter(State.DASH)
	play_anim(&"dash", 0.05, 1.0, true)


func _st_dash(_delta: float) -> void:
	_set_horizontal(_dash_dir * dash_speed * _speed_mult())
	velocity.y = 0.0
	if _consume(&"attack_light"):
		_dash_end_time = _clock
		_start_attack("dash_attack")
		return
	if state_time >= dash_time:
		_dash_end_time = _clock
		_set_horizontal(_dash_dir * run_speed * _speed_mult())
		if is_on_floor():
			_enter(State.MOVE)
		else:
			_enter_air()


func _start_dodge() -> void:
	var dir := input_direction()
	_dodge_dir = dir.normalized() if dir.length() > 0.1 else facing()
	_face(_dodge_dir, 0.0, true)
	_enter(State.DODGE)
	play_anim(&"roll", 0.05, 1.0, true)


func _st_dodge(delta: float) -> void:
	var k := clampf((1.0 - state_time / dodge_time) * 1.4, 0.0, 1.0)
	_set_horizontal(_dodge_dir * dodge_speed * _speed_mult() * k)
	_apply_gravity(delta)
	if state_time >= dodge_recovery:
		if _consume(&"attack_light", 0.3):
			_start_attack("light1")
			return
		if _consume(&"jump", 0.3) and is_on_floor():
			_jump()
			return
	if state_time >= dodge_time:
		_finish_action()


func is_invulnerable() -> bool:
	if state == State.DODGE and state_time >= dodge_iframes.x and state_time <= dodge_iframes.y:
		return true
	return _iframes > 0.0 or state in [State.BURST, State.QTE, State.DEAD, State.RECOVER]


# =================================================================== air
func _reset_air() -> void:
	air_jumps_left = max_air_jumps + (1 if burst_active else 0)
	_air_dash_ready = true


func _jump() -> void:
	velocity.y = jump_velocity
	_coyote = 0.0
	_jump_cut_done = false
	_enter(State.AIR)
	play_anim(&"jump_start", 0.05, 1.0, true)
	anim.queue(_anim_name(&"jump_rise"))


func _air_jump() -> void:
	air_jumps_left -= 1
	velocity.y = air_jump_velocity
	_jump_cut_done = true
	_enter(State.AIR)
	play_anim(&"double_jump", 0.05, 1.0, true)


func _enter_air() -> void:
	_glide_hold = 0.0
	_enter(State.AIR)


func _land() -> void:
	_reset_air()
	_enter(State.IDLE)
	play_anim(&"land", 0.05, 1.0, true)


func _air_control(delta: float, max_speed: float) -> void:
	var dir := input_direction()
	var hv := _horizontal()
	if dir.length() > 0.1:
		hv = hv.move_toward(dir.normalized() * max_speed * _speed_mult(), air_accel * delta)
		_face(dir.normalized(), delta * 0.6)
	else:
		hv = hv.move_toward(Vector3.ZERO, 2.0 * delta)
	_set_horizontal(hv)


func _st_air(delta: float) -> void:
	if is_on_floor() and velocity.y <= 0.0:
		_land()
		return
	_coyote -= delta
	var held := Input.is_action_pressed(&"jump")
	if velocity.y > 0.0 and not held and not _jump_cut_done:
		velocity.y *= jump_cut
		_jump_cut_done = true
	velocity.y = maxf(velocity.y - gravity * delta, -max_fall_speed)
	_air_control(delta, run_speed)
	if _consume(&"burst") and can_burst():
		_start_burst()
		return
	if _consume(&"jump"):
		if _coyote > 0.0:
			_jump()
		elif air_jumps_left > 0:
			_air_jump()
		else:
			_enter(State.GLIDE)
		return
	# Holding jump after the last air jump turns the fall into a glide.
	if held and velocity.y < -0.5 and air_jumps_left == 0:
		_glide_hold += delta
		if _glide_hold > 0.15:
			_enter(State.GLIDE)
			return
	else:
		_glide_hold = 0.0
	if (_consume(&"dash") or _consume(&"dodge")) and _dash_ready():
		_start_dash()
		return
	if _consume(&"attack_light"):
		_start_attack("air1")
		return
	if _consume(&"attack_heavy"):
		_start_attack("air_slam")
		return
	if not is_anim(&"double_jump") and not is_anim(&"jump_start"):
		play_anim(&"jump_rise" if velocity.y > 0.5 else &"fall", 0.2)


func _st_glide(delta: float) -> void:
	if is_on_floor():
		_land()
		return
	if state_time > 0.1 and not Input.is_action_pressed(&"jump"):
		_enter_air()
		return
	velocity.y = move_toward(velocity.y, -glide_fall_speed, gravity * 1.5 * delta)
	var dir := input_direction()
	var target := (dir.normalized() if dir.length() > 0.1 else facing() * 0.5) * glide_speed * _speed_mult()
	_set_horizontal(_horizontal().move_toward(target, air_accel * delta))
	if dir.length() > 0.1:
		_face(dir.normalized(), delta * 0.5)
	play_anim(&"glide", 0.25)
	if _consume(&"attack_light"):
		_start_attack("air1")
	elif _consume(&"attack_heavy"):
		_start_attack("air_slam")
	elif _consume(&"dash") and _dash_ready():
		_start_dash()


# =================================================================== attacks
func _start_attack(id: String) -> void:
	_atk = ATTACKS[id]
	attack_id = id
	_atk_time = 0.0
	_hit_targets.clear()
	_queued_attack = ""
	_slam_landed = false
	if id != "charged":
		_charge_level = 0.0
	var dir := input_direction()
	if dir.length() > 0.2:
		_face(dir.normalized(), 0.0, true)
	else:
		_aim_at_nearest_enemy(4.0)
	_enter(State.ATTACK)
	play_anim(_atk.anim, 0.06, _atk.get("speed", 1.0), true)
	if _atk.get("air", false) and id != "air_slam":
		velocity.y = maxf(velocity.y, 1.5)


func _aim_at_nearest_enemy(max_dist: float) -> void:
	var best: Node3D = null
	var best_d := max_dist
	for e in get_tree().get_nodes_in_group(&"enemy"):
		var d := global_position.distance_to(e.global_position)
		if d < best_d:
			best = e
			best_d = d
	if best:
		face_towards(best.global_position)


func _st_attack(delta: float) -> void:
	_atk_time += delta * anim.speed_scale
	var t := _atk_time
	var a := _atk
	var active: Array = a.active
	var lunge: float = a.get("lunge", 0.0)
	if lunge > 0.0 and t < active[1]:
		_set_horizontal(facing() * lunge * _speed_mult() * (1.0 - 0.5 * t / active[1]))
	else:
		_brake(delta)

	if attack_id == "air_slam":
		if _st_slam(t):
			return
	elif a.get("air", false) and not is_on_floor():
		velocity.y = maxf(velocity.y - gravity * 0.35 * delta, -4.0)  # hang in the air while swinging
	else:
		_apply_gravity(delta)

	if t >= active[0] and t <= active[1]:
		_do_hits()

	var chain: Array = a.get("chain", [])
	if _queued_attack == "" and not chain.is_empty() and t >= chain[0] and t <= chain[1]:
		if a.has("next_light") and _consume(&"attack_light", 0.5):
			_queued_attack = a.next_light
		elif a.has("next_heavy") and _consume(&"attack_heavy", 0.5):
			_queued_attack = a.next_heavy

	if t >= a.cancel:
		if _queued_attack != "":
			_start_attack(_queued_attack)
			return
		if _try_recovery_cancel():
			return
	if t >= anim_length(a.anim):
		_finish_action()


## Recovery cancels: dodge, jump or dash interrupt the end of an attack.
## The 0.3 s buffer lets presses made during the swing fire on the cancel frame.
func _try_recovery_cancel() -> bool:
	if _consume(&"dodge", 0.3):
		if is_on_floor():
			_start_dodge()
		else:
			_start_dash()
		return true
	if _consume(&"jump", 0.3):
		if is_on_floor():
			_jump()
			return true
		if air_jumps_left > 0:
			_air_jump()
			return true
	if _consume(&"dash", 0.3) and _dash_ready():
		_start_dash()
		return true
	return false


## Plunging attack: hover, dive, then a shockwave on impact. Returns true if it
## already handled the rest of the frame.
func _st_slam(t: float) -> bool:
	if _slam_landed:
		_set_horizontal(Vector3.ZERO)
		velocity.y = -1.0
		return false
	if t < 0.12:
		velocity = Vector3(0.0, 1.0, 0.0)
		return true
	if is_on_floor():
		_slam_landed = true
		_atk_time = maxf(t, 0.38)
		anim.seek(_atk_time, true)
		_do_hits(true)
		start_hitstop(0.08)
		return true
	_set_horizontal(facing() * 2.0)
	velocity.y = -24.0
	if t > 0.3:
		# Hold the plunge pose until impact.
		_atk_time = 0.3
		anim.seek(0.3, true)
	return true


func _do_hits(force := false) -> void:
	var a := _atk
	var radius: float = a.radius * (1.0 + 0.8 * _charge_level)
	var center := global_position + facing() * float(a.reach) + Vector3.UP * 0.9
	for e in get_tree().get_nodes_in_group(&"enemy"):
		if e in _hit_targets or not e.has_method("receive_hit"):
			continue
		var to: Vector3 = e.global_position + Vector3.UP * 0.9 - center
		if Vector2(to.x, to.z).length() > radius + 0.4 or absf(to.y) > 1.6:
			continue
		_hit_targets.append(e)
		var mult := (burst_damage_mult if burst_active else 1.0) * (1.0 + 1.5 * _charge_level)
		var info := HitInfo.new(self, a.damage * mult, a.knockback)
		info.poise_damage = a.poise * mult
		info.heavy = a.get("heavy", false)
		if e.receive_hit(info) == HitInfo.Result.HIT:
			add_burst(3.0 + info.damage * 0.25)
			start_hitstop(0.1 if info.heavy or force else 0.05)


func _st_charge(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	var held := Input.is_action_pressed(&"attack_heavy")
	if state_time < charge_threshold:
		if not held:
			_start_attack("heavy")
			return
	else:
		play_anim(&"charge", 0.15)
		_charge_level = clampf((state_time - charge_threshold) / (charge_max - charge_threshold), 0.0, 1.0)
		aura.light_energy = maxf(aura.light_energy, 2.0 * _charge_level)
		if not held:
			_start_attack("charged")
			return
	if _consume(&"dodge"):
		_charge_level = 0.0
		_start_dodge()


func _finish_action() -> void:
	attack_id = ""
	if is_on_floor():
		_enter(State.IDLE)
	else:
		_enter_air()


# =================================================================== defense
func _enter_guard() -> void:
	# The parry window opens when the button went down, not when the state began.
	_guard_started = _pressed.get(&"guard", _clock)
	_enter(State.GUARD)
	play_anim(&"guard", 0.08)


func is_parry_window() -> bool:
	return state == State.GUARD and _clock - _guard_started <= parry_window


func _st_guard(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	if not is_on_floor():
		_enter_air()
		return
	if not Input.is_action_pressed(&"guard") or _guard_broken:
		_enter(State.IDLE)
		return
	if _consume(&"dodge"):
		_start_dodge()
		return
	if _consume(&"jump"):
		_jump()
		return
	var dir := input_direction()
	if dir.length() > 0.2:
		_face(dir.normalized(), delta * 0.5)
	if not is_anim(&"guard_hit"):
		play_anim(&"guard", 0.1)


func _start_parry(info: HitInfo) -> void:
	_enter(State.PARRY)
	play_anim(&"parry", 0.04, 1.0, true)
	_iframes = 0.3
	add_burst(20.0)
	start_hitstop(0.1)
	if info.source and info.source.has_method("on_parried"):
		info.source.on_parried(self)


func _st_parry(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	if state_time > 0.12 and _consume(&"attack_light", 0.3):
		_start_attack("light3")  # riposte
		return
	if state_time >= anim_length(&"parry"):
		if Input.is_action_pressed(&"guard"):
			_guard_started = -10.0
			_enter(State.GUARD)
		else:
			_enter(State.IDLE)


## Entry point for every attack aimed at Reimu.
func receive_hit(info: HitInfo) -> HitInfo.Result:
	if state == State.DEAD:
		return HitInfo.Result.IGNORED
	if is_invulnerable():
		if state == State.DODGE:
			add_burst(12.0)
			perfect_evade.emit()
		return HitInfo.Result.EVADED
	var to_src := (info.source.global_position - global_position) if info.source else facing()
	to_src.y = 0.0
	var in_front := to_src.length() < 0.01 or facing().dot(to_src.normalized()) > 0.1
	if state in [State.GUARD, State.PARRY] and in_front and not info.unblockable:
		if info.parryable and (state == State.PARRY or is_parry_window()):
			_start_parry(info)
			return HitInfo.Result.PARRIED
		guard_points = maxf(0.0, guard_points - info.guard_damage * (0.5 if burst_active else 1.0))
		_last_block = _clock
		guard_changed.emit(guard_points, max_guard)
		velocity += info.push_direction(self) * info.knockback * 0.5
		if guard_points <= 0.0:
			_guard_broken = true
			_enter_stun(true, Vector3.ZERO)
		else:
			play_anim(&"guard_hit", 0.03, 1.0, true)
		return HitInfo.Result.BLOCKED
	hp = maxf(0.0, hp - info.damage)
	health_changed.emit(hp, max_hp)
	if hp <= 0.0:
		_die()
		return HitInfo.Result.HIT
	add_burst(info.damage * 0.3)
	if burst_active and not info.heavy:
		return HitInfo.Result.HIT  # super armor: light hits do not interrupt
	_enter_stun(info.heavy, info.push_direction(self) * info.knockback)
	return HitInfo.Result.HIT


func _enter_stun(heavy: bool, push: Vector3) -> void:
	if state == State.QTE and QTE.active:
		QTE.cancel()
	_charge_level = 0.0
	velocity = push + Vector3.UP * (2.5 if heavy else 0.0)
	_stun_length = 1.1 if heavy else 0.38
	_enter(State.STAGGER if heavy else State.HURT)
	play_anim(&"hurt", 0.03, 1.0, true)
	if heavy:
		anim.queue(_anim_name(&"stagger"))


func _st_stun(delta: float) -> void:
	_set_horizontal(_horizontal().move_toward(Vector3.ZERO, 8.0 * delta))
	_apply_gravity(delta)
	var window_end := tech_window.y + (0.4 if state == State.STAGGER else 0.0)
	if state_time >= tech_window.x and state_time <= window_end \
			and (_consume(&"dodge", 0.1) or _consume(&"jump", 0.1)):
		_enter(State.RECOVER)
		play_anim(&"tech_recover", 0.05, 1.0, true)
		velocity = -facing() * 3.0
		return
	if _consume(&"burst") and can_burst():
		_start_burst()  # bursting breaks out of stun
		return
	if state_time >= _stun_length:
		_finish_action()


func _st_recover(delta: float) -> void:
	_brake(delta, 10.0)
	_apply_gravity(delta)
	if state_time >= anim_length(&"tech_recover"):
		_finish_action()


func _die() -> void:
	_end_burst()
	_enter(State.DEAD)
	velocity = Vector3.ZERO
	play_anim(&"death", 0.1, 1.0, true)
	died.emit()


func _st_dead(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	if auto_respawn and state_time > 3.0:
		respawn()


func respawn() -> void:
	global_position = spawn_point
	velocity = Vector3.ZERO
	hp = max_hp
	guard_points = max_guard
	_guard_broken = false
	burst_meter = 0.0
	_end_burst()
	clear_input_buffer()
	_enter(State.IDLE)
	play_anim(&"idle", 0.0)
	health_changed.emit(hp, max_hp)
	guard_changed.emit(guard_points, max_guard)
	burst_changed.emit(burst_meter, burst_active)


# =================================================================== burst
func can_burst() -> bool:
	return burst_meter >= 100.0 and not burst_active


func add_burst(amount: float) -> void:
	if burst_active:
		return
	burst_meter = minf(100.0, burst_meter + amount)
	burst_changed.emit(burst_meter, burst_active)


func _start_burst() -> void:
	_burst_fired = false
	velocity = Vector3.ZERO
	_enter(State.BURST)
	play_anim(&"burst", 0.05, 1.0, true)


func _st_burst(delta: float) -> void:
	_brake(delta)
	if is_on_floor():
		velocity.y = -1.0
	else:
		velocity.y = 0.0
	if not _burst_fired and state_time >= 0.6:
		_activate_burst()
	if state_time >= 1.25:
		_finish_action()


func _activate_burst() -> void:
	_burst_fired = true
	burst_active = true
	burst_time_left = burst_duration
	_reset_air()
	sparks.emitting = true
	# The release shockwave knocks nearby enemies back.
	for e in get_tree().get_nodes_in_group(&"enemy"):
		if e.global_position.distance_to(global_position) < 3.5 and e.has_method("receive_hit"):
			var info := HitInfo.new(self, 10.0, 8.0)
			info.poise_damage = 30.0
			info.heavy = true
			e.receive_hit(info)
	burst_changed.emit(burst_meter, true)


func _end_burst() -> void:
	if not burst_active:
		return
	burst_active = false
	burst_time_left = 0.0
	burst_meter = 0.0
	sparks.emitting = false
	burst_changed.emit(burst_meter, false)


func _tick_resources(delta: float) -> void:
	if burst_active:
		burst_time_left -= delta
		burst_meter = 100.0 * maxf(burst_time_left, 0.0) / burst_duration
		burst_changed.emit(burst_meter, true)
		if burst_time_left <= 0.0:
			_end_burst()
	var target_glow := 3.0 if burst_active else 0.0
	aura.light_energy = move_toward(aura.light_energy, target_glow, 4.0 * delta)
	if state not in [State.GUARD, State.PARRY] and _clock - _last_block > 1.0 and guard_points < max_guard:
		guard_points = minf(max_guard, guard_points + guard_regen * delta)
		if _guard_broken and guard_points >= max_guard * 0.5:
			_guard_broken = false
		guard_changed.emit(guard_points, max_guard)


# ===================================================================== QTE
## Finisher on a staggered enemy: a 3-button QTE in slow motion.
func start_finisher(target: Node3D) -> void:
	_qte_target = target
	_qte_hits = []
	_qte_story_cb = Callable()
	face_towards(target.global_position)
	velocity = Vector3.ZERO
	_enter(State.QTE)
	play_anim(&"charge", 0.1)
	target.begin_finisher(self)
	clear_input_buffer()
	QTE.begin(QTE.random_sequence(3), 1.1, _on_finisher_qte, 0.35)


func _on_finisher_qte(success: bool) -> void:
	clear_input_buffer()
	if state != State.QTE:
		return
	if success:
		_qte_hits = [0.5, 1.05, 1.8]
		state_time = 0.0
		play_anim(&"qte_finisher", 0.05, 1.0, true)
	else:
		if is_instance_valid(_qte_target):
			_qte_target.end_finisher(false)
		_qte_target = null
		_enter_stun(false, -facing() * 4.0)


## Story-driven QTE (e.g. a collapsing barrier). `on_done(success)` is called after.
func begin_story_qte(sequence: Array, window: float, on_done: Callable) -> bool:
	if state in [State.DEAD, State.QTE] or QTE.active:
		return false
	_qte_target = null
	_qte_hits = []
	_qte_story_cb = on_done
	velocity = Vector3.ZERO
	clear_input_buffer()
	_enter(State.QTE)
	play_anim(&"guard", 0.1)
	return QTE.begin(sequence, window, _on_story_qte, 0.5)


func _on_story_qte(success: bool) -> void:
	var cb := _qte_story_cb
	_qte_story_cb = Callable()
	clear_input_buffer()
	if state == State.QTE:
		if success:
			_enter(State.PARRY)
			play_anim(&"parry", 0.05, 1.0, true)
		else:
			_enter(State.IDLE)
	if cb.is_valid():
		cb.call(success)


func _st_qte(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	if _qte_hits.is_empty():
		if not QTE.active and state_time > 0.2:
			_finish_action()  # safety net if the QTE ended without a callback
		return
	while not _qte_hits.is_empty() and state_time >= _qte_hits[0]:
		_qte_hits.pop_front()
		if is_instance_valid(_qte_target):
			_qte_target.receive_finisher(40.0 * (burst_damage_mult if burst_active else 1.0))
			start_hitstop(0.09)
			add_burst(8.0)
	if _qte_hits.is_empty():
		_qte_hits = [INF]  # wait for the animation to finish
	if state_time >= anim_length(&"qte_finisher"):
		_qte_hits = []
		if is_instance_valid(_qte_target):
			_qte_target.end_finisher(true)
		_qte_target = null
		_finish_action()


# ========================================================= items & interaction
func add_item(kind: String, amount := 1) -> void:
	items[kind] = items.get(kind, 0) + amount
	items_changed.emit(items)


func can_use_item() -> bool:
	return items.get("healing_charm", 0) > 0 and hp < max_hp


func _st_item(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	if not _item_applied and state_time >= 0.6:
		_item_applied = true
		items["healing_charm"] -= 1
		hp = minf(max_hp, hp + heal_amount)
		items_changed.emit(items)
		health_changed.emit(hp, max_hp)
	if state_time >= anim_length(&"heal"):
		_finish_action()


func _start_interact() -> void:
	var t := _interact_target
	if t.has_method("begin_finisher"):
		start_finisher(t)
		return
	face_towards(t.global_position)
	_interact_done = false
	_interact_len = anim_length(t.interact_anim)
	_enter(State.INTERACT)
	play_anim(t.interact_anim, 0.1, 1.0, true)


func _st_interact(delta: float) -> void:
	_brake(delta)
	_apply_gravity(delta)
	var t := _interact_target
	if not _interact_done and is_instance_valid(t) and state_time >= t.effect_time:
		_interact_done = true
		t.interact(self)
	if state_time >= _interact_len:
		_finish_action()


func _update_prompt() -> void:
	var best: Node3D = null
	if state in [State.IDLE, State.MOVE] and is_on_floor():
		var best_d := INF
		for n in get_tree().get_nodes_in_group(&"interactable"):
			if not n.can_interact(self):
				continue
			var d := Vector2(n.global_position.x - global_position.x, n.global_position.z - global_position.z).length()
			if d <= n.radius and d < best_d:
				best = n
				best_d = d
	if state == State.INTERACT:
		return
	_interact_target = best
	var text := "" if best == null else "[%s] %s" % [GameInput.describe(&"interact"), best.prompt]
	if text != _prompt:
		_prompt = text
		prompt_changed.emit(text)
