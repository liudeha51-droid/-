class_name InputSetup
extends RefCounted
## Registers the input map in code so bindings live in one readable place.
## Keyboard + mouse and a standard gamepad (Xbox layout) are both supported.


static func ensure_actions() -> void:
	_keys("move_forward", [KEY_W, KEY_UP])
	_keys("move_back", [KEY_S, KEY_DOWN])
	_keys("move_left", [KEY_A, KEY_LEFT])
	_keys("move_right", [KEY_D, KEY_RIGHT])
	_axis("move_forward", JOY_AXIS_LEFT_Y, -1.0)
	_axis("move_back", JOY_AXIS_LEFT_Y, 1.0)
	_axis("move_left", JOY_AXIS_LEFT_X, -1.0)
	_axis("move_right", JOY_AXIS_LEFT_X, 1.0)

	_axis("look_left", JOY_AXIS_RIGHT_X, -1.0)
	_axis("look_right", JOY_AXIS_RIGHT_X, 1.0)
	_axis("look_up", JOY_AXIS_RIGHT_Y, -1.0)
	_axis("look_down", JOY_AXIS_RIGHT_Y, 1.0)

	_keys("dodge", [KEY_SPACE])
	_button("dodge", JOY_BUTTON_B)
	_keys("sprint", [KEY_SHIFT])
	_button("sprint", JOY_BUTTON_A)

	_keys("attack", [KEY_J])
	_mouse("attack", MOUSE_BUTTON_LEFT)
	_button("attack", JOY_BUTTON_RIGHT_SHOULDER)

	_keys("ofuda", [KEY_K])
	_mouse("ofuda", MOUSE_BUTTON_RIGHT)
	_axis("ofuda", JOY_AXIS_TRIGGER_RIGHT, 1.0)

	_keys("spell_card", [KEY_X])
	_button("spell_card", JOY_BUTTON_LEFT_SHOULDER)

	_keys("lock_on", [KEY_Q, KEY_TAB])
	_mouse("lock_on", MOUSE_BUTTON_MIDDLE)
	_button("lock_on", JOY_BUTTON_RIGHT_STICK)

	_keys("heal", [KEY_R])
	_button("heal", JOY_BUTTON_X)

	_keys("interact", [KEY_F, KEY_E])
	_button("interact", JOY_BUTTON_Y)

	_keys("pause", [KEY_ESCAPE])
	_button("pause", JOY_BUTTON_START)


static func _ensure(action: String) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.2)


static func _keys(action: String, keys: Array) -> void:
	_ensure(action)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)


static func _mouse(action: String, button: MouseButton) -> void:
	_ensure(action)
	var e := InputEventMouseButton.new()
	e.button_index = button
	InputMap.action_add_event(action, e)


static func _button(action: String, button: JoyButton) -> void:
	_ensure(action)
	var e := InputEventJoypadButton.new()
	e.button_index = button
	InputMap.action_add_event(action, e)


static func _axis(action: String, axis: JoyAxis, value: float) -> void:
	_ensure(action)
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = value
	InputMap.action_add_event(action, e)
