class_name Player
extends CharacterBody3D
## Reimu Hakurei (placeholder model). Souls-style stamina combat plus the
## Touhou layer: graze bullets for Spirit, spend Spirit on ofuda and spell cards.

signal died

const WALK_SPEED := 4.4
const SPRINT_SPEED := 7.0
const GRAVITY := 24.0
const TURN_RATE := 14.0

const DODGE_TIME := 0.5
const DODGE_IFRAMES := Vector2(0.03, 0.36)
const DODGE_COST := 20.0
const ATTACK_COST := 16.0
const ATTACK_TIMES := [0.5, 0.5, 0.72]
const ATTACK_HIT_AT := [0.17, 0.17, 0.3]
const ATTACK_DAMAGE := [14.0, 14.0, 26.0]
const ATTACK_RANGE := 2.6
const OFUDA_COST := 10.0
const SPELL_COST := 100.0
const HEAL_TIME := 1.0
const HEAL_AMOUNT := 45.0

enum State { FREE, DODGE, ATTACK, SHOOT, HEAL, HURT, SPELL, DEAD }

var max_hp := 100.0
var hp := 100.0
var max_stamina := 100.0
var stamina := 100.0
var max_spirit := 100.0
var spirit := 30.0
var max_heals := 3
var heals := 3

var state := State.FREE
var state_time := 0.0
var combo := 0
var combo_queued := false
var did_hit := false
var did_heal := false
var dodge_dir := Vector3.FORWARD
var stamina_delay := 0.0
var invuln := 0.0
var facing := Vector3.FORWARD

var camera_rig: CameraRig
var bullets: BulletManager
var boss: Node3D
var lock_target: Node3D
var input_enabled := true

var model: Node3D
var body_pivot: Node3D
var gohei_pivot: Node3D
var _flash_mats: Array[StandardMaterial3D] = []


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1 | 4
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.6
	shape.shape = cap
	shape.position.y = 0.8
	add_child(shape)
	_build_model()


func _build_model() -> void:
	model = Node3D.new()
	add_child(model)
	body_pivot = Node3D.new()
	body_pivot.position.y = 0.8
	model.add_child(body_pivot)
	var red := MeshKit.mat(Color(0.78, 0.08, 0.12), 0.0, 0.6)
	var white := MeshKit.mat(Color(0.95, 0.94, 0.9), 0.0, 0.7)
	var skin := MeshKit.mat(Color(1.0, 0.86, 0.76), 0.0, 0.6)
	var hair := MeshKit.mat(Color(0.12, 0.07, 0.05), 0.0, 0.5)
	var gold := MeshKit.mat(Color(1.0, 0.8, 0.2), 0.6, 0.3, 0.6)
	for m in [red, white, skin, hair]:
		_flash_mats.append(m)
	var b := body_pivot
	# Skirt + torso (red), detached white sleeves, head, hair and the iconic bow.
	MeshKit.add(b, MeshKit.cylinder(0.18, 0.42, 0.6), red, Vector3(0, -0.45, 0))
	MeshKit.add(b, MeshKit.capsule(0.2, 0.7), red, Vector3(0, 0.05, 0))
	MeshKit.add(b, MeshKit.box(Vector3(0.22, 0.06, 0.08)), MeshKit.mat(Color(1.0, 0.85, 0.2)), Vector3(0, 0.28, -0.19))
	for side in [-1.0, 1.0]:
		MeshKit.add(b, MeshKit.cylinder(0.09, 0.17, 0.42), white, Vector3(0.3 * side, 0.05, 0), Vector3(0, 0, 18 * side))
		MeshKit.add(b, MeshKit.capsule(0.06, 0.55), MeshKit.mat(Color(0.12, 0.07, 0.05)), Vector3(0.14 * side, -0.9, 0))
	MeshKit.add(b, MeshKit.sphere(0.22), skin, Vector3(0, 0.62, 0))
	MeshKit.add(b, MeshKit.sphere(0.25, 0.42), hair, Vector3(0, 0.66, 0.04))
	MeshKit.add(b, MeshKit.capsule(0.15, 0.7), hair, Vector3(0, 0.35, 0.14))
	for side in [-1.0, 1.0]:
		MeshKit.add(b, MeshKit.sphere(0.07), MeshKit.mat(Color(0.35, 0.08, 0.08)), Vector3(0.08 * side, 0.64, -0.19))
		MeshKit.add(b, MeshKit.sphere(0.2, 0.26), red, Vector3(0.2 * side, 0.9, 0.08), Vector3(0, 0, 30 * side))
		MeshKit.add(b, MeshKit.box(Vector3(0.05, 0.3, 0.02)), white, Vector3(0.32 * side, 0.9, 0.06), Vector3(0, 0, 30 * side))
	MeshKit.add(b, MeshKit.sphere(0.07), red, Vector3(0, 0.88, 0.08))

	# Gohei (purification rod) held in the right hand.
	gohei_pivot = Node3D.new()
	gohei_pivot.position = Vector3(0.38, 0.0, -0.1)
	b.add_child(gohei_pivot)
	MeshKit.add(gohei_pivot, MeshKit.cylinder(0.025, 0.025, 1.1), MeshKit.mat(Color(0.55, 0.36, 0.18)), Vector3(0, 0.45, -0.05), Vector3(-10, 0, 0))
	for i in 3:
		var paper := MeshKit.add(gohei_pivot, MeshKit.box(Vector3(0.02, 0.2, 0.12)), MeshKit.mat(Color(1, 1, 1), 0.4), Vector3(0.03, 0.85 - i * 0.13, -0.15 - i * 0.04), Vector3(0, 0, 0))
		paper.rotation_degrees.z = 12.0 * (i % 2 * 2 - 1)
	# Yin-yang orb orbiting behind her, source of ofuda.
	var orb := MeshKit.add(b, MeshKit.sphere(0.12), gold, Vector3(-0.5, 0.6, 0.3))
	orb.name = "Orb"
	# The yin-yang orb is a small warm light: it keeps Reimu readable in the dark.
	var glow := OmniLight3D.new()
	glow.light_color = Color(1.0, 0.8, 0.55)
	glow.light_energy = 0.9
	glow.omni_range = 4.5
	orb.add_child(glow)
	_set_gohei_pose(0.0)


