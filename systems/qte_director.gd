extends Node
## Quick Time Event runner (autoload "QTE").
##
## A QTE is a sequence of button prompts, each of which must be pressed within
## `window` seconds of *real* time (the director keeps counting while the game
## runs in slow motion). A wrong button or a timeout fails the whole sequence.

signal started(steps: Array)
signal step_changed(index: int, action: StringName, window: float)
signal finished(success: bool)

const PROMPT_ACTIONS: Array[StringName] = [&"attack_light", &"attack_heavy", &"jump", &"dodge"]

var active := false
var steps: Array[StringName] = []
var index := 0
var window := 1.0
var time_left := 0.0
var _on_done := Callable()
var _restore_time_scale := 1.0
var _grace := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


## Starts a QTE. `on_done` is called with the success flag after `finished`.
func begin(sequence: Array, step_window := 1.0, on_done := Callable(), slow_motion := 1.0) -> bool:
	if active or sequence.is_empty():
		return false
	active = true
	steps.assign(sequence)
	index = 0
	window = step_window
	time_left = step_window
	_on_done = on_done
	_restore_time_scale = Engine.time_scale
	Engine.time_scale = slow_motion
	# Ignore buttons still held from whatever triggered the QTE.
	_grace = 2
	started.emit(steps)
	step_changed.emit(0, steps[0], window)
	return true


func random_sequence(length: int) -> Array[StringName]:
	var out: Array[StringName] = []
	for i in length:
		out.append(PROMPT_ACTIONS.pick_random())
	return out


func current_action() -> StringName:
	return steps[index] if active else &""


func cancel() -> void:
	if active:
		_finish(false)


func _process(delta: float) -> void:
	if not active:
		return
	if _grace > 0:
		_grace -= 1
		return
	for a in PROMPT_ACTIONS:
		if Input.is_action_just_pressed(a):
			if a != steps[index]:
				_finish(false)
				return
			index += 1
			if index >= steps.size():
				_finish(true)
				return
			time_left = window
			step_changed.emit(index, steps[index], window)
			return
	# `delta` is scaled by Engine.time_scale; windows run in real time.
	time_left -= delta / maxf(Engine.time_scale, 0.001)
	if time_left <= 0.0:
		_finish(false)


func _finish(success: bool) -> void:
	active = false
	Engine.time_scale = _restore_time_scale
	finished.emit(success)
	var cb := _on_done
	_on_done = Callable()
	if cb.is_valid():
		cb.call(success)
