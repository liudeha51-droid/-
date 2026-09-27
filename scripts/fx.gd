class_name Fx
extends RefCounted
## One-shot particle bursts (hits, grazes, shatters).


static func burst(parent: Node, pos: Vector3, color: Color, amount := 16, speed := 4.0, lifetime := 0.45, size := 0.08) -> void:
	if parent == null or not parent.is_inside_tree():
		return
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.emitting = false
	p.amount = amount
	p.lifetime = lifetime
	p.explosiveness = 0.95
	p.direction = Vector3.UP
	p.spread = 180.0
	p.initial_velocity_min = speed * 0.5
	p.initial_velocity_max = speed
	p.gravity = Vector3(0, -6, 0)
	p.scale_amount_min = 0.6
	p.scale_amount_max = 1.2
	var spark := MeshKit.sphere(size * 0.5, -1.0, 6)
	spark.material = MeshKit.glow(color, 4.0)
	p.mesh = spark
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	p.get_tree().create_timer(lifetime + 0.3).timeout.connect(p.queue_free)
