extends Node
## End-to-end tests for every player action, driven by simulated input.
##
##   godot --headless --fixed-fps 60 --path . res://tests/test_actions.tscn
##
## Exits with code 0 when every check passes, 1 otherwise.

const ACTIONS: Array[StringName] = [&"move_forward", &"move_back", &"move_left", &"move_right", &"jump",
		&"dodge", &"dash", &"attack_light", &"attack_heavy", &"guard", &"interact", &"use_item", &"burst",
		&"walk_toggle", &"slow_walk"]

var arena: Node
var p: Player
var d: TrainingDummy
var current := ""
var passed := 0
var failures: Array[String] = []


func _ready() -> void:
	arena = load("res://demo/arena.tscn").instantiate()
	add_child(arena)
	await frames(3)
	p = arena.player
	d = arena.dummy
	p.auto_respawn = false
	d.auto_attack = false

	await run("animations exist", test_animations_exist)
	await run("idle", test_idle)
	await run("run", test_run)
	await run("walk toggle", test_walk)
	await run("slow walk (modifier + analog)", test_slow_walk)
	await run("sudden stop", test_sudden_stop)
	await run("skid turn", test_skid_turn)
	await run("dash", test_dash)
	await run("dodge i-frames", test_dodge)
	await run("jump + variable height", test_jump)
	await run("double jump", test_double_jump)
	await run("glide", test_glide)
	await run("light combo", test_light_combo)
	await run("heavy (tap)", test_heavy)
	await run("charged attack", test_charged)
	await run("dash attack", test_dash_attack)
	await run("aerial combo", test_air_combo)
	await run("plunge attack", test_air_slam)
	await run("guard block", test_guard_block)
	await run("parry", test_parry)
	await run("unblockable vs guard", test_unblockable)
	await run("dodge evades", test_dodge_evade)
	await run("recovery cancel", test_recovery_cancel)
	await run("buffered cancel waits for recovery", test_buffered_cancel)
	await run("hurt + tech recovery", test_tech_recovery)
	await run("QTE finisher success", test_qte_finisher)
	await run("QTE finisher failure", test_qte_fail)
	await run("story QTE", test_story_qte)
	await run("burst mode", test_burst)
	await run("pickup + healing item", test_items)
	await run("faith orb", test_faith_orb)
	await run("lever mechanism", test_lever)
	await run("death + respawn", test_death)

	print("\n%d checks passed, %d failed" % [passed, failures.size()])
	for f in failures:
		print("  FAIL ", f)
	get_tree().quit(1 if failures.size() > 0 else 0)


# ------------------------------------------------------------------ helpers
func run(name: String, test: Callable) -> void:
	current = name
	await reset()
	var before := failures.size()
	await test.call()
	print("%s %s" % ["ok  " if failures.size() == before else "FAIL", name])


func reset(pos := Vector3.ZERO) -> void:
	for a in ACTIONS:
		release(a)
	if QTE.active:
		QTE.cancel()
	Engine.time_scale = 1.0
	await frames(2)
	p.spawn_point = pos
	p.respawn()
	p.items = {"healing_charm": 0}
	p.walk_toggled = false
	p.visual.rotation.y = PI  # face -Z, toward the dummies
	d.reset(Vector3(0, 0, -6))
	arena.passive_dummy.reset(Vector3(5, 0, -6))
	await frames(6)


func check(cond: bool, msg: String) -> void:
	if cond:
		passed += 1
	else:
		failures.append("%s: %s" % [current, msg])


func press(a: StringName, strength := 1.0) -> void:
	var e := InputEventAction.new()
	e.action = a
	e.pressed = true
	e.strength = strength
	Input.parse_input_event(e)


func release(a: StringName) -> void:
	var e := InputEventAction.new()
	e.action = a
	e.pressed = false
	Input.parse_input_event(e)


func tap(a: StringName) -> void:
	press(a)
	await frames(2)
	release(a)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func secs(s: float) -> void:
	await frames(int(round(s * 60.0)))


func speed() -> float:
	return Vector2(p.velocity.x, p.velocity.z).length()


## Waits up to `timeout` seconds for `cond` to become true.
func until(cond: Callable, timeout := 2.0) -> bool:
	for i in int(timeout * 60.0):
		if cond.call():
			return true
		await frames(1)
	return cond.call()