func _physics_process(delta: float) -> void:
	state_time += delta
	invuln = maxf(0.0, invuln - delta)
	_regen(delta)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = -0.5

	var move_input := Vector2.ZERO
	if input_enabled and state != State.DEAD:
		move_input = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var yaw := camera_rig.yaw if camera_rig else 0.0
	var wish := Vector3(move_input.x, 0, move_input.y).rotated(Vector3.UP, yaw)

	match state:
		State.FREE:
			_state_free(delta, wish)
		State.DODGE:
			var k := clampf(state_time / DODGE_TIME, 0.0, 1.0)
			_set_hvel(dodge_dir * lerpf(10.5, 2.0, k * k))
			body_pivot.rotation.x = -TAU * k
			if state_time >= DODGE_TIME:
				body_pivot.rotation.x = 0.0
				_enter(State.FREE)
		State.ATTACK:
			_state_attack(delta)
		State.SHOOT:
			_set_hvel(Vector3.ZERO)
			if state_time >= 0.3:
				_enter(State.FREE)
		State.HEAL:
			_set_hvel(wish * WALK_SPEED * 0.3)
			body_pivot.position.y = 0.8 - sin(clampf(state_time / HEAL_TIME, 0, 1) * PI) * 0.1
			if not did_heal and state_time >= HEAL_TIME * 0.6:
				did_heal = true
				hp = minf(max_hp, hp + HEAL_AMOUNT)
				Sfx.play("heal", 0.0)
				Fx.burst(get_parent(), global_position + Vector3(0, 1, 0), Color(0.5, 1.0, 0.6), 24, 2.0, 0.8)
			if state_time >= HEAL_TIME:
				body_pivot.position.y = 0.8
				_enter(State.FREE)
		State.HURT:
			_set_hvel(velocity.move_toward(Vector3.ZERO, 20.0 * delta) * Vector3(1, 0, 1))
			if state_time >= 0.35:
				_enter(State.FREE)
		State.SPELL:
			_set_hvel(Vector3.ZERO)
			if state_time >= 0.9:
				_enter(State.FREE)
		State.DEAD:
			_set_hvel(Vector3.ZERO)
			body_pivot.rotation.x = lerpf(body_pivot.rotation.x, PI * 0.5, 4.0 * delta)
			body_pivot.position.y = lerpf(body_pivot.position.y, 0.25, 4.0 * delta)

	_update_facing(delta)
	move_and_slide()
	_animate_idle(delta)


