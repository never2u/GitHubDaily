class_name Hud
extends CanvasLayer
## 전투 HUD: 체력, 데나리우스, 웨이브/타이머, 얼티밋 게이지.

var waves: WaveManager

var _hp_bar: ProgressBar
var _hp_label: Label
var _coin_label: Label
var _wave_label: Label
var _timer_label: Label
var _ult_bar: ProgressBar
var _ult_label: Label


func _ready() -> void:
	_build()
	EventBus.player_hp_changed.connect(_on_hp_changed)
	EventBus.coins_changed.connect(_on_coins_changed)
	EventBus.ultimate_charge_changed.connect(_on_ult_changed)
	_on_coins_changed(RunState.coins)


func _process(_delta: float) -> void:
	if waves == null:
		return
	_wave_label.text = "웨이브 %d" % waves.wave
	_timer_label.text = "%d" % ceili(waves.time_left)


func _build() -> void:
	var top_left := VBoxContainer.new()
	top_left.position = Vector2(8, 8)
	add_child(top_left)
	_hp_bar = UiKit.make_bar(Color(0.85, 0.2, 0.2), Vector2(120, 10))
	top_left.add_child(_hp_bar)
	_hp_label = _make_label(12)
	top_left.add_child(_hp_label)
	_coin_label = _make_label(12)
	top_left.add_child(_coin_label)

	var top := VBoxContainer.new()
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.offset_top = 4
	add_child(top)
	_wave_label = _make_label(14)
	_wave_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	top.add_child(_wave_label)
	_timer_label = _make_label(20)
	_timer_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	top.add_child(_timer_label)

	var bottom := VBoxContainer.new()
	bottom.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom.offset_top = -34
	bottom.offset_bottom = -6
	add_child(bottom)
	_ult_label = _make_label(12)
	_ult_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bottom.add_child(_ult_label)
	var bar_center := CenterContainer.new()
	bottom.add_child(bar_center)
	_ult_bar = UiKit.make_bar(Color(0.3, 0.75, 1.0), Vector2(160, 8))
	bar_center.add_child(_ult_bar)


func _make_label(font_size: int) -> Label:
	var label := Label.new()
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 4)
	return label


func _on_hp_changed(hp: float, max_hp: float) -> void:
	_hp_bar.max_value = max_hp
	_hp_bar.value = hp
	_hp_label.text = "HP %d / %d" % [ceili(hp), ceili(max_hp)]


func _on_coins_changed(total: int) -> void:
	_coin_label.text = "데나리우스 %d" % total


func _on_ult_changed(ratio: float) -> void:
	_ult_bar.value = ratio * 100.0
	if ratio >= 1.0:
		_ult_label.text = "얼티밋 준비! [Space / RB]"
		_ult_label.modulate = Color(1.0, 0.9, 0.3)
	else:
		_ult_label.text = "얼티밋 %d%%" % int(ratio * 100.0)
		_ult_label.modulate = Color.WHITE