## Records attack ids seen while waiting.
func watch_attacks(s: float, seen: Array) -> void:
	for i in int(s * 60.0):
		if p.attack_id != "" and (seen.is_empty() or seen[-1] != p.attack_id):
			seen.append(p.attack_id)
		await frames(1)


# -------------------------------------------------------------------- tests
func test_animations_exist() -> void:
	var clips := [&"idle", &"walk", &"slow_walk", &"run", &"sudden_stop", &"dash", &"roll", &"jump_start",
			&"jump_rise", &"fall", &"land", &"double_jump", &"glide", &"guard", &"guard_hit", &"parry",
			&"hurt", &"stagger", &"tech_recover", &"burst", &"charge", &"qte_finisher", &"heal", &"pickup",
			&"interact", &"death"]
	for k in Player.ATTACKS:
		clips.append(Player.ATTACKS[k].anim)
	for c in clips:
		check(p.anim.has_animation(p._anim_name(c)), "missing clip %s" % c)


func test_idle() -> void:
	await secs(0.3)
	check(p.state == Player.State.IDLE, "state %s" % p.state_name())
	check(p.current_anim() == &"idle", "anim %s" % p.current_anim())


func test_run() -> void:
	press(&"move_forward")
	await secs(1.0)
	check(p.state == Player.State.MOVE, "state %s" % p.state_name())
	check(p.current_anim() == &"run", "anim %s" % p.current_anim())
	check(absf(speed() - p.run_speed) < 0.3, "speed %.2f" % speed())
	check(p.velocity.z < -5.0, "should move toward -Z (camera forward), v=%s" % p.velocity)
	check(p.facing().z < -0.95, "should face movement, facing=%s" % p.facing())


func test_walk() -> void:
	await tap(&"walk_toggle")
	press(&"move_forward")
	await secs(1.0)
	check(p.walk_toggled, "walk toggle not set")
	check(p.current_anim() == &"walk", "anim %s" % p.current_anim())
	check(absf(speed() - p.walk_speed) < 0.2, "speed %.2f" % speed())
	release(&"move_forward")
	await secs(0.4)
	check(p.state == Player.State.IDLE, "walking stop should not skid, state %s" % p.state_name())


func test_slow_walk() -> void:
	press(&"slow_walk")
	press(&"move_forward")
	await secs(1.0)
	check(p.current_anim() == &"slow_walk", "anim %s" % p.current_anim())
	check(absf(speed() - p.slow_walk_speed) < 0.15, "speed %.2f" % speed())
	release(&"slow_walk")
	release(&"move_forward")
	await secs(0.3)
	press(&"move_forward", 0.45)  # light stick tilt
	await secs(1.0)
	check(p.current_anim() == &"slow_walk", "analog 0.45 anim %s" % p.current_anim())
	press(&"move_forward", 0.75)
	await secs(0.8)
	check(p.current_anim() == &"walk", "analog 0.75 anim %s" % p.current_anim())


func test_sudden_stop() -> void:
	press(&"move_right")  # open ground; running forward would hit the dummy
	await secs(1.0)
	release(&"move_right")
	var start := p.global_position
	await frames(3)
	check(p.state == Player.State.SKID, "state %s" % p.state_name())
	check(p.current_anim() == &"sudden_stop", "anim %s" % p.current_anim())
	await secs(0.6)
	var slide := start.distance_to(p.global_position)
	check(p.state == Player.State.IDLE, "after skid state %s" % p.state_name())
	check(speed() < 0.05, "still sliding %.2f" % speed())
	check(slide > 0.4 and slide < 1.6, "slide distance %.2f" % slide)


func test_skid_turn() -> void:
	press(&"move_forward")
	await secs(1.0)
	release(&"move_forward")
	press(&"move_back")
	await frames(3)
	check(p.state == Player.State.SKID, "reversal should skid, state %s" % p.state_name())
	await secs(0.6)
	check(p.facing().z > 0.9, "should have turned around, facing=%s" % p.facing())
	check(p.velocity.z > 1.0, "should run back, v=%s" % p.velocity)