func _state_free(_delta: float, wish: Vector3) -> void:
	if not input_enabled:
		_set_hvel(Vector3.ZERO)
		return
	var sprinting := Input.is_action_pressed("sprint") and wish.length() > 0.1 and stamina > 0.0
	var speed := SPRINT_SPEED if sprinting else WALK_SPEED
	if lock_target and not sprinting:
		speed *= 0.85
	_set_hvel(wish * speed)
	if sprinting:
		stamina -= 14.0 * get_physics_process_delta_time()
		stamina_delay = 0.4
	if wish.length() > 0.1 and (lock_target == null or sprinting):
		facing = wish.normalized()
	elif lock_target:
		facing = _dir_to(lock_target)

	if Input.is_action_just_pressed("dodge") and stamina > 0.0:
		dodge_dir = wish.normalized() if wish.length() > 0.1 else -facing
		facing = dodge_dir if wish.length() > 0.1 else facing
		_spend(DODGE_COST)
		Sfx.play("dodge")
		_enter(State.DODGE)
	elif Input.is_action_just_pressed("attack") and stamina > 0.0:
		combo = 0
		_start_attack()
	elif Input.is_action_just_pressed("ofuda") and spirit >= OFUDA_COST:
		_shoot_ofuda()
	elif Input.is_action_just_pressed("spell_card") and spirit >= SPELL_COST:
		_cast_spell()
	elif Input.is_action_just_pressed("heal") and heals > 0 and hp < max_hp:
		heals -= 1
		did_heal = false
		_enter(State.HEAL)


func _start_attack() -> void:
	if lock_target:
		facing = _dir_to(lock_target)
	_spend(ATTACK_COST)
	did_hit = false
	combo_queued = false
	Sfx.play("swing")
	_enter(State.ATTACK)


func _state_attack(_delta: float) -> void:
	var dur: float = ATTACK_TIMES[combo]
	var k := clampf(state_time / dur, 0.0, 1.0)
	# Short lunge on the wind-up, then plant.
	_set_hvel(facing * (4.5 if state_time < 0.14 else 0.0))
	_set_gohei_pose(k)
	if not did_hit and state_time >= ATTACK_HIT_AT[combo]:
		did_hit = true
		_melee_hit(ATTACK_DAMAGE[combo])
	if input_enabled and state_time > 0.15 and Input.is_action_just_pressed("attack"):
		combo_queued = true
	if input_enabled and state_time > 0.25 and Input.is_action_just_pressed("dodge") and stamina > 0.0:
		# Dodge-cancel the recovery, the core Souls escape hatch.
		var wish := _wish()
		dodge_dir = wish.normalized() if wish.length() > 0.1 else -facing
		_set_gohei_pose(0.0)
		_spend(DODGE_COST)
		Sfx.play("dodge")
		_enter(State.DODGE)
		return
	if state_time >= dur:
		_set_gohei_pose(0.0)
		if combo_queued and stamina > 0.0 and combo < ATTACK_TIMES.size() - 1:
			combo += 1
			_start_attack()
		else:
			_enter(State.FREE)


func _melee_hit(damage: float) -> void:
	if boss == null or not boss.has_method("take_damage"):
		return
	var to := boss.global_position - global_position
	to.y = 0.0
	if to.length() < ATTACK_RANGE + 0.6 and facing.dot(to.normalized()) > 0.25:
		if boss.take_damage(damage, self):
			spirit = minf(max_spirit, spirit + 6.0)
			Sfx.play("hit")
			Fx.burst(get_parent(), boss.global_position + Vector3(0, 1.1, 0) - to.normalized() * 0.5, Color(1.0, 0.95, 0.7), 20, 5.0)
			if camera_rig:
				camera_rig.shake(0.25)


func _shoot_ofuda() -> void:
	spirit -= OFUDA_COST
	if lock_target:
		facing = _dir_to(lock_target)
	var origin := global_position + Vector3(0, 1.1, 0) + facing * 0.5
	for i in 3:
		var dir := facing.rotated(Vector3.UP, deg_to_rad((i - 1) * 9.0))
		bullets.spawn_player_shot(origin, dir * 18.0, 7.0, lock_target)
	Sfx.play("shoot")
	_enter(State.SHOOT)


func _cast_spell() -> void:
	spirit = 0.0
	invuln = 2.2
	bullets.clear_hostile(true)
	Sfx.play("spell", 0.0, -4.0)
	if camera_rig:
		camera_rig.shake(0.5)
	# Fantasy Seal: rainbow orbs that home in on the target.
	var colors := [Color(1, 0.2, 0.2), Color(1, 0.6, 0.1), Color(1, 1, 0.2), Color(0.2, 1, 0.4), Color(0.2, 0.6, 1), Color(0.7, 0.3, 1)]
	for i in colors.size():
		var dir := Vector3.FORWARD.rotated(Vector3.UP, TAU * i / colors.size())
		bullets.spawn_player_shot(global_position + Vector3(0, 1.2, 0) + dir, dir * 6.0 + Vector3.UP * 2.0, 18.0, boss, colors[i], 0.45)
	get_parent().get_node("Hud").banner("霊符「夢想封印」", "Spirit Sign \"Fantasy Seal\"", Color(1, 0.3, 0.35))
	_enter(State.SPELL)


