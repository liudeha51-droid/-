class_name Hud
extends CanvasLayer
## Minimal Souls-style HUD: bars top-left, boss bar bottom, spell card banner
## top-right (Touhou style), and big centre text for death/victory.

var player: Player
var boss: BossCirno

var _hp: ProgressBar
var _st: ProgressBar
var _sp: ProgressBar
var _heals: Label
var _boss_box: VBoxContainer
var _boss_bar: ProgressBar
var _boss_name: Label
var _banner: PanelContainer
var _banner_jp: Label
var _banner_en: Label
var _center: Label
var _center_sub: Label
var _prompt: Label
var _help: Label
var _lock: Label


func _ready() -> void:
	name = "Hud"
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	var bars := VBoxContainer.new()
	bars.position = Vector2(32, 28)
	bars.add_theme_constant_override("separation", 6)
	root.add_child(bars)
	_hp = _bar(bars, Color(0.75, 0.1, 0.12), 360)
	_st = _bar(bars, Color(0.25, 0.7, 0.3), 300)
	_sp = _bar(bars, Color(0.95, 0.75, 0.2), 240)
	_heals = _label(bars, 18, Color(0.95, 0.9, 0.8))

	_boss_box = VBoxContainer.new()
	_boss_box.visible = false
	root.add_child(_boss_box)
	_place(_boss_box, Control.PRESET_CENTER_BOTTOM, Vector2(-450, -110), Vector2(900, 0))
	_boss_name = _label(_boss_box, 22, Color(0.9, 0.95, 1.0))
	_boss_name.text = "氷の妖精 チルノ  ·  Cirno, the Ice Fairy"
	_boss_bar = _bar(_boss_box, Color(0.55, 0.1, 0.12), 900, 14)

	_banner = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.02, 0.03, 0.08, 0.72)
	sb.border_width_bottom = 2
	sb.border_color = Color(0.45, 0.75, 1.0)
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	_banner.add_theme_stylebox_override("panel", sb)
	var bv := VBoxContainer.new()
	_banner.add_child(bv)
	_banner_jp = _label(bv, 26, Color.WHITE)
	_banner_en = _label(bv, 16, Color(0.8, 0.85, 0.95))
	_banner_jp.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_banner_en.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_banner.modulate.a = 0.0
	root.add_child(_banner)
	_place(_banner, Control.PRESET_TOP_RIGHT, Vector2(-560, 36), Vector2(520, 0))

	var center := VBoxContainer.new()
	root.add_child(center)
	_place(center, Control.PRESET_CENTER, Vector2(-500, -80), Vector2(1000, 0))
	_center = _label(center, 72, Color(0.85, 0.1, 0.1))
	_center.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_center_sub = _label(center, 22, Color(0.9, 0.9, 0.9))
	_center_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center.modulate.a = 0.0
	center.name = "Center"

	_prompt = _label(root, 22, Color(1, 0.95, 0.8))
	_place(_prompt, Control.PRESET_CENTER_BOTTOM, Vector2(-300, -190), Vector2(600, 0))
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER

	_lock = _label(root, 16, Color(1, 0.8, 0.4))
	_lock.custom_minimum_size = Vector2(40, 0)
	_lock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_lock.text = "◆"
	_lock.visible = false

	_help = _label(root, 15, Color(0.85, 0.85, 0.9, 0.85))
	_place(_help, Control.PRESET_BOTTOM_LEFT, Vector2(32, -110), Vector2(600, 0))
	_help.text = "WASD move · Mouse camera · Shift sprint · Space dodge\nLMB attack (combo) · RMB ofuda · X spell card (full Spirit)\nQ lock-on · R heal · F pray at shrine · Esc release mouse\nGraze danmaku to restore Stamina and Spirit."


func _process(_delta: float) -> void:
	if player:
		_hp.max_value = player.max_hp
		_hp.value = player.hp
		_st.max_value = player.max_stamina
		_st.value = maxf(player.stamina, 0.0)
		_sp.max_value = player.max_spirit
		_sp.value = player.spirit
		var spell_ready := "  ·  SPELL CARD READY [X]" if player.spirit >= player.max_spirit else ""
		_heals.text = "Gourd ×%d%s" % [player.heals, spell_ready]
		_update_lock_marker()
	if boss and _boss_box.visible:
		_boss_bar.max_value = BossCirno.MAX_HP
		_boss_bar.value = lerpf(_boss_bar.value, boss.hp, 0.2)


## Souls-style lock-on dot drawn over the target's chest.
func _update_lock_marker() -> void:
	var target := player.lock_target
	var cam := get_viewport().get_camera_3d()
	_lock.visible = target != null and cam != null
	if _lock.visible:
		var at := target.global_position + Vector3(0, 1.2, 0)
		_lock.visible = not cam.is_position_behind(at)
		_lock.position = cam.unproject_position(at) - Vector2(20, 14)


func show_boss(on: bool) -> void:
	_boss_box.visible = on
	if on and boss:
		_boss_bar.value = boss.hp


func set_prompt(text: String) -> void:
	_prompt.text = text


func hide_help() -> void:
	create_tween().tween_property(_help, "modulate:a", 0.0, 1.5)


## Spell card declaration banner.
func banner(jp: String, en: String, accent: Color) -> void:
	_banner_jp.text = jp
	_banner_en.text = en
	(_banner.get_theme_stylebox("panel") as StyleBoxFlat).border_color = accent
	var tw := create_tween()
	_banner.modulate.a = 0.0
	tw.tween_property(_banner, "modulate:a", 1.0, 0.25)
	tw.tween_interval(3.0)
	tw.tween_property(_banner, "modulate:a", 0.0, 0.8)


func big_message(title: String, sub: String, color: Color, hold := 3.0) -> void:
	_center.text = title
	_center.add_theme_color_override("font_color", color)
	_center_sub.text = sub
	var c := _center.get_parent() as Control
	var tw := create_tween()
	c.modulate.a = 0.0
	tw.tween_property(c, "modulate:a", 1.0, 0.8)
	tw.tween_interval(hold)
	tw.tween_property(c, "modulate:a", 0.0, 1.0)


## Anchors `c` to `preset` and offsets it from that anchor point.
func _place(c: Control, preset: Control.LayoutPreset, offset: Vector2, min_size: Vector2) -> void:
	c.custom_minimum_size = min_size
	c.set_anchors_preset(preset)
	c.offset_left = offset.x
	c.offset_top = offset.y
	c.offset_right = offset.x + min_size.x
	c.offset_bottom = offset.y + min_size.y


func _bar(parent: Control, color: Color, width: float, height := 12.0) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.custom_minimum_size = Vector2(width, height)
	bar.show_percentage = false
	bar.value = 100
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.03, 0.03, 0.05, 0.75)
	bg.border_width_left = 1
	bg.border_width_right = 1
	bg.border_width_top = 1
	bg.border_width_bottom = 1
	bg.border_color = Color(0.6, 0.55, 0.45, 0.6)
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	bar.add_theme_stylebox_override("background", bg)
	bar.add_theme_stylebox_override("fill", fill)
	parent.add_child(bar)
	return bar


func _label(parent: Control, size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	parent.add_child(l)
	return l
