class_name Hud
extends CanvasLayer
## Health / guard / burst bars, item count, interaction prompt, QTE prompts
## and a controls overlay (F1).

const HELP := """MOVE  WASD / left stick    (Alt: walk toggle, Ctrl: slow walk)
JUMP  Space / A   (again in the air: double jump, hold while falling: glide)
DODGE Shift / B   (roll with i-frames; in the air: air dash)
DASH  Q / RB      (light attack during a dash: dash attack)
LIGHT LMB / J / X (3-hit combo; in the air: aerial combo)
HEAVY RMB / K / Y (tap: heavy, hold: charge; in the air: plunge)
GUARD F / LB      (hold to block, tap just before a hit to parry)
BURST V / R3      (when the gauge is full)
INTERACT E   ITEM R   HELP F1
Dodge, jump or dash cancel an attack's recovery."""

var player: Player
var _hp := ProgressBar.new()
var _guard := ProgressBar.new()
var _burst := ProgressBar.new()
var _items := Label.new()
var _state := Label.new()
var _prompt := Label.new()
var _qte_panel := PanelContainer.new()
var _qte_label := Label.new()
var _qte_timer := ProgressBar.new()
var _help := Label.new()
var _flash := Label.new()


func _ready() -> void:
	var box := VBoxContainer.new()
	box.position = Vector2(24, 20)
	box.custom_minimum_size = Vector2(320, 0)
	add_child(box)
	for pair in [[_hp, Color(0.85, 0.15, 0.15), "HP"], [_guard, Color(0.6, 0.75, 0.95), "GUARD"],
			[_burst, Color(1.0, 0.65, 0.15), "BURST"]]:
		var row := HBoxContainer.new()
		var lbl := Label.new()
		lbl.text = pair[2]
		lbl.custom_minimum_size.x = 64
		row.add_child(lbl)
		var bar: ProgressBar = pair[0]
		bar.custom_minimum_size = Vector2(240, 16)
		bar.show_percentage = false
		var fill := StyleBoxFlat.new()
		fill.bg_color = pair[1]
		bar.add_theme_stylebox_override("fill", fill)
		row.add_child(bar)
		box.add_child(row)
	box.add_child(_items)
	box.add_child(_state)
	_state.modulate = Color(1, 1, 1, 0.6)

	_prompt.anchor_left = 0.5
	_prompt.anchor_right = 0.5
	_prompt.anchor_top = 0.72
	_prompt.offset_left = -200
	_prompt.offset_right = 200
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt.add_theme_font_size_override("font_size", 22)
	add_child(_prompt)

	_qte_panel.anchor_left = 0.5
	_qte_panel.anchor_right = 0.5
	_qte_panel.anchor_top = 0.4
	_qte_panel.offset_left = -170
	_qte_panel.offset_right = 170
	var qbox := VBoxContainer.new()
	_qte_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_qte_label.add_theme_font_size_override("font_size", 34)
	_qte_timer.show_percentage = false
	_qte_timer.custom_minimum_size.y = 10
	qbox.add_child(_qte_label)
	qbox.add_child(_qte_timer)
	_qte_panel.add_child(qbox)
	_qte_panel.visible = false
	add_child(_qte_panel)

	_flash.anchor_left = 0.5
	_flash.anchor_right = 0.5
	_flash.anchor_top = 0.3
	_flash.offset_left = -200
	_flash.offset_right = 200
	_flash.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_flash.add_theme_font_size_override("font_size", 30)
	add_child(_flash)

	_help.text = HELP
	_help.anchor_left = 1.0
	_help.anchor_right = 1.0
	_help.offset_left = -560
	_help.offset_top = 20
	_help.add_theme_font_size_override("font_size", 14)
	_help.modulate = Color(1, 1, 1, 0.85)
	add_child(_help)

	QTE.started.connect(func(_steps: Array) -> void: _qte_panel.visible = true)
	QTE.step_changed.connect(_on_qte_step)
	QTE.finished.connect(_on_qte_finished)


func bind(p: Player) -> void:
	player = p
	p.health_changed.connect(func(v: float, m: float) -> void: _set_bar(_hp, v, m))
	p.guard_changed.connect(func(v: float, m: float) -> void: _set_bar(_guard, v, m))
	p.burst_changed.connect(_on_burst)
	p.items_changed.connect(_on_items)
	p.prompt_changed.connect(func(t: String) -> void: _prompt.text = t)
	p.perfect_evade.connect(func() -> void: _show_flash("Perfect evade!", Color(0.6, 0.9, 1.0)))
	_set_bar(_hp, p.hp, p.max_hp)
	_set_bar(_guard, p.guard_points, p.max_guard)
	_on_burst(p.burst_meter, p.burst_active)
	_on_items(p.items)


func _process(delta: float) -> void:
	if Input.is_action_just_pressed(&"toggle_help"):
		_help.visible = not _help.visible
	if player:
		var extra := (" / " + player.attack_id) if player.attack_id != "" else ""
		_state.text = "%s%s  [%s]%s" % [player.state_name(), extra, player.current_anim(),
				"  WALK" if player.walk_toggled else ""]
	if QTE.active:
		_qte_timer.value = 100.0 * QTE.time_left / QTE.window
	_flash.modulate.a = maxf(0.0, _flash.modulate.a - delta * 0.8)


func _set_bar(bar: ProgressBar, value: float, max_value: float) -> void:
	bar.max_value = max_value
	bar.value = value


func _on_burst(value: float, active: bool) -> void:
	_set_bar(_burst, value, 100.0)
	_burst.modulate = Color(1.6, 1.3, 1.0) if active or value >= 100.0 else Color.WHITE
	if active and value >= 99.0:
		_show_flash("BURST!", Color(1.0, 0.5, 0.3))


func _on_items(items: Dictionary) -> void:
	_items.text = "Healing charms: %d   [%s] use" % [items.get("healing_charm", 0), GameInput.describe(&"use_item")]


func _on_qte_step(_index: int, action: StringName, _window: float) -> void:
	_qte_label.text = "Press  %s" % GameInput.describe(action)


func _on_qte_finished(success: bool) -> void:
	_qte_panel.visible = false
	_show_flash("QTE success!" if success else "QTE failed", Color(0.5, 1.0, 0.5) if success else Color(1.0, 0.4, 0.4))


func _show_flash(text: String, color: Color) -> void:
	_flash.text = text
	_flash.modulate = color
