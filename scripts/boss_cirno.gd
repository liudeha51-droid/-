class_name BossCirno
extends CharacterBody3D
## Cirno, the Ice Fairy: tutorial boss of the Misty Lake vertical slice.
##
## Phase 1 teaches the two languages of the game: Souls melee (telegraphed
## ice-sword swings, a charging dash) and danmaku (rings, spirals, aimed
## icicles). Phase 2 at 50% HP adds spell cards: Icicle Fall and Perfect Freeze.

signal defeated
signal phase_changed(phase: int)

const MAX_HP := 700.0
const MOVE_SPEED := 3.6
const POISE := 70.0

enum S { DORMANT, CHASE, WINDUP, SWING, DASH_WINDUP, DASH, CAST, RECOVER, STAGGER, TRANSITION, DEAD }

var hp := MAX_HP
var phase := 1
var state := S.DORMANT
var t := 0.0
var player: Player
var bullets: BulletManager
var hud: Node
var home := Vector3.ZERO
var rng := RandomNumberGenerator.new()

var _facing := Vector3.BACK
var _action_count := 0
var _swing_hit := false
var _double_swing := false
var _dash_dir := Vector3.ZERO
var _dash_hit := false
var _pattern := ""
var _pattern_t := 0.0
var _pattern_step := 0
var _poise_dmg := 0.0
var _poise_timer := 0.0
var _chase_time := 0.0
var _forced_action := ""

var model: Node3D
var body: Node3D
var sword_pivot: Node3D
var _sword_mat: StandardMaterial3D
var _flash_mats: Array[StandardMaterial3D] = []
var _aura: OmniLight3D


func _ready() -> void:
	collision_layer = 4
	collision_mask = 1
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.5
	cap.height = 1.8
	shape.shape = cap
	shape.position.y = 0.9
	add_child(shape)
	rng.seed = 9  # ⑨
	_build_model()


func _build_model() -> void:
	model = Node3D.new()
	add_child(model)
	body = Node3D.new()
	body.position.y = 1.0
	model.add_child(body)
	var blue := MeshKit.mat(Color(0.2, 0.45, 0.95), 0.0, 0.5)
	var white := MeshKit.mat(Color(0.95, 0.97, 1.0), 0.0, 0.6)
	var skin := MeshKit.mat(Color(1.0, 0.88, 0.8), 0.0, 0.6)
	var hair := MeshKit.mat(Color(0.45, 0.72, 1.0), 0.0, 0.4)
	var ice := MeshKit.mat(Color(0.6, 0.95, 1.0), 1.6, 0.05, 0.2, 0.7)
	_flash_mats.append_array([blue, white, skin, hair])
	# Dress, blouse, head, hair, big blue bow.
	MeshKit.add(body, MeshKit.cylinder(0.2, 0.55, 0.75), blue, Vector3(0, -0.5, 0))
	MeshKit.add(body, MeshKit.capsule(0.22, 0.7), white, Vector3(0, 0.05, 0))
	MeshKit.add(body, MeshKit.box(Vector3(0.3, 0.12, 0.06)), MeshKit.mat(Color(0.9, 0.1, 0.15)), Vector3(0, 0.3, -0.21))
	MeshKit.add(body, MeshKit.sphere(0.24), skin, Vector3(0, 0.62, 0))
	MeshKit.add(body, MeshKit.sphere(0.27, 0.4), hair, Vector3(0, 0.68, 0.04))
	for side in [-1.0, 1.0]:
		MeshKit.add(body, MeshKit.sphere(0.07), MeshKit.mat(Color(0.2, 0.4, 0.9), 0.5), Vector3(0.08 * side, 0.64, -0.21))
		MeshKit.add(body, MeshKit.sphere(0.2, 0.24), MeshKit.mat(Color(0.15, 0.35, 0.95)), Vector3(0.2 * side, 0.95, 0.06), Vector3(0, 0, 35 * side))
		MeshKit.add(body, MeshKit.capsule(0.07, 0.5), white, Vector3(0.3 * side, 0.0, 0), Vector3(0, 0, 15 * side))
		MeshKit.add(body, MeshKit.capsule(0.07, 0.6), skin, Vector3(0.13 * side, -1.0, 0))
		# Three ice-crystal wings per side.
		for i in 3:
			var wing := MeshKit.add(body, MeshKit.prism(Vector3(0.18, 0.55, 0.06)), ice, Vector3(0.28 * side + 0.12 * side * i, 0.25 - i * 0.18, 0.3), Vector3(0, 0, -side * (40 + i * 25)))
			wing.name = "Wing%d_%d" % [i, int(side)]
	# Ice sword (Cirno's melee is our Souls liberty; she's usually unarmed).
	sword_pivot = Node3D.new()
	sword_pivot.position = Vector3(0.45, 0.05, -0.1)
	body.add_child(sword_pivot)
	_sword_mat = MeshKit.mat(Color(0.55, 0.9, 1.0), 1.0, 0.05, 0.3, 0.8)
	MeshKit.add(sword_pivot, MeshKit.prism(Vector3(0.22, 1.6, 0.06)), _sword_mat, Vector3(0, 0.9, 0))
	_set_sword(0.0)
	_aura = OmniLight3D.new()
	_aura.light_color = Color(0.5, 0.8, 1.0)
	_aura.light_energy = 1.2
	_aura.omni_range = 5.0
	_aura.position.y = 1.2
	add_child(_aura)


