extends Node
## Registers the default input map at startup (keyboard/mouse + gamepad).
## Actions already defined in Project Settings are left untouched, so
## bindings can be overridden there without editing this file.

const DEADZONE := 0.2


func _enter_tree() -> void:
	var map := {
		# Movement / camera
		&"move_forward": [_key(KEY_W), _axis(JOY_AXIS_LEFT_Y, -1.0)],
		&"move_back": [_key(KEY_S), _axis(JOY_AXIS_LEFT_Y, 1.0)],
		&"move_left": [_key(KEY_A), _axis(JOY_AXIS_LEFT_X, -1.0)],
		&"move_right": [_key(KEY_D), _axis(JOY_AXIS_LEFT_X, 1.0)],
		&"camera_left": [_axis(JOY_AXIS_RIGHT_X, -1.0)],
		&"camera_right": [_axis(JOY_AXIS_RIGHT_X, 1.0)],
		&"camera_up": [_axis(JOY_AXIS_RIGHT_Y, -1.0)],
		&"camera_down": [_axis(JOY_AXIS_RIGHT_Y, 1.0)],
		&"walk_toggle": [_key(KEY_ALT), _joy(JOY_BUTTON_LEFT_STICK)],
		&"slow_walk": [_key(KEY_CTRL)],
		# Basic actions
		&"jump": [_key(KEY_SPACE), _joy(JOY_BUTTON_A)],
		&"dodge": [_key(KEY_SHIFT), _joy(JOY_BUTTON_B)],
		&"dash": [_key(KEY_Q), _joy(JOY_BUTTON_RIGHT_SHOULDER)],
		&"attack_light": [_mouse(MOUSE_BUTTON_LEFT), _key(KEY_J), _joy(JOY_BUTTON_X)],
		&"attack_heavy": [_mouse(MOUSE_BUTTON_RIGHT), _key(KEY_K), _joy(JOY_BUTTON_Y)],
		&"guard": [_key(KEY_F), _key(KEY_L), _joy(JOY_BUTTON_LEFT_SHOULDER)],
		# System / special
		&"burst": [_key(KEY_V), _joy(JOY_BUTTON_RIGHT_STICK)],
		&"interact": [_key(KEY_E), _joy(JOY_BUTTON_DPAD_UP)],
		&"use_item": [_key(KEY_R), _joy(JOY_BUTTON_DPAD_DOWN)],
		&"toggle_help": [_key(KEY_F1), _joy(JOY_BUTTON_BACK)],
	}
	for action in map:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action, DEADZONE)
		for ev in map[action]:
			InputMap.action_add_event(action, ev)


## Human-readable binding for on-screen prompts (keyboard first).
static func describe(action: StringName) -> String:
	var names := {
		&"attack_light": "LMB / J", &"attack_heavy": "RMB / K", &"jump": "Space",
		&"dodge": "Shift", &"dash": "Q", &"guard": "F", &"interact": "E", &"use_item": "R", &"burst": "V",
	}
	return names.get(action, String(action))


func _key(code: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	return e


func _mouse(button: MouseButton) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.button_index = button
	return e


func _joy(button: JoyButton) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.button_index = button
	return e


func _axis(axis: JoyAxis, value: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = value
	return e
