extends SceneTree
## Headless smoke test: loads the slice, walks into the arena, forces every boss
## action (both phases, both spell cards), kills and respawns the player, then
## defeats the boss. Exits non-zero on any failed expectation.
##
##   godot --headless --path . -s tests/smoke_test.gd

var main: Node
var failures: Array[String] = []


func _initialize() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	_run()


func _run() -> void:
	await _wait(0.5)
	var player: Player = main.player
	var boss: BossCirno = main.boss
	var bullets: BulletManager = main.bullets
	_check(player != null and boss != null, "scene built")

	player.global_position = main.ARENA_CENTER + Vector3(0, 0.1, 8)
	await _wait(0.3)
	_check(main.boss_fight, "boss fight starts when entering the arena")
	main.toggle_lock_on()
	_check(player.lock_target == boss, "lock-on targets the boss")

	var max_bullets := 0
	for action in ["swing", "dash", "ring", "spiral", "aimed"]:
		player.hp = player.max_hp
		boss.force_action(action)
		var peak := await _wait_idle(boss, bullets, 6.0)
		max_bullets = maxi(max_bullets, peak)
		print("  phase 1 %-8s ok (peak bullets %d, player hp %.0f)" % [action, peak, player.hp])
	_check(max_bullets > 20, "danmaku patterns spawn bullets")

	# Player offence: melee in range and ofuda.
	player.hp = player.max_hp
	player.global_position = boss.global_position + Vector3(0, 0, 2.0)
	var hp_before := boss.hp
	player._melee_hit(20.0)
	_check(boss.hp < hp_before, "melee damages the boss")
	player.spirit = 100.0
	player._shoot_ofuda()
	await _wait(0.6)

	# Phase 2 and both spell cards.
	boss.take_damage(boss.hp - BossCirno.MAX_HP * 0.5 + 1.0)
	_check(boss.phase == 2, "boss enters phase 2 at half HP")
	await _wait(2.5)
	for action in ["icicle_fall", "perfect_freeze", "swing", "dash"]:
		# Keep the player alive: standing still under Icicle Fall is lethal.
		player.hp = player.max_hp
		player.invuln = 999.0
		boss.force_action(action)
		var peak := await _wait_idle(boss, bullets, 9.0)
		print("  phase 2 %-14s ok (peak bullets %d, player hp %.0f)" % [action, peak, player.hp])

	player.invuln = 0.0

	# Spell card clears bullets.
	player.spirit = 100.0
	player._cast_spell()
	_check(bullets.count_hostile() == 0, "Fantasy Seal clears hostile bullets")
	await _wait(1.0)

	# Death and respawn at the shrine resets the boss.
	player.invuln = 0.0
	player.state = Player.State.FREE
	player.take_damage(9999.0, Vector3.FORWARD)
	_check(player.is_dead(), "player can die")
	await _wait(main.RESPAWN_DELAY + 0.5)
	_check(not player.is_dead() and player.hp == player.max_hp, "player respawns with full HP")
	_check(boss.hp == BossCirno.MAX_HP and not main.boss_fight, "boss resets after player death")

	# Shrine prayer.
	player.hp = 10.0
	player.heals = 0
	main.shrine.pray()
	_check(player.hp == player.max_hp and player.heals == player.max_heals, "praying restores HP and gourds")

	# Win.
	player.global_position = main.ARENA_CENTER + Vector3(0, 0.1, 8)
	await _wait(0.3)
	_check(main.boss_fight, "fight restarts")
	boss.take_damage(BossCirno.MAX_HP * 0.6)
	await _wait(2.5)
	boss.take_damage(9999.0)
	await _wait(0.2)
	_check(main.boss_beaten and not main.boss_fight, "boss can be defeated")

	if failures.is_empty():
		print("SMOKE TEST PASSED")
		quit(0)
	else:
		for f in failures:
			printerr("FAILED: " + f)
		quit(1)


func _wait(seconds: float) -> void:
	await create_timer(seconds).timeout


## Waits until the boss returns to chasing, tracking the peak hostile bullet count.
func _wait_idle(boss: BossCirno, bullets: BulletManager, timeout: float) -> int:
	var peak := 0
	var elapsed := 0.0
	var started := false
	while elapsed < timeout:
		await physics_frame
		elapsed += 1.0 / 60.0
		peak = maxi(peak, bullets.count_hostile())
		if boss.state != BossCirno.S.CHASE:
			started = true
		elif started:
			break
	_check(elapsed < timeout, "boss action finishes within %.0fs" % timeout)
	return peak


func _check(ok: bool, what: String) -> void:
	if not ok:
		failures.append(what)
		printerr("  check failed: " + what)
