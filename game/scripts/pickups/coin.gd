class_name Coin
extends Node2D
## 데나리우스. 플레이어가 가까이 가면 끌려와 획득된다.

const MAGNET_RANGE := 60.0
const PICKUP_RANGE := 8.0
const PULL_SPEED := 280.0

var value := 1
var arena: Arena

var _pulled := false


func _ready() -> void:
	add_to_group(&"coins")


func _physics_process(delta: float) -> void:
	var player := arena.player
	if not player.is_alive():
		return
	var to_player := player.global_position - global_position
	if to_player.length() <= PICKUP_RANGE:
		collect()
		return
	if _pulled or to_player.length() <= MAGNET_RANGE:
		_pulled = true
		position += to_player.normalized() * PULL_SPEED * delta


func collect() -> void:
	RunState.add_coins(value)
	queue_free()


func _draw() -> void:
	var points := PackedVector2Array([Vector2(0, -3), Vector2(3, 0), Vector2(0, 3), Vector2(-3, 0)])
	draw_colored_polygon(points, Color(1.0, 0.82, 0.25))
