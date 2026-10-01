extends "res://tests/test_actions.gd"
## Plays through the action set in the arena and saves a captioned contact
## sheet of in-game screenshots. Needs a renderer (not --headless):
##   xvfb-run godot --rendering-driver opengl3 --fixed-fps 60 --resolution 640x360 \
##       --path . res://tools/showcase.tscn -- out.png

const COLS := 4

var shots: Array[Image] = []
var caption := Label.new()


func _ready() -> void:
	arena = load("res://demo/arena.tscn").instantiate()
	add_child(arena)
	var layer := CanvasLayer.new()
	layer.layer = 10
	caption.position = Vector2(12, 300)
	caption.add_theme_font_size_override("font_size", 26)
	caption.add_theme_color_override("font_outline_color", Color.BLACK)
	caption.add_theme_constant_override("outline_size", 8)
	layer.add_child(caption)
	add_child(layer)
	arena.hud._help.visible = false
	await frames(3)
	p = arena.player
	d = arena.dummy
	p.auto_respawn = false
	d.auto_attack = false
	# Shots swing the camera around; keep movement input independent of it.
	p.camera_rig = null

	await reset()
	press(&"move_right")
	await secs(0.7)
	await shot("Run")
	release(&"move_right")
	await frames(5)
	await shot("Sudden stop")

	await reset()
	await tap(&"walk_toggle")
	press(&"move_left")
	await secs(0.8)
	await shot("Walk")
	release(&"move_left")
	await tap(&"walk_toggle")

	await reset()
	press(&"move_right")
	await frames(3)
	await tap(&"dash")
	await frames(4)
	await shot("Dash")
	release(&"move_right")

	await reset()
	press(&"move_left")
	await tap(&"dodge")
	await secs(0.15)
	await shot("Dodge roll (i-frames)")
	release(&"move_left")

	await reset()
	press(&"jump")
	await secs(0.3)
	release(&"jump")
	await frames(2)
	press(&"jump")
	await secs(0.15)
	await shot("Double jump")
	await until(func() -> bool: return p.state == Player.State.GLIDE, 2.0)
	await secs(0.3)
	await shot("Glide")
	release(&"jump")

	await reset(Vector3(0, 0, -4.6))
	await tap(&"attack_light")
	await secs(0.2)
	await tap(&"attack_light")
	await secs(0.3)
	await tap(&"attack_light")
	await until(func() -> bool: return p.attack_id == "light3", 1.0)
	await secs(0.22)
	await shot("Light combo, 3rd hit")

	await reset(Vector3(0, 0, -4.6))
	press(&"attack_heavy")
	await secs(1.0)
	await shot("Charging heavy")
	release(&"attack_heavy")
	await secs(0.4)
	await shot("Charged release")

	await reset(Vector3(0, 0, -4.6))
	press(&"jump")
	await secs(0.3)
	await tap(&"attack_light")
	await secs(0.15)
	await shot("Aerial attack")
	release(&"jump")

	await reset(Vector3(0, 0, -4.4))
	press(&"guard")
	await secs(0.3)
	d.start_attack(false)
	await secs(d.windup_time + 0.03)
	await shot("Guard (blocked)")
	release(&"guard")

	await reset(Vector3(0, 0, -4.4))
	d.start_attack(false)
	await secs(d.windup_time - 0.1)
	press(&"guard")
	await secs(0.15)
	await shot("Parry")
	release(&"guard")

	await reset(Vector3(0, 0, -4.4))
	d.start_attack(true)
	await secs(d.windup_time + 0.2)
	await shot("Stagger (unblockable hit)")

	await reset(Vector3(0, 0, -4.6))
	d.poise = 1.0
	await tap(&"attack_light")
	await until(func() -> bool: return p.state == Player.State.IDLE, 1.5)
	await frames(3)
	await tap(&"interact")
	await frames(6)
	await shot("QTE finisher prompt")
	for i in QTE.steps.size():
		await frames(4)
		await tap(QTE.current_action())
	await secs(0.9)
	await shot("QTE finisher")

	await reset()
	p.add_burst(100.0)
	await tap(&"burst")
	await secs(0.75)
	await shot("Burst transformation")

	var charm: PickupItem = arena.charm
	charm._set_available(true)
	await reset(charm.global_position + Vector3(0, 0, 1.0))
	await frames(3)
	await tap(&"interact")
	await secs(0.35)
	await shot("Pick up item")
	await secs(0.8)
	p.hp = 40.0
	await tap(&"use_item")
	await secs(0.5)
	await shot("Use healing charm")

	var lever: Lever = arena.lever
	await reset(lever.global_position + Vector3(0, 0, 1.2))
	await frames(3)
	await tap(&"interact")
	await secs(0.6)
	await shot("Operate lever")

	_save()
	get_tree().quit()


## Frames the camera on Reimu from a three-quarter front angle and captures.
func shot(label: String) -> void:
	var f := p.facing()
	var rig: CameraRig = arena.camera_rig
	rig.rotation.y = atan2(f.x, f.z) + 0.75
	rig.pitch = -0.2
	rig.global_position = p.global_position + Vector3.UP * rig.height
	caption.text = label
	var before := Engine.time_scale
	Engine.time_scale = 0.0001  # freeze the pose while rendering
	QTE.process_mode = Node.PROCESS_MODE_DISABLED  # its timer runs in real time
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	shots.append(get_viewport().get_texture().get_image())
	Engine.time_scale = before
	QTE.process_mode = Node.PROCESS_MODE_ALWAYS
	print("captured ", label)


func _save() -> void:
	var w := shots[0].get_width()
	var h := shots[0].get_height()
	var rows := int(ceil(shots.size() / float(COLS)))
	var sheet := Image.create(w * COLS, h * rows, false, Image.FORMAT_RGB8)
	for i in shots.size():
		var img := shots[i]
		img.convert(Image.FORMAT_RGB8)
		sheet.blit_rect(img, Rect2i(0, 0, w, h), Vector2i((i % COLS) * w, (i / COLS) * h))
	var out: String = OS.get_cmdline_user_args()[0] if OS.get_cmdline_user_args().size() > 0 else "user://showcase.png"
	sheet.save_png(out)
	print("saved ", out)