func test_dash() -> void:
	press(&"move_right")
	await frames(4)
	await tap(&"dash")
	await frames(3)
	check(p.state == Player.State.DASH, "state %s" % p.state_name())
	check(p.current_anim() == &"dash", "anim %s" % p.current_anim())
	check(absf(speed() - p.dash_speed) < 0.5, "speed %.2f" % speed())
	check(p.velocity.x > 10.0, "dash direction %s" % p.velocity)
	await secs(0.3)
	check(p.state == Player.State.MOVE, "after dash state %s" % p.state_name())


func test_dodge() -> void:
	await tap(&"dodge")
	await secs(0.1)
	check(p.state == Player.State.DODGE, "state %s" % p.state_name())
	check(p.current_anim() == &"roll", "anim %s" % p.current_anim())
	check(p.is_invulnerable(), "should be invulnerable early in the roll")
	await secs(0.33)
	check(not p.is_invulnerable(), "i-frames should end, t=%.2f" % p.state_time)
	await secs(0.2)
	check(p.state == Player.State.IDLE, "after dodge state %s" % p.state_name())


func test_jump() -> void:
	press(&"jump")
	var top := 0.0
	for i in 70:
		await frames(1)
		top = maxf(top, p.global_position.y)
	release(&"jump")
	check(top > 1.3 and top < 1.75, "full jump apex %.2f" % top)
	await until(func() -> bool: return p.is_on_floor() and p.state == Player.State.IDLE)
	await secs(0.3)
	await tap(&"jump")  # released immediately: short hop
	var hop := 0.0
	for i in 50:
		await frames(1)
		hop = maxf(hop, p.global_position.y)
	check(hop < top * 0.7, "short hop %.2f should be lower than full jump %.2f" % [hop, top])
	await until(func() -> bool: return p.state == Player.State.IDLE)
	check(p.state == Player.State.IDLE, "landed state %s" % p.state_name())


func test_double_jump() -> void:
	press(&"jump")
	await secs(0.3)
	release(&"jump")
	await frames(2)
	press(&"jump")
	await frames(3)
	check(p.current_anim() == &"double_jump", "anim %s" % p.current_anim())
	check(p.air_jumps_left == 0, "air jumps left %d" % p.air_jumps_left)
	var top := 0.0
	for i in 60:
		await frames(1)
		top = maxf(top, p.global_position.y)
	check(top > 2.3, "double jump apex %.2f" % top)
	release(&"jump")
	await frames(2)
	await tap(&"jump")
	await frames(2)
	check(p.state == Player.State.GLIDE or p.velocity.y <= 0.0, "a third press must not jump again, vy=%.2f" % p.velocity.y)


func test_glide() -> void:
	press(&"jump")
	await secs(0.3)
	release(&"jump")
	await frames(2)
	press(&"jump")  # double jump, keep holding
	var reached := await until(func() -> bool: return p.state == Player.State.GLIDE, 2.0)
	check(reached, "never started gliding, state %s" % p.state_name())
	press(&"move_forward")
	await secs(0.4)
	check(p.current_anim() == &"glide", "anim %s" % p.current_anim())
	check(p.velocity.y >= -p.glide_fall_speed - 0.05, "falling too fast %.2f" % p.velocity.y)
	check(speed() > 3.0, "glide should carry forward, speed %.2f" % speed())
	release(&"jump")
	await frames(10)
	check(p.state == Player.State.AIR, "releasing jump should fall, state %s" % p.state_name())


func test_light_combo() -> void:
	await reset(Vector3(0, 0, -4.6))
	var hp0 := d.hp
	var seen: Array = []
	await tap(&"attack_light")
	await watch_attacks(0.2, seen)
	await tap(&"attack_light")
	await watch_attacks(0.3, seen)
	await tap(&"attack_light")
	await watch_attacks(1.2, seen)
	check(seen == ["light1", "light2", "light3"], "combo %s" % [seen])
	check(d.hp < hp0 - 25.0, "dummy hp %.0f -> %.0f" % [hp0, d.hp])
	check(p.burst_meter > 5.0, "hits should build burst, %.1f" % p.burst_meter)
	check(p.state == Player.State.IDLE, "after combo state %s" % p.state_name())


func test_heavy() -> void:
	var seen: Array = []
	await tap(&"attack_heavy")
	await watch_attacks(1.2, seen)
	check(seen == ["heavy"], "attacks %s" % [seen])


