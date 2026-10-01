extends SceneTree
## Bakes the clips reimu.glb does not ship with (walk, jump, guard, parry, ...)
## into res://characters/reimu/reimu_extra_anims.res.
##
##   godot --headless --path . --script res://tools/build_extra_animations.gd
##
## Every clip is built from poses sampled out of the original clips (mostly
## "idle" and "run") plus joint offsets, so proportions and the gohei grip stay
## consistent with the hand-made animation. Offsets are Euler degrees applied
## in the *parent* bone's frame. The rig rests in a T-pose with identity bone
## rotations and faces +Z, so for torso and leg bones:
##   +X  = bend forward (spine/head) / swing backward (thigh, upper_arm) / knee bend (shin)
##   +Y  = twist toward the character's left
##   +Z  = lean toward the character's right; raises upper_arm.L / thigh.L outward
## Forearms are offset in the upper arm's frame, where the arm lies along X, so
## an elbow bend is a Y rotation (negative for .L, positive for .R).
## Reimu holds the gohei in her LEFT hand, so weapon poses drive the .L arm.

const OUT := "res://characters/reimu/reimu_extra_anims.res"
const SKEL := "root/Skeleton3D"
const FPS := 30.0
const THIGH := 0.39
const SHIN := 0.44
const UPPER_BODY := ["spine", "chest", "neck", "head", "shoulder.L", "shoulder.R", "upper_arm.L",
		"upper_arm.R", "forearm.L", "forearm.R", "hand.L", "hand.R"]

var src: AnimationPlayer
var skeleton: Skeleton3D
var bones: PackedStringArray = []
var lib := AnimationLibrary.new()


func _init() -> void:
	var model: Node = load("res://characters/reimu/reimu.glb").instantiate()
	root.add_child(model)
	src = model.get_node("AnimationPlayer")
	skeleton = model.get_node(SKEL)
	var idle := src.get_animation("idle")
	for i in idle.get_track_count():
		var b := String(idle.track_get_path(i).get_concatenated_subnames())
		if b not in bones:
			bones.append(b)
	build_all()
	var err := ResourceSaver.save(lib, OUT, ResourceSaver.FLAG_COMPRESS)
	print("saved %d clips to %s (err=%d)" % [lib.get_animation_list().size(), OUT, err])
	quit(err)


# --------------------------------------------------------------- pose helpers
## A pose is {bone: [position: Vector3, rotation: Quaternion]}.
func sample(clip: String, t: float) -> Dictionary:
	var a := src.get_animation(clip)
	t = fposmod(t, a.length) if a.loop_mode != Animation.LOOP_NONE else clampf(t, 0.0, a.length)
	var p := {}
	for i in a.get_track_count():
		var b := String(a.track_get_path(i).get_concatenated_subnames())
		if not p.has(b):
			# The importer keeps position tracks for the hips only.
			p[b] = [skeleton.get_bone_rest(skeleton.find_bone(b)).origin, Quaternion.IDENTITY]
		match a.track_get_type(i):
			Animation.TYPE_POSITION_3D:
				p[b][0] = a.position_track_interpolate(i, t)
			Animation.TYPE_ROTATION_3D:
				p[b][1] = a.rotation_track_interpolate(i, t)
	return p


func blend(a: Dictionary, b: Dictionary, w: float) -> Dictionary:
	var p := {}
	for k in a:
		p[k] = [a[k][0].lerp(b[k][0], w), a[k][1].slerp(b[k][1], w)]
	return p


## Offsets: {bone: Vector3 degrees}, plus optional "hips_pos": Vector3 metres.
func off(base: Dictionary, offsets: Dictionary, w := 1.0) -> Dictionary:
	var p := {}
	for k in base:
		p[k] = [base[k][0], base[k][1]]
	for k in offsets:
		if k == "hips_pos":
			p["hips"][0] += offsets[k] * w
		else:
			var e: Vector3 = offsets[k] * w
			p[k][1] = Quaternion.from_euler(Vector3(deg_to_rad(e.x), deg_to_rad(e.y), deg_to_rad(e.z))) * p[k][1]
	return p


## Upper body from `upper`, everything else from `lower`.
func mask(lower: Dictionary, upper: Dictionary) -> Dictionary:
	var p := {}
	for k in lower:
		p[k] = upper[k] if k in UPPER_BODY else lower[k]
	return p


