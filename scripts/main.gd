extends Node3D
## Vertical slice: "Misty Lake at Dusk".
## A wayside shrine (checkpoint), a stone path through a torii, and a lake that
## Cirno has frozen solid, which is the boss arena. Everything is built from
## primitives in code; see docs/GAME_DESIGN.md for the art replacement plan.

const SHRINE_POS := Vector3(0, 0, 44)
const ARENA_CENTER := Vector3(0, 0, -10)
const ARENA_RADIUS := 21.0
const RESPAWN_DELAY := 4.0
const BROKEN_TORII_POS := Vector3(0, 0, -41)

var player: Player
var boss: BossCirno
var hud: Hud
var bullets: BulletManager
var camera_rig: CameraRig
var shrine: Shrine
var boss_fight := false
var boss_beaten := false
var _arena_wall: MeshInstance3D
var _respawn_timer := -1.0
var _help_hidden := false


func _ready() -> void:
	InputSetup.ensure_actions()
	add_child(Sfx.new())
	add_child(Music.new())
	_build_environment()
	_build_world()

	bullets = BulletManager.new()
	bullets.name = "Bullets"
	add_child(bullets)

	hud = Hud.new()
	add_child(hud)

	player = Player.new()
	player.name = "Player"
	add_child(player)
	player.global_position = SHRINE_POS + Vector3(0, 0.1, -3.0)

	camera_rig = CameraRig.new()
	add_child(camera_rig)
	camera_rig.attach(player)

	boss = BossCirno.new()
	boss.name = "Cirno"
	add_child(boss)
	boss.home = ARENA_CENTER + Vector3(0, 0.1, -6.0)
	boss.global_position = boss.home

	player.camera_rig = camera_rig
	player.bullets = bullets
	player.boss = boss
	bullets.player = player
	bullets.boss = boss
	boss.player = player
	boss.bullets = bullets
	boss.hud = hud
	hud.player = player
	hud.boss = boss
	shrine.player = player
	shrine.hud = hud

	player.died.connect(_on_player_died)
	boss.defeated.connect(_on_boss_defeated)
	shrine.prayed.connect(_on_prayed)

	if not _is_headless():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	add_child(_make_grade_overlay())
	Music.play("explore")
	hud.big_message("東方虚信録", "Touhou: Hollow Faith  ·  Misty Lake (prototype)", Color(0.9, 0.2, 0.25), 2.5)


func _is_headless() -> bool:
	return DisplayServer.get_name() == "headless"


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if event.is_action_pressed("lock_on"):
		toggle_lock_on()


func toggle_lock_on() -> void:
	if player.lock_target == null and boss.is_active() and player.global_position.distance_to(boss.global_position) < 30.0:
		player.lock_target = boss
	else:
		player.lock_target = null
	camera_rig.lock_target = player.lock_target


func _physics_process(delta: float) -> void:
	if not _help_hidden and player.global_position.distance_to(SHRINE_POS) > 12.0:
		_help_hidden = true
		hud.hide_help()

	var flat := player.global_position - ARENA_CENTER
	flat.y = 0.0
	if not boss_fight and not boss_beaten and not player.is_dead() and flat.length() < ARENA_RADIUS - 3.0:
		start_boss()
	# Fog-gate rule: once the duel starts, no leaving the ice.
	if boss_fight and flat.length() > ARENA_RADIUS - 0.6:
		var clamped := ARENA_CENTER + flat.normalized() * (ARENA_RADIUS - 0.6)
		player.global_position.x = clamped.x
		player.global_position.z = clamped.z

	if _respawn_timer >= 0.0:
		_respawn_timer -= delta
		if _respawn_timer < 0.0:
			_respawn()


func start_boss() -> void:
	boss_fight = true
	boss.activate()
	hud.show_boss(true)
	_arena_wall.visible = true
	Music.play("boss")
	hud.banner("霧の湖", "Misty Lake: the ice is thick enough to fight on", Color(0.45, 0.75, 1.0))


func _on_player_died() -> void:
	camera_rig.lock_target = null
	hud.big_message("満身創痍", "Reimu has fallen. Returning to the shrine...", Color(0.8, 0.08, 0.1), 2.2)
	_respawn_timer = RESPAWN_DELAY


func _respawn() -> void:
	bullets.clear_all()
	_end_fight()
	if not boss_beaten:
		boss.reset()
	player.respawn(SHRINE_POS + Vector3(0, 0.1, -3.0))


func _on_prayed() -> void:
	if not boss_beaten and not boss_fight:
		boss.reset()


