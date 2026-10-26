extends Node
## 키보드/마우스와 게임패드 입력 액션을 런타임에 등록한다.
## project.godot 의 InputMap 을 직접 편집하지 않아도 되도록 코드로 관리한다.

const DEADZONE := 0.2


func _ready() -> void:
	_register(&"move_left", [KEY_A, KEY_LEFT], [[JOY_AXIS_LEFT_X, -1.0]], [JOY_BUTTON_DPAD_LEFT])
	_register(&"move_right", [KEY_D, KEY_RIGHT], [[JOY_AXIS_LEFT_X, 1.0]], [JOY_BUTTON_DPAD_RIGHT])
	_register(&"move_up", [KEY_W, KEY_UP], [[JOY_AXIS_LEFT_Y, -1.0]], [JOY_BUTTON_DPAD_UP])
	_register(&"move_down", [KEY_S, KEY_DOWN], [[JOY_AXIS_LEFT_Y, 1.0]], [JOY_BUTTON_DPAD_DOWN])
	_register(&"ultimate", [KEY_SPACE], [], [JOY_BUTTON_RIGHT_SHOULDER, JOY_BUTTON_Y])
	_register(&"pause", [KEY_ESCAPE], [], [JOY_BUTTON_START])


func _register(action: StringName, keys: Array, axes: Array, buttons: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, DEADZONE)
	for keycode in keys:
		var key_event := InputEventKey.new()
		key_event.physical_keycode = keycode
		InputMap.action_add_event(action, key_event)
	for axis in axes:
		var motion := InputEventJoypadMotion.new()
		motion.axis = axis[0]
		motion.axis_value = axis[1]
		InputMap.action_add_event(action, motion)
	for button in buttons:
		var button_event := InputEventJoypadButton.new()
		button_event.button_index = button
		InputMap.action_add_event(action, button_event)