func activate() -> void:
	if state == S.DORMANT:
		_enter(S.CHASE)


func reset() -> void:
	hp = MAX_HP
	phase = 1
	global_position = home
	velocity = Vector3.ZERO
	_action_count = 0
	_poise_dmg = 0.0
	_facing = Vector3.BACK
	model.rotation = Vector3.ZERO
	model.visible = true
	body.rotation = Vector3.ZERO
	_aura.light_color = Color(0.5, 0.8, 1.0)
	_set_sword(0.0)
	_enter(S.DORMANT)


func is_active() -> bool:
	return state != S.DORMANT and state != S.DEAD


## Test/debug hook: the next decision picks this action.
func force_action(action: String) -> void:
	_forced_action = action


func _physics_process(delta: float) -> void:
	t += delta
	_poise_timer -= delta
	if _poise_timer <= 0.0:
		_poise_dmg = 0.0
	velocity.y = 0.0 if is_on_floor() else velocity.y - 20.0 * delta
	_animate(delta)
	if state == S.DORMANT or state == S.DEAD or player == null:
		velocity.x = 0
		velocity.z = 0
		move_and_slide()
		return
	var to_player := player.global_position - global_position
	to_player.y = 0.0
	var dist := to_player.length()
	var dir := to_player.normalized() if dist > 0.01 else _facing

	match state:
		S.CHASE:
			_chase_time += delta
			_turn_to(dir, 6.0, delta)
			if player.is_dead():
				_hvel(Vector3.ZERO)
			elif dist > 3.0:
				_hvel(_facing * MOVE_SPEED * (1.3 if phase == 2 else 1.0))
			else:
				_hvel(Vector3.ZERO)
			if not player.is_dead() and (t > (0.5 if phase == 2 else 0.8)) and (dist < 3.4 or _chase_time > 1.6):
				_choose_action(dist)
		S.WINDUP:
			_hvel(Vector3.ZERO)
			_turn_to(dir, 3.0, delta)
			var wind := 0.75 if phase == 1 else 0.55
			_set_sword(-clampf(t / wind, 0.0, 1.0))
			_sword_mat.emission_energy_multiplier = 1.0 + 5.0 * clampf(t / wind, 0.0, 1.0)
			if t >= wind:
				_swing_hit = false
				Sfx.play("boss_swing")
				_enter(S.SWING)
		S.SWING:
			var k := clampf(t / 0.3, 0.0, 1.0)
			_set_sword(k)
			_hvel(_facing * (6.0 if t < 0.15 else 0.0))
			if not _swing_hit and t >= 0.08:
				_swing_hit = true
				_melee_check(3.6, 0.1, 24.0)
			if t >= 0.3:
				_sword_mat.emission_energy_multiplier = 1.0
				if _double_swing:
					_double_swing = false
					_enter(S.WINDUP)
					t = 0.3  # shorter wind-up for the follow-up
				else:
					_recover(0.9)
		S.DASH_WINDUP:
			_hvel(-_facing * 1.0)
			_turn_to(dir, 5.0, delta)
			body.rotation.x = lerpf(body.rotation.x, -0.5, 6.0 * delta)
			if t >= 0.65:
				_dash_dir = _facing
				_dash_hit = false
				body.rotation.x = 0.35
				Sfx.play("boss_swing", 0.0)
				_enter(S.DASH)
		S.DASH:
			_hvel(_dash_dir * 17.0)
			if not _dash_hit and dist < 1.5:
				_dash_hit = true
				player.take_damage(26.0, _dash_dir)
			if phase == 2 and int(t * 20.0) != int((t - delta) * 20.0):
				# Frost trail: short-lived icicles left behind the dash.
				var side := _dash_dir.cross(Vector3.UP)
				for s in [-1.0, 1.0]:
					bullets.spawn_orb(global_position + Vector3(0, 1.0, 0), side * s * 3.5, Color(0.7, 0.9, 1.0), 0.18, 10.0).life = 1.6
			if t >= 0.55:
				body.rotation.x = 0.0
				_recover(1.1)
		S.CAST:
			_hvel(Vector3.ZERO)
			_turn_to(dir, 4.0, delta)
			_run_pattern(delta)
		S.RECOVER:
			_hvel(velocity.move_toward(Vector3.ZERO, 30.0 * delta))
			if t >= _pattern_t:
				_enter(S.CHASE)
		S.STAGGER:
			_hvel(Vector3.ZERO)
			body.rotation.x = lerpf(body.rotation.x, 0.4, 8.0 * delta)
			if t >= 1.3:
				body.rotation.x = 0.0
				_enter(S.CHASE)
		S.TRANSITION:
			_hvel(Vector3.ZERO)
			body.position.y = 1.0 + minf(t, 1.0) * 1.2
			if t >= 0.6 and _pattern_step == 0:
				_pattern_step = 1
				bullets.clear_hostile(true)
				if dist < 6.0:
					player.take_damage(12.0, dir)
				Fx.burst(get_parent(), global_position + Vector3(0, 1.5, 0), Color(0.7, 0.95, 1.0), 80, 12.0, 0.9, 0.12)
				Sfx.play("shatter", 0.0, -2.0)
			if t >= 2.2:
				body.position.y = 1.0
				_enter(S.CHASE)
	move_and_slide()