func test_charged() -> void:
	press(&"attack_heavy")
	await secs(1.3)
	check(p.state == Player.State.CHARGE, "state %s" % p.state_name())
	check(p.current_anim() == &"charge", "anim %s" % p.current_anim())
	release(&"attack_heavy")
	await frames(3)
	check(p.attack_id == "charged", "attack %s" % p.attack_id)
	check(p._charge_level > 0.95, "charge level %.2f" % p._charge_level)


func test_dash_attack() -> void:
	await tap(&"dash")
	await frames(4)
	await tap(&"attack_light")
	await frames(2)
	check(p.attack_id == "dash_attack", "attack %s" % p.attack_id)
	check(speed() > 5.0, "dash attack should lunge, speed %.2f" % speed())


func test_air_combo() -> void:
	press(&"jump")
	await secs(0.3)
	var seen: Array = []
	await tap(&"attack_light")
	await watch_attacks(0.2, seen)
	await tap(&"attack_light")
	await watch_attacks(0.4, seen)
	check(seen == ["air1", "air2"], "air combo %s" % [seen])
	check(not p.is_on_floor(), "should hang in the air while attacking")
	release(&"jump")
	await until(func() -> bool: return p.state == Player.State.IDLE, 3.0)


func test_air_slam() -> void:
	await reset(Vector3(0, 0, -4.8))
	var hp0 := d.hp
	press(&"jump")
	await secs(0.35)
	release(&"jump")
	await tap(&"attack_heavy")
	await frames(3)
	check(p.attack_id == "air_slam", "attack %s" % p.attack_id)
	await until(func() -> bool: return p._slam_landed, 2.0)
	check(p._slam_landed, "slam never landed")
	await frames(10)
	check(d.hp < hp0, "shockwave should hit the dummy")


func test_guard_block() -> void:
	await reset(Vector3(0, 0, -4.4))
	press(&"guard")
	await secs(0.4)
	check(p.state == Player.State.GUARD, "state %s" % p.state_name())
	check(p.current_anim() == &"guard", "anim %s" % p.current_anim())
	d.start_attack(false)
	await secs(d.windup_time + 0.1)
	check(d.last_result == HitInfo.Result.BLOCKED, "result %d" % d.last_result)
	check(p.hp == p.max_hp, "blocked hit should not hurt, hp %.0f" % p.hp)
	check(p.guard_points < p.max_guard, "guard should drain")


func test_parry() -> void:
	await reset(Vector3(0, 0, -4.4))
	var burst0 := p.burst_meter
	d.start_attack(false)
	await secs(d.windup_time - 0.1)
	press(&"guard")
	await secs(0.2)
	check(d.last_result == HitInfo.Result.PARRIED, "result %d" % d.last_result)
	check(p.state == Player.State.PARRY or p.current_anim() == &"parry", "state %s anim %s" % [p.state_name(), p.current_anim()])
	check(p.burst_meter >= burst0 + 19.0, "parry should build burst")
	check(d.mode in [TrainingDummy.Mode.FLINCH, TrainingDummy.Mode.STAGGERED], "dummy mode %d" % d.mode)


func test_unblockable() -> void:
	await reset(Vector3(0, 0, -4.4))
	press(&"guard")
	await secs(0.4)
	d.start_attack(true)
	await secs(d.windup_time + 0.1)
	check(d.last_result == HitInfo.Result.HIT, "result %d" % d.last_result)
	check(p.state == Player.State.STAGGER, "state %s" % p.state_name())
	check(p.hp < p.max_hp, "should take damage")


func test_dodge_evade() -> void:
	await reset(Vector3(0, 0, -4.4))
	var burst0 := p.burst_meter
	d.start_attack(false)
	await secs(d.windup_time - 0.08)
	press(&"move_right")
	await tap(&"dodge")
	await secs(0.2)
	check(d.last_result == HitInfo.Result.EVADED, "result %d" % d.last_result)
	check(p.hp == p.max_hp, "hp %.0f" % p.hp)
	check(p.burst_meter >= burst0 + 11.0, "perfect evade should build burst")


