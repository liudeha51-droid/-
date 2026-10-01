class_name Interactable
extends Node3D
## Something the player can use with the "interact" button.
##
## The player plays `interact_anim` and calls `interact()` once the animation
## reaches `effect_time`, so the effect lines up with the hand motion.

signal interacted(player: Node)

@export var prompt := "Interact"
@export var radius := 1.7
@export var interact_anim: StringName = &"interact"
@export var effect_time := 0.45
@export var enabled := true


func _enter_tree() -> void:
	add_to_group(&"interactable")


func can_interact(_player: Node) -> bool:
	return enabled


func interact(player: Node) -> void:
	interacted.emit(player)