func _on_boss_defeated() -> void:
	boss_beaten = true
	player.lock_target = null
	camera_rig.lock_target = null
	_end_fight()
	hud.big_message("異変解決", "Incident resolved: Cirno defeated", Color(1.0, 0.85, 0.3), 4.0)
	get_tree().create_timer(5.5).timeout.connect(_show_predecessor)


## Story beat 1 (docs/STORY_AND_CHARACTERS.md): a faded red-and-white figure watches
## from the broken torii across the lake, then dissolves. It uses Reimu's own rig,
## bleached to grey rose, because she is what Reimu could become.
func _show_predecessor() -> void:
	if not ResourceLoader.exists(Player.RIG_PATH) or player.is_dead():
		return
	var ghost: Node3D = (load(Player.RIG_PATH) as PackedScene).instantiate()
	ghost.name = "FormerShrineMaiden"
	add_child(ghost)
	ghost.global_position = BROKEN_TORII_POS + Vector3(0, 0, 3.0)
	var to := player.global_position - ghost.global_position
	ghost.rotation.y = atan2(to.x, to.z)  # glTF forward is +Z
	var mats: Array[StandardMaterial3D] = []
	for mi: MeshInstance3D in ghost.find_children("*", "MeshInstance3D", true, false):
		for i in mi.mesh.get_surface_count():
			var src := mi.get_active_material(i) as StandardMaterial3D
			var m := StandardMaterial3D.new()
			var c := src.albedo_color if src else Color.WHITE
			var grey := c.r * 0.3 + c.g * 0.59 + c.b * 0.11
			m.albedo_color = Color(grey, grey, grey).lerp(c, 0.25) * Color(0.95, 0.82, 0.86)
			m.albedo_color.a = 0.0
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.diffuse_mode = BaseMaterial3D.DIFFUSE_TOON
			mi.set_surface_override_material(i, m)
			mats.append(m)
	var ap := ghost.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if ap:
		ap.play("idle")
	var tw := create_tween()
	tw.tween_method(func(a: float):
		for m in mats:
			m.albedo_color.a = a
	, 0.0, 0.85, 2.0)
	tw.tween_interval(3.5)
	tw.tween_method(func(a: float):
		for m in mats:
			m.albedo_color.a = a
	, 0.85, 0.0, 2.5)
	tw.tween_callback(ghost.queue_free)
	hud.banner("……", "Someone in faded red and white watches from the broken torii", Color(0.75, 0.62, 0.66))


func _end_fight() -> void:
	boss_fight = false
	Music.play("explore")
	hud.show_boss(false)
	_arena_wall.visible = false


## Full-screen vignette and film grain: the Souls-style frame on the dark palette.
func _make_grade_overlay() -> CanvasLayer:
	var layer := CanvasLayer.new()
	layer.layer = 0
	var rect := ColorRect.new()
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shader := Shader.new()
	shader.code = """
shader_type canvas_item;
uniform float strength = 0.6;
uniform float grain = 0.045;
void fragment() {
	vec2 uv = UV - 0.5;
	float v = smoothstep(0.35, 0.85, length(uv * vec2(1.25, 1.0)));
	float n = fract(sin(dot(UV * 1000.0 + TIME, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
	COLOR = vec4(vec3(n * grain), v * strength + abs(n) * grain);
}
"""
	var sm := ShaderMaterial.new()
	sm.shader = shader
	rect.material = sm
	layer.add_child(rect)
	return layer


# --------------------------------------------------------------------------
# World building
# --------------------------------------------------------------------------

func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.07, 0.07, 0.12)
	sky_mat.sky_horizon_color = Color(0.36, 0.26, 0.34)
	sky_mat.ground_horizon_color = Color(0.2, 0.16, 0.2)
	sky_mat.ground_bottom_color = Color(0.02, 0.02, 0.03)
	sky_mat.sun_angle_max = 20.0
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.3, 0.3, 0.4)
	env.ambient_light_energy = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 1.0
	env.glow_enabled = true
	env.glow_intensity = 0.9
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 1.1
	env.fog_enabled = true
	env.fog_light_color = Color(0.26, 0.24, 0.32)
	env.fog_density = 0.012
	env.fog_sky_affect = 0.25
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.018
	env.volumetric_fog_albedo = Color(0.55, 0.55, 0.65)
	env.ssao_enabled = true
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.72
	env.adjustment_contrast = 1.12
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.58, 0.46)
	sun.light_energy = 0.9
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	sun.rotation_degrees = Vector3(-10, 150, 0)
	add_child(sun)