## Knees-forward crouch that keeps the feet roughly planted.
func crouch(deg: float) -> Dictionary:
	var drop := (THIGH + SHIN) * (1.0 - cos(deg_to_rad(deg)))
	return {
		"thigh.L": Vector3(-deg, 0, 0), "thigh.R": Vector3(-deg, 0, 0),
		"shin.L": Vector3(2 * deg, 0, 0), "shin.R": Vector3(2 * deg, 0, 0),
		"foot.L": Vector3(-deg, 0, 0), "foot.R": Vector3(-deg, 0, 0),
		"spine": Vector3(deg * 0.35, 0, 0), "hips_pos": Vector3(0, -drop, 0),
	}


func merge(a: Dictionary, b: Dictionary) -> Dictionary:
	var m := a.duplicate()
	for k in b:
		m[k] = m.get(k, Vector3.ZERO) + b[k]
	return m


func smooth(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


## Interpolates eased between timed poses: [[t, pose], ...].
func keyed(keys: Array, t: float) -> Dictionary:
	if t <= keys[0][0]:
		return keys[0][1]
	for i in range(1, keys.size()):
		if t <= keys[i][0]:
			var t0: float = keys[i - 1][0]
			var w := smooth((t - t0) / (keys[i][0] - t0))
			return blend(keys[i - 1][1], keys[i][1], w)
	return keys[-1][1]


# ------------------------------------------------------------------ baking
func bake(name: String, length: float, loop: bool, sampler: Callable) -> void:
	var a := Animation.new()
	a.length = length
	a.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE
	var hips_track := a.add_track(Animation.TYPE_POSITION_3D)
	a.track_set_path(hips_track, NodePath(SKEL + ":hips"))
	var rot_tracks := {}
	for b in bones:
		var rt := a.add_track(Animation.TYPE_ROTATION_3D)
		a.track_set_path(rt, NodePath("%s:%s" % [SKEL, b]))
		rot_tracks[b] = rt
	var frames := int(round(length * FPS))
	for f in frames + 1:
		var t := minf(f / FPS, length)
		var p: Dictionary = sampler.call(t)
		a.position_track_insert_key(hips_track, t, p["hips"][0])
		for b in bones:
			a.rotation_track_insert_key(rot_tracks[b], t, p[b][1].normalized())
	lib.add_animation(name, a)


## Plays `clip` with its amplitude scaled toward `rest` (used for walk cycles).
func damped_cycle(clip: String, rest: Dictionary, amount: float, length: float, extra := {}) -> Callable:
	var clip_len := src.get_animation(clip).length
	return func(t: float) -> Dictionary:
		var p := blend(rest, sample(clip, t / length * clip_len), amount)
		return off(p, extra)


# ------------------------------------------------------------------- clips
func build_all() -> void:
	var idle := sample("idle", 0.0)

	# ---- locomotion -------------------------------------------------------
	bake("walk", 0.95, true, damped_cycle("run", idle, 0.5, 0.95, {"spine": Vector3(2, 0, 0)}))
	bake("slow_walk", 1.45, true, damped_cycle("run", idle, 0.28, 1.45,
			{"spine": Vector3(6, 0, 0), "head": Vector3(6, 0, 0), "hips_pos": Vector3(0, -0.02, 0)}))
	var run0 := sample("run", 0.0)
	var skid := off(idle, {
		"hips_pos": Vector3(0, -0.13, -0.06), "spine": Vector3(-14, 0, 0), "chest": Vector3(-6, 0, 0),
		"head": Vector3(8, 0, 0), "thigh.L": Vector3(-38, 0, 4), "shin.L": Vector3(6, 0, 0),
		"foot.L": Vector3(-20, 0, 0), "thigh.R": Vector3(-14, 0, -4), "shin.R": Vector3(62, 0, 0),
		"foot.R": Vector3(-40, 0, 0), "upper_arm.L": Vector3(-45, 0, 35), "upper_arm.R": Vector3(-45, 0, -35),
		"forearm.L": Vector3(0, -25, 0), "forearm.R": Vector3(0, 25, 0),
	})
	bake("sudden_stop", 0.5, false, func(t: float) -> Dictionary: return keyed([[0.0, run0], [0.07, skid], [0.3, skid], [0.5, idle]], t))
	var dash := off(idle, {
		"spine": Vector3(26, 0, 0), "chest": Vector3(6, 0, 0), "head": Vector3(-24, 0, 0),
		"hips_pos": Vector3(0, -0.06, 0), "thigh.L": Vector3(-38, 0, 0), "shin.L": Vector3(45, 0, 0),
		"thigh.R": Vector3(40, 0, 0), "shin.R": Vector3(65, 0, 0), "foot.R": Vector3(30, 0, 0),
		"upper_arm.L": Vector3(50, 0, 15), "upper_arm.R": Vector3(50, 0, -15),
	})
	bake("dash", 0.3, false, func(t: float) -> Dictionary: return keyed([[0.0, idle], [0.06, dash], [0.3, dash]], t))

	# ---- jumping ----------------------------------------------------------
	var squat := off(idle, merge(crouch(28), {"upper_arm.L": Vector3(30, 0, 0), "upper_arm.R": Vector3(30, 0, 0)}))
	var rise := off(idle, {
		"thigh.L": Vector3(-50, 0, 0), "shin.L": Vector3(85, 0, 0), "foot.L": Vector3(20, 0, 0),
		"thigh.R": Vector3(8, 0, 0), "shin.R": Vector3(35, 0, 0), "foot.R": Vector3(25, 0, 0),
		"upper_arm.L": Vector3(-25, 0, 40), "upper_arm.R": Vector3(-25, 0, -40),
		"spine": Vector3(-6, 0, 0), "head": Vector3(-8, 0, 0),
	})
	var fall := off(idle, {
		"thigh.L": Vector3(-18, 0, 4), "shin.L": Vector3(32, 0, 0), "thigh.R": Vector3(4, 0, -4),
		"shin.R": Vector3(22, 0, 0), "foot.L": Vector3(15, 0, 0), "foot.R": Vector3(20, 0, 0),
		"upper_arm.L": Vector3(-10, 0, 55), "upper_arm.R": Vector3(-10, 0, -55),
		"spine": Vector3(5, 0, 0), "head": Vector3(6, 0, 0),
	})
	bake("jump_start", 0.12, false, func(t: float) -> Dictionary: return keyed([[0.0, idle], [0.12, squat]], t))
	bake("jump_rise", 0.35, false, func(t: float) -> Dictionary: return keyed([[0.0, squat], [0.12, rise], [0.35, rise]], t))
	bake("fall", 0.8, true, func(t: float) -> Dictionary:
		var s := sin(t / 0.8 * TAU)
		return off(fall, {"upper_arm.L": Vector3(0, 0, 6 * s), "upper_arm.R": Vector3(0, 0, -6 * s),
				"shin.L": Vector3(6 * s, 0, 0), "shin.R": Vector3(-6 * s, 0, 0)}))
	bake("land", 0.32, false, func(t: float) -> Dictionary:
		return keyed([[0.0, fall], [0.06, off(idle, crouch(34))], [0.32, idle]], t))
	var tuck := off(idle, {
		"thigh.L": Vector3(-80, 0, 0), "shin.L": Vector3(120, 0, 0), "thigh.R": Vector3(-72, 0, 0),
		"shin.R": Vector3(115, 0, 0), "spine": Vector3(18, 0, 0), "head": Vector3(15, 0, 0),
		"upper_arm.L": Vector3(-55, 0, 10), "upper_arm.R": Vector3(-55, 0, -10),
		"forearm.L": Vector3(0, -50, 0), "forearm.R": Vector3(0, 50, 0),
	})
	bake("double_jump", 0.5, false, func(t: float) -> Dictionary:
		var body := keyed([[0.0, rise], [0.08, tuck], [0.38, tuck], [0.5, fall]], t)
		var spin := 360.0 * smooth(clampf((t - 0.04) / 0.4, 0.0, 1.0))
		return off(body, {"hips": Vector3(spin, 0, 0), "hips_pos": Vector3(0, 0.12 * sin(PI * clampf(t / 0.45, 0, 1)), 0)}))
	var glide := off(idle, {
		"hips": Vector3(16, 0, 0), "head": Vector3(-18, 0, 0), "spine": Vector3(-2, 0, 0),
		"thigh.L": Vector3(14, 0, 2), "thigh.R": Vector3(22, 0, -2), "shin.L": Vector3(22, 0, 0),
		"shin.R": Vector3(12, 0, 0), "foot.L": Vector3(35, 0, 0), "foot.R": Vector3(35, 0, 0),
		"upper_arm.L": Vector3(12, 0, 78), "upper_arm.R": Vector3(12, 0, -78),
		"forearm.L": Vector3(0, -12, 0), "forearm.R": Vector3(0, 12, 0),
	})
	bake("glide", 1.2, true, func(t: float) -> Dictionary:
		var s := sin(t / 1.2 * TAU)
		return off(glide, {"upper_arm.L": Vector3(0, 0, 7 * s), "upper_arm.R": Vector3(0, 0, -7 * s),
				"hips_pos": Vector3(0, 0.03 * s, 0), "thigh.L": Vector3(4 * s, 0, 0), "thigh.R": Vector3(-4 * s, 0, 0)}))

	# ---- defense ----------------------------------------------------------
	var guard := off(idle, merge(crouch(14), {
		"spine": Vector3(4, 0, 0), "head": Vector3(-4, 0, 0),
		"upper_arm.R": Vector3(-60, 0, -12), "forearm.R": Vector3(0, 75, 0),
		"upper_arm.L": Vector3(-55, 0, 12), "forearm.L": Vector3(0, -80, 0),
	}))
	var guard_push := off(guard, {"spine": Vector3(-10, 0, 0), "head": Vector3(-6, 0, 0), "hips_pos": Vector3(0, -0.02, -0.06)})
	bake("guard", 1.0, true, func(t: float) -> Dictionary: return off(guard, {"chest": Vector3(1.5 * sin(t * TAU), 0, 0)}))
	bake("guard_hit", 0.28, false, func(t: float) -> Dictionary: return keyed([[0.0, guard], [0.05, guard_push], [0.28, guard]], t))
	var parry := off(idle, merge(crouch(10), {
		"spine": Vector3(4, 28, 0), "chest": Vector3(0, 12, 0),
		"upper_arm.L": Vector3(-85, 0, 55), "forearm.L": Vector3(0, -15, 0),
		"upper_arm.R": Vector3(-25, 0, -35),
	}))
	bake("parry", 0.42, false, func(t: float) -> Dictionary: return keyed([[0.0, guard], [0.07, parry], [0.24, parry], [0.42, guard]], t))

	# ---- offense ----------------------------------------------------------
	var wind := off(sample("attack3", 0.0), {"spine": Vector3(-6, 32, 0), "chest": Vector3(0, 12, 0),
			"upper_arm.L": Vector3(35, 0, 40), "hips_pos": Vector3(0, -0.05, 0)})
	var a3_len := src.get_animation("attack3").length
	bake("heavy_attack", 0.32 + a3_len, false, func(t: float) -> Dictionary:
		if t < 0.32:
			return keyed([[0.0, idle], [0.2, wind], [0.32, wind]], t)
		var u := t - 0.32
		var lunge := {"spine": Vector3(10, 0, 0), "hips_pos": Vector3(0, -0.05, 0.08)}
		return blend(off(sample("attack3", u), lunge, 1.0 - u / a3_len), wind, maxf(0.0, 1.0 - u / 0.06)))
	for pair in [["air_attack1", "attack1"], ["air_attack2", "attack3"]]:
		var clip: String = pair[1]
		bake(pair[0], src.get_animation(clip).length, false, func(t: float) -> Dictionary: return mask(rise, sample(clip, t)))
	var plunge := off(rise, {"upper_arm.L": Vector3(-150, 0, 10), "forearm.L": Vector3(0, -30, 0), "spine": Vector3(-10, 0, 0)})
	var slam := off(off(idle, crouch(40)), {"upper_arm.L": Vector3(-30, 0, 5), "spine": Vector3(25, 0, 0), "head": Vector3(-10, 0, 0)})
	bake("air_slam", 0.6, false, func(t: float) -> Dictionary: return keyed([[0.0, rise], [0.12, plunge], [0.3, plunge], [0.38, slam], [0.6, slam]], t))
	# QTE finisher: charge -> dash strike -> final sweep, cross-faded.
	var seg := [["charge", 0.0, 0.45], ["dash_attack", 0.0, 0.6], ["attack3", 0.0, a3_len], ["spell", 0.3, 0.9]]
	var total := 0.0
	for s in seg:
		total += s[2] - s[1]
	bake("qte_finisher", total, false, func(t: float) -> Dictionary:
		var acc := 0.0
		for i in seg.size():
			var s: Array = seg[i]
			var d: float = s[2] - s[1]
			if t <= acc + d or i == seg.size() - 1:
				var p := sample(s[0], s[1] + (t - acc))
				if i > 0 and t - acc < 0.08:
					var prev: Array = seg[i - 1]
					p = blend(sample(prev[0], prev[2]), p, smooth((t - acc) / 0.08))
				return p
			acc += d
		return idle)

	# ---- stun / recovery --------------------------------------------------
	var daze := off(idle, merge(crouch(12), {"spine": Vector3(18, 0, 0), "head": Vector3(22, 0, 0),
			"upper_arm.L": Vector3(8, 0, -8), "upper_arm.R": Vector3(8, 0, 8)}))
	bake("stagger", 1.0, true, func(t: float) -> Dictionary:
		var s := sin(t * TAU)
		return off(daze, {"hips": Vector3(0, 0, 4 * s), "spine": Vector3(0, 0, -5 * s), "head": Vector3(0, 12 * s, 6 * s)}))
	var brace := off(idle, merge(crouch(30), {"upper_arm.L": Vector3(-20, 0, 50), "upper_arm.R": Vector3(-20, 0, -50), "head": Vector3(-10, 0, 0)}))
	bake("tech_recover", 0.4, false, func(t: float) -> Dictionary: return keyed([[0.0, daze], [0.12, brace], [0.4, idle]], t))

	# ---- overload ---------------------------------------------------------
	var gather := off(idle, merge(crouch(30), {"spine": Vector3(18, 0, 0), "head": Vector3(20, 0, 0),
			"upper_arm.L": Vector3(-60, 0, -10), "upper_arm.R": Vector3(-60, 0, 10),
			"forearm.L": Vector3(0, -95, 0), "forearm.R": Vector3(0, 95, 0)}))
	var release := off(idle, {"spine": Vector3(-14, 0, 0), "chest": Vector3(-8, 0, 0), "head": Vector3(-22, 0, 0),
			"upper_arm.L": Vector3(-25, 0, 105), "upper_arm.R": Vector3(-25, 0, -105),
			"thigh.L": Vector3(0, 0, 9), "thigh.R": Vector3(0, 0, -9), "hips_pos": Vector3(0, 0.05, 0)})
	bake("burst", 1.3, false, func(t: float) -> Dictionary: return keyed([[0.0, idle], [0.35, gather], [0.5, gather], [0.62, release], [1.0, release], [1.3, idle]], t))

	# ---- items & interaction ---------------------------------------------
	var reach_low := off(idle, merge(crouch(48), {"spine": Vector3(32, 0, 0), "head": Vector3(8, 0, 0),
			"upper_arm.R": Vector3(-35, 0, 5), "forearm.R": Vector3(0, 15, 0)}))
	bake("pickup", 0.85, false, func(t: float) -> Dictionary: return keyed([[0.0, idle], [0.3, reach_low], [0.48, reach_low], [0.85, idle]], t))
	var reach := off(idle, {"spine": Vector3(10, 0, 0), "upper_arm.L": Vector3(-85, 0, -15), "upper_arm.R": Vector3(-85, 0, 15),
			"forearm.L": Vector3(0, -15, 0), "forearm.R": Vector3(0, 15, 0)})
	var pull := off(idle, merge(crouch(18), {"spine": Vector3(18, 0, 0), "upper_arm.L": Vector3(-35, 0, -12),
			"upper_arm.R": Vector3(-35, 0, 12), "forearm.L": Vector3(0, -30, 0), "forearm.R": Vector3(0, 30, 0)}))
	bake("interact", 0.95, false, func(t: float) -> Dictionary: return keyed([[0.0, idle], [0.28, reach], [0.4, reach], [0.62, pull], [0.95, idle]], t))