func _choose_action(dist: float) -> void:
	_action_count += 1
	_chase_time = 0.0
	var action := _forced_action
	_forced_action = ""
	if action == "":
		if phase == 2 and _action_count % 3 == 0:
			action = "icicle_fall" if (_action_count / 3) % 2 == 1 else "perfect_freeze"
		elif dist < 3.6:
			action = ["swing", "swing", "ring"][rng.randi() % 3]
		else:
			action = ["dash", "aimed", "ring", "spiral"][rng.randi() % 4]
	match action:
		"swing":
			_double_swing = phase == 2 and rng.randf() < 0.6
			_enter(S.WINDUP)
		"dash":
			_enter(S.DASH_WINDUP)
		_:
			_start_pattern(action)


func _start_pattern(p: String) -> void:
	_pattern = p
	_pattern_step = 0
	_enter(S.CAST)
	match p:
		"icicle_fall":
			_declare("氷符「アイシクルフォール」", "Ice Sign \"Icicle Fall\"")
		"perfect_freeze":
			_declare("凍符「パーフェクトフリーズ」", "Freeze Sign \"Perfect Freeze\"")


func _run_pattern(_delta: float) -> void:
	var origin := global_position + Vector3(0, 1.1, 0)
	match _pattern:
		"ring":
			# Three rings, each offset half a gap so standing still gets you hit.
			var waves := 3 if phase == 1 else 4
			if _pattern_step < waves and t >= 0.45 + _pattern_step * 0.45:
				var n := 22 if phase == 1 else 28
				for i in n:
					var a := TAU * (i + 0.5 * (_pattern_step % 2)) / n
					bullets.spawn_orb(origin, Vector3(cos(a), 0, sin(a)) * 6.5, Color(0.35, 0.6, 1.0))
				Sfx.play("enemy_shot")
				_pattern_step += 1
			if _pattern_step >= waves:
				_recover(0.8)
		"spiral":
			var dur := 2.0
			var every := 0.07
			if t >= 0.4 and t < 0.4 + dur and int((t - 0.4) / every) >= _pattern_step:
				_pattern_step += 1
				var arms := 3 if phase == 1 else 4
				for arm in arms:
					var a := _pattern_step * 0.33 + TAU * arm / arms
					bullets.spawn_orb(origin, Vector3(cos(a), 0, sin(a)) * 5.5, Color(0.55, 0.85, 1.0), 0.2)
				if _pattern_step % 3 == 0:
					Sfx.play("enemy_shot", 0.1, -14.0)
			if t >= 0.4 + dur:
				_recover(0.9)
		"aimed":
			var volleys := 4 if phase == 1 else 6
			if _pattern_step < volleys and t >= 0.5 + _pattern_step * 0.3:
				var aim := (player.global_position + Vector3(0, 0.9, 0) - origin)
				aim.y = 0.0
				aim = aim.normalized()
				for i in 5:
					var d := aim.rotated(Vector3.UP, deg_to_rad((i - 2) * 12.0))
					bullets.spawn_icicle(origin, d * 12.0)
				Sfx.play("enemy_shot")
				_pattern_step += 1
			if _pattern_step >= volleys:
				_recover(0.7)
		"icicle_fall":
			# Icicles drop from the mist around the player; watch their shadows.
			var dur := 5.0
			if t >= 0.8 and t < 0.8 + dur and int((t - 0.8) / 0.22) >= _pattern_step:
				_pattern_step += 1
				for i in 5:
					var off := Vector3(rng.randf_range(-7, 7), 0, rng.randf_range(-7, 7))
					if i == 0:
						off = player.velocity * Vector3(1, 0, 1) * 0.9  # one leads the player
					var ground := player.global_position + off
					ground.y = 0.0
					_spawn_shadow(ground, 0.9)
					var b := bullets.spawn_icicle(ground + Vector3(0, 14.0, 0), Vector3(0, -15.5, 0), Color(0.7, 0.95, 1.0), 18.0)
					b.shatter_on_ground = true
				# Sideways fans keep her flank dangerous.
				if _pattern_step % 4 == 0:
					for i in 12:
						var a := TAU * i / 12.0 + t
						bullets.spawn_orb(origin, Vector3(cos(a), 0, sin(a)) * 5.0, Color(0.3, 0.5, 1.0))
			if t >= 0.8 + dur + 0.8:
				_recover(1.2)
		"perfect_freeze":
			# Burst of colourful bullets, freeze them all, then release slowly.
			if _pattern_step < 3 and t >= 0.6 + _pattern_step * 0.35:
				var colors := [Color(1, 0.3, 0.3), Color(1, 0.9, 0.2), Color(0.3, 1, 0.4), Color(0.3, 0.6, 1), Color(0.9, 0.4, 1)]
				for i in 36:
					var a := rng.randf() * TAU
					var d := Vector3(cos(a), rng.randf_range(-0.05, 0.05), sin(a))
					bullets.spawn_orb(origin, d * rng.randf_range(3.5, 9.0), colors[i % colors.size()], 0.2, 12.0, "freeze")
				Sfx.play("enemy_shot")
				_pattern_step += 1
			elif _pattern_step == 3 and t >= 2.4:
				_pattern_step = 4
				bullets.freeze_tag("freeze")
				Sfx.play("shatter", 0.0, -4.0)
			elif _pattern_step == 4 and t >= 3.0:
				_pattern_step = 5
				# While the field is frozen, a direct volley forces movement.
				var aim := player.global_position - global_position
				aim.y = 0
				for i in 7:
					bullets.spawn_icicle(origin, aim.normalized().rotated(Vector3.UP, deg_to_rad((i - 3) * 8.0)) * 10.0)
				Sfx.play("enemy_shot")
			elif _pattern_step == 5 and t >= 3.8:
				_pattern_step = 6
				bullets.release_tag("freeze", rng, 1.5, 4.0)
			elif _pattern_step == 6 and t >= 4.6:
				_recover(1.3)


