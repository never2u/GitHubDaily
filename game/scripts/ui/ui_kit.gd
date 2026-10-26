class_name UiKit
extends RefCounted
## 코드로 UI 를 만드는 헬퍼. 모든 대화상자는 게임패드 포커스 탐색을 지원한다.


## buttons: [[label: String, callback: Callable], ...]
static func make_dialog(title: String, body: String, buttons: Array) -> Control:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)

	var panel := PanelContainer.new()
	center.add_child(panel)

	var margin := MarginContainer.new()
	for side in ["margin_left", "margin_right", "margin_top", "margin_bottom"]:
		margin.add_theme_constant_override(side, 12)
	panel.add_child(margin)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	margin.add_child(box)

	var title_label := Label.new()
	title_label.text = title
	title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title_label.add_theme_font_size_override("font_size", 20)
	box.add_child(title_label)

	if not body.is_empty():
		var body_label := Label.new()
		body_label.text = body
		body_label.custom_minimum_size = Vector2(300, 0)
		body_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		body_label.add_theme_font_size_override("font_size", 12)
		box.add_child(body_label)

	var first: Button = null
	for entry in buttons:
		var button := Button.new()
		button.text = entry[0]
		button.pressed.connect(entry[1])
		box.add_child(button)
		if first == null:
			first = button
	if first != null:
		first.call_deferred(&"grab_focus")
	return root


static func make_bar(fill: Color, size: Vector2) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.show_percentage = false
	bar.custom_minimum_size = size
	var fill_style := StyleBoxFlat.new()
	fill_style.bg_color = fill
	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = Color(0, 0, 0, 0.6)
	bar.add_theme_stylebox_override("fill", fill_style)
	bar.add_theme_stylebox_override("background", bg_style)
	return bar
