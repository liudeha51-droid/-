class_name BulletManager
extends Node3D
## Danmaku in 3D. Bullets are plain mesh nodes updated here with manual
## distance checks (no physics bodies), which keeps hundreds on screen cheap.
##
## Hostile bullets hit the player on a vertical cylinder test and award a
## graze when they pass close without hitting. Player shots (ofuda, spell
## orbs) can home in on a target.

const PLAYER_HIT_RADIUS := 0.32
const GRAZE_RADIUS := 1.15
const MAX_RANGE := 70.0


class Bullet:
	var node: MeshInstance3D
	var vel := Vector3.ZERO
	var radius := 0.2
	var damage := 10.0
	var life := 8.0
	var hostile := true
	var grazed := false
	var tag := ""
	var homing: Node3D
	var accel := Vector3.ZERO
	var frozen := false
	var color := Color.WHITE
	var shatter_on_ground := false
	var dead := false


var bullets: Array[Bullet] = []
var player: Player
var boss: Node3D
var _orb_mesh: SphereMesh
var _icicle_mesh: CylinderMesh
var _ofuda_mesh: BoxMesh
var _big_orb_mesh: SphereMesh


func _ready() -> void:
	_orb_mesh = MeshKit.sphere(1.0, -1.0, 12)
	_icicle_mesh = MeshKit.cylinder(0.0, 0.14, 0.9, 8)
	_ofuda_mesh = MeshKit.box(Vector3(0.14, 0.02, 0.32))
	_big_orb_mesh = MeshKit.sphere(1.0, -1.0, 16)


func count_hostile() -> int:
	var n := 0
	for b in bullets:
		if b.hostile:
			n += 1
	return n


func spawn_orb(pos: Vector3, vel: Vector3, color: Color, radius := 0.22, damage := 12.0, tag := "") -> Bullet:
	var b := _make(_orb_mesh, pos, vel, color, radius, damage, true)
	b.node.scale = Vector3.ONE * radius
	b.tag = tag
	return b


func spawn_icicle(pos: Vector3, vel: Vector3, color := Color(0.6, 0.9, 1.0), damage := 14.0, tag := "") -> Bullet:
	var b := _make(_icicle_mesh, pos, vel, color, 0.2, damage, true)
	b.tag = tag
	_orient(b)
	return b


func spawn_player_shot(pos: Vector3, vel: Vector3, damage: float, homing: Node3D = null, color := Color(1.0, 0.25, 0.3), radius := 0.18) -> Bullet:
	var mesh: Mesh = _ofuda_mesh if radius < 0.3 else _big_orb_mesh
	var b := _make(mesh, pos, vel, color, radius, damage, false)
	if radius >= 0.3:
		b.node.scale = Vector3.ONE * radius
	b.homing = homing
	b.life = 4.0
	_orient_flat(b)
	return b


func _make(mesh: Mesh, pos: Vector3, vel: Vector3, color: Color, radius: float, damage: float, hostile: bool) -> Bullet:
	var b := Bullet.new()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = MeshKit.glow(color, 3.0)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.global_position = pos
	b.node = mi
	b.vel = vel
	b.radius = radius
	b.damage = damage
	b.hostile = hostile
	b.color = color
	bullets.append(b)
	return b


func _physics_process(delta: float) -> void:
	var ppos := player.global_position if player else Vector3(0, -1000, 0)
	var player_dead := player == null or player.is_dead()
	# Iterate a snapshot: hits can trigger boss phase changes that clear bullets.
	for b: Bullet in bullets.duplicate():
		if b.dead:
			continue
		b.life -= delta
		if not b.frozen:
			b.vel += b.accel * delta
			if b.homing and is_instance_valid(b.homing):
				var goal := b.homing.global_position + Vector3(0, 1.1, 0)
				var want := (goal - b.node.global_position).normalized() * maxf(b.vel.length(), 12.0)
				b.vel = b.vel.lerp(want, 1.0 - exp(-4.0 * delta))
				_orient_flat(b)
			b.node.global_position += b.vel * delta
		var p := b.node.global_position
		if b.life <= 0.0 or p.y < -0.5 or p.distance_squared_to(ppos) > MAX_RANGE * MAX_RANGE:
			_remove(b)
			continue
		if b.shatter_on_ground and p.y <= 0.1:
			Fx.burst(self, p, b.color, 8, 3.0, 0.3, 0.06)
			Sfx.play("shatter", 0.2, -18.0)
			_remove(b)
			continue
		if b.hostile:
			if player_dead:
				continue
			var flat := Vector2(p.x - ppos.x, p.z - ppos.z).length()
			var dy := p.y - ppos.y
			if flat < PLAYER_HIT_RADIUS + b.radius and dy > -0.2 and dy < 1.9:
				if player.take_damage(b.damage, b.vel):
					Fx.burst(self, p, b.color, 12, 4.0)
					_remove(b)
					continue
			if not b.grazed and flat < GRAZE_RADIUS + b.radius and dy > -0.8 and dy < 2.5:
				b.grazed = true
				player.on_graze(p)
		elif boss and is_instance_valid(boss):
			var hit_at := boss.global_position + Vector3(0, 1.1, 0)
			if p.distance_to(hit_at) < 0.9 + b.radius:
				if boss.take_damage(b.damage, player):
					Sfx.play("hit", 0.2, -12.0)
				Fx.burst(self, p, b.color, 10, 3.0)
				_remove(b)
				continue


func _remove(b: Bullet) -> void:
	if b.dead:
		return
	b.dead = true
	bullets.erase(b)
	if is_instance_valid(b.node):
		b.node.queue_free()


func clear_all() -> void:
	for b in bullets:
		if is_instance_valid(b.node):
			b.node.queue_free()
	bullets.clear()


## Removes hostile bullets. With `sparkle` each leaves a small burst (bombs, phase change).
func clear_hostile(sparkle := false) -> void:
	for b in bullets.duplicate():
		if b.hostile:
			if sparkle:
				Fx.burst(self, b.node.global_position, b.color, 3, 2.0, 0.3, 0.05)
			_remove(b)


## Perfect Freeze: stop every bullet carrying `tag` and turn it white.
func freeze_tag(tag: String) -> void:
	for b in bullets:
		if b.tag == tag:
			b.frozen = true
			b.node.material_override = MeshKit.glow(Color(0.8, 0.95, 1.0), 1.4)


## Release frozen bullets in random directions at the given speed range.
func release_tag(tag: String, rng: RandomNumberGenerator, min_speed: float, max_speed: float) -> void:
	for b in bullets:
		if b.tag == tag and b.frozen:
			b.frozen = false
			var a := rng.randf() * TAU
			b.vel = Vector3(cos(a), 0, sin(a)) * rng.randf_range(min_speed, max_speed)
			b.life = 6.0


func _orient(b: Bullet) -> void:
	var dir := b.vel.normalized()
	if dir.length() < 0.5:
		return
	if dir.dot(Vector3.UP) < -0.999:
		b.node.basis = Basis(Vector3.RIGHT, PI)
	elif dir.dot(Vector3.UP) > 0.999:
		b.node.basis = Basis.IDENTITY
	else:
		b.node.basis = Basis(Quaternion(Vector3.UP, dir))


func _orient_flat(b: Bullet) -> void:
	var dir := b.vel.normalized()
	if absf(dir.dot(Vector3.UP)) > 0.99 or dir.length() < 0.5:
		return
	var s := b.node.scale
	b.node.basis = Basis.looking_at(dir, Vector3.UP).scaled(s)