func _build_world() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1996  # Touhou's first year
	var grass := MeshKit.mat(Color(0.12, 0.13, 0.11), 0.0, 1.0)
	var stone := MeshKit.mat(Color(0.3, 0.3, 0.32), 0.0, 0.95)
	var red := MeshKit.mat(Color(0.78, 0.1, 0.08), 0.0, 0.55)
	var black := MeshKit.mat(Color(0.08, 0.07, 0.07), 0.0, 0.6)

	# Ground and invisible bounds.
	MeshKit.solid_box(self, Vector3(180, 2, 180), Vector3(0, -1, 0), grass)
	for w in [[Vector3(180, 10, 1), Vector3(0, 5, 70)], [Vector3(180, 10, 1), Vector3(0, 5, -60)], [Vector3(1, 10, 180), Vector3(60, 5, 0)], [Vector3(1, 10, 180), Vector3(-60, 5, 0)]]:
		MeshKit.solid_box(self, w[0], w[1])

	# Lake: dark water ring and the frozen arena disc.
	MeshKit.add(self, MeshKit.cylinder(34, 34, 0.04, 64), MeshKit.mat(Color(0.01, 0.015, 0.025), 0.0, 0.05, 0.3), ARENA_CENTER + Vector3(0, 0.01, 0))
	var ice := MeshKit.mat(Color(0.28, 0.34, 0.42), 0.0, 0.5, 0.0)
	ice.metallic_specular = 0.25  # low sun: keep the ice from flaring
	MeshKit.add(self, MeshKit.cylinder(ARENA_RADIUS + 1.5, ARENA_RADIUS + 1.5, 0.06, 64), ice, ARENA_CENTER + Vector3(0, 0.03, 0))
	# Frost cracks for readability of scale.
	for i in 14:
		var a := rng.randf() * TAU
		var r := rng.randf_range(2, ARENA_RADIUS - 2)
		MeshKit.add(self, MeshKit.box(Vector3(0.06, 0.01, rng.randf_range(1.5, 4.0))), MeshKit.mat(Color(0.75, 0.88, 0.95), 0.15), ARENA_CENTER + Vector3(cos(a) * r, 0.065, sin(a) * r), Vector3(0, rng.randf() * 180, 0))
	# The duel's "fog gate": a shimmering ice wall, shown only during the fight.
	var wall_mesh := MeshKit.cylinder(ARENA_RADIUS, ARENA_RADIUS, 6.0, 64)
	wall_mesh.cap_top = false
	wall_mesh.cap_bottom = false
	var wall_mat := MeshKit.mat(Color(0.55, 0.85, 1.0), 0.8, 0.1, 0.0, 0.12)
	wall_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_arena_wall = MeshKit.add(self, wall_mesh, wall_mat, ARENA_CENTER + Vector3(0, 3.0, 0))
	_arena_wall.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_arena_wall.visible = false

	# Stone path from the shrine to the lake.
	var z := SHRINE_POS.z - 2.0
	while z > ARENA_CENTER.z + ARENA_RADIUS:
		MeshKit.add(self, MeshKit.box(Vector3(rng.randf_range(1.6, 2.2), 0.08, 1.1)), stone, Vector3(rng.randf_range(-0.2, 0.2), 0.04, z), Vector3(0, rng.randf_range(-6, 6), 0))
		z -= 1.35

	# Great torii at the lake's edge, and a broken one on the far shore where the
	# Former Shrine Maiden is glimpsed (docs/STORY_AND_CHARACTERS.md).
	var tz := ARENA_CENTER.z + ARENA_RADIUS + 5.0
	if Kit.has("torii"):
		Kit.place(self, "torii", Vector3(0, 0, tz))
		for side in [-1.0, 1.0]:
			MeshKit.solid_cylinder(self, 0.3, 6.0, Vector3(2.6 * side, 3.0, tz))
	else:
		for side in [-1.0, 1.0]:
			MeshKit.solid_cylinder(self, 0.28, 6.0, Vector3(2.6 * side, 3.0, tz), red)
			MeshKit.add(self, MeshKit.cylinder(0.36, 0.36, 0.5), black, Vector3(2.6 * side, 0.25, tz))
		MeshKit.add(self, MeshKit.box(Vector3(7.6, 0.4, 0.5)), black, Vector3(0, 6.1, tz))
		MeshKit.add(self, MeshKit.box(Vector3(6.6, 0.3, 0.35)), red, Vector3(0, 5.3, tz))
		MeshKit.add(self, MeshKit.box(Vector3(0.9, 0.9, 0.12)), black, Vector3(0, 5.75, tz - 0.05))
	Kit.place(self, "torii_broken", BROKEN_TORII_POS, PI)

	# Stone lanterns (tōrō) along the path, lit.
	for i in 4:
		for side in [-1.0, 1.0]:
			var p := Vector3(2.4 * side, 0, SHRINE_POS.z - 6.0 - i * 6.0)
			MeshKit.solid_cylinder(self, 0.18, 1.0, p + Vector3(0, 0.5, 0), null if Kit.has("stone_lantern") else stone)
			if Kit.place(self, "stone_lantern", p, rng.randf_range(-0.2, 0.2)) == null:
				MeshKit.add(self, MeshKit.box(Vector3(0.5, 0.35, 0.5)), MeshKit.mat(Color(1.0, 0.75, 0.4), 2.5), p + Vector3(0, 1.17, 0))
				MeshKit.add(self, MeshKit.prism(Vector3(0.8, 0.3, 0.8)), stone, p + Vector3(0, 1.5, 0))
			var l := OmniLight3D.new()
			l.light_color = Color(1.0, 0.7, 0.4)
			l.light_energy = 1.4
			l.omni_range = 5.0
			l.position = p + Vector3(0, 1.2, 0)
			add_child(l)

	# Forest ring: dead trees and ink pines, kept off the path and the lake.
	var bark := MeshKit.mat(Color(0.1, 0.08, 0.07), 0.0, 1.0)
	var leaves := [MeshKit.mat(Color(0.07, 0.09, 0.08), 0.0, 1.0), MeshKit.mat(Color(0.1, 0.11, 0.1), 0.0, 1.0), MeshKit.mat(Color(0.2, 0.19, 0.18), 0.0, 1.0)]
	var tree_kinds := ["tree_dead_1", "tree_dead_2", "tree_dead_3", "tree_pine_1", "tree_pine_2", "tree_pine_1"]
	var placed := 0
	while placed < 140:
		var p := Vector3(rng.randf_range(-56, 56), 0, rng.randf_range(-56, 66))
		if p.distance_to(ARENA_CENTER) < 37.0 or (absf(p.x) < 6.0 and p.z > ARENA_CENTER.z) or p.distance_to(SHRINE_POS) < 7.0:
			continue
		placed += 1
		var kind: String = tree_kinds[rng.randi() % tree_kinds.size()]
		var tree := Kit.place(self, kind, p, rng.randf() * TAU, rng.randf_range(0.8, 1.3))
		if tree:
			MeshKit.solid_cylinder(self, 0.35, 4.0, p + Vector3(0, 2.0, 0))
			continue
		var h := rng.randf_range(5.0, 11.0)
		MeshKit.solid_cylinder(self, 0.3, h, p + Vector3(0, h * 0.5, 0), bark)
		var leaf: StandardMaterial3D = leaves[rng.randi() % leaves.size()]
		MeshKit.add(self, MeshKit.cylinder(0.0, h * 0.35, h * 0.7, 10), leaf, p + Vector3(0, h * 0.75, 0))

	# Rocks and reeds around the shore.
	for i in 24:
		var a := rng.randf() * TAU
		var r := rng.randf_range(34.5, 36.5)
		var s := rng.randf_range(0.6, 1.8)
		var at := ARENA_CENTER + Vector3(cos(a) * r, 0, sin(a) * r)
		if Kit.place(self, "rock_%d" % (i % 3 + 1), at, rng.randf() * TAU, s) == null:
			MeshKit.add(self, MeshKit.sphere(s, s * 1.2, 10), stone, at + Vector3(0, s * 0.3, 0))
	for i in 40:
		var a := rng.randf() * TAU
		var at := ARENA_CENTER + Vector3(cos(a), 0, sin(a)) * rng.randf_range(ARENA_RADIUS + 2.5, 33.0)
		if absf(at.x) < 4.0 and at.z > ARENA_CENTER.z:
			continue  # keep the causeway clear
		Kit.place(self, "reeds", at, rng.randf() * TAU, rng.randf_range(0.8, 1.5))

	# Fireflies / frost motes drifting over the lake.
	var motes := CPUParticles3D.new()
	motes.amount = 160
	motes.lifetime = 8.0
	motes.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	motes.emission_box_extents = Vector3(34, 3, 34)
	motes.direction = Vector3.UP
	motes.spread = 180.0
	motes.gravity = Vector3.ZERO
	motes.initial_velocity_min = 0.1
	motes.initial_velocity_max = 0.4
	var mote := MeshKit.sphere(0.035, -1.0, 6)
	mote.material = MeshKit.glow(Color(0.75, 0.95, 1.0), 3.0)
	motes.mesh = mote
	motes.position = ARENA_CENTER + Vector3(0, 3, 0)
	add_child(motes)

	shrine = Shrine.new()
	shrine.name = "Shrine"
	add_child(shrine)
	shrine.global_position = SHRINE_POS
	shrine.rotation_degrees.y = 0.0