## Called by the bullet manager. Returns true if the hit connected.
func take_damage(amount: float, from_dir: Vector3) -> bool:
	if state == State.DEAD or invuln > 0.0 or is_iframing():
		return false
	hp -= amount
	invuln = 0.6
	stamina_delay = 0.5
	Sfx.play("hurt")
	_flash(Color(1, 0.2, 0.2))
	if camera_rig:
		camera_rig.shake(0.4)
	if hp <= 0.0:
		hp = 0.0
		_die()
		return true
	var push := from_dir
	push.y = 0.0
	_set_hvel(push.normalized() * 5.0 if push.length() > 0.01 else Vector3.ZERO)
	_set_gohei_pose(0.0)
	body_pivot.rotation.x = 0.0
	body_pivot.position.y = 0.8
	_enter(State.HURT)
	return true


func is_iframing() -> bool:
	return state == State.DODGE and state_time >= DODGE_IFRAMES.x and state_time <= DODGE_IFRAMES.y


## Near-miss reward: the Touhou "graze" translated into stamina and Spirit.
func on_graze(at: Vector3) -> void:
	spirit = minf(max_spirit, spirit + 3.0)
	stamina = minf(max_stamina, stamina + 5.0)
	Sfx.play("graze", 0.15, -14.0)
	Fx.burst(get_parent(), at, Color(1, 1, 1), 6, 2.5, 0.25, 0.05)


func respawn(at: Vector3) -> void:
	global_position = at
	velocity = Vector3.ZERO
	hp = max_hp
	stamina = max_stamina
	heals = max_heals
	spirit = maxf(spirit, 30.0)
	body_pivot.rotation = Vector3.ZERO
	body_pivot.position.y = 0.8
	lock_target = null
	invuln = 1.0
	_enter(State.FREE)


func rest() -> void:
	hp = max_hp
	stamina = max_stamina
	heals = max_heals


func is_dead() -> bool:
	return state == State.DEAD


func _die() -> void:
	_enter(State.DEAD)
	lock_target = null
	Sfx.play("death", 0.0, -4.0)
	died.emit()


func _enter(s: State) -> void:
	state = s
	state_time = 0.0


func _spend(cost: float) -> void:
	stamina -= cost
	stamina_delay = 0.7


func _regen(delta: float) -> void:
	if stamina_delay > 0.0:
		stamina_delay -= delta
	elif state != State.ATTACK and state != State.DODGE:
		var rate := 20.0 if state == State.HEAL or (lock_target and velocity.length() > 0.1) else 42.0
		stamina = minf(max_stamina, stamina + rate * delta)
	stamina = maxf(stamina, -30.0)


func _wish() -> Vector3:
	var v := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	return Vector3(v.x, 0, v.y).rotated(Vector3.UP, camera_rig.yaw if camera_rig else 0.0)


func _dir_to(n: Node3D) -> Vector3:
	var d := n.global_position - global_position
	d.y = 0.0
	return d.normalized() if d.length() > 0.01 else facing


func _set_hvel(v: Vector3) -> void:
	velocity.x = v.x
	velocity.z = v.z


func _update_facing(delta: float) -> void:
	if state == State.DEAD:
		return
	var target_yaw := atan2(-facing.x, -facing.z)
	model.rotation.y = lerp_angle(model.rotation.y, target_yaw, 1.0 - exp(-TURN_RATE * delta))


func _animate_idle(_delta: float) -> void:
	var orb := body_pivot.get_node_or_null("Orb") as Node3D
	if orb:
		var t := Time.get_ticks_msec() / 1000.0
		orb.position = Vector3(cos(t * 2.0) * 0.55, 0.6 + sin(t * 3.0) * 0.08, sin(t * 2.0) * 0.55)


## 0 = rest pose, 0..1 = sweep of the swing arc.
func _set_gohei_pose(k: float) -> void:
	if gohei_pivot == null:
		return
	if k <= 0.0:
		gohei_pivot.rotation = Vector3(deg_to_rad(-20), 0, deg_to_rad(-15))
		return
	var swing := sin(clampf(k * 1.6, 0.0, 1.0) * PI * 0.5)
	var dir := -1.0 if combo % 2 == 1 else 1.0
	gohei_pivot.rotation = Vector3(deg_to_rad(-80), deg_to_rad(lerpf(80.0, -100.0, swing) * dir), 0)


func _flash(color: Color) -> void:
	for m in _flash_mats:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = 1.5
	get_tree().create_timer(0.12).timeout.connect(func():
		for m in _flash_mats:
			m.emission_enabled = false
	)
