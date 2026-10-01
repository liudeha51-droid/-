extends SceneTree
## Renders a contact sheet of animation clips (one row per clip, 6 samples per row).
##   xvfb-run godot --rendering-driver opengl3 --resolution 200x240 --path . --script res://tools/anim_sheet.gd -- out.png clip1 clip2 ...
## Requires a real renderer (not --headless).

const COLS := 6
const CELL := Vector2i(200, 240)

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var out: String = args[0]
	var clips := args.slice(1)
	DisplayServer.window_set_size(CELL)
	var model: Node3D = load("res://characters/reimu/reimu.glb").instantiate()
	root.add_child(model)
	var ap: AnimationPlayer = model.get_node("AnimationPlayer")
	var lib_path := "res://characters/reimu/reimu_extra_anims.res"
	if ResourceLoader.exists(lib_path):
		ap.add_animation_library("extra", load(lib_path))
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.22, 0.23, 0.26)
	env.environment.ambient_light_color = Color(0.6, 0.6, 0.65)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	root.add_child(env)
	var light := DirectionalLight3D.new()
	root.add_child(light)
	light.rotation_degrees = Vector3(-40, 35, 0)
	var floor_mesh := MeshInstance3D.new()
	floor_mesh.mesh = PlaneMesh.new()
	(floor_mesh.mesh as PlaneMesh).size = Vector2(4, 4)
	root.add_child(floor_mesh)
	var cam := Camera3D.new()
	root.add_child(cam)
	cam.current = true
	cam.fov = 40
	# Three-quarter front view (the model faces +Z).
	cam.look_at_from_position(Vector3(1.7, 1.25, 2.6), Vector3(0, 0.78, 0))
	var sheet := Image.create(CELL.x * COLS, CELL.y * clips.size(), false, Image.FORMAT_RGB8)
	for row in clips.size():
		var name: String = clips[row]
		if not ap.has_animation(name) and ap.has_animation("extra/" + name):
			name = "extra/" + name
		var anim := ap.get_animation(name)
		if anim == null:
			push_error("missing clip " + name)
			quit(1)
			return
		ap.play(name)
		for col in COLS:
			var t := anim.length * col / float(COLS - 1)
			ap.seek(t, true)
			await process_frame
			await process_frame
			var img := root.get_texture().get_image()
			img.convert(Image.FORMAT_RGB8)
			sheet.blit_rect(img, Rect2i(Vector2i.ZERO, CELL), Vector2i(col * CELL.x, row * CELL.y))
		print("%s (%.2fs)" % [name, anim.length])
	sheet.save_png(out)
	quit()
