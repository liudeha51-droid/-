class_name HitInfo
extends RefCounted
## Describes one attack landing on a target. Targets implement
## `receive_hit(info: HitInfo) -> HitInfo.Result`.

enum Result { HIT, BLOCKED, PARRIED, EVADED, IGNORED }

var damage := 10.0
var knockback := 3.0
## Breaks enemy posture; a broken posture opens a QTE finisher.
var poise_damage := 10.0
var guard_damage := 15.0
## Heavy hits stagger instead of flinching and ignore light super armor.
var heavy := false
var unblockable := false
var parryable := true
var source: Node3D


func _init(p_source: Node3D = null, p_damage := 10.0, p_knockback := 3.0) -> void:
	source = p_source
	damage = p_damage
	knockback = p_knockback


## Horizontal direction from the attacker to `target` (used for knockback).
func push_direction(target: Node3D) -> Vector3:
	if source == null:
		return Vector3.ZERO
	var d := target.global_position - source.global_position
	d.y = 0.0
	return d.normalized() if d.length() > 0.001 else Vector3.ZERO
