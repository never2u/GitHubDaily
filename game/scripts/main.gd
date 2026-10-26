extends Node
## 게임 진입점: 클래스 선택 → 전투(Arena) → 결과 → 클래스 선택.

const CLASSES: Array[ClassData] = [
	preload("res://data/classes/swordsman.tres"),
	preload("res://data/classes/archer.tres"),
]

var _arena: Arena
var _ui: CanvasLayer
var _menu: Control


func _ready() -> void:
	_ui = CanvasLayer.new()
	add_child(_ui)
	_show_class_select()


func _show_class_select() -> void:
	var lines: PackedStringArray = []
	var buttons: Array = []
	for class_data in CLASSES:
		lines.append("■ %s\n%s" % [class_data.display_name, class_data.description])
		buttons.append([class_data.display_name, _start_run.bind(class_data)])
	_menu = UiKit.make_dialog("크로노 글래디에이터 — M0", "클래스를 선택하세요.\n\n" + "\n\n".join(lines), buttons)
	_ui.add_child(_menu)


func _start_run(class_data: ClassData) -> void:
	_menu.queue_free()
	_arena = Arena.new()
	_arena.class_data = class_data
	_arena.run_finished.connect(_on_run_finished)
	add_child(_arena)


func _on_run_finished(_victory: bool, _wave: int) -> void:
	_arena.queue_free()
	_arena = null
	_show_class_select()