func _spawn_shadow(at: Vector3, life: float) -> void:
	var s := MeshKit.add(get_parent(), MeshKit.cylinder(0.45, 0.45, 0.02, 16), MeshKit.mat(Color(0.05, 0.1, 0.2), 0.0, 1.0, 0.0, 0.55), at + Vector3(0, 0.06, 0))
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	get_tree().create_timer(life).timeout.connect(s.queue_free)


func _declare(jp: String, en: String) -> void:
	Sfx.play("spell", 0.0, -6.0)
	if hud and hud.has_method("banner"):
		hud.banner(jp, en, Color(0.45, 0.75, 1.0))


func _melee_check(reach: float, min_dot: float, damage: float) -> void:
	var to := player.global_position - global_position
	to.y = 0.0
	if to.length() < reach and _facing.dot(to.normalized()) > min_dot:
		player.take_damage(damage, _facing)


func _recover(duration: float) -> void:
	_pattern_t = duration
	_enter(S.RECOVER)


## Returns true when the hit counted (used by the player for Spirit gain and effects).
func take_damage(amount: float, _source: Node = null) -> bool:
	if state == S.DORMANT or state == S.DEAD or state == S.TRANSITION:
		return false
	hp -= amount
	_flash()
	_poise_dmg += amount
	_poise_timer = 3.0
	if hp <= 0.0:
		hp = 0.0
		_die()
		return true
	if phase == 1 and hp <= MAX_HP * 0.5:
		phase = 2
		_pattern_step = 0
		_aura.light_color = Color(0.3, 0.55, 1.0)
		_aura.light_energy = 3.0
		_set_sword(0.0)
		_enter(S.TRANSITION)
		phase_changed.emit(2)
		_declare("「フェアリー・イズ・ストロンゲスト」", "Phase 2: the strongest fairy gets serious")
		return true
	if _poise_dmg >= POISE and (state == S.CHASE or state == S.RECOVER or state == S.CAST):
		_poise_dmg = 0.0
		bullets.clear_hostile(false)
		_set_sword(0.0)
		_enter(S.STAGGER)
	return true