func test_recovery_cancel() -> void:
	await tap(&"attack_light")
	await until(func() -> bool: return p._atk_time >= 0.31, 1.0)
	await tap(&"dodge")
	await frames(1)
	check(p.state == Player.State.DODGE, "dodge should cancel recovery, state %s" % p.state_name())
	await reset()
	await tap(&"attack_light")
	await until(func() -> bool: return p._atk_time >= 0.31, 1.0)
	await tap(&"jump")
	await frames(1)
	check(p.state == Player.State.AIR, "jump should cancel recovery, state %s" % p.state_name())


func test_buffered_cancel() -> void:
	await tap(&"attack_light")
	await secs(0.08)
	await tap(&"dodge")
	await frames(2)
	check(p.state == Player.State.ATTACK, "must not cancel during startup, state %s" % p.state_name())
	await until(func() -> bool: return p.state != Player.State.ATTACK, 1.0)
	check(p.state == Player.State.DODGE, "buffered dodge should fire at the cancel point, state %s" % p.state_name())
	check(absf(p._atk_time - 0.3) < 0.05, "cancelled at %.2f" % p._atk_time)


func test_tech_recovery() -> void:
	await reset(Vector3(0, 0, -4.4))
	d.start_attack(false)
	await secs(d.windup_time + 0.05)
	check(p.state == Player.State.HURT, "state %s" % p.state_name())
	await secs(0.12)
	await tap(&"dodge")
	await frames(2)
	check(p.state == Player.State.RECOVER, "tech recovery, state %s" % p.state_name())
	check(p.is_invulnerable(), "tech recovery should be invulnerable")
	await secs(0.5)
	check(p.state == Player.State.IDLE, "after recovery state %s" % p.state_name())


func _stagger_dummy() -> void:
	d.poise = 1.0
	await tap(&"attack_light")
	await until(func() -> bool: return d.mode == TrainingDummy.Mode.STAGGERED, 1.0)
	await until(func() -> bool: return p.state == Player.State.IDLE, 1.0)
	await frames(3)


func test_qte_finisher() -> void:
	await reset(Vector3(0, 0, -4.6))
	await _stagger_dummy()
	check(d.mode == TrainingDummy.Mode.STAGGERED, "dummy should be staggered")
	check(p._interact_target == d, "finisher prompt should target the dummy")
	var hp0 := d.hp
	await tap(&"interact")
	await frames(2)
	check(p.state == Player.State.QTE and QTE.active, "QTE should start")
	check(is_equal_approx(Engine.time_scale, 0.35), "slow motion %.2f" % Engine.time_scale)
	for i in QTE.steps.size():
		await frames(4)
		await tap(QTE.current_action())
	await frames(2)
	check(not QTE.active, "QTE should finish")
	check(is_equal_approx(Engine.time_scale, 1.0), "time scale restored %.2f" % Engine.time_scale)
	check(p.current_anim() == &"qte_finisher", "anim %s" % p.current_anim())
	await until(func() -> bool: return p.state == Player.State.IDLE, 4.0)
	check(d.hp <= hp0 - 119.0, "finisher damage %.0f -> %.0f" % [hp0, d.hp])
	check(d.mode == TrainingDummy.Mode.IDLE, "dummy recovers, mode %d" % d.mode)


func test_qte_fail() -> void:
	await reset(Vector3(0, 0, -4.6))
	await _stagger_dummy()
	await tap(&"interact")
	await frames(6)
	var wrong: StringName = &"jump" if QTE.current_action() != &"jump" else &"dodge"
	await tap(wrong)
	await frames(3)
	check(not QTE.active, "wrong button should end the QTE")
	check(p.state == Player.State.HURT, "failed finisher knocks Reimu back, state %s" % p.state_name())


func test_story_qte() -> void:
	var rift: QteTrigger = arena.rift
	rift.armed = true
	rift.sealed = false
	await reset(rift.global_position + Vector3(0, 0, 0.5))
	await frames(3)
	check(QTE.active and p.state == Player.State.QTE, "entering the rift should start a QTE")
	await secs(rift.step_window + 0.2)  # let it time out
	check(not QTE.active, "QTE should time out")
	check(p.hp == p.max_hp - rift.fail_damage, "fail damage, hp %.0f" % p.hp)
	check(p.state == Player.State.STAGGER, "state %s" % p.state_name())
	rift.armed = true
	await reset(rift.global_position + Vector3(0, 0, 0.5))
	await frames(3)
	for a in rift.sequence:
		await frames(4)
		await tap(a)
	await frames(3)
	check(rift.sealed, "correct inputs should seal the rift")
	check(p.hp == p.max_hp, "no damage on success")
	await secs(0.5)
	check(p.state == Player.State.IDLE, "prompt buttons must not leak into actions, state %s" % p.state_name())


