class_name SpawnMarker
extends Node2D
## 적 등장 예고 표시. 잠시 뒤 그 자리에 적이 생성된다.

const WARN_TIME := 0.8

var enemy_data: EnemyData
var arena: Arena
var hp_mult := 1.0
var damage_mult := 1.0

var _time_left := WARN_TIME


func setup(data: EnemyData, owner_arena: Arena, hp_multiplier: float, damage_multiplier: float) -> void:
	enemy_data = data
	arena = owner_arena
	hp_mult = hp_multiplier
	damage_mult = damage_multiplier


func _ready() -> void:
	add_to_group(&"transient")


func _physics_process(delta: float) -> void:
	_time_left -= delta
	queue_redraw()
	if _time_left <= 0.0:
		arena.spawn_enemy(enemy_data, global_position, hp_mult, damage_mult)
		queue_free()


func _draw() -> void:
	var color := Color(0.9, 0.15, 0.15, 0.4 + 0.6 * float(int(_time_left * 10.0) % 2))
	draw_line(Vector2(-5, -5), Vector2(5, 5), color, 2.0)
	draw_line(Vector2(-5, 5), Vector2(5, -5), color, 2.0)
