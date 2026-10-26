extends Node
## 현재 런(한 판)의 진행 상태.

var class_data: ClassData
var coins: int = 0
var wave: int = 0


func start_run(selected_class: ClassData) -> void:
	class_data = selected_class
	coins = 0
	wave = 0
	EventBus.coins_changed.emit(coins)


func add_coins(amount: int) -> void:
	coins += amount
	EventBus.coins_changed.emit(coins)