func test_burst() -> void:
	p.add_burst(100.0)
	check(p.can_burst(), "burst should be ready")
	await tap(&"burst")
	await frames(3)
	check(p.state == Player.State.BURST and p.current_anim() == &"burst", "state %s" % p.state_name())
	check(p.is_invulnerable(), "transformation should be invulnerable")
	await secs(0.7)
	check(p.burst_active, "burst should be active")
	await until(func() -> bool: return p.state == Player.State.IDLE, 1.0)
	press(&"move_right")
	await secs(1.0)
	check(absf(speed() - p.run_speed * p.burst_speed_mult) < 0.4, "burst speed %.2f" % speed())
	check(p.air_jumps_left == p.max_air_jumps + 1, "extra air jump, %d" % p.air_jumps_left)
	release(&"move_right")
	await secs(0.8)
	var hp0 := p.hp
	await reset_dummy_near_player()
	d.start_attack(false)
	await secs(d.windup_time + 0.05)
	check(p.hp < hp0 and p.state != Player.State.HURT, "super armor: hurt but not flinched, state %s" % p.state_name())
	p.burst_time_left = 0.05
	await frames(6)
	check(not p.burst_active and p.burst_meter == 0.0, "burst should end")


func reset_dummy_near_player() -> void:
	d.reset(p.global_position + p.facing() * 1.6)
	d.rotation.y = atan2(-p.facing().x, -p.facing().z)
	await frames(2)


func test_items() -> void:
	var charm: PickupItem = arena.charm
	charm._set_available(true)
	await reset(charm.global_position + Vector3(0, 0, 1.0))
	await frames(3)
	check(p._interact_target == charm, "charm should be the interaction target")
	await tap(&"interact")
	await frames(3)
	check(p.state == Player.State.INTERACT and p.current_anim() == &"pickup", "state %s anim %s" % [p.state_name(), p.current_anim()])
	await secs(1.0)
	check(p.items.healing_charm == 1, "items %s" % [p.items])
	check(not charm.enabled, "charm should be taken")
	p.hp = 50.0
	await tap(&"use_item")
	await frames(3)
	check(p.state == Player.State.ITEM and p.current_anim() == &"heal", "state %s" % p.state_name())
	await secs(1.1)
	check(is_equal_approx(p.hp, 90.0), "hp %.0f" % p.hp)
	check(p.items.healing_charm == 0, "charm consumed")
	check(p.state == Player.State.IDLE, "state %s" % p.state_name())
	await tap(&"use_item")
	await frames(3)
	check(p.state == Player.State.IDLE, "cannot use an item you do not have")


func test_faith_orb() -> void:
	var orb: PickupItem = arena.orb
	orb._set_available(true)
	await reset(orb.global_position + Vector3(0, 0, 1.0))
	await frames(3)
	await tap(&"interact")
	await secs(1.0)
	check(p.burst_meter >= 35.0, "burst %.1f" % p.burst_meter)


func test_lever() -> void:
	var lever: Lever = arena.lever
	var gate_y: float = arena.gate.position.y
	await reset(lever.global_position + Vector3(0, 0, 1.2))
	await frames(3)
	await tap(&"interact")
	await frames(3)
	check(p.current_anim() == &"interact", "anim %s" % p.current_anim())
	await secs(1.6)
	check(lever.is_open, "lever should be open")
	check(arena.gate.position.y > gate_y + 2.5, "gate should rise, y=%.2f" % arena.gate.position.y)


func test_death() -> void:
	await reset(Vector3(0, 0, -4.4))
	p.hp = 5.0
	d.start_attack(true)
	await secs(d.windup_time + 0.1)
	check(p.state == Player.State.DEAD and p.current_anim() == &"death", "state %s" % p.state_name())
	p.respawn()
	await frames(2)
	check(p.state == Player.State.IDLE and p.hp == p.max_hp, "respawn")