func _die() -> void:
	_enter(S.DEAD)
	bullets.clear_hostile(true)
	Sfx.play("victory", 0.0, -4.0)
	Fx.burst(get_parent(), global_position + Vector3(0, 1.2, 0), Color(0.7, 0.95, 1.0), 120, 9.0, 1.4, 0.14)
	var tw := create_tween()
	tw.tween_property(body, "rotation:x", -PI * 0.5, 0.8)
	tw.parallel().tween_property(body, "position:y", 0.3, 0.8)
	defeated.emit()


func _enter(s: S) -> void:
	state = s
	t = 0.0


func _hvel(v: Vector3) -> void:
	velocity.x = v.x
	velocity.z = v.z


func _turn_to(dir: Vector3, rate: float, delta: float) -> void:
	if dir.length() < 0.01:
		return
	var cur := atan2(-_facing.x, -_facing.z)
	var want := atan2(-dir.x, -dir.z)
	var yaw := lerp_angle(cur, want, 1.0 - exp(-rate * delta))
	_facing = Vector3(-sin(yaw), 0, -cos(yaw))


func _animate(_delta: float) -> void:
	model.rotation.y = atan2(-_facing.x, -_facing.z)
	if state != S.TRANSITION and state != S.DEAD:
		body.position.y = 1.0 + sin(Time.get_ticks_msec() * 0.003) * 0.08
	var flap := sin(Time.get_ticks_msec() * 0.012) * 8.0
	for child in body.get_children():
		if child.name.begins_with("Wing"):
			child.rotation_degrees.y = flap * (1.0 if child.name.ends_with("_1") else -1.0)


## k in -1..0 = raising the sword, 0..1 = the swing arc.
func _set_sword(k: float) -> void:
	if k <= 0.0:
		sword_pivot.rotation = Vector3(deg_to_rad(-30.0 + 110.0 * k), deg_to_rad(-20.0 * k), deg_to_rad(-20))
	else:
		sword_pivot.rotation = Vector3(deg_to_rad(-80), deg_to_rad(lerpf(70.0, -110.0, sin(k * PI * 0.5))), 0)


func _flash() -> void:
	for m in _flash_mats:
		m.emission_enabled = true
		m.emission = Color(1, 1, 1)
		m.emission_energy_multiplier = 1.2
	get_tree().create_timer(0.08).timeout.connect(func():
		for m in _flash_mats:
			m.emission_enabled = false
	)
